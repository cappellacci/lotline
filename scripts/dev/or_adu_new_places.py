"""Counts behind §3 of `reports/or/adu-coverage-and-undercount.md`: ADU permits in Oregon's new places.

    uv run python scripts/dev/or_adu_new_places.py

Descriptive counts only (data thread): no engine, scenario or calibration run. Builds the MWVCOG file for
every place (`keep=None`: Keizer and Marion are shown as floors) and loads Medford, both through
`holdout.apply`, and divides ADU permits by issue year by the eligible lots of §1
(`adu.places_from_store`, origin 2026). Prints markdown tables; writes nothing.
"""

from __future__ import annotations

import importlib

import pandas as pd

from lotline.io import DataStore
from lotline.model import calibrate_adu as ca
from lotline.model.scenarios import adu
from lotline.validation import holdout

PLACES = {"4164900": "Salem", "4138500": "Keizer", "41047": "Marion County remainder", "4147000": "Medford"}
D041 = {"exclude_cobuilt": True, "window": 1, "report_rate": 1.0}


def main() -> None:
    store = DataStore()
    lots = adu.places_from_store("OR", store, 2026).set_index("geoid")["eligible_parcels"]
    mw = importlib.import_module("lotline.adapters.states.or.mwvcog_permits")
    md = importlib.import_module("lotline.adapters.states.or.medford_permits")
    frames = [
        holdout.apply(
            mw.build(mw.download(store), keep=None),
            "OR",
            geoid_col="jurisdiction_geoid",
            year_col="issue_year",
        ),
        md.load("OR", store),
    ]
    p = pd.concat(frames, ignore_index=True)
    for geoid, name in PLACES.items():
        q = p[p["jurisdiction_geoid"] == geoid]
        flagged = q[q["building_type_std"] == "ADU"].groupby("issue_year").size()
        print(f"\n{name} ({geoid}): {len(q):,} permits, {lots.get(geoid, float('nan')):,.0f} eligible lots")
        if q["parcel_id"].notna().any():
            net = ca.adu_counts(q, 2018, 2026, D041).set_index("year")["adu_permits"]
        else:
            net = pd.Series(dtype=float)
        print("| Year | ADU permits | not co-built | per 1,000 lots |")
        print("|---|---:|---:|---:|")
        for y in range(2016, 2027):
            n = int(flagged.get(y, 0))
            nc = "" if net.empty else int(net.get(y, 0))
            print(f"| {y} | {n} | {nc} | {n / lots.get(geoid) * 1000:.2f} |")


if __name__ == "__main__":
    main()
