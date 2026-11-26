"""V1's yardsticks for the baseline (validation plan V1; split out of `model/baseline.py` in modularity plan
step 3): the two benchmarks the baseline must beat, and the scores that compare a forecast's draws with what
was built.

- **Last-k mean:** every forecast year gets the mean of the k years ending at the origin
  (k = `benchmark_mean_years`). If any of those k years is missing, the forecast is missing.
- **Linear trend:** ordinary least squares of the value on the year over the fit window, extended to each
  forecast year: `ŷ(t) = a + b·t`, with `b = Σ(t − t̄)(y − ȳ) / Σ(t − t̄)²` and `a = ȳ − b·t̄`. Permits can't
  be negative, so the line is floored at 0. Needs at least two observed years.
- **Scores:** `randomized_coverage` (P10-P90 coverage for counts), `pit_step` and `step_share` (the PIT
  histogram), `crps_from_draws`.

Both benchmarks are pure functions of one place's history up to a forecast origin, so a backtest can never
see a year after the origin. They use the baseline's own window (`baseline.window`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from lotline.config import Parameter, load_params
from lotline.model.baseline import _history, _years, window

BENCHMARKS = ("last_k_mean", "linear_trend")


def last_k_mean(series: pd.Series, origin: int, k: int, horizon: int, lead: int = 0) -> pd.Series:
    """Mean of the k years ending at `origin`, repeated for each of the `horizon` years after `lead`."""
    hist = _history(series, origin, first_year=origin - k + 1)
    value = hist.mean() if len(hist) == k else float("nan")
    return pd.Series(value, index=_years(origin, horizon, lead), dtype=float)


def linear_trend(
    series: pd.Series, origin: int, horizon: int, first_year: int | None = None, lead: int = 0
) -> pd.Series:
    """OLS line of value on year over [first_year, origin] (all history if None), floored at 0."""
    hist = _history(series, origin, first_year)
    years = _years(origin, horizon, lead)
    if len(hist) < 2:
        return pd.Series(float("nan"), index=years, dtype=float)
    t = hist.index.to_series().astype(float)
    t_bar, y_bar = t.mean(), hist.mean()
    slope = ((t - t_bar) * (hist.values - y_bar)).sum() / ((t - t_bar) ** 2).sum()
    intercept = y_bar - slope * t_bar
    return pd.Series(intercept + slope * years.to_numpy(dtype=float), index=years).clip(lower=0.0)


def benchmark_forecasts(
    panel: pd.DataFrame,
    value: str,
    origin: int,
    *,
    trend_first_year: int | None = None,
    params: dict[str, Parameter] | None = None,
    key: str = "geoid",
) -> pd.DataFrame:
    """Both benchmarks for every jurisdiction in a panel -> long table (key, year, benchmark, forecast).

    `value` is a numerator column of the panel (e.g. `units_1`). Only rows with year <= origin are used.
    """
    p = params or load_params("baseline")
    k = int(p["benchmark_mean_years"].value)
    lead, horizon, _ = window(origin, p)
    out = []
    for geoid, g in panel[panel["year"] <= origin].groupby(key, sort=True):
        series = g.set_index("year")[value]
        for name, fc in (
            ("last_k_mean", last_k_mean(series, origin, k, horizon, lead)),
            ("linear_trend", linear_trend(series, origin, horizon, trend_first_year, lead)),
        ):
            out.append(pd.DataFrame({key: geoid, "year": fc.index, "benchmark": name, "forecast": fc.values}))
    columns = [key, "year", "benchmark", "forecast"]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=columns)


def randomized_coverage(draws: np.ndarray, observed: np.ndarray, low: float, high: float) -> np.ndarray:
    """Chance that a whole-number outcome falls in the central [low, high] band, randomizing within its step.

    For counts, "inside P10-P90" is ambiguous when the forecast puts, say, 95% on 0. The predictive CDF jumps
    from F(y−) = P(Y < y) to F(y) = P(Y <= y) at the observed y; treating the PIT as uniform on that step,
    the outcome counts as covered by the share of [F(y−), F(y)] that lies inside [low, high]
    (non-randomized PIT, Czado, Gneiting & Held 2009). A calibrated forecast then covers 80% on average.

    By hand: draws 0,0,0,1 (F(0−) = 0, F(0) = 0.75), y = 0, band [0.1, 0.9]: overlap 0.75 − 0.1 = 0.65,
    coverage 0.65 / 0.75 = 0.867. y = 1: step [0.75, 1.0], overlap 0.9 − 0.75 = 0.15, coverage 0.6.
    """
    f_minus, f = pit_step(draws, observed)
    return step_share(f_minus, f, low, high)


def pit_step(draws: np.ndarray, observed: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """F(y−) = P(Y < y) and F(y) = P(Y <= y) of each row's draws at its observed y: the PIT's step."""
    y = np.asarray(observed, dtype=float)[:, None]
    return (draws < y).mean(axis=1), (draws <= y).mean(axis=1)


def step_share(f_minus: np.ndarray, f: np.ndarray, low: float, high: float) -> np.ndarray:
    """Share of each PIT step [F(y−), F(y)] inside [low, high] (a point step counts 1 if inside, else 0).

    With [low, high] = a PIT decile, the mean over outcomes is that decile's height in the non-randomized PIT
    histogram (Czado, Gneiting & Held 2009); a calibrated forecast puts 0.1 in each.
    """
    width = f - f_minus
    overlap = np.clip(np.minimum(f, high) - np.maximum(f_minus, low), 0.0, None)
    inside = ((f_minus >= low) & (f_minus <= high)).astype(float)
    return np.where(width > 0, overlap / np.where(width > 0, width, 1.0), inside)


def crps_from_draws(draws: np.ndarray, observed: np.ndarray) -> np.ndarray:
    """CRPS of each row's empirical predictive distribution: E|X − y| − ½ E|X − X'| (lower is better).

    E|X − X'| over all n² ordered pairs, from the sorted draws: Σ_i Σ_j |x_i − x_j| = 2 Σ_i (2i − n + 1) x_(i)
    (i = 0 … n − 1). By hand: draws 0, 2 and y = 1: E|X − y| = 1, Σ|x_i − x_j| = 4, so CRPS = 1 − 4 / 8 = 0.5,
    the same as ∫ (F(x) − 1[x ≥ y])² dx = 0.25 · 1 + 0.25 · 1.
    """
    x = np.sort(np.asarray(draws, dtype=float), axis=-1)
    y = np.asarray(observed, dtype=float)[:, None]
    n = x.shape[-1]
    weights = 2 * np.arange(n) - n + 1
    return np.abs(x - y).mean(axis=-1) - (x * weights).sum(axis=-1) / n**2
