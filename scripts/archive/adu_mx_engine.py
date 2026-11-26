#!/usr/bin/env python3
"""D-097's engine report: statewide ADU totals with m_x fixed, drawn from the grid, and fixed at 0.4 and 1.0.

    PYTHONPATH=src python scripts/archive/adu_mx_engine.py --out reports/adu-mx-engine [--draws 1000]

For MN, NC, OH, TX and OR: `scenarios.adu.places_from_store` (origin 2025, holdout-filtered, offline; St. Paul
left out), then `scenarios.adu.run` with state sums and own counts with drift on (D-093), once per variant:

- `fixed 0.7`: D-096 (`adu_partial_share_draws` 0);
- `grid`: m_x drawn from the grid's weights (1);
- `fold maxima`: the sensitivity weights (2);
- `fixed 0.4`, `fixed 1.0`: every draw at that m_x, with θ, α and the core term refitted there (3).

Writes `totals.csv` (every period: each year and 2027-2031) and `by_basis.csv` (per state and variant: places,
eligible parcels, recent observed ADUs a year and mean five-year current-rules ADUs, split by whether the
place has its own counts).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, offline
from lotline.model.scenarios import adu

STATES = ("MN", "NC", "OH", "TX", "OR")
ST_PAUL = "2758000"
VARIANTS = {
    "fixed 0.7": {adu.SHARE_DRAWS: 0},
    "grid": {adu.SHARE_DRAWS: 1},
    "fold maxima": {adu.SHARE_DRAWS: 2},
    "fixed 0.4": {adu.SHARE_DRAWS: 3, "adu_partial_rule_share": 0.4},
    "fixed 1.0": {adu.SHARE_DRAWS: 3, "adu_partial_rule_share": 1.0},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--draws", type=int, default=1000)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    rows, basis = [], []
    with offline.offline_build(store):
        for st in STATES:
            places = adu.places_from_store(st, store, 2025)
            places = places[places["geoid"].astype(str) != ST_PAUL].reset_index(drop=True)
            places["state"] = st
            own = places["observed_rate"].notna() & (places["eligible_parcels"] > 0)
            label = own.map({True: "own ADU counts", False: "model"})
            observed = (places["observed_rate"].fillna(0) * places["eligible_parcels"]).where(own, 0.0)
            for name, params in VARIANTS.items():
                _, totals, summ = adu.run(
                    places, 2025, draws=a.draws, summary_by="state", params={"adu_own_rate_drift": 1} | params
                )
                rows.append(summ.assign(variant=name))
                t = totals.assign(no_reform_basis=label.to_numpy(), observed_per_year=observed.to_numpy())
                g = t.groupby("no_reform_basis").agg(
                    places=("geoid", "size"),
                    eligible_parcels=("eligible_parcels", "sum"),
                    observed_per_year=("observed_per_year", "sum"),
                    current_rules_adus_mean=("current_rules_adus_mean", "sum"),
                    adu_permits_added_mean=("adu_permits_added_mean", "sum"),
                )
                basis.append(g.reset_index().assign(state=st, variant=name))
                print(st, name, flush=True)
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(a.out / "totals.csv", index=False)
    pd.concat(basis, ignore_index=True).to_csv(a.out / "by_basis.csv", index=False)
    five = out[out["period"].str.contains("-") & (out["outcome"] == "additional_homes")]
    print(five.pivot(index="state", columns="variant", values="p50").round(0).to_string())


if __name__ == "__main__":
    main()
