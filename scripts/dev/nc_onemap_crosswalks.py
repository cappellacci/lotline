#!/usr/bin/env python3
"""Draft land-use crosswalks for the NC OneMap counties that have none yet (NC thread 10, S1).

For every county in NC1Map_Parcels_Transform_Dates that is not in config/crosswalks/nc_land_use_counties.csv,
reads its code inventory (`onemap_parcels.code_inventory`: statistics queries, cached in the manifest),
drafts a crosswalk (`onemap_codes.draft`) and, with --write, writes config/crosswalks/nc_land_use_<county>.csv
and appends the county to nc_land_use_counties.csv. Counties whose codes classify less than --min-share of
their parcels (first field read) are reported and left out: they stay on the ACS fallback. The rest are
downloaded, and D-017 decides per jurisdiction on the real parcels whether the roll is used.

    uv run python scripts/dev/nc_onemap_crosswalks.py             # report only
    uv run python scripts/dev/nc_onemap_crosswalks.py --write     # write the files
"""

from __future__ import annotations

import argparse
import csv

import pandas as pd

from lotline.adapters.states.nc import onemap_codes as oc
from lotline.adapters.states.nc import onemap_parcels as m
from lotline.io import DataStore

SOURCE_URL = m.LAYER_URL
MIN_SHARE = 0.5  # mechanics: download filter only; D-017 then checks each jurisdiction on the real parcels
# Counties left out after the post-download check against ACS (reports/nc/onemap_county_check.md): parcels
# coded SF_DETACHED over ACS B25024_002 (one-unit detached homes, 2020-2024) outside 0.6-1.4.
EXCLUDED = {
    "37015": "Bertie: one broad 'RESIDENTIAL' class, 2.84 x ACS",
    "37123": "Montgomery: one broad 'RESIDENTIAL' class, 2.55 x ACS",
    "37079": "Greene: one broad 'Residential' class, 2.52 x ACS",
    "37083": "Halifax: one broad 'Residential' class, 2.32 x ACS",
    "37091": "Hertford: broad 'RES' and 'Residential and Agriculture' classes, 2.10 x ACS",
    "37191": "Wayne: rural single-family class lumps other homes, 1.66 x ACS",
    "37141": "Pender: one broad 'Residential' class, 1.55 x ACS",
    "37163": "Sampson: one broad 'RESIDENTIAL' class, 1.52 x ACS",
    "37047": "Columbus: houses coded 'OCCUPIED RURAL' (read as agricultural), 0.32 x ACS",
}


def county_names(store: DataStore) -> dict[str, str]:
    d = m.download_dates(store)
    return {"37" + str(f).zfill(3): str(n).title() for f, n in zip(d["cntyfips"], d["cntyname"], strict=True)}


def slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace(".", "")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--min-share", type=float, default=MIN_SHARE)
    args = ap.parse_args(argv)
    store = DataStore()
    have = set(m.counties())
    names = county_names(store)
    kept, dropped = [], []
    for fips in sorted(set(names) - have - set(EXCLUDED)):
        inv = m.code_inventory(store, fips[2:])
        d = oc.draft(inv)
        unmatched = inv.loc[
            inv["field"].isin(d.fields[:1]) & inv["code"].map(lambda c: oc.classify(c)[0] is None)
        ]
        top = ", ".join(
            f"{c[:28]} ({n:,})" for c, n in unmatched.nlargest(4, "n")[["code", "n"]].itertuples(False)
        )
        fields = ";".join(d.fields) or "-"
        line = (
            f"{fips} {names[fips]:<14} share {d.land_use_share:5.1%} tier {d.data_tier} fields {fields:<22} "
            f"vacant_flag {d.vacant_when_unimproved!s:<5} unmatched: {top}"
        )
        print(line)
        (kept if d.land_use_share >= args.min_share else dropped).append((fips, d))
    print(
        f"\n{len(kept)} counties drafted, {len(dropped)} left on the ACS fallback "
        f"(share < {args.min_share:.0%})"
    )
    if not args.write:
        return
    for fips, d in kept:
        name = names[fips]
        path = m.CROSSWALK_DIR / f"nc_land_use_{slug(name)}.csv"
        rows = d.rows.sort_values(["field", "n", "code"], ascending=[True, False, True])
        out = pd.DataFrame(
            {
                "field": rows["field"],
                "code": rows["code"],
                "description": rows["description"],
                "land_use_std": rows["land_use_std"],
                "notes": "keyword rule " + rows["rule"] + " (scripts/dev/nc_onemap_crosswalks.py, reviewed)",
                "source_url": SOURCE_URL,
            }
        )
        out.to_csv(path, index=False)
    with m.COUNTIES_CSV.open("a", newline="") as f:
        w = csv.writer(f)
        for fips, d in kept:
            name = names[fips]
            w.writerow([fips, name, f"nc_land_use_{slug(name)}.csv", ";".join(d.fields), 0,
                        d.vacant_when_unimproved, d.built_signal, "", d.data_tier, d.tier_basis,
                        "drafted from the county's code inventory by keyword rules (onemap_codes), reviewed",
                        SOURCE_URL])  # fmt: skip
    print(f"wrote {len(kept)} crosswalks and appended them to {m.COUNTIES_CSV.name}")


if __name__ == "__main__":
    main()
