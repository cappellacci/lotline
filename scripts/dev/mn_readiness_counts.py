#!/usr/bin/env python3
"""Counts behind `docs/build/mn-readiness.md` (thread 13, M5). Read-only: no model, scenario or dev run.

    uv run python scripts/dev/mn_readiness_counts.py

Reads the processed MN tables in `LOTLINE_DATA_DIR` and `config/reforms/mn.csv`, `config/fees/mn.csv`. Every
outcome table (permits, BPS) goes through `holdout.apply` first, and parcel rolls with `snapshot=True`, so
nothing for St. Paul (2758000) from 2024-01-01 is read, nor a St. Paul roll exported on or after that day.

"In window" means effective 2010-01-02 to 2025-12-31, as in the Ohio, Texas and NC reports; a `[predates]` row
(HANDOFF, 2026-11-01) is never an event. A "none" row ("no ADUs", or one home per lot) is a
control, not an event. A D-025 place needs a permit source that flags ADUs and covers it
(Met Council's residential permits cover every metro community; Minneapolis CCS covers Minneapolis) and a
dated ADU rule; a D-024 place is a BPS reporter of 10,000+ people (2020 Census).
"""

from __future__ import annotations

import pandas as pd

from lotline.io import DataStore
from lotline.validation import holdout

STATE = "MN"
WINDOW = ("2010-01-02", "2025-12-31")
ST_PAUL = "2758000"
PARCEL_SOURCES = ("metc_parcels", "mpls_assessor_parcels", "mngeo_parcels")


def read(store: DataStore, table: str, name: str, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(store.processed(STATE, table, name), columns=columns)


def outcomes(df: pd.DataFrame) -> pd.DataFrame:
    return holdout.apply(
        df, STATE, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )


def main() -> None:
    store = DataStore()
    j = read(store, "jurisdictions", "jurisdictions")
    j["bps"] = j["in_bps"].fillna(False).astype(bool)
    names = j.set_index("geoid")["name"]
    e = read(store, "eligible_parcels", "eligible")
    real = e["denominator_source"] != "acs_sf_fallback"
    j["den"] = (
        j["geoid"]
        .map(real.groupby(e["jurisdiction_geoid"]).any().map({True: "parcels", False: "acs"}))
        .fillna("none")
    )
    pop = j["pop_2020"].sum()

    print("## Jurisdictions")
    print(j.groupby(["kind", "bps"]).size().to_string())
    print("tiers:", j["data_tier"].value_counts().sort_index().to_dict())
    print(
        "tier population shares (%):",
        (j.groupby("data_tier")["pop_2020"].sum() / pop * 100).round(1).to_dict(),
    )

    print("\n## Denominator")
    print(
        "source mix per jurisdiction:",
        e.groupby("jurisdiction_geoid")["denominator_source"]
        .agg(lambda s: "+".join(sorted(set(s))))
        .value_counts()
        .to_dict(),
    )
    for (kind, den), g in j.groupby(["kind", "den"]):
        print(
            f"  {kind:22} {den:8} {len(g):4}  "
            f"pop {g['pop_2020'].sum():>9,}  ({g['pop_2020'].sum() / pop:.1%})"
        )
    print("jurisdictions with no eligible row:", j.loc[j["den"] == "none", ["geoid", "name"]].values.tolist())
    print(
        "window years 2010-2024 per jurisdiction:",
        e[e["year"].between(2010, 2024)]
        .groupby("jurisdiction_geoid")["year"]
        .nunique()
        .value_counts()
        .to_dict(),
    )
    print("quality:", e.groupby("denominator_quality").size().to_dict())
    places = j[j["kind"] == "place"]
    top = places.nlargest(40, "pop_2020")
    print("40 largest places on ACS:", ", ".join(top.loc[top["den"] != "parcels", "name"]))

    print("\n## Parcels and D-020")
    from lotline.build.eligible import single_source
    from lotline.config import load_state

    cols = ["jurisdiction_geoid", "county_geoid", "vintage", "vintage_date", "land_use_std", "source"]
    parts = []
    for s in PARCEL_SOURCES:
        p = read(store, "parcels", s, cols)
        p = holdout.apply(
            p,
            STATE,
            geoid_col="jurisdiction_geoid",
            date_col="vintage_date",
            year_col="vintage",
            snapshot=True,
        )
        print(
            f"{s}: {len(p):,} rows, {p['jurisdiction_geoid'].nunique()} jurisdictions, "
            f"{p['county_geoid'].nunique()} counties, rolls {sorted(p['vintage'].unique())}"
        )
        parts.append(p)
    kept = single_source(pd.concat(parts, ignore_index=True), load_state(STATE).parcel_sources)
    n = kept.groupby("jurisdiction_geoid")["source"].nunique()
    print("jurisdictions with more than one source after parcel_sources:", int((n > 1).sum()))
    by_source = kept.groupby("source")["jurisdiction_geoid"].nunique().to_dict()
    print("jurisdictions per source after parcel_sources:", by_source)
    mg = kept[kept["source"] == "mngeo_parcels"]
    known = (mg["land_use_std"] != "UNKNOWN").groupby(mg["jurisdiction_geoid"]).mean()
    print(f"mngeo jurisdictions: {len(known)}; passing the 90% gate: {int((known >= 0.9).sum())}")

    print("\n## Permits (after the holdout filter)")
    covered: set[str] = set()
    for s in ("metc_permits", "mpls_permits", "stpaul_permits"):
        p = outcomes(read(store, "permits", s))
        adu = p[p["building_type_std"].eq("ADU")]
        print(
            f"{s}: {len(p):,} permits, {p['jurisdiction_geoid'].nunique()} jurisdictions, "
            f"{p['issue_year'].min()}-{p['issue_year'].max()}, ADU {len(adu):,} in "
            f"{adu['jurisdiction_geoid'].nunique()} places "
            f"({adu['issue_year'].min()}-{adu['issue_year'].max()})"
        )
        if s != "stpaul_permits":
            covered |= set(p["jurisdiction_geoid"])
    covered.discard(ST_PAUL)

    print("\n## Rules")
    r = pd.read_csv("config/reforms/mn.csv", dtype=str)
    r["in_window"] = pd.to_datetime(r["effective_date"]).between(*WINDOW)
    r["predates"] = r["coding_notes"].str.contains("[predates]", na=False, regex=False)
    r["earliest_known"] = (
        r["coding_notes"].str.contains("earliest-known", na=False) | r["adoption_date"].isna()
    )
    # A "none" row (no ADUs, or one home per lot) is a control on evidence, not a reform event.
    r["none_row"] = (r["theme"].eq("adu") & r["adus_per_lot"].eq("0")) | (
        r["theme"].eq("missing_middle") & r["unit_cap"].eq("1")
    )
    r["event"] = r["in_window"] & ~r["predates"] & ~r["none_row"]
    # Second coder 2026-11-02: a date with no signed-ordinance record still counts, but is flagged.
    r["unconfirmed"] = r["coding_notes"].str.contains("DATE UNCONFIRMED", na=False, regex=False)
    print(r.groupby(["theme", "status"]).size().to_string())
    print("coder agreement:", r["coder_agreement"].value_counts().to_dict())
    print("jurisdictions per theme:", r.groupby("theme")["jurisdiction_geoid"].nunique().to_dict())
    adu = r[r["theme"] == "adu"]
    with_rule = set(adu["jurisdiction_geoid"])
    events = set(adu.loc[adu["event"], "jurisdiction_geoid"])
    controls = set(adu.loc[adu["none_row"], "jurisdiction_geoid"]) - events
    print(
        f"D-025: covered {len(covered)}; with an ADU rule {len(covered & with_rule)}; "
        f"with an in-window change {len(covered & events)}; 'no ADUs' controls {len(covered & controls)}; "
        f"no rule {len(covered - with_rule)}"
    )
    print(
        "D-025 in-window events dated [earliest-known]:",
        int((adu["event"] & adu["earliest_known"] & adu["jurisdiction_geoid"].isin(covered)).sum()),
    )
    ev = adu[adu["event"] & adu["jurisdiction_geoid"].isin(covered)]
    firm = ev.loc[~ev["unconfirmed"], "jurisdiction_geoid"]
    print(
        f"D-025 in-window event rows {len(ev)} in {ev['jurisdiction_geoid'].nunique()} places; "
        f"DATE UNCONFIRMED {int(ev['unconfirmed'].sum())} rows; places with a confirmed-date event "
        f"{firm.nunique()}"
    )
    print("coder_2 adjudication:", r["coder_agreement"].value_counts().to_dict())
    missing = j[j["geoid"].isin(covered - with_rule)].sort_values("pop_2020", ascending=False)
    print(
        "covered places with no ADU rule (largest 25):",
        missing[["name", "pop_2020"]].head(25).values.tolist(),
    )
    print(
        "ADU rule places outside the covered metro:",
        sorted(names.get(g, g) for g in with_rule - covered - {ST_PAUL}),
    )

    d24 = places[places["bps"] & (places["pop_2020"] >= 10_000)]
    mm = r[r["theme"] == "missing_middle"]
    ev = mm[mm["event"] & mm["jurisdiction_geoid"].isin(set(d24["geoid"]) - {ST_PAUL})]
    print(f"\nD-024: {len(d24)} BPS places of 10,000+; in-window missing-middle events:")
    print(
        ev.assign(name=ev["jurisdiction_geoid"].map(names))[
            ["reform_id", "name", "effective_date"]
        ].to_string(index=False)
    )
    print(
        "other missing-middle rows:", ", ".join(mm.loc[~mm["reform_id"].isin(ev["reform_id"]), "reform_id"])
    )

    print("\n## Fees")
    f = pd.read_csv("config/fees/mn.csv", dtype=str)
    print(
        f"{len(f)} rows, {f['jurisdiction_geoid'].nunique()} jurisdictions, "
        f"years {f['year'].min()}-{f['year'].max()}:",
        f.groupby("jurisdiction_geoid").size().rename(index=lambda g: names.get(g, g)).to_dict(),
    )


if __name__ == "__main__":
    main()
