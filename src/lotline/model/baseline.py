"""Baseline ("what gets built with no policy change"). For now: the two benchmarks V1 must beat.

Validation plan V1: the baseline must beat (a) the last-3-year average and (b) a simple trend on mean
absolute error. Both are written here as pure functions of one place's history up to a forecast origin, so a
backtest can never see a year after the origin.

- **Last-k mean:** every forecast year gets the mean of the k years ending at the origin
  (k = `benchmark_mean_years`). If any of those k years is missing, the forecast is missing.
- **Linear trend:** ordinary least squares of the value on the year over the fit window, extended to each
  forecast year: `ŷ(t) = a + b·t`, with `b = Σ(t − t̄)(y − ȳ) / Σ(t − t̄)²` and `a = ȳ − b·t̄`. Permits can't
  be negative, so the line is floored at 0. Needs at least two observed years.

Both forecast counts (the numerator); rates per 1,000 eligible parcels are formed only at evaluation, from the
panel's separate denominator. The horizon comes from `forecast_horizon_years` (config/params/baseline.yaml).
"""

from __future__ import annotations

import pandas as pd

from lotline.config import Parameter, load_params

BENCHMARKS = ("last_k_mean", "linear_trend")


def _history(series: pd.Series, origin: int, first_year: int | None = None) -> pd.Series:
    """Observed values (year -> value) up to and including the origin; missing values dropped."""
    s = series.dropna()
    s.index = s.index.astype(int)
    keep = s.index <= origin
    if first_year is not None:
        keep &= s.index >= first_year
    return s[keep].astype(float).sort_index()


def _years(origin: int, horizon: int) -> pd.Index:
    return pd.Index(range(origin + 1, origin + horizon + 1), name="year")


def last_k_mean(series: pd.Series, origin: int, k: int, horizon: int) -> pd.Series:
    """Mean of the k years ending at `origin`, repeated for each of the next `horizon` years."""
    hist = _history(series, origin, first_year=origin - k + 1)
    value = hist.mean() if len(hist) == k else float("nan")
    return pd.Series(value, index=_years(origin, horizon), dtype=float)


def linear_trend(series: pd.Series, origin: int, horizon: int, first_year: int | None = None) -> pd.Series:
    """OLS line of value on year over [first_year, origin] (all history if None), floored at 0."""
    hist = _history(series, origin, first_year)
    years = _years(origin, horizon)
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
    horizon = int(p["forecast_horizon_years"].value)
    out = []
    for geoid, g in panel[panel["year"] <= origin].groupby(key, sort=True):
        series = g.set_index("year")[value]
        for name, fc in (
            ("last_k_mean", last_k_mean(series, origin, k, horizon)),
            ("linear_trend", linear_trend(series, origin, horizon, trend_first_year)),
        ):
            out.append(pd.DataFrame({key: geoid, "year": fc.index, "benchmark": name, "forecast": fc.values}))
    columns = [key, "year", "benchmark", "forecast"]
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=columns)
