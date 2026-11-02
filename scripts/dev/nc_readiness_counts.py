#!/usr/bin/env python3
"""Counts behind `docs/build/nc-readiness.md` (thread 13). Read-only: no model, scenario or dev run.

    uv run python scripts/dev/nc_readiness_counts.py

Reads the processed NC tables in `LOTLINE_DATA_DIR` and `config/reforms/nc.csv`, `config/fees/nc.csv`. Every
outcome table (permits, BPS) goes through `holdout.apply` first, so nothing for Charlotte (3712000) or
Mecklenburg (37119) from 2023-06-01 is read; the Mecklenburg towns' permits stay.

"In window" means effective 2010-01-02 to 2025-12-31, as in the Ohio and Texas reports. A D-025 place needs a
permit source that flags ADUs and covers it, plus a dated ADU rule; a D-024 place is a BPS reporter of
10,000+ people (2020 Census). A row tagged `[predates]` (HANDOFF, 2026-11-01) is a code rewrite, not a reform:
it never counts as an event, whatever its date.
"""

from __future__ import annotations

import pandas as pd

from lotline.io import DataStore
from lotline.validation import holdout

STATE = "NC"
WINDOW = ("2010-01-02", "2025-12-31")
PERMIT_SOURCES = ("raleigh_permits", "durham_permits", "greensboro_permits", "meck_permits")
V5_GEOIDS = ("3712000", "37119")


def read(store: DataStore, table: str, name: str) -> pd.DataFrame:
    return pd.read_parquet(store.processed(STATE, table, name))


def main() -> None:
    store = DataStore()
    j = read(store, "jurisdictions", "jurisdictions")
    j["bps"] = j["in_bps"].fillna(False).astype(bool)
    e = read(store, "eligible_parcels", "eligible")
    real = e["denominator_source"] != "acs_sf_fallback"
    j["den"] = j["geoid"].map(
        real.groupby(e["jurisdiction_geoid"]).any().map({True: "parcels", False: "acs"})
    )
    places = j[j["kind"] == "place"]
    pop = places["pop_2020"].sum()

    print("## Jurisdictions")
    print(j.groupby(["kind", "bps"]).size().to_string())
    print("tiers:", j["data_tier"].value_counts().sort_index().to_dict())
    print(
        "tier population shares (places, %):",
        (places.groupby("data_tier")["pop_2020"].sum() / pop * 100).round(1).to_dict(),
    )

    print("\n## Denominator")
    print(
        "source mix per jurisdiction:",
        e.groupby("jurisdiction_geoid")["denominator_source"]
        .agg(lambda s: "+".join(sorted(set(s))))
        .value_counts()
        .to_dict(),
    )
    for (kind, bps, den), g in j.groupby(["kind", "bps", "den"]):
        print(
            f"  {kind:22} in_bps={bps!s:5} {den:8} {len(g):4}  "
            f"pop {g['pop_2020'].sum():>9,}  ({g['pop_2020'].sum() / pop:.1%} of place pop)"
        )
    print(
        "window years 2010-2024 per jurisdiction:",
        e[e["year"].between(2010, 2024)]
        .groupby("jurisdiction_geoid")["year"]
        .nunique()
        .value_counts()
        .to_dict(),
    )
    print(
        "jurisdictions with any 'high' row:",
        e.loc[e["denominator_quality"] == "high", "jurisdiction_geoid"].nunique(),
    )
    big = places[places["bps"] & (places["pop_2020"] >= 10_000) & (places["den"] == "acs")]
    print(
        "BPS places of 10,000+ on the ACS fallback:",
        ", ".join(big.sort_values("pop_2020", ascending=False)["name"]),
    )
    top = places.nlargest(40, "pop_2020")
    print("40 largest places on ACS:", ", ".join(top.loc[top["den"] == "acs", "name"]))

    print("\n## D-020: one parcels source per jurisdiction")
    from lotline.build.eligible import single_source
    from lotline.config import load_state

    parcels = pd.concat(
        [
            read(store, "parcels", s)[["jurisdiction_geoid", "vintage", "source"]]
            for s in ("onemap_parcels", "wake_realestate", "clt_udo_translation")
        ]
    )
    kept = single_source(parcels, load_state(STATE).parcel_sources)
    n = kept.groupby("jurisdiction_geoid")["source"].nunique()
    print("jurisdictions with more than one source after parcel_sources:", int((n > 1).sum()))
    print("roll years kept per source:", kept.groupby("source")["vintage"].unique().map(sorted).to_dict())

    print("\n## Permits (after the holdout filter)")
    covered = {}
    for s in PERMIT_SOURCES:
        p = holdout.apply(
            read(store, "permits", s),
            STATE,
            geoid_col="jurisdiction_geoid",
            date_col="issue_date",
            year_col="issue_year",
        )
        adu = p[p["building_type_std"].eq("ADU")]
        g = p.groupby("jurisdiction_geoid")["issue_year"].agg(["size", "min", "max"])
        g = g.join(
            adu.groupby("jurisdiction_geoid")["issue_year"].agg(adus="size", adu_from="min", adu_to="max")
        )
        g = g[g["size"] >= 1000]  # places the source covers, not stray records
        covered.update(dict.fromkeys(g.index, s))
        print(f"{s}: {len(p):,} permits, {len(adu):,} ADU")
        print(g.join(j.set_index("geoid")["name"]).to_string())
    towns = holdout.apply(
        read(store, "permits", "meck_permits"),
        STATE,
        geoid_col="jurisdiction_geoid",
        date_col="issue_date",
        year_col="issue_year",
    )
    towns = towns[~towns["jurisdiction_geoid"].isin(V5_GEOIDS)]
    print(
        "Mecklenburg towns, permits per year 2022-2026:",
        towns[towns["issue_year"] >= 2022].groupby("issue_year").size().to_dict(),
    )

    print("\n## Rules")
    r = pd.read_csv("config/reforms/nc.csv", dtype=str)
    r["state_law"] = r["reform_id"].str.startswith("NC-SL")
    r["in_window"] = pd.to_datetime(r["effective_date"]).between(*WINDOW)
    r["earliest_known"] = (
        r["coding_notes"].str.contains("earliest-known", na=False) | r["adoption_date"].isna()
    )
    r["predates"] = r["coding_notes"].str.contains("[predates]", na=False, regex=False)
    r["event"] = r["in_window"] & ~r["predates"]
    print(r.groupby(["theme", "status"]).size().to_string())
    print(
        "coder agreement:",
        r["coder_agreement"].value_counts().to_dict(),
        "| [predates]:",
        int(r["predates"].sum()),
    )
    print(
        "local rows:",
        int((~r["state_law"]).sum()),
        "| single-coder:",
        int((r["coder_agreement"] == "single_coder").sum()),
    )
    print(
        "jurisdictions with any rule:",
        r["jurisdiction_geoid"].nunique(),
        "| with a local ADU rule:",
        r.loc[(r["theme"] == "adu") & ~r["state_law"], "jurisdiction_geoid"].nunique(),
        "| with a missing-middle rule:",
        r.loc[r["theme"] == "missing_middle", "jurisdiction_geoid"].nunique(),
    )
    print("rule GEOIDs not in jurisdictions:", sorted(set(r["jurisdiction_geoid"]) - set(j["geoid"])))
    names = j.set_index("geoid")["name"]

    adu = r[(r["theme"] == "adu") & ~r["state_law"] & r["event"]]
    d025 = adu[adu["jurisdiction_geoid"].isin(covered) & ~adu["jurisdiction_geoid"].isin(V5_GEOIDS)]
    print("\nD-025 event rows (covered by an ADU-flagged source, in window):")
    print(
        d025.assign(name=d025["jurisdiction_geoid"].map(names))[
            ["reform_id", "name", "effective_date", "earliest_known", "coder_agreement"]
        ].to_string(index=False)
    )
    no_rule = sorted(
        set(covered)
        - set(r.loc[(r["theme"] == "adu") & ~r["state_law"], "jurisdiction_geoid"])
        - set(V5_GEOIDS)
    )
    print("covered places with no local ADU rule:", [names.get(g, g) for g in no_rule])

    d24 = places[places["bps"] & (places["pop_2020"] >= 10_000)]
    mm = r[(r["theme"] == "missing_middle")]
    ev = mm[mm["event"] & mm["jurisdiction_geoid"].isin(set(d24["geoid"]) | {"37063"})]
    print(
        f"\nD-024: {len(d24)} BPS places of 10,000+; in-window missing-middle rows among them "
        "(plus unincorporated Durham):"
    )
    print(
        ev.assign(name=ev["jurisdiction_geoid"].map(names))[
            ["reform_id", "name", "effective_date", "by_right", "earliest_known", "coder_agreement"]
        ].to_string(index=False)
    )
    out = mm[~mm["reform_id"].isin(ev["reform_id"])]
    print("other missing-middle rows (not BPS, holdout, outside the window):", ", ".join(out["reform_id"]))
    print("in-window rows tagged [predates]:", ", ".join(r.loc[r["in_window"] & r["predates"], "reform_id"]))

    print("\n## Fees")
    f = pd.read_csv("config/fees/nc.csv", dtype=str)
    print(
        f"{len(f)} rows, {f['jurisdiction_geoid'].nunique()} jurisdictions:",
        f.groupby("jurisdiction_geoid").size().rename(index=lambda g: names.get(g, g)).to_dict(),
    )

    print("\n## V5 Charlotte input years (inputs only; no outcome table is read here)")
    for table, name, col in (
        ("acs_geo_year", "acs", "end_year"),
        ("market_geo_year", "fhfa", "year"),
        ("market_geo_year", "demand", "year"),
    ):
        d = read(store, table, name)
        d = d[d["geo"].isin(["place:3712000", "county:37119"])]
        print(f"{name}: {d.groupby('geo')[col].agg(['min', 'max']).to_dict('index')}")
    c = e[e["jurisdiction_geoid"] == "3712000"]
    print(
        "eligible (Charlotte):", c.groupby("denominator_source")["year"].agg(["min", "max"]).to_dict("index")
    )


if __name__ == "__main__":
    main()
