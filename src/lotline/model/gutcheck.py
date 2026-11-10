"""The `historical_floor` scorecard check (WS-NC-GUTCHECK task 6; office hours 2026-11-09, action item 3).

A reform that legalizes more should not forecast less than places already build. For each state and scenario
the check compares the **with-reform** forecast (no-reform baseline + added, gross permits a year, median over
draws) with the **trailing observed average** (the `historical_floor_years` years ending at the data origin)
on the same places and the same unit. Below the floor the row is flagged, not failed (verdict `partial`),
unless config/historical_floor_reasons.yaml gives a reason for that state and scenario; then it passes and
the row carries the reason.

    floor  = mean(observed[origin - k + 1 .. origin])
    value  = median over draws of (with-reform permits over the window / window years)
    ratio  = value / floor; flagged when ratio < 1 and no reason is given

By hand: observed 2023-25 = 146, 109, 123 -> floor 126; with-reform draws averaging 80, 90, 100 a year ->
median 90, ratio 0.71, flagged. Draws averaging 130, 140, 150 -> median 140, ratio 1.11, pass.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from lotline.config import CONFIG_DIR, load_params

CHECK_ID = "historical_floor"
REASONS_FILE = CONFIG_DIR / "historical_floor_reasons.yaml"


def reasons(path: Path = REASONS_FILE) -> dict[str, dict[str, str]]:
    """State -> scenario -> the stated reason a with-reform median may sit below history (may be empty)."""
    if not path.exists():
        return {}
    doc = yaml.safe_load(path.read_text()) or {}
    return {st.upper(): dict(v or {}) for st, v in doc.items()}


def floor(observed: Mapping[int, float] | pd.Series, origin: int, years: int) -> float | None:
    """Mean observed count a year over the `years` years ending at `origin`; None if any year is missing."""
    obs = pd.Series(observed, dtype=float)
    want = range(origin - years + 1, origin + 1)
    if any(y not in obs.index or pd.isna(obs[y]) for y in want):
        return None
    return float(obs.loc[list(want)].mean())


def historical_floor(
    scenario: str,
    with_reform: np.ndarray,
    observed: Mapping[int, float] | pd.Series,
    origin: int,
    *,
    scope: str,
    years: int | None = None,
    reason: str | None = None,
) -> dict:
    """One `results_scorecard` row (without `state`) for one scenario in one state.

    `with_reform`: gross with-reform permits per draw, draws x window years, or 1-D window totals per draw
    (divided by the window's length, `baseline.window`). `observed`: year -> observed count on
    the same places and unit. `scope` names the places compared, for the label.
    """
    k = int(years if years is not None else load_params("aggregate")["historical_floor_years"].value)
    a = np.asarray(with_reform, dtype=float)
    per_year = a.mean(axis=1) if a.ndim == 2 else a / _window_years()
    f = floor(observed, origin, k)
    label = (
        f"With-reform {scenario} permits a year vs the {origin - k + 1}-{origin} observed average ({scope})"
    )
    row = {
        "check_id": f"{CHECK_ID}:{scenario}",
        "label": label,
        "metric": "with-reform median / trailing observed average",
        "target": ">= 1 (flag below, unless a reason is stated)",
        "report_path": "reports/diagnostics/",
    }
    if f is None or f <= 0 or per_year.size == 0:
        return row | {"value": None, "verdict": "not_run", "label": label + ": no observed history"}
    ratio = float(np.median(per_year) / f)
    if ratio >= 1:
        return row | {"value": ratio, "verdict": "pass"}
    if reason:
        return row | {"value": ratio, "verdict": "pass", "label": f"{label}. Below history, reason: {reason}"}
    return row | {"value": ratio, "verdict": "partial", "label": f"{label}. FLAG: below recent history"}


def _window_years() -> int:
    from lotline.model import baseline

    return baseline.window(0)[1]
