#!/usr/bin/env python3
"""D-097: A + place types fitted at each partial-rule share m_x on the 0.1 grid, and weights to draw it.

    PYTHONPATH=<checkout with the corrected rows>/src python scripts/dev/adu_refit_fixed_rows.py \
        adu_mx_grid.py --out reports/adu-mx-grid --config-out config/params/adu_partial_share_grid.csv

For all states and for each state left out: at every m_x in `calibrate_adu.GRID3`, with m_o at
`adu_owner_occupancy_share`, θ, α and β_core maximized (`adu_types._maximize`, as `adu_types_slopes`). The
draw weight is the average over the five leave-one-state-out folds of each fold's normalized profile
likelihood; `weight_fold_max` puts 1/5 on each fold's maximum (the sensitivity). The all-states fit at each
m_x gives θ̂, α̂ and β̂_core for the engine. Nothing is scored.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore, offline
from lotline.model import adu_owner as ao
from lotline.model import adu_screen as scr
from lotline.model import adu_types as ty
from lotline.model import calibrate_adu as cal

HERE = Path(__file__).resolve().parent


def _load(name: str, file: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TYP = _load("adu_types_refit", "adu_types_refit.py")


def places(store):
    pls, _new, own = TYP.OWN.inputs(store)
    z = dict(zip(own["geoid"], own["z_fit"], strict=True))
    tt = TYP.type_table(store)
    ids = {p.geoid for p in pls}
    ft = tt[tt["geoid"].isin(ids)][["state", "geoid", "type_raw"]].rename(columns={"type_raw": "type"})
    mapping, _ = ty.merge_small(ft)
    tt["type"] = tt["type_raw"].map(mapping)
    return TYP.attach(
        [ao.with_z(p, z[p.geoid]) for p in pls], dict(zip(tt["geoid"], tt["type"], strict=True))
    )


def fit_at(pz, m_o: float, m_x: float) -> dict:
    d = np.array([ty.type_d(p) for p in pz])
    zm = d[:, [j for j in range(d.shape[1]) if d[:, j].any()]]
    f = ty._maximize(scr.prepare(pz, cal._cvals(m_o, m_x)), zm)
    return {"theta": math.exp(f.lt), "alpha": math.exp(f.la), "core": float(f.b[0]), "loglik": f.loglik}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--config-out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    m_o = load_params("adu")["adu_owner_occupancy_share"].value
    store = DataStore()
    with offline.offline_build(store):
        pz = places(store)
    states = sorted({p.state for p in pz})
    rows = []
    for fold in ["all"] + [f"without {s}" for s in states]:
        sub = pz if fold == "all" else [p for p in pz if p.state != fold.removeprefix("without ")]
        for m in cal.GRID3:
            rows.append({"fold": fold, "m_x": m} | fit_at(sub, m_o, m))
            print(f"{fold} m_x {m}: {rows[-1]}", flush=True)
    prof = pd.DataFrame(rows)
    prof.to_csv(a.out / "profiles.csv", index=False)
    folds = prof[prof["fold"] != "all"].copy()
    folds["rel"] = folds.groupby("fold")["loglik"].transform(lambda x: np.exp(x - x.max()))
    folds["norm"] = folds.groupby("fold")["rel"].transform(lambda x: x / x.sum())
    w = folds.groupby("m_x")["norm"].mean()
    tops = folds.loc[folds.groupby("fold")["loglik"].idxmax(), "m_x"]
    wmax = tops.value_counts() / len(tops)
    grid = prof[prof["fold"] == "all"].set_index("m_x")[["theta", "alpha", "core", "loglik"]]
    grid["weight"] = w.reindex(grid.index).fillna(0.0)
    grid["weight_fold_max"] = wmax.reindex(grid.index).fillna(0.0)
    grid = grid.reset_index()
    grid["source"] = (
        f"D-097: A + P at m_x held, m_o {m_o}, {len(pz)} places, {sum(len(p.y) for p in pz)} place-years "
        "(scripts/dev/adu_mx_grid.py on the D-096 rows); weight = mean of the leave-one-state-out folds' "
        "normalized profile likelihoods"
    )
    grid.to_csv(a.config_out, index=False, float_format="%.6g")
    summary = {
        "fold_maxima": dict(
            zip(folds.loc[folds.groupby("fold")["loglik"].idxmax(), "fold"], tops, strict=True)
        ),
        "grid": grid.drop(columns="source").round(6).to_dict(orient="records"),
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(grid.drop(columns="source").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
