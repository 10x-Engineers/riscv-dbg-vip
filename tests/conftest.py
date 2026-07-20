"""
conftest.py — Shared fixtures and regression-tier wiring for the pydebug suite.

Regression tiers are defined in `pydebug/regressions.json` and carried on the
tests themselves by markers, so a test cannot silently drop out of the regression
because a manifest went stale:

    @pytest.mark.feature("run_control")   # -> in the STATIC tier
    @pytest.mark.smoke                    # -> ALSO in the SMOKE tier

    smoke   pytest -m smoke     one basic test per feature; fast, no simulator
    static  pytest              every test; maximum coverage

`tests/test_regression_integrity.py` enforces the policy in regressions.json
against the live session (e.g. every implemented feature has a smoke test, every
test declares a known feature).
"""

import json
from pathlib import Path

import pytest

#: Repository-relative path to the regression definition.
REGRESSIONS_JSON = Path(__file__).resolve().parents[1] / "regressions.json"


def load_regressions() -> dict:
    """The parsed regression definition (tiers, features, policy)."""
    with REGRESSIONS_JSON.open() as fh:
        return json.load(fh)


def feature_ids() -> set:
    return {f["id"] for f in load_regressions()["features"]}


#: Every test collected this session, captured *before* marker deselection so the
#: integrity checks still see the whole suite when running `pytest -m smoke`.
ALL_COLLECTED_ITEMS = []


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(session, config, items):
    ALL_COLLECTED_ITEMS.clear()
    ALL_COLLECTED_ITEMS.extend(items)


@pytest.fixture
def all_collected_items():
    """Every test collected this session (pre-deselection)."""
    return list(ALL_COLLECTED_ITEMS)


@pytest.fixture
def regressions():
    """The parsed regressions.json definition."""
    return load_regressions()


def pytest_configure(config):
    """Register the tier markers so `--strict-markers` accepts them."""
    config.addinivalue_line(
        "markers",
        "smoke: the one basic, happy-path test for a feature. Runs in the smoke tier.",
    )
    config.addinivalue_line(
        "markers",
        "feature(id): the regressions.json feature this test belongs to. Required on every test.",
    )
    config.addinivalue_line(
        "markers",
        "sim: requires a live simulator; excluded from the mock-only tiers.",
    )


# ── Shared fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def predictor():
    """A fresh golden-reference predictor with the DM already activated."""
    from pydebug.model import DMCONTROL, DMPredictor

    p = DMPredictor()
    p.on_write(DMCONTROL.address, DMCONTROL.encode(dmactive=1))
    return p


@pytest.fixture
def model_dm():
    """(dm, transport) on the spec-accurate, model-backed mock — no simulator.

    Unlike the ad-hoc MockTransport in test_riscv_dm.py, every modeled register
    read here is computed by DMPredictor from spec semantics, so assertions about
    resume-ack, havereset stickiness and ndmresetpending are meaningful.
    """
    from pydebug.api.riscv_dm import RISCVDebug
    from pydebug.model import ModelBackedMockTransport

    t = ModelBackedMockTransport()
    t.connect()
    return RISCVDebug(t), t


@pytest.fixture
def observed_dm():
    """(dm, transport, observations) — a model-backed DM with every DMI
    transaction recorded, for coverage/invariant tests.
    """
    from pydebug.api.observer import ObservingTransport
    from pydebug.api.riscv_dm import RISCVDebug
    from pydebug.model import ModelBackedMockTransport

    backend = ModelBackedMockTransport()
    observations = []
    t = ObservingTransport(backend)
    t.add_observer(lambda op, addr, data, readback: observations.append((op, addr, data, readback)))
    t.connect()
    return RISCVDebug(t), backend, observations
