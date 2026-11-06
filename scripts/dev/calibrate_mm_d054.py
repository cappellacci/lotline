#!/usr/bin/env python3
"""Missing middle: statewide backtest, leave one state out, as pre-registered in D-054 (run once).

    uv run python scripts/dev/calibrate_mm_d054.py --out reports/mm-d054
    uv run python scripts/dev/calibrate_mm_d054.py --out /tmp/x --dry   # inputs and structure only, no fit

Specifications, on the same targets (D-042 events: the classes above the prior cap, years T … T + 4):
  (b) main: D-038's likelihood and own-growth baseline, no capacity modifier (`calibrate_mm.fit`);
  (c) D-042: comparison-place baseline and builder-capacity slope (`calibrate_mm.fit_capacity`);
  (a) the adopted `mm_hazard.yaml` values held fixed (in-sample reference only).
Test 1 refits (b) and (c) without each state and predicts its places jointly (`predict_places`); test 2
refits (b) without each place and sums by state. Benchmarks: no effect and D-038's outside rate.
Scores: D-040's verdict and CRPS per state total, D-049's held-out log score per place. Then τ's profile
on the full (b) fit (report only). Everything is computed before anything is written; --out gets CSVs,
draws of the state totals and a summary (no outcome panel).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore
from lotline.model import calibrate_mm as cal
from lotline.model import estimate_mm as mm
from lotline.model.baseline import crps_from_draws

_spec = importlib.util.spec_from_file_location("d042", Path(__file__).with_name("calibrate_mm_d042.py"))
d042 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d042)

TESTS = d042.TESTS  # Minneapolis, Durham city, Durham County, Raleigh
HOLDOUTS = {"2758000": "St. Paul", "3712000": "Charlotte", "37119": "Mecklenburg County"}
STATES = ("MN", "NC", "OH", "TX")
INFORMATIVE = ("NC", "TX")  # D-054: MN and OH folds have one fit place with one post year each
OUTSIDE_RATE, OUTSIDE_HALF = d042.OUTSIDE_RATE, d042.OUTSIDE_HALF
HORIZON = 5
DRAWS, SEED = 20_000, 20261106
TAU_HALF_NOTE = "half-way point held at the full (b) fit's value"


def horizon(places):
    return [p.upto(p.T + HORIZON - 1) for p in places]


def adopted() -> dict:
    h = load_params("mm_hazard")
    th = h["mm_mature_hazard_ref"]
    return {
        "theta": th.value,
        "log_se": (math.log(th.high) - math.log(th.low)) / (2 * cal.Z_95),
        "alpha": h["mm_place_effect_variance"].value,
        "half": h["mm_ramp_half_years"].value,
    }


def fit_row(label: str, f: cal.Fit, b: float = 0.0, note: str = "") -> dict:
    return {
        "fit": label,
        "per_1000": f.theta * 1000,
        "low_per_1000": f.low * 1000,
        "high_per_1000": f.high * 1000,
        "log_se": f.log_se,
        "alpha": f.alpha,
        "alpha_low": f.alpha_low,
        "alpha_high": f.alpha_high,
        "half": f.half,
        "half_low": f.half_low,
        "half_high": f.half_high,
        "b": b,
        "places": f.n_places,
        "place_years": f.n_years,
        "loglik": f.loglik,
        "note": note,
    }


def total_row(state, line, model, obs, draws) -> dict:
    p10, p50, p90 = (float(v) for v in np.percentile(draws, [10, 50, 90]))
    return {
        "state": state,
        "line": line,
        "model": model,
        "observed": obs,
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "mean": float(np.mean(draws)),
        "obs_over_p50": obs / p50 if p50 > 0 else np.nan,
        "p90_over_p10": p90 / p10 if p10 > 0 else np.inf,
        "crps": float(crps_from_draws(np.asarray(draws)[None, :], np.array([obs]))[0]),
        "verdict": cal.verdict(obs, p10, p50, p90),
    }


def paired(scores: pd.DataFrame, a: str, b: str) -> dict:
    d = (scores[a] - scores[b]).dropna()
    return {"delta": float(d.sum()), "paired_se": float(d.std(ddof=1) * math.sqrt(len(d))), "n": len(d)}


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
    test_events = {g: e for g, e in all_events.items() if g in TESTS and cal.outcome_classes(e[1])}

    rp0 = cal.retarget(panel, classes, fit_events | test_events)
    h = d042.capacity(classes, rp0, fit_events | test_events)
    lz = {g: np.log1p(v) for g, v in h.items() if pd.notna(v)}
    m = float(np.mean([lz[g] for g in fit_events if g in lz]))
    z = {g: v - m for g, v in lz.items()}

    fit_b, _ = d042.build(panel, classes, fit_events, margin, sigma, baseline="own")
    fit_c, _ = d042.build(panel, classes, fit_events, margin, sigma, z=z)
    test_b, _ = d042.build(panel, classes, test_events, margin, sigma, baseline="own")
    test_c, _ = d042.build(panel, classes, test_events, margin, sigma, z=z)
    tgt_b = {p.geoid: p for p in horizon(fit_b + test_b)}
    tgt_c = {p.geoid: p for p in horizon(fit_c + test_c)}
    fit_ids = [p.geoid for p in fit_b]
    test_ids = [p.geoid for p in test_b]
    assert [p.geoid for p in fit_c] == fit_ids, "(b) and (c) fit sets differ"
    by_state = {s: [g for g in fit_ids if state_of[g] == s] for s in STATES}
    tests_by_state = {s: [g for g in test_ids if state_of[g] == s] for s in STATES}
    tick(f"fit set {len(fit_ids)}, tests {[TESTS[g] for g in test_ids]}")
    if dry:  # structure only: no outcome printed, no fit
        for s in STATES:
            print(s, "fit:", [(tgt_b[g].name, tgt_b[g].T, len(tgt_b[g].years)) for g in by_state[s]])
            print(s, "tests:", [(TESTS[g], tgt_b[g].T, len(tgt_b[g].years)) for g in tests_by_state[s]])
        print(
            "not scored (no cap rise or no class above the cap):",
            [TESTS[g] for g in TESTS if g not in test_ids],
        )
        print("adopted values:", adopted())
        return

    # ---- full fits ----
    full_b = cal.fit(fit_b)
    tick(f"full (b): {full_b.theta * 1000:.3f} per 1,000")
    full_c = cal.fit_capacity(fit_c)
    tick(f"full (c): {full_c.fit.theta * 1000:.3f} per 1,000, b {full_c.b}")
    fits = [
        fit_row("b_full", full_b, note="13-place fit set expected"),
        fit_row("c_full", full_c.fit, full_c.b),
    ]
    a = adopted()

    # ---- test 1: leave one state out ----
    totals, place_rows, npz = [], {}, {}
    for s in STATES:
        targets = by_state[s] + tests_by_state[s]
        if not targets:
            continue
        train_b = [p for p in fit_b if state_of[p.geoid] != s]
        train_c = [p for p in fit_c if state_of[p.geoid] != s]
        fb = cal.fit(train_b)
        cf = cal.fit_capacity(train_c)
        fits += [fit_row(f"b_without_{s}", fb), fit_row(f"c_without_{s}", cf.fit, cf.b)]
        tick(f"fold {s}: (b) {fb.theta * 1000:.3f}, (c) {cf.fit.theta * 1000:.3f}")
        pb = [tgt_b[g] for g in targets]
        pc = [tgt_c[g] for g in targets]
        draws = {
            "b": cal.predict_places(pb, fb.theta, fb.log_se, fb.alpha, fb.half, draws=DRAWS, seed=SEED),
            "c": cal.predict_places(
                pc, cf.fit.theta, cf.fit.log_se, cf.fit.alpha, cf.fit.half, cf.b, DRAWS, SEED
            ),
            "a_insample": cal.predict_places(pb, a["theta"], a["log_se"], a["alpha"], a["half"], draws=DRAWS,
                                             seed=SEED),
            "none": cal.benchmark_places(pb, 0.0, OUTSIDE_HALF, DRAWS, SEED),
            "outside": cal.benchmark_places(pb, OUTSIDE_RATE, OUTSIDE_HALF, DRAWS, SEED),
        }  # fmt: skip
        lines = {"fit set": by_state[s]}
        if tests_by_state[s]:
            lines["with test places"] = targets
        for line, ids in lines.items():
            if not ids:
                continue
            obs = float(sum(tgt_b[g].y.sum() for g in ids))
            for model, d in draws.items():
                tot = cal.state_total(d, ids)
                totals.append(total_row(s, line, model, obs, tot))
                npz[f"{s}|{line}|{model}"] = tot
        for g in targets:
            p, q = tgt_b[g], tgt_c[g]
            place_rows[g] = {
                "geoid": g,
                "name": p.name,
                "state": s,
                "test_place": g in test_ids,
                "T": p.T,
                "years": len(p.years),
                "observed": float(p.y.sum()),
                "ls_b": cal.heldout_log_score(p, fb.theta, fb.log_se, fb.alpha, fb.half),
                "ls_c": cal.heldout_log_score(
                    q, cf.fit.theta, cf.fit.log_se, cf.fit.alpha, cf.fit.half, cf.b
                ),
                "ls_a_insample": cal.heldout_log_score(p, a["theta"], a["log_se"], a["alpha"], a["half"]),
                "ls_none": cal.no_effect_log_score(p),
                "ls_none_comparison": cal.no_effect_log_score(q),
                "ls_outside": cal.heldout_log_score(p, OUTSIDE_RATE, 0.0, 0.0, OUTSIDE_HALF),
            }  # fmt: skip
    totals = pd.DataFrame(totals)
    scores = pd.DataFrame(place_rows.values())
    tick("test 1 done")

    # ---- test 2: leave one place out, (b), summed by state ----
    lopo = {}
    for p in fit_b:
        f = cal.fit([q for q in fit_b if q.geoid != p.geoid])
        lopo[p.geoid] = cal.predict_places([tgt_b[p.geoid]], f.theta, f.log_se, f.alpha, f.half, draws=DRAWS,
                                           seed=SEED)[p.geoid]  # fmt: skip
        fits.append(fit_row(f"b_without_{p.name}", f))
        tick(f"lopo {p.name}: {f.theta * 1000:.3f}")
    full_tests = cal.predict_places([tgt_b[g] for g in test_ids], full_b.theta, full_b.log_se, full_b.alpha,
                                    full_b.half, draws=DRAWS, seed=SEED)  # fmt: skip
    lopo_rows = []
    for s in STATES:
        lines = {"fit set": by_state[s], "with test places": by_state[s] + tests_by_state[s]}
        for line, ids in lines.items():
            if not ids or (line == "with test places" and not tests_by_state[s]):
                continue
            obs = float(sum(tgt_b[g].y.sum() for g in ids))
            tot = cal.state_total(lopo | full_tests, ids)
            lopo_rows.append(total_row(s, line, "b_lopo", obs, tot))
            npz[f"{s}|{line}|b_lopo"] = tot
    lopo_rows = pd.DataFrame(lopo_rows)
    tick("test 2 done")

    # ---- τ, report only ----
    prof = cal.tau_profile(fit_b, [state_of[p.geoid] for p in fit_b], full_b.half)
    tau = cal.tau_summary(prof, draws=DRAWS, seed=SEED)
    tick(f"tau: {tau}")

    # ---- reading rule ----
    fs = scores[~scores["test_place"]]
    ts = scores[scores["test_place"]]
    main_lines = totals[(totals["model"] == "b") & (totals["line"] == "fit set")].set_index("state")
    transfer = all(main_lines.loc[s, "verdict"] != "missed" for s in INFORMATIVE if s in main_lines.index)
    sig = paired(fs, "ls_b", "ls_none")
    cb = paired(fs, "ls_c", "ls_b")
    reading = {
        "1_transfer_nc_tx_not_missed": transfer,
        "2_signal_b_beats_none_by_2se": bool(sig["delta"] > 2 * sig["paired_se"]),
        "3_c_beats_b_by_2se": bool(cb["delta"] > 2 * cb["paired_se"]),
    }
    reading["preferred"] = "c" if reading["3_c_beats_b_by_2se"] else "b"
    if reading["1_transfer_nc_tx_not_missed"] and reading["2_signal_b_beats_none_by_2se"]:
        reading["next"] = "propose replacing mm_hazard.yaml with the preferred full fit (own PR, Ben decides)"
    elif reading["1_transfer_nc_tx_not_missed"]:
        reading["next"] = "report the options; Ben decides (D-038 stays meanwhile)"
    else:
        reading["next"] = "D-038 values stay; report the miss"

    log_cols = [c for c in scores if c.startswith("ls_")]
    log_summary = pd.concat(
        [
            fs.groupby("state")[log_cols].sum().assign(group="fit set"),
            fs[log_cols].sum().to_frame().T.assign(group="fit set", state="all").set_index("state"),
            ts.groupby("state")[log_cols].sum().assign(group="test places"),
        ]
    ).reset_index()

    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(fits).to_csv(out / "fits.csv", index=False)
    totals.to_csv(out / "loso.csv", index=False)
    lopo_rows.to_csv(out / "lopo_state.csv", index=False)
    scores.to_csv(out / "place_scores.csv", index=False)
    log_summary.to_csv(out / "log_scores.csv", index=False)
    prof.to_csv(out / "tau_profile.csv", index=False)
    np.savez_compressed(out / "draws_state_totals.npz", **npz)
    summary = {
        "fit_set": {s: [tgt_b[g].name for g in by_state[s]] for s in STATES},
        "test_places": [TESTS[g] for g in test_ids],
        "not_scored_tests": [TESTS[g] for g in TESTS if g not in test_ids],
        "adopted_values": a,
        "full_b": fit_row("b_full", full_b),
        "full_c": fit_row("c_full", full_c.fit, full_c.b),
        "paired_b_minus_none": sig,
        "paired_c_minus_b": cb,
        "paired_a_insample_minus_none": paired(fs, "ls_a_insample", "ls_none"),
        "paired_outside_minus_none": paired(fs, "ls_outside", "ls_none"),
        "tau": tau | {"note": TAU_HALF_NOTE},
        "reading_rule": reading,
        "draws": DRAWS,
        "seed": SEED,
        "margin": margin,
        "sigma": sigma,
        "seconds": round(time.time() - t0),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=1, default=float))
    print(totals.to_string())
    print(lopo_rows.to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry", action="store_true", help="build the inputs and print their structure; no fit")
    args = ap.parse_args()
    main(args.out, args.dry)
