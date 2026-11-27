#!/usr/bin/env python3
"""Are the ADU ranges the right width? Coverage of the held-out predictive ranges, place by place.

    PYTHONPATH=src python scripts/archive/adu_range_coverage.py --out reports/adu-range-coverage --workers 7

For each state left out (D-075's tier-1 inputs, as D-088's held-out log score), Form A and Form A + P are
refitted on the other states, and each held-out place's total count over its fit years is drawn from
`joint_refit.predict` (shared draws, then the place's own new place effect). From those draws:

- whether the observed total is inside the P10-P90 range (the app's range);
- the randomized percentile (PIT): F(y - 1) + U x P(y). With counts, many places have P10 = 0 and observed 0,
  so "inside" flatters; the randomized PIT is uniform on 0-1 when the predictive is calibrated, piles up in
  the middle when the ranges are too wide, and at the ends when they are too narrow.

Two saved tables are read for the same summary, without refitting: test D's place forecasts
(`reports/adu-place-types-checked/test_d_places_scores.csv`) and D-091's forecasts with drift
(`reports/adu-drift/place_scores.csv`); their percentile is the plain one, so their PIT summary is
approximate for small counts.

Offline from cached tables; St. Paul stays out (adu_joint_refit); nothing is unblinded or written to config.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.calibrate.adu import calibrate_adu as cal
from lotline.calibrate.adu import joint_refit as jr
from lotline.io import DataStore, offline
from lotline.model import adu_owner as ao
from lotline.model import adu_types as ty

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FORMS = ("A", "A+P")
LEVELS = (0.5, 0.8, 0.9)


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TYP = _load("adu_types_refit", "adu_types_refit.py")
R, OWN = TYP.R, TYP.OWN


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def pit(draws: np.ndarray, y: float, u: float) -> float:
    """Randomized PIT of a count: P(Y < y) + u * P(Y = y), from predictive draws."""
    return float((draws < y).mean() + u * (draws == y).mean())


def place_row(form, st, pl, totals, rng) -> dict:
    y = float(np.sum(pl.y))
    p10, p50, p90 = np.percentile(totals, [10, 50, 90])
    row = {
        "form": form,
        "state": st,
        "geoid": pl.geoid,
        "name": pl.name,
        "years": len(pl.y),
        "observed": y,
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "inside": bool(p10 <= y <= p90),
        "pit": pit(totals, y, rng.random()),
        "zero_share": float((totals == 0).mean()),
    }
    for lv in LEVELS:
        lo, hi = np.percentile(totals, [50 * (1 - lv), 50 * (1 + lv)])
        row[f"inside_{int(lv * 100)}"] = bool(lo <= y <= hi)
    return row


def width(totals: np.ndarray) -> dict:
    p10, p50, p90 = np.percentile(totals, [10, 50, 90])
    return {"p10": p10, "p50": p50, "p90": p90, "ratio": p90 / max(p10, 1.0)}


def decompose(form, st, t1, fit, g, pred) -> dict:
    """The held-out state's total over its places' fit years, with each source of spread switched off:
    the state multiplier (τ = 0, so v = 1), the places' own luck (α = 0), and both (θ, β and the rule
    multipliers' draws alone, plus Poisson noise)."""
    out = {"form": form, "state": st, "places": len(t1)}
    no_tau = TYP.globals_for(fit, np.zeros(R.DRAWS), R.SEED)

    def no_luck(x):  # every place's α to 0, core cities' too where the draws carry their own (D-094)
        return dataclasses.replace(x, alpha=0.0, alpha_core=None if x.alpha_core is None else 0.0)

    for name, gg in (
        ("full", g),
        ("no_state_multiplier", no_tau),
        ("no_place_luck", no_luck(g)),
        ("shared_parameters_only", no_luck(no_tau)),
    ):
        pr = pred if name == "full" else jr.predict(t1, gg, R.SEED)
        tot = np.sum([pr[p.geoid].sum(axis=1) for p in t1], axis=0)
        for k, v in width(tot).items():
            out[f"{name}_{k}"] = v
    return out


def summarize(frame: pd.DataFrame, by: list[str], pit_col="pit") -> pd.DataFrame:
    def one(g):
        p = g[pit_col].to_numpy()
        out = {"places": len(g), "inside_p10_p90": g["inside"].mean()}
        for lv in LEVELS:
            out[f"pit_central_{int(lv * 100)}"] = float(((p >= (1 - lv) / 2) & (p <= (1 + lv) / 2)).mean())
        out["pit_below_10"] = float((p < 0.1).mean())
        out["pit_above_90"] = float((p > 0.9).mean())
        out["pit_sd"] = float(np.std(p))  # uniform: 0.289; smaller = ranges too wide
        return pd.Series(out)

    return frame.groupby(by).apply(one, include_groups=False).reset_index()


def run(a, store) -> None:
    places, _new, own = OWN.inputs(store)
    z_fit = dict(zip(own["geoid"], own["z_fit"], strict=True))
    fit_ids = {p.geoid for p in places}
    tt = TYP.type_table(store)
    fit_t = tt[tt["geoid"].isin(fit_ids)][["state", "geoid", "type_raw"]].rename(columns={"type_raw": "type"})
    mapping, _ = ty.merge_small(fit_t)
    tt["type"] = tt["type_raw"].map(mapping)
    types = dict(zip(tt["geoid"], tt["type"], strict=True))
    pz = TYP.attach([ao.with_z(p, z_fit[p.geoid]) for p in places], types)
    log(f"{len(pz)} places, {sum(len(p.y) for p in pz)} place-years")

    loso = [f"without {st}" for st in R.STATES]
    jobs = {k: {f: [p for p in pz if p.state != k.removeprefix("without ")] for f in FORMS} for k in loso}
    with ProcessPoolExecutor(a.workers) as pool:
        fits, taus = TYP.run_fits(pool, jobs, FORMS, tau_for=loso)

    rows, parts = [], []
    for st in R.STATES:
        held = [p for p in pz if p.state == st]
        if not held:
            continue
        inp = R.tier_inputs(st, store, held)
        for form in FORMS:
            fit = fits[(f"without {st}", form)]
            rng = np.random.default_rng([R.SEED, 1])
            tau_draws = cal.draw_tau(
                cal.TAU_GRID, cal.tau_probabilities(taus[(f"without {st}", form)]), R.DRAWS, rng
            )
            g = TYP.globals_for(fit, tau_draws, R.SEED)
            t1 = [inp["t1"][p.geoid] for p in held]
            pred = jr.predict(t1, g, R.SEED)
            parts.append(decompose(form, st, t1, fit, g, pred))
            prng = np.random.default_rng([R.SEED, 7])
            for pl in t1:
                rows.append(place_row(form, st, pl, pred[pl.geoid].sum(axis=1), prng))
            log(f"  {st} {form}: {len(t1)} places")
    places_df = pd.DataFrame(rows).merge(
        pd.DataFrame([{"geoid": g, "type": t} for g, t in types.items()]), on="geoid", how="left"
    )
    places_df.to_csv(a.out / "heldout_places.csv", index=False)
    pd.DataFrame(parts).to_csv(a.out / "state_width_parts.csv", index=False)


def saved_tables(out: Path) -> None:
    """Test D and D-091's drift forecasts, from their saved place tables (plain percentile as PIT)."""
    d = pd.read_csv(REPO / "reports/adu-place-types-checked/test_d_places_scores.csv", dtype={"geoid": str})
    d = d.rename(columns={"forecast": "form", "percentile": "pit"})
    summarize(d, ["form"]).assign(test="test D, within-state forecast 2021-25").to_csv(
        out / "test_d_coverage.csv", index=False
    )
    f = pd.read_csv(REPO / "reports/adu-drift/place_scores.csv", dtype={"geoid": str})
    f = f.rename(columns={"percentile": "pit"})
    summarize(f, ["variant", "forecaster"]).assign(test="D-091 forecasts, 2021-25").to_csv(
        out / "drift_coverage.csv", index=False
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--summary-only", action="store_true", help="re-summarize the saved tables only")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if not a.summary_only:
        store = DataStore()
        with offline.offline_build(store):
            run(a, store)
    saved_tables(a.out)
    p = pd.read_csv(a.out / "heldout_places.csv", dtype={"geoid": str})
    s = pd.concat(
        [
            summarize(p, ["form"]).assign(group="all"),
            summarize(p, ["form", "state"]).rename(columns={"state": "group"}),
            summarize(p, ["form", "type"]).rename(columns={"type": "group"}),
            summarize(p[p["observed"] > 0], ["form"]).assign(group="observed > 0"),
        ]
    )
    s.to_csv(a.out / "heldout_coverage.csv", index=False)
    log("\n" + s.round(3).to_string(index=False))
    (a.out / "summary.json").write_text(
        json.dumps({"heldout": s.round(4).to_dict(orient="records")}, indent=1, default=str)
    )


if __name__ == "__main__":
    main()
