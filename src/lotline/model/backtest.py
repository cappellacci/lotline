"""V1 backtest: does the baseline beat the benchmarks out of sample? (validation plan V1)

For each fit end (2016, 2018, 2020 from config/params/baseline.yaml), every method sees only rows with
year <= fit end, forecasts the next `forecast_horizon_years` (capped at `v1_last_outcome_year`), and is
scored against what BPS recorded:

- **Error:** mean absolute error in units per 1,000 eligible parcels, each place-year counting once. Counts
  become rates with the target year's denominator (carried forward from the newest ACS estimate, as the panel
  does), the same for every method. The model's point forecast is its P50.
- **Coverage:** randomized coverage of the central [P10, P90] band (analysis plan D-003;
  `baseline.randomized_coverage`): for whole-number outcomes, each observed value counts as covered by the
  share of its predictive-CDF step that lies inside the band, so a calibrated forecast covers 80% on average.
  The pass range is 70-90%. The inclusive share (ends included) is still reported, but it flatters forecasts
  of mostly-zero counts, so it is not the test.
- **Bias after 2022:** mean signed error (forecast − observed) for years from `v1_bias_first_year`.
- **By place size:** the same error within terciles of eligible parcels at the fit end, per state.
- **State totals (D-029):** for every state, fit end, size class and forecast year, the scored places' draws
  are summed draw by draw (keeping the cycle they share) and compared with the same places' observed sum;
  also over the whole window (places scored in every year). Reported: randomized P10-P90 coverage, the PIT
  step (for the PIT histogram, `pit_histogram`), the CRPS of the summed draws, and absolute error of the P50
  of the sum against the benchmarks' sums (`state_window`, `score_state`). Reported, not a pass criterion.

**V1 is a development set (D-029).** The 2016/2018/2020 windows have been used to choose among
specifications (A, B, C, state momentum, the D-011 cycle fix, the scoring floor), so their scores are
in-sample for that choice. Confirmatory evidence comes only from the holdout tests.

Every method is scored on the same place-years: those where all three have a forecast and the outcome and
denominator are observed. Reforming places are excluded (`config/params/v1_excluded_places.csv`, a
placeholder until a reform registry exists). Held-out rows never reach this module: the panel loader reads
holdout-filtered tables and re-checks them.

**Specifications:** `spec="B"` is the adopted baseline (D-002). `spec="C"` (D-006) multiplies each place's
level by the demand term from `model.demand` (county household growth and house-price change), with its
coefficients fitted per state on the fit years only; it needs each state's `demand.DemandInputs`.

Run on real data: `uv run python -m lotline.model.backtest --state MN NC OH TX [--spec C]`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.build import eligible
from lotline.config import CONFIG_DIR, Parameter, load_params
from lotline.model import baseline, demand

EXCLUDED_CSV = CONFIG_DIR / "params" / "v1_excluded_places.csv"
METHODS = ("model", *baseline.BENCHMARKS)
TERCILES = ("small", "medium", "large")
KEY = "geoid"
SPECS = ("B", "C")
DEV_SET_LABEL = "V1 windows 2016/2018/2020: development set (used to choose specifications; D-029)"
PIT_BINS = 10


def excluded_places(path: Path = EXCLUDED_CSV) -> set[str]:
    """GEOIDs left out of V1 because they reformed (placeholder list until config/reforms/ has a registry)."""
    return set(pd.read_csv(path, dtype=str)["geoid"])


def fit_ends(params: dict[str, Parameter]) -> list[int]:
    first, last = int(params["v1_fit_end_years_first"].value), int(params["v1_fit_end_years_last"].value)
    return list(range(first, last + 1, int(params["v1_fit_end_step"].value)))


def _terciles(parcels: pd.Series) -> pd.Series:
    """Small / medium / large thirds by eligible parcels (ranks first, so ties never break the cut)."""
    if len(parcels) < len(TERCILES):
        return pd.Series(TERCILES[1], index=parcels.index)
    return pd.qcut(parcels.rank(method="first"), len(TERCILES), labels=list(TERCILES)).astype(str)


def window(
    panel: pd.DataFrame,
    size_class: str,
    fit_end: int,
    *,
    params: dict[str, Parameter] | None = None,
    group: str = "county_geoid",
    excluded: set[str] | None = None,
    reported_only: bool | None = None,
    spec: str = "B",
    demand_inputs: demand.DemandInputs | None = None,
) -> pd.DataFrame:
    """One fit window: every method's forecast beside the observed value, one row per place-year-method.

    See `_window` for the columns; `state_window` gives the same window's state totals.
    """
    return _window(
        panel,
        size_class,
        fit_end,
        params=params,
        group=group,
        excluded=excluded,
        reported_only=reported_only,
        spec=spec,
        demand_inputs=demand_inputs,
    )[0]


def state_window(
    panel: pd.DataFrame,
    size_class: str,
    fit_end: int,
    *,
    params: dict[str, Parameter] | None = None,
    group: str = "county_geoid",
    excluded: set[str] | None = None,
    reported_only: bool | None = None,
    spec: str = "B",
    demand_inputs: demand.DemandInputs | None = None,
) -> pd.DataFrame:
    """One fit window's state totals over the scored places (columns: see `_state_totals`)."""
    return _window(
        panel,
        size_class,
        fit_end,
        params=params,
        group=group,
        excluded=excluded,
        reported_only=reported_only,
        spec=spec,
        demand_inputs=demand_inputs,
    )[1]


def _window(
    panel: pd.DataFrame,
    size_class: str,
    fit_end: int,
    *,
    params: dict[str, Parameter] | None,
    group: str,
    excluded: set[str] | None,
    reported_only: bool | None,
    spec: str,
    demand_inputs: demand.DemandInputs | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The place-level table and the state totals of one fit window.

    Columns: state, geoid, size_class, fit_end, year, horizon, method, tercile, parcels (target year),
    actual, forecast, mean, p10, p90 (rates per 1,000 eligible parcels; mean/p10/p90 only for the model;
    the model's forecast is its P50), coverage_rand (model only, see `baseline.randomized_coverage`), spec,
    and the demand term behind the model row: multiplier (1 in spec B), fallback (spec C: True where the
    place used multiplier 1), beta_h and beta_p (NaN in spec B).
    """
    if spec not in SPECS:
        raise ValueError(f"spec {spec!r} not in {SPECS}")
    if spec == "C" and demand_inputs is None:
        raise ValueError("spec C needs demand_inputs (county households and the FHFA index)")
    p = params or load_params("baseline")
    if reported_only is None:
        reported_only = bool(p["use_reported_only"].value)
    value = baseline.outcome_column(size_class, reported_only)
    if excluded:
        panel = panel[~panel[KEY].isin(excluded)]
    horizon = int(p["forecast_horizon_years"].value)
    last = min(fit_end + horizon, int(p["v1_last_outcome_year"].value))
    fit = panel[panel["year"] <= fit_end]

    mult, fits = None, {}
    if spec == "C":
        mult, fits = demand.multipliers(fit, value, fit_end, demand_inputs, params=p, group=group)
    factor = mult.set_index(KEY)["multiplier"] if mult is not None else None
    table, draws = baseline.forecast_draws(fit, value, fit_end, group=group, params=p, multiplier=factor)
    observed = table[[KEY, "year"]].merge(panel[[KEY, "year", value]], on=[KEY, "year"], how="left")[value]
    seen = observed.notna().to_numpy()
    lo, hi = p["interval_low_quantile"].value, p["interval_high_quantile"].value
    table["coverage_rand"] = np.nan
    table.loc[seen, "coverage_rand"] = baseline.randomized_coverage(
        draws[seen], observed[seen].to_numpy(dtype=float), lo, hi
    )
    model = table.assign(method="model", forecast=table["p50"])
    model = model[[KEY, "year", "method", "forecast", "mean", "p10", "p90", "coverage_rand"]]
    trend_first = fit_end - int(p["benchmark_trend_years"].value) + 1
    bench = baseline.benchmark_forecasts(fit, value, fit_end, trend_first_year=trend_first, params=p)
    bench = bench.rename(columns={"benchmark": "method"})
    fc = pd.concat([model, bench], ignore_index=True)
    fc = fc[(fc["year"] > fit_end) & (fc["year"] <= last)]

    target = panel[(panel["year"] > fit_end) & (panel["year"] <= last)][
        [KEY, "state", "year", value, "eligible_parcels"]
    ]
    target = target.rename(columns={value: "actual_count", "eligible_parcels": "parcels"})
    target = target[target["actual_count"].notna() & (target["parcels"].astype(float) > 0)]
    out = fc.merge(target, on=[KEY, "year"], how="inner").dropna(subset=["forecast"])
    complete = out.groupby([KEY, "year"])["method"].transform("nunique") == len(METHODS)
    out = out[complete].copy()

    out["forecast_count"] = out["forecast"].astype(float)
    parcels = out["parcels"].astype(float)
    out["actual"] = baseline.PER * out["actual_count"].astype(float) / parcels
    for col in ("forecast", "mean", "p10", "p90"):
        out[col] = baseline.PER * out[col].astype(float) / parcels
    origin = fit[fit["year"] == fit_end].drop_duplicates(KEY).set_index(KEY)
    # Places too small to score (decision 5, Ben 2026-10-14): still forecast, rolled into their county for
    # reporting, but left out of V1 scoring because a few lots swing their rates for every method.
    floor = p["v1_min_eligible_parcels"].value
    big_enough = origin.index[origin["eligible_parcels"].astype(float) >= floor]
    out = out[out[KEY].isin(big_enough)].copy()
    sizes = origin.loc[origin.index.isin(out[KEY]), ["state", "eligible_parcels"]]
    tercile = sizes.groupby("state", group_keys=False)["eligible_parcels"].apply(
        lambda s: _terciles(s.astype(float))
    )
    out["tercile"] = out[KEY].map(tercile)
    out["size_class"], out["fit_end"], out["horizon"] = size_class, fit_end, out["year"] - fit_end
    out["spec"] = spec
    if mult is not None:
        m = mult.set_index(KEY)
        out["multiplier"] = out[KEY].map(m["multiplier"]).fillna(1.0)
        out["fallback"] = out[KEY].map(m["fallback"]).fillna(True).astype(bool)
    else:
        out["multiplier"], out["fallback"] = 1.0, False
    out["beta_h"] = out["state"].map({s: f.beta_h for s, f in fits.items()}).astype(float)
    out["beta_p"] = out["state"].map({s: f.beta_p for s, f in fits.items()}).astype(float)
    cols = ["state", KEY, "size_class", "fit_end", "year", "horizon", "method", "tercile", "parcels"]
    cols += ["actual", "forecast", "mean", "p10", "p90", "coverage_rand"]
    cols += ["spec", "multiplier", "fallback", "beta_h", "beta_p"]
    states = _state_totals(out, table, draws, lo, hi)
    states["size_class"], states["fit_end"], states["spec"] = size_class, fit_end, spec
    return out[cols].sort_values([KEY, "year", "method"], ignore_index=True), states


STATE_COLUMNS = ["state", "size_class", "fit_end", "spec", "scope", "year", "places", "actual", "mean", "p10"]
STATE_COLUMNS += [
    "p50",
    "p90",
    "coverage_rand",
    "pit_lo",
    "pit_hi",
    "crps",
    *[f"fc_{b}" for b in baseline.BENCHMARKS],
]


def _state_totals(
    out: pd.DataFrame, table: pd.DataFrame, draws: np.ndarray, low: float, high: float
) -> pd.DataFrame:
    """State totals (counts) over the scored place-years in `out`, from the model's draws summed draw by draw.

    scope "year": one row per state and forecast year, over the places scored that year. scope "total": one
    row per state, the sum over every forecast year of the places scored in all of them (year = last year).
    Benchmarks' totals (fc_<method>) are the sums of their point forecasts over the same place-years.
    """
    model = out[out["method"] == "model"]
    if model.empty:
        return pd.DataFrame(columns=STATE_COLUMNS)
    row_of = pd.Series(np.arange(len(table)), index=pd.MultiIndex.from_frame(table[[KEY, "year"]]))
    bench = out[out["method"] != "model"].pivot_table(
        index=[KEY, "year"], columns="method", values="forecast_count", aggfunc="first"
    )
    n_years = model["year"].nunique()
    rows, sums, observed = [], [], []
    for state, m in model.groupby("state", sort=True):
        full = m.groupby(KEY)["year"].transform("nunique") == n_years
        groups = [("year", int(y), g) for y, g in m.groupby("year", sort=True)]
        groups.append(("total", int(m["year"].max()), m[full]))
        for scope, year, g in groups:
            if g.empty:
                continue
            idx = pd.MultiIndex.from_frame(g[[KEY, "year"]])
            sums.append(draws[row_of.loc[idx].to_numpy()].sum(axis=0))
            observed.append(float(g["actual_count"].astype(float).sum()))
            fc = bench.reindex(idx).sum()
            rows.append(
                {"state": state, "scope": scope, "year": year, "places": g[KEY].nunique()}
                | {f"fc_{b}": float(fc.get(b, np.nan)) for b in baseline.BENCHMARKS}
            )
    s = np.vstack(sums).astype(float)
    y = np.array(observed)
    res = pd.DataFrame(rows).assign(actual=y)
    res["p10"], res["p50"], res["p90"], res["mean"] = baseline.interval_from_draws(s, low, high)
    res["pit_lo"], res["pit_hi"] = baseline.pit_step(s, y)
    res["coverage_rand"] = baseline.step_share(res["pit_lo"].to_numpy(), res["pit_hi"].to_numpy(), low, high)
    res["crps"] = baseline.crps_from_draws(s, y)
    return res.reindex(columns=STATE_COLUMNS)


def score_state(
    states: pd.DataFrame, by: tuple[str, ...] = ("state", "fit_end", "size_class")
) -> pd.DataFrame:
    """State-total scores per `by` and scope: n, coverage_rand (mean randomized P10-P90 coverage), crps,
    mae of the P50 of the sum and of each benchmark's sum, bias_mean (mean of the summed mean − actual) and
    ratio_mean (Σ summed means / Σ actual). Counts, not rates: a state total has no single denominator.
    """
    r = states.assign(
        err_model=(states["p50"] - states["actual"]).abs(), err_mean=states["mean"] - states["actual"]
    )
    for b in baseline.BENCHMARKS:
        r[f"err_{b}"] = (r[f"fc_{b}"] - r["actual"]).abs()
    g = r.groupby([*by, "scope"], sort=True)
    out = pd.DataFrame(
        {
            "n": g.size(),
            "coverage_rand": g["coverage_rand"].mean(),
            "crps": g["crps"].mean(),
            "mae_model": g["err_model"].mean(),
            **{f"mae_{b}": g[f"err_{b}"].mean() for b in baseline.BENCHMARKS},
            "bias_mean": g["err_mean"].mean(),
            "ratio_mean": g["mean"].sum() / g["actual"].sum(),
        }
    )
    return out.reset_index()


def pit_histogram(
    states: pd.DataFrame, by: tuple[str, ...] = ("scope",), bins: int = PIT_BINS
) -> pd.DataFrame:
    """Non-randomized PIT histogram of state totals: the mean share of each row's PIT step in each of `bins`
    equal bins of [0, 1], per `by`. Calibrated: 1 / bins everywhere; U-shaped: bands too narrow; mass at the
    top: the forecast is too low."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    lo, hi = states["pit_lo"].to_numpy(dtype=float), states["pit_hi"].to_numpy(dtype=float)
    mass = pd.DataFrame(
        {
            f"{a:.1f}-{b:.1f}": baseline.step_share(lo, hi, a, b)
            for a, b in zip(edges[:-1], edges[1:], strict=True)
        },
        index=states.index,
    )
    if not by:
        return mass.mean().to_frame().T
    return mass.groupby([states[c] for c in by]).mean().reset_index()


def score(
    results: pd.DataFrame, params: dict[str, Parameter] | None = None, by: tuple[str, ...] = ()
) -> pd.DataFrame:
    """MAE, coverage and post-2022 bias per state, fit end, size class and method (plus any `by` columns).

    mae: mean |forecast − actual|. coverage: share with p10 <= actual <= p90; coverage_rand: mean of the
    randomized coverage (model only). bias_post / mae_post: mean signed and absolute error of the point
    forecast over years >= v1_bias_first_year; bias_post_mean: the same signed error for the model's mean
    (NaN where the window has no such years or the method has no mean).
    """
    p = params or load_params("baseline")
    first_post = int(p["v1_bias_first_year"].value)
    r = results.assign(
        err=results["forecast"] - results["actual"], err_mean=results["mean"] - results["actual"]
    )
    r["abs_err"] = r["err"].abs()
    r["covered"] = (
        ((r["p10"] <= r["actual"]) & (r["actual"] <= r["p90"])).astype(float).where(r["p10"].notna())
    )
    keys = ["state", "fit_end", "size_class", *by, "method"]
    g = r.groupby(keys, sort=True)
    out = pd.DataFrame(
        {
            "n": g.size(),
            "mae": g["abs_err"].mean(),
            "coverage": g["covered"].mean(),
            "coverage_rand": g["coverage_rand"].mean(),
        }
    )
    post = r[r["year"] >= first_post].groupby(keys)
    out["bias_post"] = post["err"].mean()
    out["bias_post_mean"] = post["err_mean"].mean()
    out["mae_post"] = post["abs_err"].mean()
    return out.reset_index()


def verdict(summary: pd.DataFrame, params: dict[str, Parameter] | None = None) -> pd.DataFrame:
    """V1's proposed pass criteria per state, fit end and size class (from a `score` table without `by`).

    beats_benchmarks: model MAE below both benchmarks'. coverage_ok: v1_coverage_low <= coverage_rand <=
    v1_coverage_high (randomized coverage, because outcomes are whole numbers; the inclusive share is kept as
    `coverage`). bias_ok: |bias_post_mean| <= v1_bias_tolerance × mae_post, judged on the model's mean (the
    median of a right-skewed count sits below its mean by construction); True when the window has no
    post-2022 years. passes: all three.
    """
    p = params or load_params("baseline")
    lo, hi = p["v1_coverage_low"].value, p["v1_coverage_high"].value
    tol = p["v1_bias_tolerance"].value
    wide = summary.pivot_table(index=["state", "fit_end", "size_class"], columns="method", values="mae")
    m = summary[summary["method"] == "model"].set_index(["state", "fit_end", "size_class"])
    out = pd.DataFrame(index=wide.index)
    for method in METHODS:
        out[f"mae_{method}"] = wide[method]
    out["beats_benchmarks"] = (wide["model"] < wide[list(baseline.BENCHMARKS)].min(axis=1)).astype(bool)
    out["coverage"] = m["coverage"]
    out["coverage_rand"] = m["coverage_rand"]
    out["coverage_ok"] = out["coverage_rand"].between(lo, hi)
    out["bias_post"] = m["bias_post"]
    out["bias_post_mean"] = m["bias_post_mean"]
    out["bias_ok"] = (m["bias_post_mean"].abs() <= tol * m["mae_post"]) | m["bias_post_mean"].isna()
    out["passes"] = out["beats_benchmarks"] & out["coverage_ok"] & out["bias_ok"]
    return out.reset_index()


def run(
    panels: dict[str, pd.DataFrame],
    size_classes: tuple[str, ...] = baseline.SIZE_CLASSES,
    *,
    params: dict[str, Parameter] | None = None,
    group: str = "county_geoid",
    reported_only: bool | None = None,
    excluded: set[str] | None = None,
    spec: str = "B",
    demand_inputs: dict[str, demand.DemandInputs] | None = None,
    state_totals: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    """All windows for every state panel and size class -> one long results table (see `window`).

    `demand_inputs` is keyed like `panels` (by state) and is needed for spec C. With `state_totals`, returns
    (place results, state totals) from the same draws (see `state_window`).
    """
    p = params or load_params("baseline")
    excluded = excluded_places() if excluded is None else excluded
    d = demand_inputs or {}
    parts = [
        _window(
            panel,
            s,
            end,
            params=p,
            group=group,
            excluded=excluded,
            reported_only=reported_only,
            spec=spec,
            demand_inputs=d.get(state),
        )
        for state, panel in panels.items()
        for s in size_classes
        for end in fit_ends(p)
    ]
    places = pd.concat([a for a, _ in parts], ignore_index=True)
    if not state_totals:
        return places
    return places, pd.concat([b for _, b in parts if not b.empty], ignore_index=True)


def demand_inputs_for(state: str, store) -> demand.DemandInputs:  # pragma: no cover - real data
    """Spec C's inputs from a state's processed ACS and market tables (no downloads)."""
    acs, market = store.read(state, "acs_geo_year"), store.read(state, "market_geo_year")
    if acs is None or market is None:
        raise FileNotFoundError(f"{state}: build acs_geo_year and market_geo_year first")
    return demand.inputs_from_tables(acs, market)


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - real-data entry point
    from lotline.build import panels as panel_mod
    from lotline.io import DataStore

    ap = argparse.ArgumentParser(description="V1 baseline backtest on processed (holdout-filtered) data")
    ap.add_argument("--state", nargs="+", required=True)
    ap.add_argument("--theme", default="adu", help="eligible-parcel theme used as the denominator")
    ap.add_argument(
        "--rule-version", default=eligible.RULE_VERSION, help="eligibility rule (default: current)"
    )
    ap.add_argument("--group", default="county_geoid", help="shrinkage group column, or 'state'")
    ap.add_argument("--totals", action="store_true", help="score totals incl. imputation, not reported units")
    ap.add_argument("--out", type=Path, help="write the long results table here (CSV)")
    ap.add_argument("--state-out", type=Path, help="write the state-total table here (CSV)")
    ap.add_argument("--set", nargs="*", default=[], help="parameter overrides, name=value (sensitivity runs)")
    ap.add_argument("--spec", choices=SPECS, default="B", help="B: baseline; C: + demand term (D-006)")
    a = ap.parse_args(argv)
    params = load_params("baseline")
    for item in a.set:
        name, val = item.split("=")
        params[name] = params[name].model_copy(update={"value": float(val)})
    store = DataStore()
    loaded = {s: panel_mod.load(s, store, theme=a.theme, rule_version=a.rule_version) for s in a.state}
    inputs = None
    if a.spec == "C":
        inputs = {s: demand_inputs_for(s, store) for s in a.state}
    results = run(
        loaded,
        params=params,
        group=a.group,
        reported_only=False if a.totals else None,
        spec=a.spec,
        demand_inputs=inputs,
        state_totals=True,
    )
    results, states = results
    if a.out:
        results.to_csv(a.out, index=False)
    if a.state_out:
        states.to_csv(a.state_out, index=False)
    pd.set_option("display.width", 200)
    print(DEV_SET_LABEL)
    print(verdict(score(results, params), params).round(3).to_string(index=False))
    print(score(results, params, by=("tercile",)).round(3).to_string(index=False))
    print("State totals (counts; reported, not a pass criterion):")
    print(score_state(states).round(3).to_string(index=False))
    print(pit_histogram(states).round(3).to_string(index=False))


if __name__ == "__main__":  # pragma: no cover
    main()
