#!/usr/bin/env python3
"""Estimate `adu_mature_hazard_ref` from Lotline's own post-reform places, as pre-registered in D-019.

    uv run python scripts/dev/calibrate_adu.py [--explore-austin]
    uv run python scripts/dev/calibrate_adu.py --draw-terms   # config/params/adu_anchor.yaml (D-030)

Fit 2 (D-022): a place-year whose rule class depends on blank rubric fields enters as a two-component mixture.

Fit set: Minneapolis and every other Twin Cities place with a coded ADU rule (2016-2025; St. Paul never, it is
the V5 blind test), and Austin 2016-2023 once its ADU rules are coded. Test set: Raleigh 2021-2025, and Durham
once its ADU-eligible parcel count is fixed (every roll the test uses has 1,000+). Place-years enter only with
a coded ADU rule in force by 1 July and a permit source flagging ADUs that year
(`lotline.model.calibrate_adu.place_years`). Reforms are read from config/reforms/*.csv at run time.

Prints the fit (θ with its 90% profile interval, α, the partial-rule share decision), the test set's observed
vs predicted counts with 90% predictive intervals, and the comparison with Portland's anchor.
`--explore-austin` adds an exploratory fit (not pre-registered, never used for the parameter) treating
Austin's uncoded ADU rules as a mature Handbook-equivalent rule, to preview what coding Austin will do.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.io import DataStore
from lotline.model import calibrate_adu as cal
from lotline.model.scenarios import adu

ST_PAUL, DURHAM, RALEIGH, AUSTIN = "2758000", "3719000", "3755000", "4805000"
FIT_YEARS_MN, FIT_YEARS_AUSTIN, TEST_YEARS = range(2016, 2026), range(2016, 2024), range(2021, 2026)
JUDGMENT_RANGE = (0.1, 0.6)
GRID = np.round(np.arange(0.02, 1.0001, 0.02), 2)
PORTLAND = 0.004  # adu-study-design calibration band, Portland about 4 per 1,000 lots a year


def mn_places() -> list[str]:
    r = adu.load_reforms("MN")
    return sorted(set(r.loc[r["theme"] == "adu", "jurisdiction_geoid"]) - {ST_PAUL})


def describe(rows: pd.DataFrame) -> None:
    for name, d in rows.groupby("name"):
        partial, handbook = (d.ramp_partial > 0).any(), (d.ramp_handbook > 0).any()
        kinds = "partial+handbook" if partial and handbook else ("partial" if partial else "handbook")
        span = f"{d.year.min()}-{d.year.max()}"
        print(f"  {name:22s} {span}  n={len(d):2d}  observed {d.adu_permits.sum():5d}  {kinds}")


def fit_and_test(fit_rows: pd.DataFrame, test_rows: pd.DataFrame) -> cal.Fit:
    """Fit 2 (D-019, D-022): place-years whose rule class depends on blank fields enter as a mixture."""
    y = fit_rows["adu_permits"].to_numpy()
    q = fit_rows["q_blank"].to_numpy()
    share = adu.central_params()["adu_partial_rule_share"]
    print(
        f"Place-years whose class depends on blank fields: {(q > 0).sum()} of {len(q)} "
        f"(mean P(restricted) {q[q > 0].mean() if (q > 0).any() else 0:.2f})"
    )
    grid_used = None
    rp = fit_rows["ramp_partial"].to_numpy()
    if ((rp > 0) | (q > 0)).any():
        grid, ll, (s_lo, s_hi) = cal.profile_share_rows(y, fit_rows, GRID)
        s_hat = float(grid[np.argmax(ll)])
        identified = (s_hi - s_lo) < (JUDGMENT_RANGE[1] - JUDGMENT_RANGE[0])
        verdict = (
            "identified -> estimated jointly" if identified else "not identified -> kept at 0.3 (judgment)"
        )
        print(
            f"Partial-rule share: profile max s = {s_hat:.2f}, 90% interval {s_lo:.2f}-{s_hi:.2f} "
            f"(judgment range {JUDGMENT_RANGE[0]}-{JUDGMENT_RANGE[1]}): {verdict}"
        )
        if identified:
            share, grid_used = s_hat, grid
    if grid_used is not None:
        paths = [cal.k_paths(fit_rows, s) for s in grid_used]
        ka, kb = np.array([a for a, _ in paths]), np.array([b for _, b in paths])
    else:
        ka, kb = cal.k_paths(fit_rows, share)
    fit = cal.fit_anchor(y, ka, k_b=kb, q=q)
    a, b = cal.k_paths(fit_rows, share)
    fitted = fit.theta * (q * a + (1 - q) * b)
    print(
        f"theta = {fit.theta:.6f}  90% profile interval {fit.low:.6f}-{fit.high:.6f}  "
        f"({fit.theta * 1000:.3f} per 1,000 parcels a year at Portland's rent, value and rate)"
    )
    print(
        f"alpha = {fit.alpha:.3f}; n = {fit.n} place-years; log-likelihood {fit.loglik:.2f}; "
        f"observed {y.sum()}, fitted mean {fitted.sum():.0f}"
    )
    for name, d in fit_rows.assign(fitted=fitted).groupby("name"):
        if d.adu_permits.sum() >= 5 or d.fitted.sum() >= 5:
            print(f"    {name:22s} observed {d.adu_permits.sum():5d}  fitted mean {d.fitted.sum():7.1f}")
    print(f"vs Portland's 4 per 1,000: {fit.theta / PORTLAND:.2f} of it")
    if test_rows.empty:
        print("Test set: no place-years")
        return fit
    ta, tb = cal.k_paths(test_rows, share)
    tq = test_rows["q_blank"].to_numpy()
    draws = cal.predictive(ta, fit, draws=20_000, seed=20261020, k_b=tb, q=tq)
    mean_t = fit.theta * (tq * ta + (1 - tq) * tb)
    print("Test set (not used in the fit): observed vs predicted median (90% predictive interval)")
    for i, r in test_rows.iterrows():
        lo, mid, hi = np.percentile(draws[:, i], [5, 50, 95])
        flag = "inside" if lo <= r.adu_permits <= hi else "OUTSIDE"
        print(
            f"  {r['name']:14s} {r.year}: observed {r.adu_permits:4d}  predicted {mid:5.0f} "
            f"({lo:.0f}-{hi:.0f}), mean {mean_t[i]:5.1f}  {flag}"
        )
    lo, mid, hi = np.percentile(draws.sum(axis=1), [5, 50, 95])
    obs = int(test_rows["adu_permits"].sum())
    verdict = "inside" if lo <= obs <= hi else "OUTSIDE: transport failure, reported not refitted"
    print(
        f"  TOTAL: observed {obs}, predicted median {mid:.0f}, mean {mean_t.sum():.0f} "
        f"(90% {lo:.0f}-{hi:.0f}) -> {verdict}"
    )
    return fit


def fit3_main(store) -> None:
    """D-019 fit 3, pre-registered: graded shares, gamma place effects, blank fields per place, coverage."""
    mn = cal.place_data("MN", store, mn_places(), FIT_YEARS_MN)
    austin = cal.place_data("TX", store, [AUSTIN], FIT_YEARS_AUSTIN)
    fit_places = mn + austin
    test = cal.place_data("NC", store, [RALEIGH, DURHAM], TEST_YEARS)
    rows = cal.place_years("NC", store, [DURHAM], TEST_YEARS)
    durham_ok = len(rows) > 0 and rows["eligible_parcels"].min() >= 1000
    if not durham_ok:
        smallest = int(rows["eligible_parcels"].min()) if len(rows) else 0
        print(f"Durham: a roll the test uses has {smallest} ADU-eligible parcels (< 1,000) -> not tested")
        test = [p for p in test if p.geoid != DURHAM]
    print("=== Fit 3 (D-019, pre-registered) ===\nFit set:")
    for pl in fit_places:
        print(
            f"  {pl.name:22s} {pl.years.min()}-{pl.years.max()}  n={len(pl.y):2d}  "
            f"observed {int(pl.y.sum()):5d}  "
            f"blank-field combinations {len(pl.w)}"
        )
    fit = cal.fit3(fit_places)
    print(
        f"theta = {fit.theta:.6f}  90% profile interval {fit.low:.6f}-{fit.high:.6f} "
        f"({fit.theta * 1000:.3f} per 1,000 a year at Portland's rent, value and rate; "
        f"{fit.theta / PORTLAND:.2f} of Portland's 4)"
    )
    print(
        f"place-effect variance alpha = {fit.alpha:.3f}; places {fit.n_places}, place-years {fit.n_years}, "
        f"log-likelihood {fit.loglik:.2f}"
    )
    for label, val, (lo, hi), est, jr in (
        ("owner-occupancy share m_o", fit.m_owner, fit.owner_interval, fit.owner_estimated, "0.2-1.0"),
        ("other-restriction share m_x", fit.m_other, fit.other_interval, fit.other_estimated, "0.1-0.6"),
    ):
        verdict = "estimated" if est else "not identified -> judgment value kept"
        print(f"{label}: {val:.1f}  (profile 90% {lo:.1f}-{hi:.1f}; judgment range {jr}) -> {verdict}")
    cv = cal._cvals(fit.m_owner, fit.m_other)
    print("\nObserved vs fitted (mean without the place's own effect; with it = posterior mean of u):")
    for pl in fit_places:
        k = (pl.w[:, None] * pl.k(cv)).sum(axis=0)
        mean0 = fit.theta * k
        r = 1 / fit.alpha if fit.alpha > 0 else np.inf
        u_post = (pl.y.sum() + r) / (r + mean0.sum()) if np.isfinite(r) else 1.0
        print(
            f"  {pl.name:22s} observed {int(pl.y.sum()):5d}  fitted {mean0.sum():7.1f}  with own effect "
            f"{u_post * mean0.sum():7.1f}  (u = {u_post:.2f})"
        )
        if pl.geoid == "2743000":
            print(
                "    Minneapolis by year: "
                + "; ".join(
                    f"{int(yr)} {int(o)} vs {m:.1f}" for yr, o, m in zip(pl.years, pl.y, mean0, strict=True)
                )
            )
    print("\nTest set (not used in the fit): observed vs predicted median (90% predictive interval)")
    for pl in test:
        draws = cal.predict_place(pl, fit, seed=20261020)
        for t, yr in enumerate(pl.years):
            lo, mid, hi = np.percentile(draws[:, t], [5, 50, 95])
            flag = "inside" if lo <= pl.y[t] <= hi else "OUTSIDE"
            print(
                f"  {pl.name:14s} {int(yr)}: observed {int(pl.y[t]):4d}  "
                f"predicted {mid:6.0f} ({lo:.0f}-{hi:.0f}) "
                f"mean {draws[:, t].mean():6.1f}  {flag}"
            )
        tot = draws.sum(axis=1)
        lo, mid, hi = np.percentile(tot, [5, 50, 95])
        obs = int(pl.y.sum())
        verdict = "inside" if lo <= obs <= hi else "OUTSIDE: transport failure, reported not refitted"
        print(
            f"  {pl.name} TOTAL: observed {obs}, predicted median {mid:.0f}, mean {tot.mean():.0f} "
            f"(90% {lo:.0f}-{hi:.0f}) -> {verdict}"
        )


def fit_set(store, params=None) -> list[cal.PlaceData]:
    """The fit-3 places (Twin Cities and Austin) with the transport evaluated at `params`."""
    mn = cal.place_data("MN", store, mn_places(), FIT_YEARS_MN, params)
    return mn + cal.place_data("TX", store, [AUSTIN], FIT_YEARS_AUSTIN, params)


def _fit_at(params):
    """(θ̂, α̂) at the central rule shares of `params`, and the fit inputs' fingerprint (base and ramp)."""
    places = fit_set(DataStore(), params)
    cv = cal._cvals(params["adu_owner_occupancy_share"], params["adu_partial_rule_share"])
    key = tuple(np.concatenate([np.r_[pl.base, pl.cr.ravel()] for pl in places]).round(15)) + tuple(cv)
    return places, cv, key


def _slope(key: str) -> tuple[str, float, float]:
    """d log θ̂ / dp and d log α̂ / dp for one parameter by central differences (0, 0: not in the fit)."""
    central = adu.central_params()
    s = adu.specs()[key]
    d = 0.1 * (s.high - s.low)
    lo, hi = max(s.low, s.value - d), min(s.high, s.value + d)
    _, _, k0 = _fit_at(central)
    p_lo, cv_lo, k_lo = _fit_at(central | {key: lo})
    if k_lo == k0:
        return key, 0.0, 0.0
    p_hi, cv_hi, _ = _fit_at(central | {key: hi})
    t_lo, a_lo = cal.fit_theta_alpha(p_lo, cv_lo)
    t_hi, a_hi = cal.fit_theta_alpha(p_hi, cv_hi)
    g_t = (math.log(t_hi) - math.log(t_lo)) / (hi - lo)
    g_a = (math.log(a_hi) - math.log(a_lo)) / (hi - lo)
    print(
        f"  {key:28s} refit at {lo:g}, {hi:g}: d log theta/dp {g_t:+.5g}  d log alpha/dp {g_a:+.5g}",
        flush=True,
    )
    return key, g_t, g_a


def draw_terms_main(out: Path, workers: int) -> None:
    """What the scenario's draws need from the fit (D-030): the observed-information SEs of (log θ, log α) and
    how the fitted θ and α move with each judgment parameter they were fitted at (`adu.anchor_inputs`).

    Each slope re-runs the fit (θ, α at the central rule shares) with one parameter at central ± 10% of its
    range (clipped to the range) and takes d log θ̂ / dp and d log α̂ / dp; parameters the fit does not depend
    on (the fit inputs do not change) are left out and read as 0. Writes `out` (default
    config/params/adu_anchor.yaml); `workers` parameters run at once.
    """
    from concurrent.futures import ProcessPoolExecutor

    places, cv, _ = _fit_at(adu.central_params())
    theta, alpha = cal.fit_theta_alpha(places, cv)
    se_t, se_a, corr = cal.information_se(places, theta, alpha, cv)
    n_years = sum(len(pl.y) for pl in places)
    print(
        f"At central parameters: theta {theta:.6f}, alpha {alpha:.3f} ({len(places)} places, {n_years} "
        f"place-years); observed-information log-SE theta {se_t:.3f}, alpha {se_a:.3f}, "
        f"correlation {corr:.3f}",
        flush=True,
    )
    with ProcessPoolExecutor(workers) as pool:
        slopes = list(pool.map(_slope, adu.anchor_inputs()))
    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    where = f"{len(places)} places, {n_years} place-years, {today}"
    lines = [
        "# How the fitted ADU anchor (theta = adu_mature_hazard_ref) and place-effect variance (alpha =",
        "# adu_place_effect_variance) move with the judgment parameters they were fitted at (D-030).",
        "# Generated by scripts/dev/calibrate_adu.py --draw-terms; do not edit by hand. Each simulation draw",
        "# shifts log(theta) and log(alpha) by slope x (drawn - central value) for every parameter here, so",
        "# the anchor stays consistent with the Minnesota and Austin data under that draw's transport.",
        "# Parameters the fit does not depend on are left out (slope 0).",
        "",
        "adu_anchor_info_log_se_theta:",
        *_entry(se_t, "log-SE of theta (observed information, alpha profiled jointly)", where),
        "adu_anchor_info_log_se_alpha:",
        *_entry(se_a, "log-SE of alpha (observed information)", where),
        "adu_anchor_info_corr:",
        *_entry(corr, "correlation of log theta and log alpha (observed information)", where),
    ]
    for key, g_t, g_a in slopes:
        if g_t == 0 and g_a == 0:
            continue
        how = f"{where}; refit at central +/- 10% of the {key} range"
        lines += [f"anchor_slope_theta__{key}:", *_entry(g_t, f"change in log(theta) per unit of {key}", how)]
        lines += [f"anchor_slope_alpha__{key}:", *_entry(g_a, f"change in log(alpha) per unit of {key}", how)]
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")


def _entry(v: float, unit: str, how: str) -> list[str]:
    return [
        f"  value: {v:.6g}",
        f"  low: {v:.6g}",
        f"  high: {v:.6g}",
        f"  unit: {unit}",
        f'  source: "Estimated, scripts/dev/calibrate_adu.py --draw-terms (D-019 fit 3 likelihood; {how})"',
        "",
    ]


# D-039: the four-state fit set (place GEOIDs and years); MN is every coded place but St. Paul, as in fit 3.
FOUR_STATE = {
    "TX": {AUSTIN: FIT_YEARS_AUSTIN, "4865000": range(2021, 2026)},  # San Antonio's file starts 2020-07
    # Mecklenburg towns (parser-based counts), Greensboro, Durham County; Raleigh and Durham are the tests
    "NC": {g: range(2016, 2026) for g in ("3743480", "3741960", "3714700", "3733120", "3728000", "37063")},
    "OH": {"3915000": range(2024, 2026)},  # Cincinnati, the only complete OH ADU count
}
P_BANDS = (10, 50, 90)


def four_state_places(store, counts=None) -> list[cal.PlaceData]:
    out = cal.place_data("MN", store, mn_places(), FIT_YEARS_MN, counts=counts)
    for st, places in FOUR_STATE.items():
        for g, yrs in places.items():
            out += cal.place_data(st, store, [g], yrs, counts=counts)
    return out


def _portland_paths(store, places: list[cal.PlaceData], counts=None) -> dict[str, np.ndarray]:
    """Benchmark (b): Portland's 4 per 1,000 × eligible parcels × the ramp of the rule in force, per year
    (× the survey reporting rate under D-041's count rules)."""
    out = {}
    for pl in places:
        rows = cal.place_years(pl.state, store, [pl.geoid], pl.years, counts=counts).set_index("year")
        ramp = rows[["ramp_handbook", "ramp_partial", "ramp_blank"]].max(axis=1)  # any rule in force
        k = PORTLAND * rows["eligible_parcels"] * ramp * rows["report_rate"]
        out[pl.geoid] = k.reindex(pl.years).to_numpy(dtype=float)
    return out


def _leave_out(args) -> tuple[str, np.ndarray]:
    places, i = args
    fit = cal.fit3([pl for j, pl in enumerate(places) if j != i])
    return places[i].geoid, cal.predict_place(places[i], fit, seed=20261020)


def _parcels(store, pl: cal.PlaceData) -> np.ndarray:
    rows = cal.place_years(pl.state, store, [pl.geoid], pl.years).set_index("year")
    return rows["eligible_parcels"].reindex(pl.years).to_numpy(dtype=float)


def _score(label: str, store, places, draws: dict, portland: dict, out: Path | None) -> pd.DataFrame:
    """Per place and year: observed, P10/P50/P90, inside; then coverage and error per 1,000 parcels a year."""
    recs = []
    for pl in places:
        d, parcels = draws[pl.geoid], _parcels(store, pl)
        for t, yr in enumerate(pl.years):
            lo, mid, hi = np.percentile(d[:, t], P_BANDS)
            recs.append(dict(set=label, place=pl.geoid, name=pl.name, state=pl.state, year=str(int(yr)),
                             observed=int(pl.y[t]), p10=lo, p50=mid, p90=hi, mean=d[:, t].mean(),
                             portland=portland[pl.geoid][t], parcels=parcels[t]))  # fmt: skip
        lo, mid, hi = np.percentile(d.sum(axis=1), P_BANDS)
        recs.append(dict(set=label, place=pl.geoid, name=pl.name, state=pl.state, year="total",
                         observed=int(pl.y.sum()), p10=lo, p50=mid, p90=hi, mean=d.sum(axis=1).mean(),
                         portland=portland[pl.geoid].sum(),
                         parcels=np.nanmean(parcels) * len(pl.years)))  # fmt: skip
    df = pd.DataFrame(recs)
    df["inside"] = (df["observed"] >= df["p10"]) & (df["observed"] <= df["p90"])
    yr, tot = df[df["year"] != "total"], df[df["year"] == "total"]

    def err(col):  # mean absolute error per 1,000 eligible parcels a year, over place-years
        return float((abs(yr[col] - yr["observed"]) / yr["parcels"] * 1000).mean())

    print(
        f"\n{label}: {len(tot)} places, {len(yr)} place-years\n"
        f"  P10-P90 coverage: place totals {tot['inside'].mean():.0%} "
        f"({int(tot['inside'].sum())} of {len(tot)}), "
        f"place-years {yr['inside'].mean():.0%}\n"
        f"  mean abs error per 1,000 eligible parcels a year: model (median) {err('p50'):.3f}; "
        f"no effect {float((yr['observed'] / yr['parcels'] * 1000).mean()):.3f}; "
        f"Portland unadjusted {err('portland'):.3f}"
    )
    print(
        tot[["name", "state", "observed", "p10", "p50", "p90", "portland", "inside"]]
        .round(1)
        .to_string(index=False)
    )
    if out is not None:
        df.to_csv(out / f"backtest_{label.split()[0].lower()}.csv", index=False)
    return df


def four_state_main(store, out: Path | None, workers: int) -> None:
    """D-039: fit 3 on the four-state fit set, the test set, and the leave-one-place-out backtest (V4)."""
    from concurrent.futures import ProcessPoolExecutor

    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
    places = four_state_places(store)
    print("=== D-039: fit 3 on the four-state fit set ===")
    for pl in places:
        print(
            f"  {pl.state} {pl.name:34s} {pl.years.min()}-{pl.years.max()}  n={len(pl.y):2d}  "
            f"observed {int(pl.y.sum()):5d}"
        )
    fit = cal.fit3(places)
    print(
        f"theta = {fit.theta:.6f}  90% profile interval {fit.low:.6f}-{fit.high:.6f} "
        f"({fit.theta * 1000:.3f} per 1,000 a year at the reference rent, value and rate; "
        f"fit 3 on main: 0.001038, 0.000453-0.003173; {fit.theta / PORTLAND:.2f} of Portland's 4)\n"
        f"place-effect variance alpha = {fit.alpha:.3f}; owner share {fit.m_owner:.1f} "
        f"({'estimated' if fit.owner_estimated else 'judgment'}), other share {fit.m_other:.1f} "
        f"({'estimated' if fit.other_estimated else 'judgment'}); "
        f"places {fit.n_places}, place-years {fit.n_years}",
        flush=True,
    )
    if out is not None:
        pd.DataFrame([{k: getattr(fit, k) for k in fit.__dataclass_fields__}]).to_csv(
            out / "fit.csv", index=False
        )
    test = cal.place_data("NC", store, [RALEIGH, DURHAM], TEST_YEARS)
    rows = cal.place_years("NC", store, [DURHAM], TEST_YEARS)
    if not (len(rows) and rows["eligible_parcels"].min() >= 1000):
        print("Durham: a roll the test uses has < 1,000 ADU-eligible parcels -> not tested")
        test = [p for p in test if p.geoid != DURHAM]
    test_draws = {pl.geoid: cal.predict_place(pl, fit, seed=20261020) for pl in test}
    _score("Test set (held out)", store, test, test_draws, _portland_paths(store, test), out)
    print(f"\nLeave-one-place-out backtest: {len(places)} refits on {workers} workers ...", flush=True)
    with ProcessPoolExecutor(workers) as pool:
        draws = dict(pool.map(_leave_out, [(places, i) for i in range(len(places))]))
    _score("Backtest (leave one place out)", store, places, draws, _portland_paths(store, places), out)


# ---------------------------------------------------------------------------------------------------------
# D-040: statewide backtest (joint draws summed over a state's places)
# ---------------------------------------------------------------------------------------------------------

SEED = 20261020


def _test_set(store, counts=None) -> list[cal.PlaceData]:
    test = cal.place_data("NC", store, [RALEIGH, DURHAM], TEST_YEARS, counts=counts)
    rows = cal.place_years("NC", store, [DURHAM], TEST_YEARS)
    if not (len(rows) and rows["eligible_parcels"].min() >= 1000):
        test = [p for p in test if p.geoid != DURHAM]
    return test


def _leave_state(args) -> tuple[str, cal.Fit3, dict]:
    places, test, st = args
    fit = cal.fit3([pl for pl in places if pl.state != st])
    pred = [pl for pl in places + test if pl.state == st]
    return st, fit, cal.predict_places(pred, fit, seed=SEED)


def _leave_place_joint(args) -> tuple[str, np.ndarray]:
    places, i = args
    fit = cal.fit3([pl for j, pl in enumerate(places) if j != i])
    return places[i].geoid, cal.predict_places([places[i]], fit, seed=SEED)[places[i].geoid]


def verdict(observed: float, p10: float, p50: float, p90: float) -> str:
    """D-040's bar: useful = inside P10-P90 and P50 within a factor of 2 of the observed total."""
    inside = p10 <= observed <= p90
    close = p50 > 0 and observed > 0 and 0.5 <= observed / p50 <= 2
    return "useful" if inside and close else "inside only" if inside else "missed"


def state_totals(label: str, groups: dict, draws: dict, portland: dict) -> pd.DataFrame:
    """One row per group of places: observed total, P10/P50/P90 of the summed joint draws, and the scores."""
    recs = []
    for name, pls in groups.items():
        tot = sum(draws[pl.geoid].sum(axis=1) for pl in pls)
        obs = float(sum(pl.y.sum() for pl in pls))
        lo, mid, hi = np.percentile(tot, P_BANDS)
        recs.append(dict(test=label, group=name, places=len(pls), place_years=sum(len(pl.y) for pl in pls),
                         observed=int(obs), p10=lo, p50=mid, p90=hi, mean=float(tot.mean()),
                         obs_over_p50=obs / mid if mid > 0 else float("inf"),
                         p90_over_p10=hi / lo if lo > 0 else float("inf"),
                         portland=float(sum(portland[pl.geoid].sum() for pl in pls)),
                         verdict=verdict(obs, lo, mid, hi)))  # fmt: skip
    df = pd.DataFrame(recs)
    print(f"\n{label}")
    print(df.drop(columns=["test"]).round(2).to_string(index=False), flush=True)
    return df


def _groups(places, test, with_test: bool) -> dict:
    g = {st: [pl for pl in places if pl.state == st] for st in ("MN", "NC", "OH", "TX")}
    if with_test:
        g["NC with Raleigh and Durham"] = g["NC"] + test
    return g


def statewide_main(store, out: Path | None, workers: int) -> None:
    """D-040: leave one state out (main) and leave one place out summed by state, joint draws."""
    from concurrent.futures import ProcessPoolExecutor

    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
    places, test = four_state_places(store), _test_set(store)
    portland = _portland_paths(store, places + test)
    print(f"=== D-040: {len(places)} fit places, test set {[p.name for p in test]} ===", flush=True)
    with ProcessPoolExecutor(workers) as pool:
        loso = list(pool.map(_leave_state, [(places, test, st) for st in ("MN", "NC", "OH", "TX")]))
        print("\nLeave one state out: the fit without each state", flush=True)
        draws_s = {}
        for st, fit, d in loso:
            print(f"  without {st}: theta {fit.theta * 1000:.3f} per 1,000 ({fit.low * 1000:.3f}-"
                  f"{fit.high * 1000:.3f}), alpha {fit.alpha:.2f}, places {fit.n_places}")  # fmt: skip
            draws_s.update(d)
        main = state_totals("Main: leave one state out", _groups(places, test, True), draws_s, portland)
        print(f"\nLeave one place out: {len(places)} refits on {workers} workers ...", flush=True)
        draws_p = dict(pool.map(_leave_place_joint, [(places, i) for i in range(len(places))]))
    draws_p.update(cal.predict_places(test, cal.fit3(places), seed=SEED))  # test set from the full fit
    second = state_totals("Second: leave one place out, summed by state", _groups(places, test, True),
                          draws_p, portland)  # fmt: skip
    if out is not None:
        pd.concat([main, second]).to_csv(out / "statewide.csv", index=False)
        for tag, d in (("loso", draws_s), ("lopo", draws_p)):
            np.savez_compressed(out / f"draws_{tag}.npz", **{g: v.sum(axis=1) for g, v in d.items()})


# ---------------------------------------------------------------------------------------------------------
# D-041: consistent counts (co-built units, survey reporting rate), then the four-state comparison
# ---------------------------------------------------------------------------------------------------------

STATES = ("MN", "NC", "OH", "TX")
LOG_THETA_BOUNDS = (-14.0, 0.0)  # fit3's search range: an interval reaching it is "not estimable"


def _fit_task(args) -> tuple[str, str, cal.Fit3 | None, str]:
    """('state', st) fits one state alone; ('without', st) leaves it out; ('all', '') fits every place."""
    kind, st, places = args
    use = {"state": [p for p in places if p.state == st], "without": [p for p in places if p.state != st],
           "all": places}[kind]  # fmt: skip
    try:
        return kind, st, cal.fit3(use), ""
    except Exception as e:  # noqa: BLE001 - a failed fit is a reported result ("not estimable")
        return kind, st, None, f"{type(e).__name__}: {e}"


def _fit_row(run: str, kind: str, st: str, fit, err: str) -> dict:
    if fit is None:
        return dict(run=run, fit=kind, state=st, status=f"not estimable ({err})")
    lo, hi = math.log(fit.low), math.log(fit.high)
    bounded = lo <= LOG_THETA_BOUNDS[0] + 0.05 or hi >= LOG_THETA_BOUNDS[1] - 0.05
    return dict(run=run, fit=kind, state=st, status="not estimable (bound)" if bounded else "ok",
                theta_per_1000=fit.theta * 1000, low=fit.low * 1000, high=fit.high * 1000, alpha=fit.alpha,
                m_owner=fit.m_owner, places=fit.n_places, place_years=fit.n_years)  # fmt: skip


def _market(run: str, store, places, counts) -> list[dict]:
    """Descriptive (D-041 item 6): correlation of log observed rate with log h1 across places."""
    recs = []
    for pl in places:
        rows = cal.place_years(pl.state, store, [pl.geoid], pl.years, counts=counts)
        exposure = float((rows["eligible_parcels"] * rows["report_rate"]).sum())
        recs.append(dict(state=pl.state, log_rate=math.log((pl.y.sum() + 0.5) / exposure),
                         log_h1=math.log(rows["h1"].mean())))  # fmt: skip
    df = pd.DataFrame(recs)
    out = [dict(run=run, scope="pooled", places=len(df), corr=float(df["log_rate"].corr(df["log_h1"])))]
    for st, d in df.groupby("state"):
        c = float(d["log_rate"].corr(d["log_h1"])) if len(d) >= 3 else float("nan")
        out.append(dict(run=run, scope=st, places=len(d), corr=c))
    return out


def _count_rows(run: str, store, before, after, counts) -> list[dict]:
    """D-041 item 1: per state (NC without the test set; the test set on its own), D-039's count, the count
    under this run's rules, and the place-years counted from the survey."""

    def group(pl):
        return "test set" if pl.geoid in (RALEIGH, DURHAM) else pl.state

    recs = []
    for g in STATES + ("test set",):
        b, a = [p for p in before if group(p) == g], [p for p in after if group(p) == g]
        rates = [cal.place_years(p.state, store, [p.geoid], p.years, counts=counts)["report_rate"] for p in a]
        recs.append(dict(run=run, group=g, places=len(a), place_years=sum(len(p.y) for p in a),
                         d039_count=int(sum(p.y.sum() for p in b)), count=int(sum(p.y.sum() for p in a)),
                         survey_place_years=int(sum((r < 1).sum() for r in rates))))  # fmt: skip
    return recs


def counts_main(store, out: Path | None, workers: int) -> None:
    """D-041: the main run (co-built excluded, ρ central) and sensitivities S1-S3, each across four states."""
    from concurrent.futures import ProcessPoolExecutor

    runs = {
        "main": cal.count_settings(),
        "S1 co-built included": cal.count_settings(exclude_cobuilt=False),
        "S2 rho 1.0": cal.count_settings(report_rate=1.0),
        "S3 rho 0.3": cal.count_settings(report_rate=0.3),
    }
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
    before = four_state_places(store) + _test_set(store)
    fits, totals, market, counted = [], [], [], []
    with ProcessPoolExecutor(workers) as pool:
        for run, cs in runs.items():
            print(f"\n=== D-041 run: {run} {cs} ===", flush=True)
            places, test = four_state_places(store, cs), _test_set(store, cs)
            counted += _count_rows(run, store, before, places + test, cs)
            tasks = [("all", "", places)] + [(k, st, places) for k in ("state", "without") for st in STATES]
            results = list(pool.map(_fit_task, tasks))
            fits += [_fit_row(run, k, st, f, e) for k, st, f, e in results]
            full = next(f for k, _, f, _ in results if k == "all")
            draws = {}
            for k, st, f, _ in results:
                if k == "without" and f is not None:
                    draws |= cal.predict_places([p for p in places + test if p.state == st], f, seed=SEED)
            portland = _portland_paths(store, places + test, cs)
            groups = _groups(places, test, True)
            loso = state_totals(f"{run}: leave one state out", groups, draws, portland)
            totals.append(loso.assign(run=run))
            if full is not None:
                tdraws = cal.predict_places(test, full, seed=SEED)
                totals.append(state_totals(f"{run}: test set from the full fit", {"Raleigh and Durham": test},
                                           tdraws, portland).assign(run=run))  # fmt: skip
            market += _market(run, store, places + test, cs)
            print(pd.DataFrame([r for r in fits if r["run"] == run]).round(3).to_string(index=False))
            print(pd.DataFrame([r for r in market if r["run"] == run]).round(2).to_string(index=False))
            if run == "main":
                sub = None if out is None else out / "main"
                if sub is not None:
                    sub.mkdir(exist_ok=True)
                print(f"\nLeave one place out (main): {len(places)} refits ...", flush=True)
                lopo = dict(pool.map(_leave_place_joint, [(places, i) for i in range(len(places))]))
                _score("Backtest (leave one place out)", store, places, lopo, portland, sub)
                if full is not None:
                    _score("Test set (held out)", store, test, tdraws, portland, sub)
                    lopo |= tdraws
                totals.append(state_totals("main: leave one place out, summed by state", groups, lopo,
                                           portland).assign(run=run))  # fmt: skip
    print("\n=== Counts per state ===")
    print(pd.DataFrame(counted).to_string(index=False))
    if out is not None:
        pd.DataFrame(fits).to_csv(out / "fits.csv", index=False)
        pd.concat(totals).to_csv(out / "statewide.csv", index=False)
        pd.DataFrame(market).to_csv(out / "market_term.csv", index=False)
        pd.DataFrame(counted).to_csv(out / "counts.csv", index=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--fit", type=int, default=3, choices=(2, 3), help="2: the earlier spec, for reproduction"
    )
    ap.add_argument("--explore-austin", action="store_true")
    ap.add_argument(
        "--draw-terms",
        type=Path,
        nargs="?",
        const=CONFIG_DIR / "params" / "adu_anchor.yaml",
        help="write the anchor's SEs and slopes for the scenario's draws (D-030)",
    )
    ap.add_argument("--workers", type=int, default=4, help="parallel refits for --draw-terms / --four-state")
    ap.add_argument(
        "--four-state", action="store_true", help="D-039: four-state fit and leave-one-out backtest"
    )
    ap.add_argument("--statewide", action="store_true", help="D-040: statewide backtest (state totals)")
    ap.add_argument("--counts", action="store_true", help="D-041: consistent counts, four-state comparison")
    ap.add_argument("--out", type=Path, help="--four-state / --statewide: folder for the CSVs")
    a = ap.parse_args()
    if a.counts:
        counts_main(DataStore(), a.out, a.workers)
        return
    if a.statewide:
        statewide_main(DataStore(), a.out, a.workers)
        return
    if a.four_state:
        four_state_main(DataStore(), a.out, a.workers)
        return
    if a.draw_terms:
        draw_terms_main(a.draw_terms, a.workers)
        return
    if a.fit == 3:
        fit3_main(DataStore())
        return
    store = DataStore()
    mn = cal.place_years("MN", store, mn_places(), FIT_YEARS_MN)
    austin = cal.place_years("TX", store, [AUSTIN], FIT_YEARS_AUSTIN)
    fit_rows = pd.concat([mn, austin], ignore_index=True)
    test_rows = cal.place_years("NC", store, [RALEIGH, DURHAM], TEST_YEARS)
    durham = test_rows.loc[test_rows["geoid"] == DURHAM, "eligible_parcels"]
    if not (len(durham) and durham.min() >= 1000):
        smallest = int(durham.min()) if len(durham) else 0
        print(f"Durham: a roll the test uses has {smallest} ADU-eligible parcels (< 1,000) -> not tested")
        test_rows = test_rows[test_rows["geoid"] != DURHAM].reset_index(drop=True)
    if austin.empty:
        print(
            "Austin: no coded ADU rule in config/reforms/tx.csv yet -> not in the fit (pre-registered rule)"
        )

    print("\n=== Pre-registered fit (D-019) ===\nFit set:")
    describe(fit_rows)
    fit_and_test(fit_rows, test_rows)

    if a.explore_austin and austin.empty:
        assumed = {AUSTIN: [("handbook", pd.Timestamp("1990-01-01"))]}
        austin_x = cal.place_years("TX", store, [AUSTIN], FIT_YEARS_AUSTIN, assume_rules=assumed)
        print("\n=== Exploratory, NOT pre-registered, not used: Austin's uncoded rules taken as mature ===")
        describe(austin_x)
        fit_and_test(pd.concat([mn, austin_x], ignore_index=True), test_rows)


if __name__ == "__main__":
    main()
