#!/usr/bin/env python3
"""Estimate `adu_mature_hazard_ref` from Lotline's own post-reform places, as pre-registered in D-019.

    uv run python scripts/dev/calibrate_adu.py [--explore-austin]

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

import numpy as np
import pandas as pd

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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--fit", type=int, default=3, choices=(2, 3), help="2: the earlier spec, for reproduction"
    )
    ap.add_argument("--explore-austin", action="store_true")
    a = ap.parse_args()
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
