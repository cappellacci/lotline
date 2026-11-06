#!/usr/bin/env python3
"""Missing middle: D-054's statewide backtest with Lubbock out of the fit and targets (D-059, run once).

    uv run python scripts/dev/calibrate_mm_d059.py --out reports/mm-d059
    uv run python scripts/dev/calibrate_mm_d059.py --out /tmp/x --dry   # inputs and structure; no fit

Lubbock (4845000) is dropped as an unverified rule (its pre-UDC duplex rule is not coded).
Specifications, both with D-058's zero floor, on D-054's events, outcome classes, places and years:
  (b') main: D-054's (b), the adopted D-055 specification, with the floor;
  (d) D-058's stability rule, reported beside it.
Test 1 refits each without each state; test 2 refits (b') without each place and sums by state. Benchmarks: no
effect under each specification's own baseline, and D-038's outside rate.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore
from lotline.model import calibrate_mm as cal
from lotline.model import estimate_mm as mm

_spec = importlib.util.spec_from_file_location("d054", Path(__file__).with_name("calibrate_mm_d054.py"))
d054 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d054)
d042 = d054.d042

TESTS, HOLDOUTS, STATES, INFORMATIVE = d054.TESTS, d054.HOLDOUTS, d054.STATES, d054.INFORMATIVE
DRAWS, SEED = d054.DRAWS, d054.SEED
OUTSIDE_RATE, OUTSIDE_HALF = d054.OUTSIDE_RATE, d054.OUTSIDE_HALF
SPECS = {"b1": "fixed", "d": "stability"}  # b1 = (b′), the main specification
MAIN = "b1"
EXCLUDE = {"4845000": "Lubbock"}  # D-059: unverified rule, out of the fit and the targets


def build(panel, classes, events, margin, sigma, rule):
    rp = cal.retarget(panel, classes, events)
    return cal.place_inputs(
        rp, list(events), margin, sigma, growth="own", baseline_rule=rule, zero_floor=True
    )


def main(out: Path, dry: bool = False) -> None:
    t0 = time.time()

    def tick(msg):
        print(f"[{time.time() - t0:5.0f}s] {msg}", flush=True)

    store = DataStore()
    margin = {k: v.value for k, v in load_params("proforma").items()}["developer_margin"]
    sigma = load_params("mm_hazard")["mm_feasibility_dispersion"].value
    panel = mm.build_panel(store).data
    leaked = sorted(set(panel["place"]) & set(HOLDOUTS))
    assert not leaked, f"holdout places in the panel: {leaked}"
    state_of = panel.groupby("place")["state"].first().to_dict()
    classes = d042.bps_classes(store, set(panel["place"]))
    treated = sorted(panel.loc[panel["T"].notna() & (panel["eligible"] > 0), "place"].unique())
    all_events = d042.events_for(store, panel, treated)
    fit_events = {g: e for g, e in all_events.items() if g not in TESTS and cal.outcome_classes(e[1])}
    assert set(EXCLUDE) <= set(fit_events), "Lubbock is not in D-054's fit set"
    fit_events = {g: e for g, e in fit_events.items() if g not in EXCLUDE}
    test_events = {g: e for g, e in all_events.items() if g in TESTS and cal.outcome_classes(e[1])}

    fit = {k: build(panel, classes, fit_events, margin, sigma, r) for k, r in SPECS.items()}
    tst = {k: build(panel, classes, test_events, margin, sigma, r) for k, r in SPECS.items()}
    tgt = {k: {p.geoid: p for p in d054.horizon(fit[k] + tst[k])} for k in SPECS}
    fit_ids = [p.geoid for p in fit[MAIN]]
    test_ids = [p.geoid for p in tst[MAIN]]
    for k in SPECS:
        assert [p.geoid for p in fit[k]] == fit_ids, f"fit set differs for {k}"
    by_state = {s: [g for g in fit_ids if state_of[g] == s] for s in STATES}
    tests_by_state = {s: [g for g in test_ids if state_of[g] == s] for s in STATES}
    flags = [
        {"name": p.name, "state": state_of[p.geoid], "test_place": p.geoid in TESTS, "T": p.T,
         "unstable": p.unstable}
        for p in fit[MAIN] + tst[MAIN]
    ]  # fmt: skip
    tick(f"fit set {len(fit_ids)}, tests {[TESTS[g] for g in test_ids]}")
    if dry:  # structure and flags only: no outcome printed, no fit
        print(pd.DataFrame(flags).to_string(index=False))
        return

    fits, totals, place_rows, npz = [], [], {}, {}
    full = {}
    for k in SPECS:
        full[k] = cal.fit(fit[k])
        fits.append(d054.fit_row(f"{k}_full", full[k]))
        tick(f"full ({k}): {full[k].theta * 1000:.3f} per 1,000")

    # ---- test 1: leave one state out ----
    for s in STATES:
        targets = by_state[s] + tests_by_state[s]
        if not targets:
            continue
        draws, fold = {}, {}
        for k in SPECS:
            f = cal.fit([p for p in fit[k] if state_of[p.geoid] != s])
            fold[k] = f
            fits.append(d054.fit_row(f"{k}_without_{s}", f))
            ps = [tgt[k][g] for g in targets]
            draws[k] = cal.predict_places(ps, f.theta, f.log_se, f.alpha, f.half, draws=DRAWS, seed=SEED)
            draws[f"none_{k}"] = cal.benchmark_places(ps, 0.0, OUTSIDE_HALF, DRAWS, SEED)
        draws["outside"] = cal.benchmark_places(
            [tgt[MAIN][g] for g in targets], OUTSIDE_RATE, OUTSIDE_HALF, DRAWS, SEED
        )
        tick(f"fold {s}: " + ", ".join(f"({k}) {fold[k].theta * 1000:.3f}" for k in SPECS))
        lines = {"fit set": by_state[s]}
        if tests_by_state[s]:
            lines["with test places"] = targets
        for line, ids in lines.items():
            if not ids:
                continue
            obs = float(sum(tgt[MAIN][g].y.sum() for g in ids))
            for model, d in draws.items():
                tot = cal.state_total(d, ids)
                totals.append(d054.total_row(s, line, model, obs, tot))
                npz[f"{s}|{line}|{model}"] = tot
        for g in targets:
            p = tgt[MAIN][g]
            row = {"geoid": g, "name": p.name, "state": s, "test_place": g in test_ids, "T": p.T,
                   "years": len(p.years), "observed": float(p.y.sum()), "unstable": p.unstable}  # fmt: skip
            for k in SPECS:
                q, f = tgt[k][g], fold[k]
                row[f"ls_{k}"] = cal.heldout_log_score(q, f.theta, f.log_se, f.alpha, f.half)
                row[f"ls_none_{k}"] = cal.no_effect_log_score(q)
            row["ls_outside"] = cal.heldout_log_score(p, OUTSIDE_RATE, 0.0, 0.0, OUTSIDE_HALF)
            place_rows[g] = row
    totals = pd.DataFrame(totals)
    scores = pd.DataFrame(place_rows.values())
    tick("test 1 done")

    # ---- test 2: leave one place out, (b'), summed by state ----
    lopo = {}
    for p in fit[MAIN]:
        f = cal.fit([q for q in fit[MAIN] if q.geoid != p.geoid])
        lopo[p.geoid] = cal.predict_places(
            [tgt[MAIN][p.geoid]], f.theta, f.log_se, f.alpha, f.half, draws=DRAWS, seed=SEED
        )[p.geoid]
        fits.append(d054.fit_row(f"{MAIN}_without_{p.name}", f))
        tick(f"lopo {p.name}: {f.theta * 1000:.3f}")
    fd = full[MAIN]
    full_tests = cal.predict_places(
        [tgt[MAIN][g] for g in test_ids], fd.theta, fd.log_se, fd.alpha, fd.half, draws=DRAWS, seed=SEED
    )
    lopo_rows = []
    for s in STATES:
        for line, ids in {
            "fit set": by_state[s],
            "with test places": by_state[s] + tests_by_state[s],
        }.items():
            if not ids or (line == "with test places" and not tests_by_state[s]):
                continue
            obs = float(sum(tgt[MAIN][g].y.sum() for g in ids))
            tot = cal.state_total(lopo | full_tests, ids)
            lopo_rows.append(d054.total_row(s, line, f"{MAIN}_lopo", obs, tot))
            npz[f"{s}|{line}|{MAIN}_lopo"] = tot
    lopo_rows = pd.DataFrame(lopo_rows)
    tick("test 2 done")

    # ---- reading rule ----
    fs = scores[~scores["test_place"]]
    main_lines = totals[(totals["model"] == MAIN) & (totals["line"] == "fit set")].set_index("state")
    transfer = all(main_lines.loc[s, "verdict"] != "missed" for s in INFORMATIVE if s in main_lines.index)
    sig = d054.paired(fs, f"ls_{MAIN}", f"ls_none_{MAIN}")
    d_vs = d054.paired(fs, "ls_d", f"ls_{MAIN}")
    reading = {
        "1_transfer_nc_tx_not_missed": transfer,
        "2_signal_main_beats_none_by_2se": bool(sig["delta"] > 2 * sig["paired_se"]),
    }
    if all(reading.values()):
        reading["next"] = "propose the main full fit for mm_hazard.yaml (own PR, Ben decides)"
    elif transfer:
        reading["next"] = "report; Ben decides (D-055 values stay meanwhile)"
    else:
        reading["next"] = "D-055 values stay; report the miss"

    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fits).to_csv(out / "fits.csv", index=False)
    totals.to_csv(out / "loso.csv", index=False)
    lopo_rows.to_csv(out / "lopo_state.csv", index=False)
    scores.to_csv(out / "place_scores.csv", index=False)
    pd.DataFrame(flags).to_csv(out / "flags.csv", index=False)
    np.savez_compressed(out / "draws_state_totals.npz", **npz)
    summary = {
        "fit_set": {s: [tgt[MAIN][g].name for g in by_state[s]] for s in STATES},
        "excluded": EXCLUDE,
        "flagged_unstable": [r["name"] for r in flags if r["unstable"]],
        "test_places": [TESTS[g] for g in test_ids],
        "full": {k: d054.fit_row(f"{k}_full", full[k]) for k in SPECS},
        "paired_main_minus_none": sig,
        "paired_d_minus_main": d_vs,
        "paired_d_minus_none_d": d054.paired(fs, "ls_d", "ls_none_d"),
        "reading_rule": reading,
        "draws": DRAWS,
        "seed": SEED,
        "seconds": round(time.time() - t0),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=1, default=float))
    print(totals.to_string())
    print(lopo_rows.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--dry", action="store_true", help="build the inputs and print flags and structure; no fit"
    )
    args = ap.parse_args()
    main(args.out, args.dry)
