#!/usr/bin/env python3
"""D-054 POST-HOC diagnostics (not pre-registered; written after the run was seen).

    uv run python scripts/dev/d054_posthoc.py --run reports/mm-d054

1. Per-place P10/P50/P90 under each place's leave-one-state-out (b) fold and under no effect, to show which
   places drive a state total (D-054 saved only state totals).
2. The TX total without Lubbock, whose pre-reform 2-4 unit pace collapsed after its reform (D-042).
Reuses the fold fits in fits.csv (no refit) and the run's seed, so the draws match the main run.
"""

from __future__ import annotations

import argparse
import importlib.util
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


def main(run: Path) -> None:
    store = DataStore()
    margin = {k: v.value for k, v in load_params("proforma").items()}["developer_margin"]
    sigma = load_params("mm_hazard")["mm_feasibility_dispersion"].value
    panel = mm.build_panel(store).data
    assert not set(panel["place"]) & set(d054.HOLDOUTS)
    state_of = panel.groupby("place")["state"].first().to_dict()
    classes = d042.bps_classes(store, set(panel["place"]))
    treated = sorted(panel.loc[panel["T"].notna() & (panel["eligible"] > 0), "place"].unique())
    events = d042.events_for(store, panel, treated)
    ev = {g: e for g, e in events.items() if cal.outcome_classes(e[1])}
    places, _ = d042.build(panel, classes, ev, margin, sigma, baseline="own")
    tgt = {p.geoid: p for p in d054.horizon(places)}
    fits = pd.read_csv(run / "fits.csv").set_index("fit")
    rows, tx = [], {}
    for s in d054.STATES:
        f = fits.loc[f"b_without_{s}"]
        th, se = f["per_1000"] / 1000, f["log_se"]
        ids = [g for g in tgt if state_of[g] == s]
        if not ids:
            continue
        ps = [tgt[g] for g in ids]
        dr = cal.predict_places(ps, th, se, f["alpha"], f["half"], draws=d054.DRAWS, seed=d054.SEED)
        nn = cal.benchmark_places(ps, 0.0, d054.OUTSIDE_HALF, d054.DRAWS, d054.SEED)
        for g in ids:
            p = tgt[g]
            q = np.percentile(dr[g].sum(axis=1), [10, 50, 90])
            n = np.percentile(nn[g].sum(axis=1), [10, 50, 90])
            rows.append(
                {
                    "state": s,
                    "name": p.name,
                    "test_place": g in d054.TESTS,
                    "years": len(p.years),
                    "observed": float(p.y.sum()),
                    "baseline_expected": float(p.B.sum()),
                    "b_p10": q[0],
                    "b_p50": q[1],
                    "b_p90": q[2],
                    "none_p10": n[0],
                    "none_p50": n[1],
                    "none_p90": n[2],
                }
            )
        if s == "TX":
            tx = {"b": dr, "none": nn, "ids": [g for g in ids if "Lubbock" not in tgt[g].name]}
    pd.DataFrame(rows).to_csv(run / "posthoc_places.csv", index=False)
    obs = float(sum(tgt[g].y.sum() for g in tx["ids"]))
    out = [
        d054.total_row("TX", "fit set without Lubbock (POST-HOC)", m, obs, cal.state_total(tx[m], tx["ids"]))
        for m in ("b", "none")
    ]
    pd.DataFrame(out).to_csv(run / "posthoc_tx_without_lubbock.csv", index=False)
    print(pd.DataFrame(rows).round(1).to_string())
    print(pd.DataFrame(out).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", type=Path, required=True)
    main(ap.parse_args().run)
