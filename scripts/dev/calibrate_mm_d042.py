#!/usr/bin/env python3
"""Calibrate the missing-middle uptake hazard as pre-registered in D-042 (run once).

    uv run python scripts/dev/calibrate_mm_d042.py --out reports/mm-d042

D-042 keeps D-038's likelihood (`lotline.model.calibrate_mm`) and changes three inputs:

1. the event is a place's first in-window rise in its unit cap, and the outcome counts only the BPS building
   classes above the prior cap (`prior_cap`, `event_year`, `retarget`);
2. the baseline follows same-state comparison places (`comparison_series`, `baseline_series`);
3. θ_i = θ exp(b z_i), z the centred log builder capacity (`capacity_z`, `fit_capacity`).

It then runs checks 1-9, the V4 leave-one-place-out backtest against three benchmarks, and the D-037 test
places. Everything is computed before anything is written; --out gets CSVs and a summary (no outcome panel).
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore
from lotline.model import calibrate_mm as cal
from lotline.model import estimate_mm as mm
from lotline.model import rule_tags
from lotline.model.scenarios import adu

TESTS = {"2743000": "Minneapolis", "3719000": "Durham city", "37063": "Durham County", "3755000": "Raleigh"}
FIT_FIRST, FIT_LAST = 2013, 2025
PREREGISTERED = {  # D-042's list; places with no pre-reform BPS year drop out under the stated rule
    "Wilson",
    "Morrisville",
    "Wake Forest",
    "Sanford",
    "Burlington",
    "Mooresville",
    "Garner",
    "League City",
    "Lewisville",
    "Lubbock",
    "Cincinnati",
    "Euclid",
    "Richfield",
    "St. Louis Park",
    "Austin",
    "Houston",
}
OUTSIDE_RATE, OUTSIDE_HALF = 0.0005, 2.5  # D-038's outside benchmark
STATUSES = ("coded_not_treated", "uncoded")
NO_CAP_RISE: dict[str, tuple[int, int, int]] = {}  # places whose in-window change did not raise the cap
FRED = ("PERMIT24NSA", "PERMITNSA")
VALUE_FILES = {  # parcel tables with land and building values (check 6)
    "MN": ["metc_parcels"],
    "NC": ["wake_realestate", "onemap_parcels"],
    "TX": ["stratmap_parcels", "tcad_parcels"],
}


def short(name: str) -> str:
    for suffix in (" city", " town", " village"):
        name = name.removesuffix(suffix)
    return name


def bps_classes(store: DataStore, places: set[str]) -> pd.DataFrame:
    """BPS buildings and homes by class, (geoid, year), for panel places only (holdouts never enter)."""
    cols = ["bldgs_2", "bldgs_3_4", "units_2", "units_3_4"]
    out = []
    for st in mm.STATES:
        b = store.read(st, "bps_place_year")
        b = b[b["geoid"].isin(places)]
        out.append(b.groupby(["geoid", "year"])[cols].sum(min_count=1))
    return pd.concat(out).sort_index()


def events_for(store: DataStore, panel: pd.DataFrame, geoids) -> dict[str, tuple[int, int]]:
    """geoid -> (event year, prior cap) for every place with a D-042 event."""
    pa = {k: v.value for k, v in load_params("adu").items()}
    out = {}
    for st in sorted(panel["state"].unique()):
        ref = rule_tags.apply(adu.load_reforms(st))
        rows = ref[(ref["theme"] == "missing_middle") & (ref["status"] == "in_force")]
        cov = mm._mm_coverage(st, store, rows, pa)
        for g, d in panel[(panel["state"] == st) & panel["place"].isin(geoids)].groupby("place"):
            E = cal.event_year(d["T"].iloc[0], d.set_index("year")["dose"].to_dict(), FIT_FIRST, FIT_LAST)
            if np.isnan(E):
                continue
            mine = rows[rows["jurisdiction_geoid"] == g]
            before, after = cal.prior_cap(mine, int(E) - 1, cov), cal.prior_cap(mine, int(E), cov)
            if after > before:  # D-042: the event raises the unit cap on most eligible parcels
                out[g] = (int(E), before)
            else:
                NO_CAP_RISE[g] = (int(E), before, after)
    return out


def capacity(classes: pd.DataFrame, rp: pd.DataFrame, events) -> dict[str, float]:
    """h_i: 2-4 unit homes per 1,000 eligible parcels a year, mean over E − 3 … E − 1 (years with data)."""
    out = {}
    for g, (E, _) in events.items():
        r = rp[rp["place"] == g].set_index("year")
        vals = []
        for y in range(E - 3, E):
            if (g, y) in classes.index and y in r.index and r.at[y, "eligible"] > 0:
                homes = classes.loc[(g, y), ["units_2", "units_3_4"]]
                if homes.notna().all():
                    vals.append(float(homes.sum()) / float(r.at[y, "eligible"]) * 1000)
        out[g] = float(np.mean(vals)) if vals else np.nan
    return out


def national_series(store: DataStore) -> dict[int, float]:
    """US 2-4 unit share of permitted homes by year (FRED, complete years only)."""
    s = {}
    for sid in FRED:
        path = sorted((store.root / "raw" / "fred").glob(f"*/{sid}.csv"))[-1]
        df = pd.read_csv(path, parse_dates=["observation_date"])
        g = df.groupby(df["observation_date"].dt.year)[sid]
        s[sid] = g.sum()[g.count() == 12]
    share = (s[FRED[0]] / s[FRED[1]]).dropna()
    return {int(y): float(v) for y, v in share.items()}


def land_share(store: DataStore, events) -> pd.DataFrame:
    """Median land / (land + building) value over a place's single-family detached parcels, from the vintage
    nearest its event year (check 6); flagged when that vintage is after the event (C17)."""
    rows = []
    for st, files in VALUE_FILES.items():
        for f in files:
            path = store.processed(st, "parcels") / f"{f}.parquet"
            if not path.exists():
                continue
            cols = ["jurisdiction_geoid", "vintage", "land_use_std", "land_value", "bldg_value"]
            p = pd.read_parquet(path, columns=cols)
            p = p[p["jurisdiction_geoid"].isin(events) & (p["land_use_std"] == "SF_DETACHED")]
            p = p[(p["land_value"] > 0) & (p["bldg_value"] > 0)]
            for (g, v), d in p.groupby(["jurisdiction_geoid", "vintage"]):
                share = d["land_value"] / (d["land_value"] + d["bldg_value"])
                rows.append(
                    {"geoid": g, "vintage": int(v), "file": f, "parcels": len(d), "share": share.median()}
                )
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    t["E"] = t["geoid"].map(lambda g: events[g][0])
    t["gap"] = (t["vintage"] - t["E"]).abs() + (t["vintage"] > t["E"]) * 0.5  # ties go to the earlier roll
    best = t.sort_values(["geoid", "gap"]).drop_duplicates("geoid")
    return best.assign(after_event=best["vintage"] > best["E"]).drop(columns="gap")


def build(
    panel,
    classes,
    events,
    margin,
    sigma,
    *,
    baseline="comparison",
    shift=0,
    statuses=STATUSES,
    feasibility=True,
    nat=None,
    z=None,
):
    """D-042 places for the given events. baseline: 'comparison' (main), 'own' (D-038's), 'national'."""
    rp = cal.retarget(panel, classes, events)
    series = {}
    if baseline == "comparison":
        cache = {}
        for g, (E, cap) in events.items():
            cols = cal.outcome_classes(cap)
            if cols not in cache:
                cache[cols] = cal.comparison_series(panel, classes, cols, statuses)
            by_state, pool = cache[cols]
            st = panel.loc[panel["place"] == g, "state"].iloc[0]
            pre = range(E - shift - 3, E - shift)
            series[g] = cal.baseline_series(by_state.get(st, {}), pool, pre)
    elif baseline == "national":
        series = {g: nat for g in events}
    growth = "own" if baseline == "own" else "given"
    ps = cal.place_inputs(
        rp,
        list(events),
        margin,
        sigma,
        growth=growth,
        shift=shift,
        feasibility=feasibility,
        series_by_place=series,
    )
    z = z or {}
    return [replace(p, z=float(z.get(p.geoid, 0.0))) for p in ps], rp


def fit_row(label: str, cf: cal.CapacityFit, note: str = "") -> dict:
    f = cf.fit
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
        "b": cf.b,
        "b_low": cf.b_low,
        "b_high": cf.b_high,
        "places": f.n_places,
        "place_years": f.n_years,
        "loglik": f.loglik,
        "note": note,
    }


def place_table(places, cf: cal.CapacityFit, margin, sigma, rp, h) -> pd.DataFrame:
    rows = []
    for p in places:
        r = rp[rp["place"] == p.geoid]
        pcr = r["pcr"].dropna()
        fr = cal.feasibility_ratio(float(pcr.iloc[0]), margin, sigma) if len(pcr) else 1.0
        dose = float(p.kr[-1] / p.eligible[-1] / fr) if p.eligible[-1] > 0 else np.nan
        mult = float(np.exp(cf.b * p.z))
        rows.append(
            {
                "geoid": p.geoid,
                "name": p.name,
                "event_year": p.T,
                "prior_cap": int(r["prior_cap"].iloc[0]),
                "years": len(p.years),
                "eligible": float(np.mean(p.eligible)),
                "dose_increase": dose,
                "pcr": float(pcr.iloc[0]) if len(pcr) else np.nan,
                "F_ratio": fr,
                "capacity_h": h.get(p.geoid, np.nan),
                "z": p.z,
                "capacity_multiplier": mult,
                "baseline_per_year": p.beta,
                "observed": float(p.y.sum()),
                "expected_baseline": float(p.B.sum()),
                "excess_per_1000_per_year": float(
                    (p.y - p.B).sum() / p.eligible.mean() / len(p.years) * 1000
                ),
                "implied_mature_per_1000": cf.fit.theta * mult * dose * fr * 1000,
            }
        )
    return pd.DataFrame(rows)


def summarize(bt: pd.DataFrame, prefix: str) -> dict:
    s = bt.dropna(subset=[f"{prefix}_covered"]) if f"{prefix}_covered" in bt else bt.iloc[0:0]
    return {
        "scored": len(s),
        "coverage": float(s[f"{prefix}_covered"].mean()) if len(s) else np.nan,
        "mae": float(s[f"{prefix}_error_per_1000"].abs().mean()) if len(s) else np.nan,
    }


def main(out: Path, dry: bool = False) -> None:
    t0 = time.time()

    def tick(msg):
        print(f"[{time.time() - t0:5.0f}s] {msg}", flush=True)

    store = DataStore()
    margin = {k: v.value for k, v in load_params("proforma").items()}["developer_margin"]
    sigma = load_params("mm_hazard")["mm_feasibility_dispersion"].value

    panel = mm.build_panel(store).data
    classes = bps_classes(store, set(panel["place"]))
    treated = sorted(panel.loc[panel["T"].notna() & (panel["eligible"] > 0), "place"].unique())
    all_events = events_for(store, panel, treated)
    fit_events = {g: e for g, e in all_events.items() if g not in TESTS and cal.outcome_classes(e[1])}
    test_events = {g: e for g, e in all_events.items() if g in TESTS}
    tick(f"panel and events: {len(fit_events)} fit events, {len(test_events)} test events")

    rp0 = cal.retarget(panel, classes, fit_events | test_events)
    h = capacity(classes, rp0, fit_events | test_events)
    lz = {g: np.log1p(v) for g, v in h.items() if pd.notna(v)}
    m = float(np.mean([lz[g] for g in fit_events if g in lz]))
    z = {g: v - m for g, v in lz.items()}  # centred on the fit set's mean (test places use the same centre)

    places, rp = build(panel, classes, fit_events, margin, sigma, z=z)
    names = {short(p.name) for p in places}
    assert names <= PREREGISTERED, f"fit set outside D-042's list: {sorted(names - PREREGISTERED)}"
    dropped = sorted(PREREGISTERED - names)
    tick(f"fit set {len(places)} places; not in it: {dropped}")
    if dry:  # structure only, no outcome printed and no fit
        for p in places:
            print(
                p.geoid,
                p.name,
                "event",
                p.T,
                "prior cap",
                fit_events[p.geoid][1],
                "years",
                len(p.years),
                f"z {p.z:+.2f}",
                "g range",
                np.round([p.g.min(), p.g.max()], 2),
            )
        print("tests:", {TESTS[g]: e for g, e in test_events.items()})
        print("land share:", land_share(store, fit_events)[["geoid", "vintage", "after_event"]].to_string())
        print("national share years:", min(national_series(store)), max(national_series(store)))
        return

    main_fit = cal.fit_capacity(places)
    tick(f"main: {fit_row('main', main_fit)}")
    fits = [fit_row("main", main_fit, f"{len(places)} places")]
    realized = cal.realized_hazard(cal.scaled(places, main_fit.b))
    table = place_table(places, main_fit, margin, sigma, rp, h)

    nat = national_series(store)
    cap_ids = [
        g
        for g, (_, cap) in fit_events.items()
        if short(panel.loc[panel["place"] == g, "name"].iloc[0]) not in ("Houston", "Austin")
    ]
    checks = {
        "1_placebo_date_minus3": dict(shift=3),
        "2_comparison_coded_only": dict(statuses=("coded_not_treated",)),
        "3_baseline_own_growth_D038": dict(baseline="own"),
        "4_baseline_national_2_4_share": dict(baseline="national", nat=nat),
        "5_without_houston_austin": dict(events={g: fit_events[g] for g in cap_ids}),
        "7_sigma_0.25": dict(sigma=0.25),
        "7_sigma_0.8": dict(sigma=0.8),
    }
    for label, kw in checks.items():
        ev = kw.pop("events", fit_events)
        s = kw.pop("sigma", sigma)
        ps, _ = build(panel, classes, ev, margin, s, z=z, **kw)
        fits.append(fit_row(label, cal.fit_capacity(ps), f"{len(ps)} places"))
        tick(label)

    # 6: land share as a second modifier, capacity held at its estimate
    ls = land_share(store, fit_events)
    if len(ls):
        lzl = dict(zip(ls["geoid"], ls["share"], strict=True))
        mean_ls = float(np.mean(list(lzl.values())))
        base = cal.scaled(places, main_fit.b)
        for label, keep in (("6_land_share_nearest_vintage", None), ("6_land_share_pre_event_only", False)):
            ok = set(ls["geoid"] if keep is None else ls.loc[ls["after_event"] == keep, "geoid"])
            ps = [replace(p, z=(lzl[p.geoid] - mean_ls) if p.geoid in ok else 0.0) for p in base]
            cf = cal.fit_capacity(ps)
            fits.append(
                fit_row(label, cf, f"land share known for {len(ok)} of {len(ps)}; b is the land slope")
            )
            tick(label)

    firm = mm.build_panel(store, drop_tags=rule_tags.SENSITIVITIES).data
    firm_ids = sorted(firm.loc[firm["T"].notna() & (firm["eligible"] > 0), "place"].unique())
    firm_events = {
        g: e
        for g, e in events_for(store, firm, firm_ids).items()
        if g not in TESTS and cal.outcome_classes(e[1])
    }
    ps, _ = build(firm, classes, firm_events, margin, sigma, z=z)
    fits.append(fit_row("8_tags_dropped", cal.fit_capacity(ps), f"{len(ps)} places"))
    tick("8 tags")

    bt = cal.loo_backtest(places, OUTSIDE_RATE, OUTSIDE_HALF, slopes=cal.CAPACITY_SLOPES)
    tick("backtest")
    bt_held = cal.loo_backtest(
        places, OUTSIDE_RATE, OUTSIDE_HALF, slopes=cal.CAPACITY_SLOPES, hold_growth=True
    )
    tick("backtest, index held at 1")
    own, _ = build(panel, classes, fit_events, margin, sigma, baseline="own")
    bt38 = cal.loo_backtest(own, OUTSIDE_RATE, OUTSIDE_HALF)  # the D-038 specification, same outcome
    bt = bt.merge(
        bt38[["geoid", *[c for c in bt38 if c.startswith("fit_")]]].rename(
            columns=lambda c: c.replace("fit_", "d038_")
        ),
        on="geoid",
        how="left",
    )
    tick("backtest, D-038 specification")

    tests = []
    tps, _ = build(panel, classes, test_events, margin, sigma, z=z)
    for p in tps:
        p = cal.scaled([p.upto(p.T + 4)], main_fit.b)[0]
        f = main_fit.fit
        row = {
            "geoid": p.geoid,
            "name": TESTS[p.geoid],
            "event_year": p.T,
            "prior_cap": test_events[p.geoid][1],
            "years": len(p.years),
            "z": p.z,
        }
        row |= {
            f"fit_{k}": v
            for k, v in cal.score(p, cal.predict_total(p, f.theta, f.log_se, f.alpha, f.half)).items()
        }
        for name, rate in (("none", 0.0), ("outside", OUTSIDE_RATE)):
            b = cal.score(p, cal.benchmark_total(p, rate, OUTSIDE_HALF))
            row |= {f"{name}_{k}": v for k, v in b.items() if k != "observed"}
        tests.append(row)
    tests = pd.DataFrame(tests)
    tick("test places")

    scores = {k: summarize(bt, k) for k in ("fit", "none", "outside", "d038")}
    scores["fit_index_held"] = summarize(bt_held, "fit")
    reading = {
        "mae_10pct_below_none": bool(scores["fit"]["mae"] <= 0.9 * scores["none"]["mae"]),
        "coverage_at_least_60pct": bool(scores["fit"]["coverage"] >= 0.6),
        "alpha_below_d038_7.29": bool(main_fit.fit.alpha < 7.29),
    }
    reading["confounders_supported"] = all(reading.values())

    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fits).to_csv(out / "fits.csv", index=False)
    table.to_csv(out / "places.csv", index=False)
    bt.to_csv(out / "backtest.csv", index=False)
    bt_held.to_csv(out / "backtest_index_held.csv", index=False)
    tests.to_csv(out / "test_places.csv", index=False)
    ls.to_csv(out / "land_share.csv", index=False)
    pd.Series(main_fit.profile_b).rename("max_loglik").rename_axis("b").to_csv(out / "profile_b.csv")
    pd.Series(main_fit.fit.profile_half).rename("max_loglik").rename_axis("half").to_csv(
        out / "profile_half.csv"
    )
    events_table = pd.DataFrame(
        [
            {
                "geoid": g,
                "name": panel.loc[panel["place"] == g, "name"].iloc[0],
                "event_year": e,
                "prior_cap": c,
                "test_place": g in TESTS,
            }
            for g, (e, c) in sorted(all_events.items())
        ]
    )
    events_table.to_csv(out / "events.csv", index=False)
    summary = {
        "main": fit_row("main", main_fit),
        "realized": realized,
        "backtest": scores,
        "reading_rule": reading,
        "dropped_from_preregistered_list": dropped,
        "no_cap_rise": {g: list(v) for g, v in NO_CAP_RISE.items()},
        "margin": margin,
        "sigma": sigma,
        "seconds": round(time.time() - t0),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=1, default=float))
    print(pd.DataFrame(fits)[["fit", "per_1000", "low", "high", "alpha", "half", "b", "places"]].to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry", action="store_true", help="build the inputs and print the fit set; no fit")
    a = ap.parse_args()
    main(a.out, a.dry)
