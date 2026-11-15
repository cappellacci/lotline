#!/usr/bin/env python3
"""Statewide ADU scenario totals with D-091's own-counts-with-drift path off and on (development check).

    PYTHONPATH=src python scripts/dev/adu_engine_drift_check.py --out reports/adu-engine-drift [--draws 1000]

For MN, NC, OH, TX and OR: `scenarios.adu.places_from_store` (origin 2025, holdout-filtered tables, offline),
then `scenarios.adu.run` with state sums, once with `adu_own_rate_drift` 0 (the A + P engine of #432, the
observed rate as a floor) and once with 1 (D-091 adopted: own counts × drift as the no-reform rate, the
mechanism's ratio for the bill). St. Paul (V5, blind) is left out. Same seeds both ways.

Writes `totals.csv` (state, switch, outcome, P10/P50/P90/mean for 2027-2031) and `by_basis.csv` (per state
and switch: places, eligible parcels and mean five-year current-rules ADUs and ADUs added, split by
whether the place has an observed ADU rate, the 'on' run's `no_reform_basis`).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, offline
from lotline.model.scenarios import adu

STATES = ("MN", "NC", "OH", "TX", "OR")
ST_PAUL = "2758000"


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
            label = own.map({True: "own ADU counts with drift", False: "model"})
            for switch in (0, 1):
                _, totals, summ = adu.run(
                    places, 2025, draws=a.draws, summary_by="state", params={"adu_own_rate_drift": switch}
                )
                if switch == 1:
                    assert (totals["no_reform_basis"].to_numpy() == label.to_numpy()).all()
                summ = summ[summ["period"].str.contains("-")].assign(own_rate_drift=switch)
                rows.append(summ)
                totals = totals.assign(no_reform_basis=label.to_numpy())
                g = totals.groupby("no_reform_basis", dropna=False).agg(
                    places=("geoid", "size"),
                    eligible_parcels=("eligible_parcels", "sum"),
                    current_rules_adus_mean=("current_rules_adus_mean", "sum"),
                    adu_permits_added_mean=("adu_permits_added_mean", "sum"),
                )
                basis.append(g.reset_index().assign(state=st, own_rate_drift=switch))
            print(st, len(places), "places", flush=True)
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(a.out / "totals.csv", index=False)
    b = pd.concat(basis, ignore_index=True)
    b.to_csv(a.out / "by_basis.csv", index=False)
    print(out.round(0).to_string(index=False))
    print(b.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
