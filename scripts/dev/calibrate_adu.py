#!/usr/bin/env python3
"""Estimate `adu_mature_hazard_ref` from Lotline's own post-reform places, as pre-registered in D-019.

    uv run python scripts/dev/calibrate_adu.py [--explore-austin]

Fit set: Minneapolis and every other Twin Cities place with a coded ADU rule (2016-2025; St. Paul never, it is
the V5 blind test), and Austin 2016-2023 once its ADU rules are coded. Test set: Raleigh 2021-2025, and Durham
once its ADU-eligible parcel count is fixed (every roll the test uses has 1,000+). Place-years enter only with
a coded ADU rule in force by 1 July and a permit source flagging ADUs that year
(`lotline.model.calibrate_adu.place_years`). Reforms are read from config/reforms/*.csv at run time.

Prints the fit (θ with its 90% profile interval, α, the partial-rule share decision), the test set's observed
vs predicted counts with 90% predictive intervals, and the comparison with Portland's anchor.
`--explore-austin` adds an exploratory fit (not pre-registered, never used for the parameter) treating Austin's
uncoded ADU rules as a mature Handbook-equivalent rule, to preview what coding Austin will do.
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
    y = fit_rows["adu_permits"].to_numpy()
    kh, kp = fit_rows["k_handbook"].to_numpy(), fit_rows["k_partial"].to_numpy()
    share = adu.central_params()["adu_partial_rule_share"]
    ks = kh
    if (kp > kh).any():
        grid, ll, (s_lo, s_hi) = cal.profile_share(y, kh, kp, GRID)
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
            share = s_hat
            ks = np.array([cal.k_of_share(kh, kp, s) for s in grid])
        else:
            ks = cal.k_of_share(kh, kp, share)
    fit = cal.fit_anchor(y, ks)
    fitted = fit.theta * cal.k_of_share(kh, kp, share)
    print(
        f"theta = {fit.theta:.6f}  90% profile interval {fit.low:.6f}-{fit.high:.6f}  "
        f"({fit.theta * 1000:.3f} per 1,000 parcels a year at Portland's rent, value and rate)"
    )
    print(
        f"alpha = {fit.alpha:.3f}; n = {fit.n} place-years; log-likelihood {fit.loglik:.2f}; "
        f"observed {y.sum()}, fitted {fitted.sum():.0f}"
    )
    print(f"vs Portland's 4 per 1,000: {fit.theta / PORTLAND:.2f} of it")
    if test_rows.empty:
        print("Test set: no place-years")
        return fit
    kt = cal.k_of_share(test_rows["k_handbook"], test_rows["k_partial"], share)
    draws = cal.predictive(kt, fit, draws=20_000, seed=20261020)
    print("Test set (not used in the fit): observed vs predicted median (90% predictive interval)")
    for i, r in test_rows.iterrows():
        lo, mid, hi = np.percentile(draws[:, i], [5, 50, 95])
        flag = "inside" if lo <= r.adu_permits <= hi else "OUTSIDE"
        print(
            f"  {r['name']:14s} {r.year}: observed {r.adu_permits:4d}  predicted {mid:5.0f} "
            f"({lo:.0f}-{hi:.0f}), mean {kt[i] * fit.theta:5.1f}  {flag}"
        )
    lo, mid, hi = np.percentile(draws.sum(axis=1), [5, 50, 95])
    obs = int(test_rows["adu_permits"].sum())
    mean = float((kt * fit.theta).sum())
    verdict = "inside" if lo <= obs <= hi else "OUTSIDE: transport failure, reported not refitted"
    print(
        f"  TOTAL: observed {obs}, predicted median {mid:.0f}, mean {mean:.0f} (90% {lo:.0f}-{hi:.0f}) -> {verdict}"
    )
    return fit


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--explore-austin", action="store_true")
    a = ap.parse_args()
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
