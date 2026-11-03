#!/usr/bin/env python3
"""Calibrate the missing-middle uptake hazard on the four states, as pre-registered in D-038 (run once).

    uv run python scripts/dev/calibrate_mm.py --out reports/mm-d038

Builds the D-024 panel (`estimate_mm.build_panel`, holdout-filtered), fits θ = `mm_mature_hazard_ref`, α and
the ramp's half-way point on the 16 fit places (`lotline.model.calibrate_mm`), runs the D-038 checks, the V4
leave-one-place-out backtest, the D-037 out-of-sample predictions, homes per building from local permit
files and the eligible-lot check. Everything is computed before anything is written; --out gets CSVs and a
summary (no outcome panel: outcomes stay in the data directory).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore
from lotline.model import calibrate_mm as cal
from lotline.model import estimate_mm as mm
from lotline.model import rule_tags

TESTS = {"2743000": "Minneapolis", "3719000": "Durham city", "37063": "Durham County", "3755000": "Raleigh"}
FIT_FIRST, FIT_LAST = 2013, 2025
PREREGISTERED = {  # D-038's list, checked against the panel
    "Wilson", "Morrisville", "Wake Forest", "Sanford", "Burlington", "Mooresville", "Garner", "League City",
    "Lewisville", "Austin", "Houston", "Lubbock", "Cincinnati", "Euclid", "Richfield", "St. Louis Park",
}  # fmt: skip
OUTSIDE_RATE, OUTSIDE_HALF = 0.0005, 2.5  # first draft of D-038 (Portland, Houston), the benchmark
UNIT_SOURCES = {  # (state, source) for homes per building, as D-038 lists them
    ("NC", "raleigh_permits"), ("NC", "durham_permits"), ("NC", "greensboro_permits"), ("NC", "meck_permits"),
    ("MN", "metc_residential_permits"), ("TX", "austin_permits"), ("TX", "dallas_permits"),
    ("TX", "fw_permits"), ("TX", "sa_permits"),
}  # fmt: skip


def fit_geoids(panel: pd.DataFrame) -> list[str]:
    first = panel.groupby("place").agg(T=("T", "first"), name=("name", "first"), dose=("dose", "max"))
    keep = first[
        first["T"].between(FIT_FIRST, FIT_LAST)
        & (first["dose"] > 0)
        & ~first.index.isin(list(TESTS))
        & (panel.groupby("place")["eligible"].max() > 0)
    ]
    return sorted(keep.index)


def short(name: str) -> str:
    for suffix in (" city", " town", " village"):
        name = name.removesuffix(suffix)
    return name


def fit_row(label: str, f: cal.Fit) -> dict:
    return {
        "fit": label,
        "theta": f.theta,
        "low": f.low,
        "high": f.high,
        "per_1000": f.theta * 1000,
        "alpha": f.alpha,
        "alpha_low": f.alpha_low,
        "alpha_high": f.alpha_high,
        "half": f.half,
        "half_low": f.half_low,
        "half_high": f.half_high,
        "places": f.n_places,
        "place_years": f.n_years,
        "loglik": f.loglik,
    }


def place_table(places: list[cal.Place], f: cal.Fit, margin: float, sigma: float, panel) -> pd.DataFrame:
    rows = []
    for p in places:
        pcr = float(panel.loc[panel["place"] == p.geoid, "pcr"].dropna().iloc[0])
        fr = cal.feasibility_ratio(pcr, margin, sigma)
        dose = float(p.kr[-1] / p.eligible[-1] / fr)
        rows.append(
            {
                "geoid": p.geoid,
                "name": p.name,
                "T": p.T,
                "years": len(p.years),
                "eligible": float(np.mean(p.eligible)),
                "dose": dose,
                "pcr": pcr,
                "F_ratio": fr,
                "baseline_per_year": p.beta,
                "observed": float(p.y.sum()),
                "expected_baseline": float(p.B.sum()),
                "excess_per_1000_per_year": float(
                    (p.y - p.B).sum() / p.eligible.mean() / len(p.years) * 1000
                ),
                "implied_mature_per_1000": f.theta * dose * fr * 1000,
            }
        )
    return pd.DataFrame(rows)


def units_per_building(store: DataStore) -> pd.DataFrame:
    rows = []
    for st, src in sorted(UNIT_SOURCES):
        permits = store.read(st, "permits")
        if permits is None or not (permits["source"] == src).any():
            rows.append({"state": st, "source": src, "note": "not loaded"})
            continue
        c = mm.local_counts(permits, src).reset_index()
        c = c[c["year"] >= 2016]
        rows.append(
            {
                "state": st,
                "source": src,
                "years": f"{c['year'].min()}-{c['year'].max()}" if len(c) else "",
                "homes": float(c["y"].sum()),
                "buildings": float(c["y_buildings"].sum()),
                "homes_per_building": float(c["y"].sum() / c["y_buildings"].sum()) if len(c) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def eligible_lot_check(store: DataStore, panel: pd.DataFrame, geoids: list[str]) -> pd.DataFrame:
    """Share of 2-4 unit buildings on rule-1.1 eligible parcels before and after T, where a fit place's local
    permits carry parcel numbers that match its roll (D-038 check 6)."""
    from lotline.build import eligible as eligible_rule

    rows = []
    T = panel.groupby("place")["T"].first()
    states = panel.groupby("place")["state"].first()
    for st in sorted({states[g] for g in geoids}):
        permits = store.read(st, "permits")
        if permits is None or "parcel_id" not in permits:
            continue
        mmp = permits[
            permits["building_type_std"].isin(mm.MM_TYPES)
            & permits["jurisdiction_geoid"].isin(geoids)
            & permits["parcel_id"].notna()
        ]
        if mmp.empty:
            continue
        parcels = store.read(st, "parcels")
        if parcels is None:
            continue
        for g, d in mmp.groupby("jurisdiction_geoid"):
            rolls = parcels[parcels["jurisdiction_geoid"] == g]
            if rolls.empty:
                rows.append({"geoid": g, "note": "no roll"})
                continue
            t = int(T[g])
            before = rolls["vintage"][rolls["vintage"] < t]
            vintage = int(before.max()) if len(before) else int(rolls["vintage"].min())
            roll = rolls[rolls["vintage"] == vintage]
            flag = eligible_rule.classify(roll, "missing_middle")
            elig = set(roll.loc[flag["eligible"].astype(bool).to_numpy(), "parcel_id"])
            known = set(roll["parcel_id"])
            d = d.assign(post=d["issue_year"] >= t, matched=d["parcel_id"].isin(known),
                         on_eligible=d["parcel_id"].isin(elig))  # fmt: skip
            for post, s in d.groupby("post"):
                m = s[s["matched"]]
                rows.append(
                    {
                        "geoid": g,
                        "name": str(panel.loc[panel["place"] == g, "name"].iloc[0]),
                        "roll_vintage": vintage,
                        "period": "after T" if post else "before T",
                        "buildings_with_parcel": len(s),
                        "matched_to_roll": len(m),
                        "on_eligible_share": float(m["on_eligible"].mean()) if len(m) else np.nan,
                    }
                )
    return pd.DataFrame(rows)


def main(out: Path) -> None:
    t0 = time.time()
    store = DataStore()
    pp = {k: v.value for k, v in load_params("proforma").items()}
    margin = pp["developer_margin"]
    sigma = load_params("mm_hazard")["mm_feasibility_dispersion"].value

    panel = mm.build_panel(store).data
    geoids = fit_geoids(panel)
    names = {short(n) for n in panel.loc[panel["place"].isin(geoids), "name"].unique()}
    assert names == PREREGISTERED, f"fit set differs from D-038: {sorted(names ^ PREREGISTERED)}"
    print(f"panel built ({time.time() - t0:.0f}s); fit set {len(geoids)} places", flush=True)

    places = cal.place_inputs(panel, geoids, margin, sigma)
    main_fit = cal.fit(places)
    print(f"main fit ({time.time() - t0:.0f}s): {fit_row('main', main_fit)}", flush=True)
    fits = [fit_row("main", main_fit)]
    realized = cal.realized_hazard(places)
    table = place_table(places, main_fit, margin, sigma, panel)

    checks = {
        "placebo_date_minus3": dict(shift=3),
        "growth_units_5p": dict(growth="own_5p"),
        "growth_state_comparisons": dict(growth="state"),
        "growth_none": dict(growth="none"),
        "feasibility_off": dict(feasibility=False),
        "sigma_0.25": dict(sigma=0.25),
        "sigma_0.8": dict(sigma=0.8),
        "baseline_T-5": dict(baseline_years=5),
    }
    for label, kw in checks.items():
        s = kw.pop("sigma", sigma)
        ps = cal.place_inputs(panel, geoids, margin, s, **kw)
        fits.append(fit_row(label, cal.fit(ps)) | {"note": f"{len(ps)} places"})
        print(f"  {label} ({time.time() - t0:.0f}s)", flush=True)
    firm = mm.build_panel(store, drop_tags=rule_tags.SENSITIVITIES).data
    firm_ids = fit_geoids(firm)
    fits.append(fit_row("tags_dropped", cal.fit(cal.place_inputs(firm, firm_ids, margin, sigma))))
    print(f"  tags ({time.time() - t0:.0f}s)", flush=True)

    backtest = cal.loo_backtest(places, OUTSIDE_RATE, OUTSIDE_HALF)
    backtest_g1 = cal.loo_backtest(places, OUTSIDE_RATE, OUTSIDE_HALF, hold_growth=True)
    print(f"backtest ({time.time() - t0:.0f}s)", flush=True)

    tests = []
    for p in cal.place_inputs(panel, list(TESTS), margin, sigma):
        p = p.upto(p.T + 4)
        row = {"geoid": p.geoid, "name": TESTS[p.geoid], "T": p.T, "years": len(p.years)}
        s = cal.score(p, cal.predict_total(p, main_fit.theta, main_fit.log_se, main_fit.alpha, main_fit.half))
        row |= {f"fit_{k}": v for k, v in s.items()}
        for name, rate in (("none", 0.0), ("outside", OUTSIDE_RATE)):
            b = cal.score(p, cal.benchmark_total(p, rate, OUTSIDE_HALF))
            row |= {f"{name}_{k}": v for k, v in b.items() if k != "observed"}
        tests.append(row)
    tests = pd.DataFrame(tests)

    units = units_per_building(store)
    bps_units = panel[panel["place"].isin(geoids)]
    bps_ratio = float(bps_units["y"].sum() / bps_units["y_buildings"].sum())
    try:
        lots = eligible_lot_check(store, panel, geoids)
    except Exception as e:  # reported, not fatal: the check is descriptive
        lots = pd.DataFrame([{"note": f"not done: {type(e).__name__}: {e}"}])
    print(f"done ({time.time() - t0:.0f}s)", flush=True)

    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fits).to_csv(out / "fits.csv", index=False)
    table.to_csv(out / "places.csv", index=False)
    backtest.to_csv(out / "backtest.csv", index=False)
    backtest_g1.to_csv(out / "backtest_growth_held.csv", index=False)
    tests.to_csv(out / "test_places.csv", index=False)
    units.to_csv(out / "units_per_building.csv", index=False)
    lots.to_csv(out / "eligible_lots.csv", index=False)
    pd.Series(main_fit.profile_half).rename("max_loglik").rename_axis("half").to_csv(out / "profile_half.csv")
    (out / "summary.json").write_text(
        json.dumps(
            {
                "main": fit_row("main", main_fit),
                "realized": realized,
                "bps_homes_per_building_fit_places": bps_ratio,
                "outside_rate": OUTSIDE_RATE,
                "margin": margin,
                "sigma": sigma,
                "seconds": round(time.time() - t0),
            },
            indent=2,
            default=float,
        )
    )
    print(json.dumps({"main": fit_row("main", main_fit), "realized": realized}, indent=1, default=float))
    print(pd.DataFrame(fits)[["fit", "per_1000", "low", "high", "alpha", "half", "places"]].to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    main(ap.parse_args().out)
