"""
test_regression_integrity.py — Keeps the regression tiers honest.

The regression tiers only mean something if the rules in `regressions.json` are
actually enforced. Without these checks, the failure mode is silent and nasty: a
new test lands with no feature marker, or a feature quietly has no smoke test,
and the smoke tier keeps reporting green while covering less and less.

These checks run against the live pytest session, so they cannot go stale the way
a hand-maintained list of test names would.
"""

import pytest

#: Feature statuses that are exempt from "must have at least one test".
#: See `status_values` in regressions.json.
UNTESTED_OK = {"planned"}


@pytest.mark.smoke
@pytest.mark.feature("packaging")
def test_regressions_json_is_well_formed(regressions):
    """The regression definition parses and declares both required tiers."""
    assert set(regressions["tiers"]) == {"smoke", "static"}, (
        "regressions.json must define exactly the smoke and static tiers"
    )
    ids = [f["id"] for f in regressions["features"]]
    assert len(ids) == len(set(ids)), f"duplicate feature ids: {ids}"

    known_statuses = set(regressions["status_values"])
    for f in regressions["features"]:
        assert f["status"] in known_statuses, (
            f"feature {f['id']!r} has unknown status {f['status']!r}; "
            f"expected one of {sorted(known_statuses)}"
        )


@pytest.mark.feature("packaging")
def test_every_test_declares_a_known_feature(all_collected_items, regressions):
    """Every test carries @pytest.mark.feature(<known id>).

    A test with no feature marker belongs to no feature, so it can never be
    accounted for in the smoke tier or traced back to the testplan.
    """
    known = {f["id"] for f in regressions["features"]}
    unmarked = []
    unknown = []

    for item in all_collected_items:
        marker = item.get_closest_marker("feature")
        if marker is None:
            unmarked.append(item.nodeid)
            continue
        fid = marker.args[0] if marker.args else None
        if fid not in known:
            unknown.append(f"{item.nodeid} -> {fid!r}")

    assert not unmarked, (
        "these tests have no @pytest.mark.feature(...) and so belong to no "
        "regression feature:\n  " + "\n  ".join(unmarked)
    )
    assert not unknown, (
        "these tests name a feature that is not declared in regressions.json:\n  "
        + "\n  ".join(unknown)
    )


@pytest.mark.feature("packaging")
def test_every_tested_feature_has_a_smoke_test(all_collected_items, regressions):
    """Every feature that has tests has at least one smoke test.

    This is what makes the smoke tier's promise -- "one basic test per feature"
    -- true by construction rather than by convention.
    """
    tests_by_feature = {}
    smoke_by_feature = {}

    for item in all_collected_items:
        marker = item.get_closest_marker("feature")
        if marker is None or not marker.args:
            continue  # reported by test_every_test_declares_a_known_feature
        fid = marker.args[0]
        tests_by_feature.setdefault(fid, []).append(item.nodeid)
        if item.get_closest_marker("smoke") is not None:
            smoke_by_feature.setdefault(fid, []).append(item.nodeid)

    missing = sorted(set(tests_by_feature) - set(smoke_by_feature))
    assert not missing, (
        "these features have tests but no @pytest.mark.smoke test, so the smoke "
        f"tier does not exercise them at all: {missing}"
    )


@pytest.mark.feature("packaging")
def test_declared_features_are_actually_tested(all_collected_items, regressions):
    """A feature declared as tested must really have tests.

    Guards the opposite drift from the check above: a feature whose status claims
    coverage while no test references it.
    """
    tested = set()
    for item in all_collected_items:
        marker = item.get_closest_marker("feature")
        if marker is not None and marker.args:
            tested.add(marker.args[0])

    claimed_but_untested = [
        f["id"]
        for f in regressions["features"]
        if f["status"] not in UNTESTED_OK and f["id"] not in tested
    ]
    assert not claimed_but_untested, (
        "these features claim a tested status in regressions.json but no test "
        f"declares them: {claimed_but_untested}. Either add tests or set their "
        f"status to one of {sorted(UNTESTED_OK)}."
    )
