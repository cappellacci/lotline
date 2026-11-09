#!/usr/bin/env python3
"""Missing middle: the five-year rate r5 = θ × m(half) by profile likelihood (D-062, run once).

    uv run python scripts/dev/calibrate_mm_d062.py --out reports/mm-d062

Two fits, no folds, on D-054's fit-set place-years only (test places and holdouts are not read):
  main: D-055's adopted specification, D-054 (b), 13 places (must reproduce θ = 0.1235 per 1,000);
  beside it: D-059's (b′), 12 places without Lubbock.
For each: the best fit at each half-way point, the r5 profile and its 90% interval, the profile curve, and
the not-chosen joint draw over the grid (weights exp(ℓ_h), θ lognormal at each half from its conditional
interval) for comparison. The current scenario range (θ's interval × m(0.5)) is printed beside them.
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

_spec = importlib.util.spec_from_file_location("d054", Path(__file__).with_name("calibrate_mm_d054.py"))
d054 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d054)
d042 = d054.d042

ADOPTED_PER_1000 = 0.1235  # mm_hazard.yaml, D-055
EXCLUDE = {"4845000": "Lubbock"}  # D-059
JOINT_DRAWS, JOINT_SEED = 200_000, 20261108
Z90 = 1.644854


def conditional_theta(places, half: float, theta: float, ll: float) -> tuple[float, float]:
    """90% interval of θ with the half-way point held (α profiled)."""
    st = cal.Stack.of(places)
    lo, hi = cal._interval(
        lambda lt: cal._best_alpha(st, math.exp(lt), half)[1], math.log(theta), ll, *cal.LOG_THETA
    )
    return math.exp(lo), math.exp(hi)


def analyse(label: str, places, tick) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    p = cal.five_year_profile(places)
    tick(f"{label}: r5 {p.r5 * 1000:.4f} per 1,000 ({p.low * 1000:.4f}-{p.high * 1000:.4f})")
    bh = p.by_half.copy()
    lows, highs = [], []
    for _, r in bh.iterrows():
        lo, hi = conditional_theta(places, r["half"], r["theta"], r["loglik"])
        lows.append(lo)
        highs.append(hi)
    bh["theta_low"], bh["theta_high"] = lows, highs
    bh["weight"] = np.exp(bh["loglik"] - bh["loglik"].max())
    bh["weight"] /= bh["weight"].sum()
    tick(f"{label}: conditional intervals done")

    rng = np.random.default_rng(JOINT_SEED)
    idx = rng.choice(len(bh), size=JOINT_DRAWS, p=bh["weight"].to_numpy())
    sd = (np.log(bh["theta_high"]) - np.log(bh["theta_low"])) / (2 * Z90)
    lt = np.log(bh["theta"].to_numpy())[idx] + sd.to_numpy()[idx] * rng.standard_normal(JOINT_DRAWS)
    r5_joint = np.exp(lt) * bh["m"].to_numpy()[idx]
    q = np.percentile(r5_joint, [5, 10, 50, 90, 95])

    grid = np.exp(np.linspace(math.log(p.low / 4), math.log(p.high * 4), 41))
    st = cal.Stack.of(places)
    curve = pd.DataFrame(
        {
            "r5_per_1000": grid * 1000,
            "profile_loglik": [
                max(cal._best_alpha(st, r / cal.ramp_mean(h), h)[1] for h in cal.HALF_GRID) for r in grid
            ],
        }
    )
    curve["lr"] = 2 * (p.loglik - curve["profile_loglik"])
    best = bh.loc[bh["loglik"].idxmax()]
    out = {
        "label": label,
        "places": len(places),
        "r5_per_1000": p.r5 * 1000,
        "r5_low_per_1000": p.low * 1000,
        "r5_high_per_1000": p.high * 1000,
        "loglik": p.loglik,
        "best_half": float(best["half"]),
        "theta_per_1000": float(best["theta"]) * 1000,
        "theta_at_half_0p5_low_per_1000": p.low / cal.ramp_mean(0.5) * 1000,
        "theta_at_half_0p5_high_per_1000": p.high / cal.ramp_mean(0.5) * 1000,
        "joint_r5_per_1000": dict(zip(("p5", "p10", "p50", "p90", "p95"), (q * 1000).tolist(), strict=True)),
    }
    bh["label"] = label
    curve["label"] = label
    return out, bh, curve


def main(out: Path) -> None:
    t0 = time.time()

    def tick(msg):
        print(f"[{time.time() - t0:5.0f}s] {msg}", flush=True)

    store = DataStore()
    margin = {k: v.value for k, v in load_params("proforma").items()}["developer_margin"]
    hz = load_params("mm_hazard")
    sigma = hz["mm_feasibility_dispersion"].value
    panel = mm.build_panel(store).data
    leaked = sorted(set(panel["place"]) & set(d054.HOLDOUTS))
    assert not leaked, f"holdout places in the panel: {leaked}"
    classes = d042.bps_classes(store, set(panel["place"]))
    treated = sorted(panel.loc[panel["T"].notna() & (panel["eligible"] > 0), "place"].unique())
    all_events = d042.events_for(store, panel, treated)
    fit_events = {g: e for g, e in all_events.items() if g not in d054.TESTS and cal.outcome_classes(e[1])}

    main_places, _ = d042.build(panel, classes, fit_events, margin, sigma, baseline="own")
    assert set(EXCLUDE) <= {p.geoid for p in main_places}, "Lubbock is not in D-054's fit set"
    beside_events = {g: e for g, e in fit_events.items() if g not in EXCLUDE}
    beside_places = cal.place_inputs(
        cal.retarget(panel, classes, beside_events), list(beside_events), margin, sigma, growth="own",
        baseline_rule="fixed", zero_floor=True,
    )  # fmt: skip
    tick(f"main {len(main_places)} places, beside {len(beside_places)}")

    rows, halves, curves = [], [], []
    for label, places in (("D-055 (b), 13 places", main_places), ("D-059 (b′), 12 places", beside_places)):
        o, bh, c = analyse(label, places, tick)
        rows.append(o)
        halves.append(bh)
        curves.append(c)
    main_row = rows[0]
    assert math.isclose(main_row["theta_per_1000"], ADOPTED_PER_1000, rel_tol=0.01), (
        f"main fit {main_row['theta_per_1000']} is not the adopted {ADOPTED_PER_1000}"
    )
    m05 = cal.ramp_mean(0.5)
    th = hz["mm_mature_hazard_ref"]
    current = {
        "label": "current config: θ interval × m(0.5)",
        "r5_per_1000": th.value * m05 * 1000,
        "r5_low_per_1000": th.low * m05 * 1000,
        "r5_high_per_1000": th.high * m05 * 1000,
    }
    out.mkdir(parents=True, exist_ok=True)
    summary = {"fits": rows, "current": current, "m_half_0p5": m05}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    pd.concat(halves).round(8).to_csv(out / "by_half.csv", index=False)
    pd.concat(curves).round(6).to_csv(out / "profile_curve.csv", index=False)
    print(json.dumps({"fits": rows, "current": current}, indent=2))
    tick("done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("reports/mm-d062"))
    main(ap.parse_args().out)
