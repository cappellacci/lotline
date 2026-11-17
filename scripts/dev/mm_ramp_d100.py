#!/usr/bin/env python3
"""Missing middle's ramp after St. Paul (analysis plan D-100): R0, R1 and R2, chosen by D-092 §5's rule.

    uv run python scripts/dev/mm_ramp_d100.py --out /tmp/x --dry               # route split, no fit
    uv run python scripts/dev/mm_ramp_d100.py --out reports/mm-d100/run1      # Ben's go-ahead (2026-11-16)

- **R0:** C4 as on main: D-092's 93 fit places, the C0 baseline, φ 13.63, the θ_L prior, one ramp.
- **R1:** the same with St. Paul added (released 2026-11-16, D-098), one ramp.
- **R2:** R1's places, one half-way point per adoption route (`lotline.model.mm_routes`): HB 2001-covered
  Oregon places (state-required) against every other place (locally adopted); θ shared.

Each is fitted on all its places and in leave-one-state-out folds. Every fold scores the held-out state's
places of R1's set plus D-092's test places with the same three models, so the paired comparison uses the same
targets. Writes fits.csv (rows `<R>_full` and `<R>_without_<state>`, in `calibrate_mm_d092.py`'s format so
`mm_tests_d092.py --run4` can score them), place_scores.csv, routes.csv and summary.json. §5's rule needs §7's
pass counts; this script reports the held-out comparison and leaves the rule to `--tests-passed`. Offline.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from dataclasses import replace
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.model import calibrate_mm as cal
from lotline.model import estimate_mm as mm
from lotline.model import mm_routes as mr


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


d092 = _load("d092", "calibrate_mm_d092.py")
d054 = d092.d054
ST_PAUL = "2758000"
PHI = 13.632980572972555  # run 9 (D-092 deviation (b)); C4 in config
MODELS = ("R0", "R1", "R2")


def shifted(q: cal.Place, rf: mr.RouteFit, local: set[str]) -> cal.Place:
    return replace(q, age=q.age + (rf.half_state - rf.half_local)) if q.geoid in local else q


def main(out: Path, dry: bool) -> None:
    t0 = time.time()

    def tick(msg):
        print(f"[{time.time() - t0:5.0f}s] {msg}", flush=True)

    p = d092.params()
    store = DataStore()
    panel = mm.build_panel(store, states=d092.STATES, include=(ST_PAUL,)).data
    keep_out = set(d092.HOLDOUTS) - {ST_PAUL}  # Ramsey, Charlotte, Mecklenburg stay out
    panel = panel[~panel["place"].isin(keep_out)]
    state_of = panel.groupby("place")["state"].first().to_dict()
    name_of = panel.groupby("place")["name"].first().to_dict()
    rules = d092.rule_rows(store, d092.STATES)
    classes = d092.bps_classes(store, set(panel["place"]))
    all_events, _ = d092.events_d092(panel, rules)
    usable = {g: e for g, e in all_events.items() if e.classes}
    fit_events = {g: e for g, e in usable.items() if g not in d092.TESTS and g not in d092.EXCLUDE}
    test_events = {g: e for g, e in usable.items() if g in d092.TESTS}
    if ST_PAUL not in fit_events:
        raise SystemExit("St. Paul has no usable D-092 event: check its rule row and panel years")
    m_all, _ = d092.build_m(panel, classes, fit_events, p, p["s_dose"])
    m_all = cal.with_phi(m_all, PHI)
    m_test = cal.with_phi(d092.build_m(panel, classes, test_events, p, p["s_dose"])[0], PHI)
    m_r0 = [q for q in m_all if q.geoid != ST_PAUL]

    # ---- level set (C4's prior), as D-092 ----
    panel_ids = set(panel["place"])
    always = set().union(*(d092.rule_tags.always_allowed_places(r["raw"]) for r in rules.values()))
    level_ids = sorted((always & panel_ids) - set(all_events) - set(d092.TESTS) - set(d092.EXCLUDE)
                       - set(d092.HOLDOUTS))  # fmt: skip
    none_ids = set().union(*(d092.rule_tags.none_places(r["raw"]) for r in rules.values()))
    none_ids = (none_ids & panel_ids) - set(d092.TESTS) - set(d092.HOLDOUTS)
    none_rows = panel[panel["place"].isin(none_ids) & panel["year"].isin(d092.LEVEL_YEARS)]
    lv = cal.level_places(panel, level_ids, none_rows, p["margin"], p["sigma"], d092.LEVEL_YEARS,
                          p["pool_min"])  # fmt: skip

    # ---- routes ----
    metro = mr.metro_geoids()
    pop = {}
    for st in d092.STATES:
        j = store.read(st.lower(), "jurisdictions")
        pop |= dict(zip(j["geoid"].astype(str), j["pop_2020"], strict=True))
    rows = []
    for q in m_all + m_test:
        g = q.geoid
        role = "test" if g in d092.TESTS else "fit"
        route = mr.route_of(state_of[g], g, pop.get(g), metro)
        rows.append({"geoid": g, "name": name_of[g], "state": state_of[g], "role": role,
                     "pop_2020": pop.get(g), "route": route, "T": q.T,
                     "post_years": len(q.years)})  # fmt: skip
    routes = pd.DataFrame(rows)
    local = set(routes.loc[routes["route"] == mr.LOCAL, "geoid"])
    sp = all_events[ST_PAUL]
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print("R0 fit places:", len(m_r0), "| R1/R2 fit places:", len(m_all), "| test places:", len(m_test))
        print(f"St. Paul event: year {sp.year}, cap {sp.prior_cap} -> {sp.new_cap}, classes {sp.classes}")
        split = routes.groupby(["role", "state", "route"])
        print(split.agg(places=("geoid", "size"), place_years=("post_years", "sum")).to_string())
        print("locally adopted fit places:",
              sorted(routes.loc[(routes.route == mr.LOCAL) & (routes.role == "fit"), "name"]))  # fmt: skip
    if dry:
        return

    # ================= Run on Ben's go-ahead (D-100, 2026-11-16) =================
    out.mkdir(parents=True, exist_ok=True)
    routes.to_csv(out / "routes.csv", index=False)
    prior = cal.level_prior(cal.fit_level(lv), p["widening"])
    full = {"R0": cal.fit(m_r0, log_prior=prior), "R1": cal.fit(m_all, log_prior=prior)}
    tick(f"R0 {full['R0'].theta * 1000:.4f}/1,000 half {full['R0'].half}; "
         f"R1 {full['R1'].theta * 1000:.4f} half {full['R1'].half}")  # fmt: skip
    rf = mr.fit_routes(m_all, local, log_prior=prior)
    full["R2"] = rf.fit
    tick(f"R2 {rf.fit.theta * 1000:.4f}/1,000 half state {rf.half_state}, local {rf.half_local} "
         f"({rf.local_low}-{rf.local_high})")  # fmt: skip
    fits = [d054.fit_row(f"{k}_full", f) for k, f in full.items()]
    route_fits = {"full": rf}

    scores = []
    targets = {q.geoid: q for q in d054.horizon(m_all + m_test)}
    for s in d092.STATES:
        held = [g for g in targets if state_of[g] == s]
        if not held:
            continue
        lf = cal.level_prior(cal.fit_level([q for q in lv if state_of[q.geoid] != s]), p["widening"])
        k0 = [q for q in m_r0 if state_of[q.geoid] != s]
        k1 = [q for q in m_all if state_of[q.geoid] != s]
        fold = {"R0": cal.fit(k0, log_prior=lf), "R1": cal.fit(k1, log_prior=lf)}
        rff = mr.fit_routes(k1, local, log_prior=lf)
        fold["R2"] = rff.fit
        route_fits[s] = rff
        for g in held:
            q = targets[g]
            row = {"geoid": g, "name": q.name, "state": s, "test_place": g in d092.TESTS, "T": q.T,
                   "years": len(q.years), "route": mr.route_of(s, g, pop.get(g), metro)}  # fmt: skip
            for k in ("R0", "R1"):
                f = fold[k]
                row[f"ls_{k}"] = cal.heldout_log_score(q, f.theta, f.log_se, f.alpha, f.half)
            f = fold["R2"]
            row["ls_R2"] = cal.heldout_log_score(shifted(q, rff, local), f.theta, f.log_se, f.alpha, f.half)
            row["ls_none"] = cal.no_effect_log_score(q)
            scores.append(row)
        for k, f in fold.items():
            fits.append(d054.fit_row(f"{k}_without_{s}", f))
        tick(f"fold {s}: " + ", ".join(f"{k} {f.theta * 1000:.4f}" for k, f in fold.items())
             + f" | R2 halves {rff.half_state}/{rff.half_local}")  # fmt: skip
    scores = pd.DataFrame(scores)
    fs = scores[~scores["test_place"]]
    pd.DataFrame(fits).to_csv(out / "fits.csv", index=False)
    scores.to_csv(out / "place_scores.csv", index=False)
    r5 = {k: f.theta * cal.ramp_mean(f.half) for k, f in full.items()}
    r5["R2_local"] = rf.fit.theta * cal.ramp_mean(rf.half_local)
    summary = {
        "status": "D-100, run on Ben's go-ahead (2026-11-16)",
        "phi": PHI,
        "places": {"R0": len(m_r0), "R1": len(m_all), "test": len(m_test)},
        "st_paul_event": {
            "year": sp.year,
            "prior_cap": sp.prior_cap,
            "cap": sp.new_cap,
            "classes": sp.classes,
        },  # fmt: skip
        "route_counts": routes.groupby(["role", "route"]).size().to_dict(),
        "full": {k: d054.fit_row(f"{k}_full", f) for k, f in full.items()},
        "R2_halves": {
            "state": rf.half_state,
            "local": rf.half_local,
            "local_low": rf.local_low,
            "local_high": rf.local_high,
        },  # fmt: skip
        "R2_fold_halves": {s: [x.half_state, x.half_local] for s, x in route_fits.items() if s != "full"},
        "r5_per_1000": {k: v * 1000 for k, v in r5.items()},
        "paired": {
            "R1_vs_R0": cal.paired_delta(fs, "ls_R1", "ls_R0"),
            "R2_vs_R1": cal.paired_delta(fs, "ls_R2", "ls_R1"),
            "R2_vs_R0": cal.paired_delta(fs, "ls_R2", "ls_R0"),
            "R1_vs_none": cal.paired_delta(fs, "ls_R1", "ls_none"),
        },  # fmt: skip
        "se_margin": p["se_margin"],
        "seconds": round(time.time() - t0),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry", action="store_true", help="print the route split only; fit nothing")
    a = ap.parse_args()
    main(a.out, a.dry)
