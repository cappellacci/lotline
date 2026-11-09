"""Shared test fixtures."""

import pytest

from lotline.validation import holdout


@pytest.fixture
def v5_blind(monkeypatch):
    """The NC holdout registry with V5-NC-CHARLOTTE still blind.

    V5 was scored and released on 2026-11-09 (D-071), so the live config no longer hides Charlotte's outcomes.
    Adapter tests that check the filter itself use Charlotte as their example; they run against the blind
    registry, as the filter behaves for any test that is not yet released."""
    real = holdout.holdouts_for

    def blind(state):
        hs = real(state)
        if state.upper() != "NC":
            return hs
        return [h.model_copy(update={"released_on": None, "released_note": None}) for h in hs]

    monkeypatch.setattr(holdout, "holdouts_for", blind)
