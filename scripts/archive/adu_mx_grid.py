#!/usr/bin/env python3
"""D-097: A + place types fitted at each partial-rule share m_x on the 0.1 grid, and weights to draw it.

    uv run python scripts/archive/adu_mx_grid.py --out reports/adu-mx-grid \
        --config-out config/params/adu_partial_share_grid.csv
    uv run lotline calibrate --run --step adu_partial_share_grid [--write]   # the same, from the registry

For all states and for each state left out: at every m_x in `calibrate_adu.GRID3`, with m_o at
`adu_owner_occupancy_share`, θ, α and β_core maximized (`adu_types._maximize`, as `adu_types_slopes`). The
draw weight is the average over the five leave-one-state-out folds of each fold's normalized profile
likelihood; `weight_fold_max` puts 1/5 on each fold's maximum (the sensitivity). The all-states fit at each
m_x gives θ̂, α̂ and β̂_core for the engine. Nothing is scored.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore, offline
from lotline.model import adu_fit_set as fs
from lotline.model import adu_refit as rf
from lotline.model import calibrate_adu as cal

places = (
    fs.d096_places
)  # the D-096 inputs (fit set, unknown years cut, owner z, types); other scripts call it
fit_at = rf.fit_at_mx


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
    rows = []
    for fold, sub in rf.folds_of(pz):
        for m in cal.GRID3:
            rows.append({"fold": fold, "m_x": m} | fit_at(sub, m_o, m))
            print(f"{fold} m_x {m}: {rows[-1]}", flush=True)
    prof = pd.DataFrame(rows)
    prof.to_csv(a.out / "profiles.csv", index=False)
    grid = rf.grid_table(prof, m_o, len(pz), sum(len(p.y) for p in pz))
    a.config_out.write_text(rf.grid_csv(grid))
    folds = prof[prof["fold"] != "all"]
    top = folds.loc[folds.groupby("fold")["loglik"].idxmax()]
    summary = {
        "fold_maxima": dict(zip(top["fold"], top["m_x"], strict=True)),
        "grid": grid.drop(columns="source").round(6).to_dict(orient="records"),
    }
    (a.out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(grid.drop(columns="source").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
