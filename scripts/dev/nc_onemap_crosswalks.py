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
import dataclasses

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
    "37079": "Greene: one broad 'Residential' class, 2.52 x ACS",
    "37083": "Halifax: one broad 'Residential' class and no building values, 2.32 x ACS",
    "37091": "Hertford: broad 'RES' and 'Residential and Agriculture' classes, 2.10 x ACS",
    "37141": "Pender: one broad 'Residential' class, 1.55 x ACS",
    "37163": "Sampson: one broad 'RESIDENTIAL' class and no building values, 1.52 x ACS",
}
# Counties the first draft got wrong whose codes do separate houses (checked against ACS on improved parcels:
# reports/nc/onemap_county_check.md): fields read in order, leading building fields, vacant rule.
OVERRIDES = {
    "37047": (
        ("parusedsc2", "parusedesc"),
        1,
        True,
        "Columbus: building type in parusedsc2 (SINGLE FAMILY UNIT, "
        "MOBILE HOME, MODULAR; NONE = no building), land use in parusedesc",
    ),
    "37191": (("parusedesc",), 0, True, "Wayne: vacant rule on (rural single-family class includes lots)"),
    "37123": (
        ("parusedsc2", "parusedesc"),
        0,
        True,
        "Montgomery: manufactured homes coded apart; vacant rule on",
    ),
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
    for fips in sorted(set(names) - have - set(EXCLUDED)):  # rerun adds only counties not yet configured
        inv = m.code_inventory(store, fips[2:])
        d = oc.draft(inv)
        if fips in OVERRIDES:
            fields, _, vacant, _ = OVERRIDES[fips]
            rows = inv.loc[inv["field"].isin(fields)].copy()
            std_rule = rows["code"].map(oc.classify)
            rows = rows.assign(land_use_std=[s for s, _ in std_rule], rule=[r for _, r in std_rule])
            rows = rows.loc[rows["land_use_std"].notna()].assign(description=lambda r: r["code"])
            total = inv.groupby("field")["n"].sum().max()
            share = max(rows.loc[rows["field"] == f, "n"].sum() / total for f in fields)
            yb = d.year_built_share
            tier = (
                1
                if share >= oc.TIER2_MIN_LAND_USE and yb >= oc.TIER1_MIN_YEAR_BUILT
                else (2 if share >= oc.TIER2_MIN_LAND_USE else 3)
            )
            basis = f"land-use codes for {share:.0%} of parcels (best field); structyear {yb:.0%}"
            d = dataclasses.replace(
                d,
                rows=rows,
                fields=fields,
                vacant_when_unimproved=vacant,
                land_use_share=float(share),
                data_tier=tier,
                tier_basis=basis,
            )
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
            bf, note = (OVERRIDES[fips][1], OVERRIDES[fips][3]) if fips in OVERRIDES else (0, "")
            w.writerow([fips, name, f"nc_land_use_{slug(name)}.csv", ";".join(d.fields), bf,
                        d.vacant_when_unimproved, d.built_signal, "", d.data_tier, d.tier_basis,
                        "drafted from the county's code inventory by keyword rules (onemap_codes), reviewed"
                        + (f"; fields set by hand ({note})" if note else ""),
                        SOURCE_URL])  # fmt: skip
    print(f"wrote {len(kept)} crosswalks and appended them to {m.COUNTIES_CSV.name}")


if __name__ == "__main__":
    main()
