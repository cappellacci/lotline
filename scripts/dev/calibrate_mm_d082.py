#!/usr/bin/env python3
"""Missing middle: D-082's five-state refit with the level component and challengers (PROPOSED; not run).

    uv run python scripts/dev/calibrate_mm_d082.py --out /tmp/x --dry     # structure only: no counts, no fit
    uv run python scripts/dev/calibrate_mm_d082.py --out reports/mm-d082  # ONLY with Ben's go-ahead (§9)

D-082 is proposed, not approved. Without --dry this script fits on real data, so it must not be run until Ben
approves D-082 and asks for the run (D-082 §9: each run needs his go-ahead after its code is pushed).

What it wires (D-082 §1, §1b, §5; analysis plan on branch ws/mm-review):
- Fit set: every place in MN, NC, OH, TX and OR with a D-082 event in 2013-2025
  (`calibrate_mm.classify_event`: a cap rise, D-042, or a `[standards]` row, dose class S), under the
  accepted rule rows. Oregon joins.
- Test places (Minneapolis, Durham city, Durham County, and Raleigh as in D-054 to D-059) are held out of the
  fit and scored as before. Lubbock stays out (D-059). St. Paul, Ramsey County, Charlotte and Mecklenburg are
  asserted absent from the panel (holdouts; never read).
- M: D-054 (b) with D-058's zero floor (D-059 (b')), on these events, with S events at dose 1/3.
- L: always-allowed places (`rule_tags.always_allowed_places`, no event) fitted on the level model with the
  no-rule level from coded "none" places in the same state and size band (`calibrate_mm.level_places`).
- C1 (Oregon not-yet-treated growth index), C3 (u_i's mean shifted by the pre-reform pace) and C4 (θ_L as a
  lognormal prior on M's θ); C2 needs the permit counts (§2) and is not here.
- Leave one state out over the five states: held-out log scores for M and each challenger; §5's rule
  (`calibrate_mm.select_model`) once tests A-C have pass counts (`--tests-passed`, a JSON file).
- Sensitivities on the full fit: S excluded, S dose 1, and the tag sensitivity read on the event-setting row
  (`rule_tags.dropped_places(rule="event_setting_row")`).
"""

from __future__ import annotations

import argparse
import importlib.util
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

_spec = importlib.util.spec_from_file_location("d054", Path(__file__).with_name("calibrate_mm_d054.py"))
d054 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d054)
d042 = d054.d042

STATES = ("MN", "NC", "OH", "TX", "OR")
TESTS = d042.TESTS  # Minneapolis, Durham city, Durham County, Raleigh (scored as in D-054 to D-059)
HOLDOUTS = {
    "2758000": "St. Paul",
    "27123": "Ramsey County",
    "3712000": "Charlotte",
    "37119": "Mecklenburg County",
}
EXCLUDE = {  # out of the fit, the targets and the level set
    "4845000": "Lubbock",  # D-059: no usable source for its pre-UDC rule (#398 confirms)
    "2754214": "Richfield",  # D-082 §1b: no cap rise, and its effective date is unresolved
}
FIRST, LAST = d042.FIT_FIRST, d042.FIT_LAST  # D-042's event window, 2013-2025
EVENT_YEARS = range(FIRST, LAST + 1)
LEVEL_YEARS = range(2016, 2026)  # the level model's years: the D-054 fit's outcome years
DRAWS, SEED = d054.DRAWS, d054.SEED
CHALLENGERS = ("C1", "C3", "C4")
TAGS = tuple(rule_tags.SENSITIVITIES)


def params() -> dict:
    pm = load_params("mm")
    return {
        "margin": {k: v.value for k, v in load_params("proforma").items()}["developer_margin"],
        "sigma": load_params("mm_hazard")["mm_feasibility_dispersion"].value,
        "s_dose": pm["mm_standards_dose_increase"].value,
        "s_dose_high": pm["mm_standards_dose_increase"].high,
        "pool_min": int(pm["mm_level_pool_min_places"].value),
        "widening": pm["mm_level_prior_widening"].value,
        "se_margin": pm["mm_challenger_se_margin"].value,
    }


def bps_classes(store: DataStore, places: set[str]) -> pd.DataFrame:
    """`calibrate_mm_d042.bps_classes` over the five states (it reads the four D-024 states only)."""
    cols = ["bldgs_2", "bldgs_3_4", "units_2", "units_3_4"]
    out = []
    for st in STATES:
        b = store.read(st, "bps_place_year")
        b = b[b["geoid"].isin(places)]
        out.append(b.groupby(["geoid", "year"])[cols].sum(min_count=1))
    return pd.concat(out).sort_index()


def rule_rows(store: DataStore, states) -> dict:
    """Per state: raw in-force missing-middle rows, the same after `rule_tags.apply`, and their coverage."""
    pa = {k: v.value for k, v in load_params("adu").items()}
    out = {}
    for st in states:
        raw = adu.load_reforms(st)
        raw = raw[(raw["theme"] == "missing_middle") & (raw["status"] == "in_force")]
        applied = rule_tags.apply(raw)
        out[st] = {"raw": raw, "applied": applied, "cov": mm._mm_coverage(st, store, applied, pa)}
    return out


def events_d082(panel: pd.DataFrame, rules: dict) -> tuple[dict[str, cal.Event], dict]:
    """geoid -> Event for every panel place with a D-082 event in the window (the first cap rise or standards
    row at or after its first in-window dose change, `calibrate_mm.first_event`); and the places with a dose
    change but no event (geoid -> (year, prior cap, cap after) at that first change)."""
    events, no_event = {}, {}
    for st, d_st in panel.groupby("state"):
        r = rules[st]
        for g, d in d_st.groupby("place"):
            mine = r["applied"][r["applied"]["jurisdiction_geoid"].astype(str) == g]
            E = cal.event_year(d["T"].iloc[0], d.set_index("year")["dose"].to_dict(), FIRST, LAST)
            Es = cal.standards_year(mine, FIRST, LAST)
            cands = [x for x in (E, Es) if pd.notna(x)]
            if not cands:
                continue
            ev, misses = cal.first_event(mine, min(cands), r["cov"], LAST)
            if ev is None:
                no_event[g] = misses[0]
            else:
                events[g] = ev
    return events, no_event


def tag_drops(rules: dict, drop, rule: str) -> set[str]:
    out = set()
    for r in rules.values():
        cov = r["cov"] if rule == "event_setting_row" else None
        years = EVENT_YEARS if rule == "event_setting_row" else LEVEL_YEARS
        out |= rule_tags.dropped_places(r["applied"], years, drop, rule=rule, coverage=cov)
    return out


def build_m(panel, classes, events, p, s_dose):
    """M's places (D-059 (b')): own-growth baseline, fixed window, zero floor; S events at `s_dose`."""
    rp = cal.retarget_events(panel, classes, events, s_dose)
    return cal.place_inputs(rp, list(events), p["margin"], p["sigma"], growth="own", zero_floor=True), rp


def build_c1(panel, classes, events, all_events, p, s_dose):
    """C1: Oregon places' growth index from Oregon places with no cap rise yet that year; others as M."""
    rp = cal.retarget_events(panel, classes, events, s_dose)
    state_of = panel.groupby("place")["state"].first()
    ev_years = {g: float(e.year) for g, e in all_events.items()}
    or_ids = [g for g in events if state_of[g] == "OR"]
    cache, series = {}, {}
    for g in or_ids:
        cols = events[g].classes
        if cols not in cache:
            cache[cols] = cal.not_yet_treated_series(panel, classes, cols, ev_years, "OR")
        series[g] = cache[cols]
    others = [g for g in events if state_of[g] != "OR"]
    a = cal.place_inputs(rp, others, p["margin"], p["sigma"], growth="own", zero_floor=True)
    b = cal.place_inputs(rp, or_ids, p["margin"], p["sigma"], growth="given", series_by_place=series,
                         zero_floor=True)  # fmt: skip
    order = {g: i for i, g in enumerate(events)}
    return sorted(a + b, key=lambda q: order[q.geoid])


def with_z(places, pace, fit_ids):
    z = cal.conditional_z(pace, fit_ids)
    return [replace(q, z=float(z.get(q.geoid, 0.0))) for q in places]


def main(out: Path, dry: bool = False, tests_passed: Path | None = None) -> None:
    t0 = time.time()

    def tick(msg):
        print(f"[{time.time() - t0:5.0f}s] {msg}", flush=True)

    p = params()
    store = DataStore()
    panel = mm.build_panel(store, states=STATES).data
    leaked = sorted(set(panel["place"]) & set(HOLDOUTS))
    assert not leaked, f"holdout places in the panel: {leaked}"
    state_of = panel.groupby("place")["state"].first().to_dict()
    name_of = panel.groupby("place")["name"].first().to_dict()
    band_of = panel.groupby("place")["band"].first().to_dict()
    rules = rule_rows(store, STATES)
    classes = bps_classes(store, set(panel["place"]))
    all_events, no_event = events_d082(panel, rules)
    usable = {g: e for g, e in all_events.items() if e.classes}
    fit_events = {g: e for g, e in usable.items() if g not in TESTS and g not in EXCLUDE}
    test_events = {g: e for g, e in usable.items() if g in TESTS}

    # ---- level set L and the "none" comparison places (fixed from rule rows, D-082 §1b) ----
    panel_ids = set(panel["place"])
    always = set().union(*(rule_tags.always_allowed_places(r["raw"]) for r in rules.values()))
    level_ids = sorted((always & panel_ids) - set(all_events) - set(TESTS) - set(EXCLUDE) - set(HOLDOUTS))
    none_ids = set().union(*(rule_tags.none_places(r["raw"]) for r in rules.values()))
    none_ids = (none_ids & panel_ids) - set(TESTS) - set(HOLDOUTS)
    none_rows = panel[panel["place"].isin(none_ids) & panel["year"].isin(LEVEL_YEARS)]

    # ---- tag sensitivity, both readings (D-082 §1: report the event-setting-row reading) ----
    drops = {
        f"{rule}:{t}": tag_drops(rules, [t], rule)
        for rule in ("event_setting_row", "any_event_row")
        for t in TAGS
    }

    m_fit, rp = build_m(panel, classes, fit_events, p, p["s_dose"])
    m_test, _ = build_m(panel, classes, test_events, p, p["s_dose"])
    fit_ids = [q.geoid for q in m_fit]
    test_ids = [q.geoid for q in m_test]
    lv = cal.level_places(panel, level_ids, none_rows, p["margin"], p["sigma"], LEVEL_YEARS, p["pool_min"])

    struct = []
    for g, e in sorted(usable.items(), key=lambda kv: (state_of[kv[0]], name_of[kv[0]])):
        role = "test" if g in TESTS else ("excluded" if g in EXCLUDE else "fit")
        built = g in fit_ids or g in test_ids
        role = role if built else f"{role} (no pre/post year)"
        struct.append({"state": state_of[g], "geoid": g, "name": name_of[g], "role": role,
                       "event": e.year, "class": e.dose_class, "prior_cap": e.prior_cap, "cap": e.new_cap,
                       "outcome": "+".join(c.removeprefix("bldgs_") for c in e.classes), "level_set": False,
                       **{k: g in v for k, v in drops.items()}})  # fmt: skip
    lv_ids = {q.geoid for q in lv}
    for g in level_ids:
        pool = cal.level_rate(none_rows, state_of[g], int(band_of[g]), p["pool_min"])
        struct.append({"state": state_of[g], "geoid": g, "name": name_of[g],
                       "role": "level" if g in lv_ids else "level (no year or zero dose)", "event": np.nan,
                       "class": "", "prior_cap": np.nan, "cap": np.nan, "outcome": "2+3_4", "level_set": True,
                       "level_pool": f"{pool['pool']} ({pool['places']} none places)",
                       **{k: g in v for k, v in drops.items()}})  # fmt: skip
    struct = pd.DataFrame(struct)
    tick(f"fit set {len(fit_ids)}, tests {[TESTS[g] for g in test_ids]}, level set {len(lv)}, "
         f"none places {len(none_ids)}")  # fmt: skip
    if dry:  # structure only: places, event years, dose class, prior caps, L-set membership; no counts
        with pd.option_context("display.width", 250, "display.max_rows", 500, "display.max_columns", 30):
            old = [c for c in struct if c.startswith("any_event_row:")]
            print(struct.drop(columns=old).to_string(index=False))
        print("\nby state:")
        print(struct.groupby(["state", "role"]).size().unstack(fill_value=0).to_string())
        print("\nS events:", {name_of[g]: e.year for g, e in usable.items() if e.dose_class == "S"})
        print("no event (in-window change raised no cap):",
              {name_of[g]: v for g, v in sorted(no_event.items()) if g not in TESTS})  # fmt: skip
        print("excluded:", EXCLUDE, "| Lubbock has an event:", "4845000" in usable)
        print("holdouts asserted absent:", sorted(HOLDOUTS.values()))
        print("tag drops, event-setting-row rule:",
              {k.split(":")[1]: sorted(name_of.get(g, g) for g in v if g in fit_events)
               for k, v in drops.items() if k.startswith("event_setting_row")})  # fmt: skip
        print("tag drops, old any-row rule (fit places):",
              {k.split(":")[1]: len([g for g in v if g in fit_events])
               for k, v in drops.items() if k.startswith("any_event_row")})  # fmt: skip
        return

    # ================= Not run without Ben's go-ahead (D-082 §9) =================
    targets_by_id = {q.geoid: q for q in d054.horizon(m_fit + m_test)}
    pace = d042.capacity(
        classes, rp, {g: (e.year, e.prior_cap) for g, e in {**fit_events, **test_events}.items()}
    )
    c1_fit = build_c1(panel, classes, fit_events, all_events, p, p["s_dose"])
    c1_test = build_c1(panel, classes, test_events, all_events, p, p["s_dose"])
    c1_targets = {q.geoid: q for q in d054.horizon(c1_fit + c1_test)}

    fits, full = [], {}
    full["M"] = cal.fit(m_fit)
    r5 = cal.five_year_profile(m_fit)
    full["L"] = cal.fit_level(lv)
    full["C1"] = cal.fit(c1_fit)
    c3 = cal.fit_capacity(with_z(m_fit, pace, fit_ids))
    full["C3"] = c3.fit
    full["C4"] = cal.fit(m_fit, log_prior=cal.level_prior(full["L"], p["widening"]))
    for k, f in full.items():
        fits.append(d054.fit_row(f"{k}_full", f, b=c3.b if k == "C3" else 0.0))
        tick(f"full {k}: {f.theta * 1000:.4f} per 1,000")

    # ---- sensitivities on the full fit ----
    for variant in ("exclude", "dose1"):
        ev, sd = cal.standards_variant(fit_events, variant, p["s_dose"])
        if variant == "dose1":
            sd = p["s_dose_high"]
        fits.append(d054.fit_row(f"M_S_{variant}", cal.fit(build_m(panel, classes, ev, p, sd)[0])))
    for t in TAGS:
        keep = {g: e for g, e in fit_events.items() if g not in drops[f"event_setting_row:{t}"]}
        fits.append(d054.fit_row(f"M_drop_{t}", cal.fit(build_m(panel, classes, keep, p, p["s_dose"])[0])))
    tick("sensitivities done")

    # ---- leave one state out: held-out log scores ----
    rows = []
    for s in STATES:
        held = [g for g in fit_ids + test_ids if state_of[g] == s]
        if not held:
            continue
        keep_m = [q for q in m_fit if state_of[q.geoid] != s]
        fold = {"M": cal.fit(keep_m), "C1": cal.fit([q for q in c1_fit if state_of[q.geoid] != s])}
        keep_ids = [q.geoid for q in keep_m]
        c3f = cal.fit_capacity(with_z(keep_m, pace, keep_ids))
        fold["C3"] = c3f.fit
        lf = cal.fit_level([q for q in lv if state_of[q.geoid] != s])
        fold["C4"] = cal.fit(keep_m, log_prior=cal.level_prior(lf, p["widening"]))
        z = cal.conditional_z(pace, keep_ids)
        for g in held:
            q = targets_by_id[g]
            row = {
                "geoid": g,
                "name": q.name,
                "state": s,
                "test_place": g in TESTS,
                "T": q.T,
                "years": len(q.years),
            }
            for k in ("M", "C4"):
                f = fold[k]
                row[f"ls_{k}"] = cal.heldout_log_score(q, f.theta, f.log_se, f.alpha, f.half)
            f = fold["C1"]
            row["ls_C1"] = cal.heldout_log_score(c1_targets[g], f.theta, f.log_se, f.alpha, f.half)
            f = fold["C3"]
            qz = replace(q, z=float(z.get(g, 0.0)))
            row["ls_C3"] = cal.heldout_log_score(qz, f.theta, f.log_se, f.alpha, f.half, b=c3f.b)
            row["ls_none"] = cal.no_effect_log_score(q)
            rows.append(row)
        for k, f in fold.items():
            fits.append(d054.fit_row(f"{k}_without_{s}", f, b=c3f.b if k == "C3" else 0.0))
        tick(f"fold {s}: " + ", ".join(f"{k} {f.theta * 1000:.4f}" for k, f in fold.items()))
    scores = pd.DataFrame(rows)
    fs = scores[~scores["test_place"]]

    selection = {"status": "pending: tests A-C have no pass counts yet (D-082 §7)"}
    if tests_passed is not None:
        passed = json.loads(tests_passed.read_text())
        sel = cal.select_model(fs, passed, "M", CHALLENGERS, p["se_margin"])
        selection = {
            "chosen": sel["chosen"],
            "table": sel["table"].to_dict("records"),
            "tests_passed": passed,
        }

    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fits).to_csv(out / "fits.csv", index=False)
    scores.to_csv(out / "place_scores.csv", index=False)
    struct.to_csv(out / "structure.csv", index=False)
    summary = {
        "status": "D-082 proposed; run with Ben's go-ahead",
        "fit_set": {s: [name_of[g] for g in fit_ids if state_of[g] == s] for s in STATES},
        "test_places": [TESTS[g] for g in test_ids],
        "level_set": [q.name for q in lv],
        "excluded": EXCLUDE,
        "full": {k: d054.fit_row(f"{k}_full", f) for k, f in full.items()},
        "r5_M": {"r5": r5.r5, "low": r5.low, "high": r5.high},
        "c3_slope": {"c": c3.b, "low": c3.b_low, "high": c3.b_high},
        "c4_prior": dict(zip(("log_mean", "log_sd"), cal.level_prior(full["L"], p["widening"]), strict=True)),
        "paired_vs_M": {c: cal.paired_delta(fs, f"ls_{c}", "ls_M") for c in CHALLENGERS},
        "paired_M_vs_none": cal.paired_delta(fs, "ls_M", "ls_none"),
        "selection": selection,
        "seconds": round(time.time() - t0),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--dry", action="store_true", help="structure only: places, events, classes; no counts, no fit"
    )
    ap.add_argument("--tests-passed", type=Path, help="JSON {model: tests A-C passed} for §5's rule")
    args = ap.parse_args()
    main(args.out, args.dry, args.tests_passed)
