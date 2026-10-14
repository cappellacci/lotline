"""Baseline ("what gets built with no policy change"): the model and the two benchmarks V1 must beat.

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

**The baseline model** (`baseline_forecast`), in plain words: each place keeps building at its own recent
pace, pulled toward its neighbours' pace when its own record is too short or too small to trust, and the range
around that reflects lumpy years and the regional building cycle. Per place and size class, with r a rate per
1,000 eligible parcels and `level_years` = m:

1. **Recent level (direct estimate).** y_i = 1000 · Σ units / Σ eligible parcels over the m years ending at
   the origin (a ratio of sums, so a place's size weights its own years).
2. **Shrinkage (Fay-Herriot, protocol §5.7).** The group rate ḡ is the same ratio of sums over all places
   in the place's county (or the state, if the county has fewer than `min_group_places` places). Annual
   counts are treated as negative binomial, Var(c) = λ + λ²/k, with 1/k estimated by pooled moments
   (`nb_inverse_dispersion`). The sampling variance of y_i uses the group-smoothed mean count
   λ_i = ḡ · P̄_i / 1000 (P̄_i = mean eligible parcels): v_i = 10⁶ / P̄_i² · (λ_i + λ_i²/k) / m, raised
   to the place's own observed variance of annual rates / m when that is larger (`use_direct_variance`), so
   one subdivision year in a 40-parcel township counts as noise, not as its pace.
   The between-place variance A = max(0, mean (y_i − ḡ)² − mean v_i) (moments, per state), the weight
   B_i = v_i / (v_i + A), and the shrunk level μ_i = (1 − B_i) · y_i + B_i · ḡ with posterior variance
   (1 − B_i) · v_i. Big places (small v_i) keep their own rate; small places move toward the group's.
3. **Range (P10/P50/P90), by simulation** (`simulation_draws`, fixed `simulation_seed`), from three sources:
   the true level is drawn from a gamma with mean μ_i and the posterior variance; the regional cycle
   multiplies it by exp(sum of h resampled, demeaned year-to-year log changes in the state's total permits
   over the `cycle_history_years` before the origin), a random walk, so the band widens with the horizon;
   and the year's count is negative binomial around that. The point forecast is the median (P50), which is
   what minimises mean absolute error; `mean` is reported too, because means add up to state totals.

4. **Optional regional cycle term** (`use_state_momentum`): every place's level is scaled by the state's pace
   over the last `momentum_recent_years` relative to its pace over the level window (`state_momentum`).
   Off by default: the V1 backtest decides whether it earns its place.
"""

from __future__ import annotations

import numpy as np
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


# ---------------------------------------------------------------------------------------------------------
# The baseline model
# ---------------------------------------------------------------------------------------------------------

PER = 1000.0  # unit conversion: rates are per 1,000 eligible parcels
PARCELS = "eligible_parcels"
SIZE_CLASSES = ("1", "2", "3_4", "5p")


def outcome_column(size_class: str, reported_only: bool) -> str:
    """Panel column for a size class: BPS reported units (`units_1_rep`) or totals incl. imputation."""
    if size_class not in SIZE_CLASSES:
        raise ValueError(f"size class {size_class!r} not in {SIZE_CLASSES}")
    return f"units_{size_class}" + ("_rep" if reported_only else "")


def nb_inverse_dispersion(counts: list[np.ndarray]) -> float:
    """Pooled moment estimate of 1/k for Var(c) = λ + λ²/k from each place's annual counts.

    1/k = max(0, Σ_i (s_i² − c̄_i) / Σ_i c̄_i²), with s_i² the sample variance (ddof 1) of place i's counts and
    c̄_i their mean. 0 means Poisson. Places with fewer than two years or a zero mean carry no information.
    """
    excess = scale = 0.0
    for c in counts:
        c = np.asarray(c, dtype=float)
        if len(c) < 2 or c.mean() == 0:
            continue
        excess += c.var(ddof=1) - c.mean()
        scale += c.mean() ** 2
    return max(0.0, excess / scale) if scale > 0 else 0.0


def fay_herriot(
    direct: np.ndarray, sampling_var: np.ndarray, group_mean: np.ndarray
) -> tuple[float, np.ndarray]:
    """Between-place variance A and shrinkage weights B_i = v_i / (v_i + A) toward the group mean.

    A = max(0, mean (y_i − ḡ_i)² − mean v_i), the method-of-moments estimate: the spread of the direct
    estimates around their group means, less the part that sampling noise alone would produce.

    Two places, worked by hand: y = (10, 2), ḡ = (5, 5), v = (1, 9).
    mean (y − ḡ)² = (25 + 9) / 2 = 17; mean v = 5; A = 12.
    B = (1/13, 9/21) = (0.0769, 0.4286). Shrunk: 10 − 0.0769·5 = 9.615 and 2 + 0.4286·3 = 3.286.
    The precise place barely moves; the noisy one moves 43% of the way to its group.
    """
    y, v, g = (np.asarray(a, dtype=float) for a in (direct, sampling_var, group_mean))
    if len(y) == 0:
        return 0.0, np.array([])
    a = max(0.0, float(np.mean((y - g) ** 2) - np.mean(v)))
    total = v + a
    b = np.divide(v, total, out=np.zeros_like(v), where=total > 0)
    return a, b


def _group_keys(places: pd.DataFrame, group: str, min_places: int) -> pd.Series:
    """Each place's shrinkage group: its `group` value, or the state when that group is missing or small."""
    state = "state:" + places["state"].astype(str)
    if group == "state":
        return state
    key = places[group].astype("string")
    size = key.map(key.value_counts())
    small = key.isna() | (size < min_places).fillna(True).astype(bool)
    return (group + ":" + key.astype(str)).where(~small, state)


def level_estimates(
    panel: pd.DataFrame,
    value: str,
    origin: int,
    *,
    level_years: int,
    min_group_places: int,
    group: str = "county_geoid",
    use_direct_variance: bool = True,
    key: str = "geoid",
) -> pd.DataFrame:
    """Step 1-2 of the model: each place's direct rate, its group rate, and the Fay-Herriot shrunk rate.

    Uses only rows with year in [origin − level_years + 1, origin]; a place needs all of those years with both
    a count and a positive denominator. One row per place.
    """
    first = origin - level_years + 1
    w = panel[(panel["year"] >= first) & (panel["year"] <= origin)]
    w = w[w[value].notna() & (w[PARCELS].astype(float) > 0)]
    cols = [key, "state"] + ([group] if group not in ("state", key) else [])
    agg = w.groupby(key, sort=True).agg(
        years=("year", "nunique"), units=(value, "sum"), parcels_sum=(PARCELS, "sum")
    )
    meta = w.sort_values("year").groupby(key).last()[[c for c in cols if c != key]]
    places = agg.join(meta)
    places = places[places["years"] == level_years].copy()
    if places.empty:
        return places.assign(direct=[], group_rate=[], v=[], a=[], b=[], level=[], level_var=[], inv_k=[])
    places["parcels_mean"] = places["parcels_sum"].astype(float) / level_years
    origin_p = w[w["year"] == origin].set_index(key)[PARCELS].astype(float)
    places["parcels_origin"] = origin_p.reindex(places.index)
    places["direct"] = PER * places["units"].astype(float) / places["parcels_sum"].astype(float)
    places["group"] = _group_keys(places.reset_index(), group, min_group_places).to_numpy()
    sums = places.groupby("group")[["units", "parcels_sum"]].transform("sum").astype(float)
    state_sums = places.groupby("state")[["units", "parcels_sum"]].transform("sum").astype(float)
    sums = sums.where(~places["group"].str.startswith("state:"), state_sums)  # fallback = whole state
    places["group_rate"] = PER * sums["units"] / sums["parcels_sum"]

    counts = w[w[key].isin(places.index)].groupby(key)[value]
    annual = PER * w[value].astype(float) / w[PARCELS].astype(float)
    places["v_direct"] = annual.groupby(w[key]).var(ddof=1).reindex(places.index).fillna(0.0) / level_years
    out = []
    for _state, p in places.groupby("state"):
        inv_k = nb_inverse_dispersion([counts.get_group(g).to_numpy() for g in p.index])
        lam = p["group_rate"] * p["parcels_mean"] / PER
        v = PER**2 / p["parcels_mean"] ** 2 * (lam + lam**2 * inv_k) / level_years
        if use_direct_variance:
            v = np.maximum(v, p["v_direct"])
        a, b = fay_herriot(p["direct"].to_numpy(), v.to_numpy(), p["group_rate"].to_numpy())
        out.append(p.assign(v=v, a=a, b=b, inv_k=inv_k))
    places = pd.concat(out)
    places["level"] = (1 - places["b"]) * places["direct"] + places["b"] * places["group_rate"]
    places["level_var"] = (1 - places["b"]) * places["v"]
    return places.reset_index()


def cycle_shocks(
    panel: pd.DataFrame, value: str, origin: int, history_years: int, key: str = "geoid"
) -> np.ndarray:
    """Demeaned year-to-year log changes in the state's total permits, years (origin − history_years, origin].

    Each change compares the same places in both years (a place entering or leaving BPS is not a boom or a
    bust). Changes where either total is 0 are dropped. Demeaned so the cycle widens the range without
    tilting the median.
    """
    h = panel[(panel["year"] > origin - history_years) & (panel["year"] <= origin) & panel[value].notna()]
    wide = h.pivot_table(index=key, columns="year", values=value, aggfunc="sum")
    changes = []
    years = sorted(wide.columns)
    for prev, cur in zip(years[:-1], years[1:], strict=True):
        both = wide[[prev, cur]].dropna()
        a, b = float(both[prev].sum()), float(both[cur].sum())
        if cur == prev + 1 and a > 0 and b > 0:
            changes.append(np.log(b / a))
    x = np.asarray(changes, dtype=float)
    return x - x.mean() if len(x) else x


def state_momentum(
    panel: pd.DataFrame, value: str, origin: int, recent_years: int, level_years: int
) -> float:
    """The state's recent pace relative to its pace over the level window: an optional regional cycle term.

    factor = (Σ units over the last `recent_years` / recent_years) / (Σ units over the last `level_years` /
    level_years), over the places in `panel`. By hand: yearly totals 10, 10, 10, 20, 30 with recent_years 3
    and level_years 5: (60 / 3) / (80 / 5) = 20 / 16 = 1.25, so every place's level is scaled up 25%.
    1.0 when the window has no units.
    """

    def pace(years: int) -> float:
        w = panel[(panel["year"] > origin - years) & (panel["year"] <= origin)]
        return float(w[value].sum()) / years

    base = pace(level_years)
    return pace(recent_years) / base if base > 0 else 1.0


def interval_from_draws(draws: np.ndarray, low: float, high: float) -> tuple[np.ndarray, ...]:
    """P_low, P50, P_high and the mean along the last axis (draws), interpolating between order statistics."""
    q = np.quantile(draws, [low, 0.5, high], axis=-1)
    return q[0], q[1], q[2], draws.mean(axis=-1)


def _simulate(
    places: pd.DataFrame, shocks: np.ndarray, horizon: int, n: int, rng: np.random.Generator
) -> np.ndarray:
    """Count draws, shape (places, horizon, n): gamma level × cycle factor × negative-binomial year."""
    mu = places["level"].to_numpy(dtype=float)
    var = places["level_var"].to_numpy(dtype=float)
    p = places["parcels_origin"].to_numpy(dtype=float)
    inv_k = places["inv_k"].to_numpy(dtype=float)
    ok = (mu > 0) & (var > 0)
    shape = np.where(ok, mu**2 / np.where(ok, var, 1), 1.0)
    scale = np.where(ok, var / np.where(mu > 0, mu, 1), 0.0)
    theta = np.where(ok[:, None], rng.gamma(shape[:, None], scale[:, None], size=(len(mu), n)), mu[:, None])
    if len(shocks):
        cycle = np.exp(rng.choice(shocks, size=(horizon, n)).cumsum(axis=0))
    else:
        cycle = np.ones((horizon, n))
    lam = theta[:, None, :] * cycle[None, :, :] * p[:, None, None] / PER
    k_inv = np.broadcast_to(inv_k[:, None, None], lam.shape)
    nb = k_inv > 0  # gamma-Poisson mixture = negative binomial with mean λ and 1/k = inv_k; else Poisson
    shape = 1 / np.where(nb, k_inv, 1.0)
    mixed = np.where(nb, rng.gamma(shape, lam * k_inv), lam)
    return rng.poisson(mixed).astype(np.int32)


def forecast_draws(
    panel: pd.DataFrame,
    value: str,
    origin: int,
    *,
    group: str = "county_geoid",
    params: dict[str, Parameter] | None = None,
    key: str = "geoid",
) -> tuple[pd.DataFrame, np.ndarray]:
    """`baseline_forecast` plus its simulated counts: draws[i] are the draws behind row i of the table."""
    p = params or load_params("baseline")
    horizon = int(p["forecast_horizon_years"].value)
    n = int(p["simulation_draws"].value)
    low, high = p["interval_low_quantile"].value, p["interval_high_quantile"].value
    rng = np.random.default_rng(int(p["simulation_seed"].value))
    hist = panel[panel["year"] <= origin]
    places = level_estimates(
        hist,
        value,
        origin,
        level_years=int(p["level_years"].value),
        min_group_places=int(p["min_group_places"].value),
        group=group,
        use_direct_variance=bool(p["use_direct_variance"].value),
        key=key,
    )
    columns = [key, "state", "year", "horizon", "parcels_origin", "level", "direct", "group_rate", "b"]
    columns += ["momentum", "mean", "p10", "p50", "p90"]
    tables, all_draws = [], []
    for state, ps in places.groupby("state", sort=True):
        history = int(p["cycle_history_years"].value)
        in_state = hist[(hist["state"] == state) & hist[key].isin(ps[key])]
        factor = 1.0
        if bool(p["use_state_momentum"].value):
            factor = state_momentum(
                in_state, value, origin, int(p["momentum_recent_years"].value), int(p["level_years"].value)
            )
        ps = ps.assign(momentum=factor, level=ps["level"] * factor, level_var=ps["level_var"] * factor**2)
        shocks = cycle_shocks(hist[hist["state"] == state], value, origin, history, key)
        draws = _simulate(ps, shocks, horizon, n, rng)  # (places, horizon, n)
        lo, mid, hi, mean = interval_from_draws(draws, low, high)
        rows = ps.loc[ps.index.repeat(horizon), [key, "state", "parcels_origin", "level", "direct"]]
        rows = rows.assign(group_rate=np.repeat(ps["group_rate"].to_numpy(), horizon))
        rows = rows.assign(b=np.repeat(ps["b"].to_numpy(), horizon), momentum=factor)
        rows["horizon"] = np.tile(np.arange(1, horizon + 1), len(ps))
        rows["year"] = origin + rows["horizon"]
        for name, q in (("mean", mean), ("p10", lo), ("p50", mid), ("p90", hi)):
            rows[name] = q.reshape(-1)
        tables.append(rows[columns])
        all_draws.append(draws.reshape(len(ps) * horizon, n))
    if not tables:
        return pd.DataFrame(columns=columns), np.empty((0, n))
    return pd.concat(tables, ignore_index=True), np.concatenate(all_draws)


def baseline_forecast(
    panel: pd.DataFrame,
    value: str,
    origin: int,
    *,
    group: str = "county_geoid",
    params: dict[str, Parameter] | None = None,
    key: str = "geoid",
) -> pd.DataFrame:
    """The baseline: per place, the next `forecast_horizon_years` of `value` counts as P10/P50/P90 and mean.

    Only rows with year <= origin are used. Long table: key, state, year, horizon, parcels_origin, level
    (shrunk rate per 1,000 parcels), direct, group_rate, b (shrinkage weight), mean, p10, p50, p90.
    """
    table, _ = forecast_draws(panel, value, origin, group=group, params=params, key=key)
    return table


def randomized_coverage(draws: np.ndarray, observed: np.ndarray, low: float, high: float) -> np.ndarray:
    """Chance that a whole-number outcome falls in the central [low, high] band, randomizing within its step.

    For counts, "inside P10-P90" is ambiguous when the forecast puts, say, 95% on 0. The predictive CDF jumps
    from F(y−) = P(Y < y) to F(y) = P(Y <= y) at the observed y; treating the PIT as uniform on that step,
    the outcome counts as covered by the share of [F(y−), F(y)] that lies inside [low, high]
    (non-randomized PIT, Czado, Gneiting & Held 2009). A calibrated forecast then covers 80% on average.

    By hand: draws 0,0,0,1 (F(0−) = 0, F(0) = 0.75), y = 0, band [0.1, 0.9]: overlap 0.75 − 0.1 = 0.65,
    coverage 0.65 / 0.75 = 0.867. y = 1: step [0.75, 1.0], overlap 0.9 − 0.75 = 0.15, coverage 0.6.
    """
    y = np.asarray(observed, dtype=float)[:, None]
    f_minus = (draws < y).mean(axis=1)
    f = (draws <= y).mean(axis=1)
    width = f - f_minus
    overlap = np.clip(np.minimum(f, high) - np.maximum(f_minus, low), 0.0, None)
    inside = ((f_minus >= low) & (f_minus <= high)).astype(float)
    return np.where(width > 0, overlap / np.where(width > 0, width, 1.0), inside)
