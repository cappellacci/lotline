#!/usr/bin/env python3
"""Missing middle: choose the no-reform baseline before the refit (D-092 deviation (b), 2026-11-15).

    uv run python scripts/dev/mm_baseline_choice_d092.py --out /tmp/x --dry    # place counts only
    uv run python scripts/dev/mm_baseline_choice_d092.py --out reports/mm-d092/run8-baseline  # go-ahead

Eight candidates, as pre-registered: four constructions × two noise forms.
- Constructions (all with the zero floor):
  - C0: 3 pre-years with the place's own growth index (runs 4-7);
  - C1: 6 pre-years with its own growth index;
  - C2: 6 pre-years with the state's growth index;
  - C3: 6 pre-years with no growth index.
- Noise forms:
  - Nw: one multiplier per place, variance κ;
  - Ny: independent negative binomial per year, φ.

Places are run 7's uncoded places (`mm_kappa_d092.kept_ids`), which no fit or §7 test uses. Each candidate's
parameter is fitted on the 2016 origin and scored, held out, on the 2021 origin. Only (place, origin) pairs
present under every construction are used. The rule picks the best Σ held-out log score; a candidate within
2 paired SE of the best is preferred in the order C0 > C1 > C2 > C3, then Nw > Ny. Reported, never selected:
each candidate's 2021 P10-P90 coverage (20,000 draws, seed 20261115), its parameter, and the median
predicted ÷ baseline. Stop rule: if the chosen candidate's coverage is under 0.5, the refit is not run.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.io import DataStore
from lotline.model import calibrate_mm as cal
from lotline.model import estimate_mm as mm

HERE = Path(__file__).resolve().parent


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


K = _load("mm_kappa_d092", "mm_kappa_d092.py")
d092 = K.d092

CONSTRUCTIONS = {  # in preference order (fewest changes first)
    "C0": {"baseline_rule": "fixed", "growth": "own"},
    "C1": {"baseline_rule": "long", "growth": "own"},
    "C2": {"baseline_rule": "long", "growth": "state"},
    "C3": {"baseline_rule": "long", "growth": "none"},
}
FORMS = ("w", "year")  # Nw before Ny
TRAIN, SCORE = 2016, 2021
SE_MARGIN = 2.0
DRAWS, SEED = 20_000, 20261115
COVERAGE_STOP = 0.5


def build(panel, ids, origin, p, how) -> dict[str, cal.Place]:
    sub = panel[panel["place"].isin(ids)].copy()
    sub["T"], sub["dose"] = float(origin), 0.0
    sub["eligible"] = sub["eligible"].where(sub["eligible"] > 0, 1.0)
    out = cal.place_inputs(sub, ids, p["margin"], p["sigma"], zero_floor=True, **how)
    return {q.geoid: q.upto(origin + K.HORIZON - 1) for q in out if len(q.upto(origin + K.HORIZON - 1).years)}


def coverage(places, form: str, param: float) -> tuple[float, float]:
    """(share of observed totals inside their P10-P90, median predicted total ÷ baseline total)."""
    rng = np.random.default_rng(SEED)
    inside, ratio = [], []
    for q in places:
        B = np.asarray(q.B, float)
        if param <= 0:
            mu = np.broadcast_to(B, (DRAWS, len(B)))
        elif form == "w":
            mu = rng.gamma(1 / param, param, size=DRAWS)[:, None] * B[None, :]
        else:
            mu = rng.gamma(1 / param, param, size=(DRAWS, len(B))) * B[None, :]
        tot = rng.poisson(mu).sum(axis=1)
        lo, mid, hi = np.percentile(tot, [10, 50, 90])
        inside.append(lo <= q.y.sum() <= hi)
        ratio.append(mid / B.sum() if B.sum() > 0 else np.nan)
    return float(np.mean(inside)), float(np.nanmedian(ratio))


def choose(table: pd.DataFrame, scores: pd.DataFrame) -> dict:
    best = table.loc[table["heldout"].idxmax(), "candidate"]
    near = []
    for c in table["candidate"]:
        d = scores[best] - scores[c]
        se = float(d.std(ddof=1) * np.sqrt(len(d)))
        if float(d.sum()) <= SE_MARGIN * se:
            near.append(c)
    order = [f"{c}-{f}" for c in CONSTRUCTIONS for f in FORMS]
    chosen = min(near, key=order.index)
    return {"best_score": best, "within_2se": near, "chosen": chosen}


def main(out: Path, dry: bool) -> None:
    t0 = time.time()
    p = d092.params()
    store = DataStore()
    panel = mm.build_panel(store, states=d092.STATES).data
    # D-100: St. Paul is released (D-098); D-092's runs still keep every listed place out
    panel = panel[~panel["place"].isin(d092.HOLDOUTS)]
    keep, removed = K.kept_ids(panel, store)
    built = {
        (c, o): build(panel, keep, o, p, how) for c, how in CONSTRUCTIONS.items() for o in (TRAIN, SCORE)
    }
    common = {o: set.intersection(*(set(built[(c, o)]) for c in CONSTRUCTIONS)) for o in (TRAIN, SCORE)}
    for o in (TRAIN, SCORE):
        sizes = {c: len(built[(c, o)]) for c in CONSTRUCTIONS}
        print(f"origin {o}: places per construction {sizes}; in all four: {len(common[o])}", flush=True)
    if dry:
        return

    # ================= Not run without Ben's go-ahead (D-092 §9) =================
    rows, per_place = [], {}
    order = sorted(common[SCORE])
    for c in CONSTRUCTIONS:
        train = [built[(c, TRAIN)][g] for g in sorted(common[TRAIN])]
        test = [built[(c, SCORE)][g] for g in order]
        for f in FORMS:
            fit = cal.fit_noise(train, f)
            s = cal.baseline_scores(test, f, fit.kappa)
            cov, med = coverage(test, f, fit.kappa)
            name = f"{c}-{f}"
            per_place[name] = s
            rows.append({"candidate": name, "construction": c, "form": f, "param": fit.kappa,
                         "param_low": fit.low, "param_high": fit.high, "train_places": len(train),
                         "heldout": float(np.sum(s)), "coverage_2021": cov,
                         "median_pred_over_baseline": med})  # fmt: skip
            print(f"  {name}: param {fit.kappa:.3f} ({fit.low:.3f}-{fit.high:.3f}), "
                  f"held-out {np.sum(s):.1f}, "
                  f"coverage {cov:.2f}, median pred/base {med:.2f}", flush=True)  # fmt: skip
    table = pd.DataFrame(rows)
    scores = pd.DataFrame(per_place, index=order)
    pick = choose(table, scores)
    chosen = table.set_index("candidate").loc[pick["chosen"]]
    pick["coverage_2021"] = float(chosen["coverage_2021"])
    pick["stop"] = bool(chosen["coverage_2021"] < COVERAGE_STOP)
    table["vs_best"] = table["heldout"] - table["heldout"].max()
    table["paired_se_vs_best"] = [
        float((scores[pick["best_score"]] - scores[c]).std(ddof=1) * np.sqrt(len(scores)))
        for c in table["candidate"]
    ]
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "candidates.csv", index=False)
    scores.rename_axis("geoid").to_csv(out / "place_scores.csv")
    summary = {"choice": pick, "candidates": table.to_dict("records"), "kept_places": len(keep),
               "removed": removed, "train_places": len(common[TRAIN]), "score_places": len(common[SCORE]),
               "seconds": round(time.time() - t0)}  # fmt: skip
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(pick, indent=1, default=float))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry", action="store_true", help="place counts only, no outcome read")
    a = ap.parse_args()
    main(a.out, a.dry)
