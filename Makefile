# pydebug — regression entry points.
#
# Tiers are defined in regressions.json and carried by pytest markers on the
# tests themselves (see tests/conftest.py). Adding a test to the regression is
# a marker, not an edit to a list:
#
#     @pytest.mark.feature("run_control")   -> in the static tier
#     @pytest.mark.smoke                    -> also in the smoke tier
#
# tests/test_regression_integrity.py enforces that policy against the live
# session, so a test cannot silently fall out of a tier.

PYTEST ?= python3 -m pytest
TESTS  ?= tests

.PHONY: help smoke static test regress coverage clean

help:
	@echo "Regression tiers:"
	@echo "  make smoke    One basic test per feature. Fast gate, no simulator."
	@echo "  make static   Every test. Maximum coverage. The sign-off tier."
	@echo ""
	@echo "Other:"
	@echo "  make regress  Run smoke, then static."
	@echo "  make coverage Static tier with the functional-coverage report printed."
	@echo ""
	@echo "Simulator-backed runs live in the per-SoC Makefiles, e.g.:"
	@echo "  make -C ../integration_with_cva6/cva6_sim soc_test"

## smoke — one basic, happy-path test per feature. Seconds, mock-backed only.
smoke:
	$(PYTEST) $(TESTS) -m smoke -v

## static — every test, maximum coverage. Includes coverage closure + invariants.
static:
	$(PYTEST) $(TESTS) -v

## test — alias for the static tier (the default expectation of `make test`).
test: static

## regress — smoke first (fail fast), then the full static tier.
regress: smoke static

## coverage — static tier, showing the functional coverage report.
coverage:
	$(PYTEST) $(TESTS) -v -s -k "coverage"

clean:
	rm -rf .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
