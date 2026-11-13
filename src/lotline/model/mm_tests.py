"""Pass rules for D-082 §7's missing-middle accuracy tests, fixed in code before any test is run.

Each function takes already-scored rows (observed total and predictive P10/P50/P90, or draws) and applies one
rule from the §7 table. The thresholds live in `config/params/mm.yaml` (the `mm_test_*`, `mm_loso_*`,
`mm_placebo_*` and `mm_place_coverage_*` keys); each function takes them as arguments, with those values as
defaults, so tests can pass hand-worked values. Nothing here reads data or fits anything:
`scripts/dev/mm_tests_d082.py` builds the inputs.

- **Test A, new places** (`test_a`): at least 60% of newly entering non-Oregon places inside P10–P90, and the
  median of observed ÷ P50 within ×2.
- **Test C, no-reform floor** (`test_c`): at least 70% of coded "none" places (plus Franklin County) inside
  P10–P90 over 2021–25, and no state total missed.
- **Leave one state out** (`loso`): no state with 3 or more fit places gets D-040's "missed" verdict.
- **Placebo** (`placebo`): the placebo r5's 90% upper bound is below the main r5.
- **Place coverage** (`randomized_pit`, `place_coverage`): randomized P10–P90 coverage. A count's predictive
  CDF jumps at the observed value, so the PIT is drawn uniformly between F(y − 1) and F(y). A place is inside
  if its PIT lies in [0.1, 0.9]. The target is 0.6–0.95, and outside it is flagged.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.model.calibrate_mm import verdict


def _p(name: str) -> float:
    return float(load_params("mm")[name].value)


def inside(observed: float, p10: float, p90: float) -> bool:
    return bool(p10 <= observed <= p90)


def ratio_to_median(observed: float, p50: float) -> float:
    """observed ÷ P50, with 0 ÷ 0 = 1 (both zero meets the bar, as D-040) and x ÷ 0 = inf."""
    if p50 == 0:
        return 1.0 if observed == 0 else float("inf")
    return float(observed / p50)


def test_a(rows: pd.DataFrame, *, coverage: float | None = None, factor: float | None = None) -> dict:
    """rows: observed, p10, p50, p90 per new place. Pass: share inside ≥ coverage and the median of
    observed ÷ P50 in [1 / factor, factor]."""
    coverage = _p("mm_test_a_coverage") if coverage is None else coverage
    factor = _p("mm_test_a_ratio") if factor is None else factor
    if rows.empty:
        return {"places": 0, "share_inside": np.nan, "median_ratio": np.nan, "pass": None}
    ins = [inside(o, a, b) for o, a, b in zip(rows["observed"], rows["p10"], rows["p90"], strict=True)]
    ratios = [ratio_to_median(o, m) for o, m in zip(rows["observed"], rows["p50"], strict=True)]
    share, med = float(np.mean(ins)), float(np.median(ratios))
    ok = share >= coverage and 1 / factor <= med <= factor
    return {"places": len(rows), "share_inside": share, "median_ratio": med, "pass": bool(ok)}


def test_c(rows: pd.DataFrame, state_rows: pd.DataFrame, *, coverage: float | None = None) -> dict:
    """rows: observed, p10, p90 per no-reform place; state_rows: state, observed, p10, p90 of each state's
    total. Pass: share inside ≥ coverage and every state total inside P10–P90."""
    coverage = _p("mm_test_c_coverage") if coverage is None else coverage
    if rows.empty:
        return {"places": 0, "share_inside": np.nan, "states_missed": [], "pass": None}
    ins = [inside(o, a, b) for o, a, b in zip(rows["observed"], rows["p10"], rows["p90"], strict=True)]
    missed = [
        s
        for s, o, a, b in zip(
            state_rows["state"], state_rows["observed"], state_rows["p10"], state_rows["p90"], strict=True
        )
        if not inside(o, a, b)
    ]
    share = float(np.mean(ins))
    return {"places": len(rows), "share_inside": share, "states_missed": missed,
            "pass": bool(share >= coverage and not missed)}  # fmt: skip


def loso(state_rows: pd.DataFrame, *, min_places: float | None = None) -> dict:
    """state_rows: state, fit_places, observed, p10, p50, p90 per held-out state total. Each gets D-040's
    verdict; the test fails if a state with at least `min_places` fit places is 'missed'."""
    min_places = _p("mm_loso_min_places") if min_places is None else min_places
    v = [
        verdict(o, a, m, b)
        for o, a, m, b in zip(
            state_rows["observed"], state_rows["p10"], state_rows["p50"], state_rows["p90"], strict=True
        )
    ]
    out = state_rows.assign(verdict=v)
    bad = out[(out["fit_places"] >= min_places) & (out["verdict"] == "missed")]["state"].tolist()
    return {"verdicts": dict(zip(out["state"], out["verdict"], strict=True)), "failed_states": bad,
            "pass": not bad}  # fmt: skip


def placebo(placebo_high: float, main_r5: float) -> dict:
    """Pass if the placebo r5's 90% upper bound is below the main r5."""
    return {"placebo_high": placebo_high, "main_r5": main_r5, "pass": bool(placebo_high < main_r5)}


def randomized_pit(draws: np.ndarray, observed: float, rng: np.random.Generator) -> float:
    """A uniform draw between F(y − 1) and F(y) of the predictive draws. By hand: draws [0, 1, 1, 2], y = 1 →
    F(0) = 0.25, F(1) = 0.75, so the PIT is uniform on [0.25, 0.75]."""
    d = np.asarray(draws)
    lo, hi = float(np.mean(d < observed)), float(np.mean(d <= observed))
    return lo + rng.uniform() * (hi - lo)


def place_coverage(pits: Sequence[float], *, low: float | None = None, high: float | None = None) -> dict:
    """Share of PITs in [0.1, 0.9], flagged if outside the target [low, high]."""
    low = _p("mm_place_coverage_low") if low is None else low
    high = _p("mm_place_coverage_high") if high is None else high
    p = np.asarray(list(pits), dtype=float)
    if not len(p):
        return {"places": 0, "coverage": np.nan, "flag": None}
    cov = float(np.mean((p >= 0.1) & (p <= 0.9)))
    return {"places": int(len(p)), "coverage": cov, "flag": not (low <= cov <= high)}
