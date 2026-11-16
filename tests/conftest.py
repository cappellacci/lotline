"""Shared test fixtures."""

import pytest

from lotline.validation import holdout


@pytest.fixture
def v5_blind(monkeypatch):
    """The holdout registry with every V5 test still blind (Charlotte, NC; St. Paul, MN).

    Both were scored and released (Charlotte 2026-11-09, D-071; St. Paul 2026-11-16, D-098), so the live
    config no longer hides their outcomes. Adapter tests that check the filter itself use them as their
    examples; they run against the blind registry, as the filter behaves for any test not yet released."""
    real = holdout.holdouts_for

    def blind(state):
        return [h.model_copy(update={"released_on": None, "released_note": None}) for h in real(state)]

    monkeypatch.setattr(holdout, "holdouts_for", blind)
