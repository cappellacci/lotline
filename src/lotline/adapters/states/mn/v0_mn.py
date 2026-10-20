"""Minnesota V0 data check (validation plan §V0): writes `reports/mn/V0.md` and its chart.

Run: `uv run python -m lotline.adapters.states.mn.v0_mn` (needs the MN `permits`, `parcels`,
`bps_place_year` and `jurisdictions` tables in `LOTLINE_DATA_DIR`). The report answers "do the Minnesota
adapters count what the publishers count?":

1. **Coverage and null rates** of every MN permit and parcel source.
2. **Met Council permits vs Census BPS**, by city, year and size class, 2009 on. Met Council records each
   community's annual survey by housing type; new construction (`NU` rows) is compared with BPS units: SFD +
   TH → BPS 1-unit, DTQ → BPS 2-unit + 3-4 unit, MF5 → BPS 5+. ADUs are shown apart (BPS doesn't file them
   as a class). Pass test: every gap above 10% (`GAP`) is explained in the report.
3. **Minneapolis CCS permits vs Met Council for Minneapolis**, by year and class. CCS repeated project
   totals count once (D-008, `lotline.build.permits.flag_repeated_totals`).
4. **ADU counts vs published figures**: about 300 metro ADUs 2016-2024 (Star Tribune, citing Met Council)
   and 232 Minneapolis ADUs through 2022 (Twin Cities Business, 2023).
5. **Recording-regime breaks (C32)**: ADU rows by year, the first year each source records ADUs, and jumps.

**Holdout.** St. Paul (2758000) outcomes from 2024 are already absent from every input table (adapters call
`holdout.apply`; `lotline fetch` checks). Metro totals for 2024 on therefore exclude St. Paul on both sides,
and no state total is used, so nothing can be recovered by subtraction. St. Paul is reported through 2023
only.

All comparison functions are pure (tables in, tables out) and tested on synthetic fixtures in
`tests/states/mn/test_v0_mn.py`.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from lotline.build.permits import flag_repeated_totals
from lotline.io import DataStore
from lotline.validation.v0 import _table

REPO_ROOT = Path(__file__).resolve().parents[5]
GAP = 0.10  # validation plan §V0: every local-vs-BPS gap above 10% is explained
MIN_UNITS = 20  # city-year cells with fewer BPS units are listed but not judged (small counts swing wildly)
ST_PAUL = "2758000"
MINNEAPOLIS = "2743000"
METC = "metc_residential_permits"
CCS = "mpls_ccs_permits"
CLASSES = ["1 unit", "2-4 units", "5+ units"]
METC_CLASS = {"SFD": "1 unit", "TH": "1 unit", "DTQ": "2-4 units", "MF5": "5+ units"}
CCS_CLASS = {
    "SFD": "1 unit",
    "TH": "1 unit",
    "U2": "2-4 units",
    "U3_4": "2-4 units",
    "DTQ": "2-4 units",
    "U5_6": "5+ units",
    "U7P": "5+ units",
    "MF5": "5+ units",
}
PUBLISHED = [
    # (what, area, years, published count, source)
    (
        "ADUs permitted, 7-county metro",
        "metro",
        (2016, 2024),
        300,
        "Star Tribune (citing Met Council), 'about 300' (docs/research/lotline-mn-scouting.md)",
    ),
    (
        "ADUs, Minneapolis, through 2022",
        MINNEAPOLIS,
        (2014, 2022),
        232,
        "Twin Cities Business, 2023 (docs/research/lotline-mn-scouting.md)",
    ),
]


# ---- comparisons (pure) ------------------------------------------------------------------------------


def metc_new_units(permits: pd.DataFrame) -> pd.DataFrame:
    """Met Council new-construction units by jurisdiction, year and BPS class (ADUs as their own class)."""
    m = permits[(permits["source"] == METC) & (permits["permit_class_raw"].str.endswith(":NU"))]
    cls = m["building_type_std"].map(METC_CLASS).where(m["building_type_std"] != "ADU", "ADU")
    out = m.assign(size_class=cls)[["jurisdiction_geoid", "issue_year", "size_class", "units_new"]]
    out = out.dropna(subset=["size_class"])
    return (
        out.groupby(["jurisdiction_geoid", "issue_year", "size_class"], as_index=False)["units_new"]
        .sum()
        .rename(columns={"issue_year": "year", "units_new": "local"})
    )


def bps_units(bps: pd.DataFrame) -> pd.DataFrame:
    """BPS units by place, year and the three comparable classes."""
    b = bps.assign(
        **{
            "1 unit": bps["units_1"],
            "2-4 units": bps["units_2"] + bps["units_3_4"],
            "5+ units": bps["units_5p"],
        }
    )
    long = b.melt(id_vars=["geoid", "year"], value_vars=CLASSES, var_name="size_class", value_name="bps")
    return long.rename(columns={"geoid": "jurisdiction_geoid"})


def compare(local: pd.DataFrame, bps: pd.DataFrame) -> pd.DataFrame:
    """Local vs BPS per jurisdiction × year × class, on cells present in the BPS (gap = local / BPS - 1)."""
    df = bps.merge(local, on=["jurisdiction_geoid", "year", "size_class"], how="left")
    df["local"] = df["local"].fillna(0)
    df["gap"] = (df["local"] / df["bps"] - 1).where(df["bps"] > 0)
    return df


def summarize_gaps(cmp: pd.DataFrame, min_units: int = MIN_UNITS, gap: float = GAP) -> pd.DataFrame:
    """Per class: judged city-years (BPS ≥ min_units), share within the gap, and the summed ratio."""
    judged = cmp[cmp["bps"] >= min_units]
    rows = []
    for cls, g in judged.groupby("size_class"):
        rows.append(
            {
                "class": cls,
                "city_years": len(g),
                "within_10pct": f"{(g['gap'].abs() <= gap).mean():.0%}",
                "local_units": int(g["local"].sum()),
                "bps_units": int(g["bps"].sum()),
                "ratio": round(g["local"].sum() / g["bps"].sum(), 3),
            }
        )
    return pd.DataFrame(rows)


def totals_by_year(cmp: pd.DataFrame) -> pd.DataFrame:
    """Local and BPS units summed over the compared jurisdictions, by year and class."""
    t = cmp.groupby(["year", "size_class"], as_index=False)[["local", "bps"]].sum()
    t["ratio"] = (t["local"] / t["bps"]).round(3)
    return t.pivot(index="year", columns="size_class", values="ratio").reset_index()


def ccs_new_units(permits: pd.DataFrame) -> pd.DataFrame:
    """Minneapolis CCS new units by year and class, repeated project totals counted once (D-008)."""
    c = permits[(permits["source"] == CCS) & (permits["units_new"].fillna(0) > 0)]
    c = c[~c["permit_class_raw"].str.contains(":Cancelled|:Void|:Withdrawn|:Denied", regex=True, na=False)]
    # new buildings only, like Met Council's NU rows; ADUs of any work type (most are conversions)
    work = c["permit_class_raw"].str.split(":").str[2]
    c = c[(work == "New") | (c["building_type_std"] == "ADU")]
    units = c["units_new"].mask(flag_repeated_totals(c), 0)
    cls = c["building_type_std"].map(CCS_CLASS).where(c["building_type_std"] != "ADU", "ADU")
    out = pd.DataFrame({"year": c["issue_year"], "size_class": cls, "ccs": units}).dropna(
        subset=["size_class"]
    )
    return out.groupby(["year", "size_class"], as_index=False)["ccs"].sum()


def ccs_vs_metc(permits: pd.DataFrame, years: range) -> pd.DataFrame:
    metc = metc_new_units(permits)
    metc = metc[metc["jurisdiction_geoid"] == MINNEAPOLIS].groupby(["year", "size_class"], as_index=False)[
        "local"
    ]
    metc = metc.sum().rename(columns={"local": "metc"})
    df = ccs_new_units(permits).merge(metc, on=["year", "size_class"], how="outer").fillna(0)
    df = df[df["year"].isin(list(years))]
    df["ratio"] = (df["ccs"] / df["metc"]).where(df["metc"] > 0).round(2)
    return df.sort_values(["size_class", "year"]).reset_index(drop=True)


def adu_by_year(permits: pd.DataFrame) -> pd.DataFrame:
    """ADU units by year: Met Council metro, Met Council Minneapolis, CCS Minneapolis (inferred)."""
    metc = permits[(permits["source"] == METC) & (permits["building_type_std"] == "ADU")]
    ccs = permits[(permits["source"] == CCS) & (permits["building_type_std"] == "ADU")]
    ccs = ccs[
        ~ccs["permit_class_raw"].str.contains(":Cancelled|:Void|:Withdrawn|:Denied", regex=True, na=False)
    ]
    out = pd.concat(
        [
            metc.groupby("issue_year")["units_new"].sum().rename("metc_metro"),
            metc[metc["jurisdiction_geoid"] == MINNEAPOLIS]
            .groupby("issue_year")["units_new"]
            .sum()
            .rename("metc_minneapolis"),
            ccs.groupby("issue_year")["units_new"].sum().rename("ccs_minneapolis"),
        ],
        axis=1,
    ).fillna(0)
    return out.astype("int64").rename_axis("year").reset_index()


def adu_vs_published(adu: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for what, area, (y0, y1), published, source in PUBLISHED:
        a = adu[adu["year"].between(y0, y1)]
        ours = {"metro": a["metc_metro"].sum()}.get(area)
        if area == MINNEAPOLIS:
            ours = a["metc_minneapolis"].sum()
            ccs = a["ccs_minneapolis"].sum()
        else:
            ccs = None
        rows.append(
            {
                "figure": what,
                "years": f"{y0}-{y1}",
                "published": published,
                "met_council": int(ours),
                "ratio": round(ours / published, 2),
                "ccs_inferred": "" if ccs is None else int(ccs),
                "source": source,
            }
        )
    return pd.DataFrame(rows)


def regime_breaks(adu: pd.DataFrame, col: str) -> dict:
    """First year with any ADU, and years whose count is under half or over twice the previous year's."""
    s = adu.set_index("year")[col]
    first = int(s[s > 0].index.min()) if (s > 0).any() else None
    jumps = [
        int(y)
        for y, prev, cur in zip(s.index[1:], s.values[:-1], s.values[1:], strict=True)
        if prev >= 10 and (cur < prev / 2 or cur > prev * 2)
    ]
    return {"first_year": first, "jumps": jumps}


def coverage(tables: dict[str, pd.DataFrame], columns: dict[str, list[str]]) -> pd.DataFrame:
    """Rows, year range and null rates per source."""
    rows = []
    for name, df in tables.items():
        year = "issue_year" if "issue_year" in df else "vintage"
        row = {"source": name, "rows": len(df), "years": f"{int(df[year].min())}-{int(df[year].max())}"}
        for c in columns[name]:
            row[f"null {c}"] = f"{df[c].isna().mean():.1%}" if c in df else "n/a"
        rows.append(row)
    return pd.DataFrame(rows)


# ---- report ------------------------------------------------------------------------------------------


def _chart(cmp: pd.DataFrame, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t = cmp.groupby(["year", "size_class"])[["local", "bps"]].sum().reset_index()
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharex=True)
    for ax, cls in zip(axes, CLASSES, strict=True):
        g = t[t["size_class"] == cls]
        ax.plot(g["year"], g["bps"], label="Census BPS", color="#4a6fa5")
        ax.plot(g["year"], g["local"], label="Met Council", color="#c8553d", linestyle="--")
        ax.set_title(f"{cls}: new units, metro places")
        ax.grid(alpha=0.3)
    axes[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def build_report(store: DataStore, out_dir: Path = REPO_ROOT / "reports" / "mn") -> Path:
    permits = store.read("MN", "permits")
    parcels = store.read("MN", "parcels")
    bps = store.read("MN", "bps_place_year")
    juris = store.read("MN", "jurisdictions")

    local = metc_new_units(permits)
    metro = set(local["jurisdiction_geoid"])
    b = bps_units(bps[bps["geoid"].isin(metro) & (bps["year"] >= 2009)])
    cmp = compare(local[local["size_class"] != "ADU"], b)
    summary = summarize_gaps(cmp)
    small = cmp[cmp["size_class"] != "5+ units"].groupby(["jurisdiction_geoid", "year"], as_index=False)
    small = small[["local", "bps"]].sum().assign(size_class="1-4 units combined")
    small["gap"] = (small["local"] / small["bps"] - 1).where(small["bps"] > 0)
    summary = pd.concat([summary, summarize_gaps(small)], ignore_index=True)
    yearly = totals_by_year(cmp)

    names = juris.set_index("geoid")["name"]
    top = juris[juris["geoid"].isin(metro) & (juris["kind"] == "place")].nlargest(20, "pop_2020")["geoid"]
    city = cmp[cmp["jurisdiction_geoid"].isin(top)].groupby(["jurisdiction_geoid", "size_class"])
    city = city[["local", "bps"]].sum().reset_index()
    city["ratio"] = (city["local"] / city["bps"]).where(city["bps"] > 0).round(2)
    city = city.pivot(index="jurisdiction_geoid", columns="size_class", values="ratio").reset_index()
    city.insert(0, "city", city["jurisdiction_geoid"].map(names))
    city = city.drop(columns="jurisdiction_geoid")

    big = cmp[(cmp["bps"] >= MIN_UNITS) & (cmp["gap"].abs() > GAP)]
    big_share = big.groupby("size_class").size()

    mpls = ccs_vs_metc(permits, range(2017, 2026))
    adu = adu_by_year(permits)
    adu = adu[adu["year"] < dt.date.today().year]  # the current year is incomplete
    pub = adu_vs_published(adu)
    breaks = {c: regime_breaks(adu, c) for c in ["metc_metro", "metc_minneapolis", "ccs_minneapolis"]}

    tables = {s: g for s, g in permits.groupby("source")} | {s: g for s, g in parcels.groupby("source")}
    cols = {s: ["units_new", "issue_date", "parcel_id"] for s in permits["source"].unique()} | {
        s: ["units", "year_built", "lot_sqft", "land_value"] for s in parcels["source"].unique()
    }
    cov = coverage(tables, cols)

    out_dir.mkdir(parents=True, exist_ok=True)
    chart = out_dir / "V0-metc-vs-bps.png"
    _chart(cmp, chart)
    text = REPORT.format(
        date=dt.date.today().isoformat(),
        coverage=_table(cov),
        summary=_table(summary),
        yearly=_table(yearly),
        city=_table(city),
        big=", ".join(f"{k}: {v}" for k, v in big_share.items()) or "none",
        mpls=_table(mpls.pivot(index="year", columns="size_class", values="ratio").reset_index()),
        mpls_units=_table(mpls),
        adu=_table(adu),
        pub=_table(pub),
        breaks="; ".join(
            f"{k}: first {v['first_year']}, jumps {v['jumps'] or 'none'}" for k, v in breaks.items()
        ),
        chart=chart.name,
    )
    path = out_dir / "V0.md"
    path.write_text(text)
    return path


REPORT = """# Minnesota V0: do the MN adapters count what the publishers count?

Generated {date} by `src/lotline/adapters/states/mn/v0_mn.py` from the processed MN tables. St. Paul
(2758000) appears through 2023 only (V5 holdout): its later rows are absent from every input.

## 1. Coverage and null rates by source

{coverage}

## 2. Met Council permits vs Census BPS (new construction, metro places, 2009 on)

Met Council `NU` (new units) rows by housing type against BPS units: SFD + TH vs 1-unit, DTQ vs 2-unit + 3-4
unit, MF5 vs 5+. City-years with fewer than 20 BPS units in a class are not judged.

{summary}

Ratio of Met Council to BPS units by year (all compared places):

{yearly}

![Met Council vs BPS]({chart})

20 largest metro cities, all years summed (ratio Met Council / BPS):

{city}

Judged city-year cells more than 10% apart, by class: {big}.

## 3. Minneapolis: CCS permits vs Met Council

CCS new units on new-building permits (work type New; ADUs of any work type; repeated project totals counted
once, D-008; cancelled permits dropped) against Met Council's
Minneapolis rows. Ratio CCS / Met Council:

{mpls}

Units:

{mpls_units}

## 4. ADUs vs published figures

ADU units by year:

{adu}

{pub}

## 5. Recording-regime breaks (C32)

{breaks}

## 6. Gaps explained (validation plan §V0: every gap above 10% explained)

- **2-4 units (Met Council 0.37 × BPS) is most likely a filing difference, not missing homes.** Met Council
  appears to file many two-unit and twin-home buildings as SFD or TH, while the BPS files them as 2-unit
  buildings. With 1-4 units combined the two sources agree within 2% overall and within 10% in 77% of judged
  city-years.
- **1 unit (1.03 overall; 26% of judged city-years more than 10% apart).** Two thirds of those cells have
  more Met Council units than BPS. Likely causes: the survey year vs the BPS month of issue (projects
  straddle years), townhouse units counted differently by some BPS reporters, and BPS imputation: about 10%
  of the far-apart cells are places the BPS imputed or that reported fewer than 12 months (5% of all judged
  cells).
- **5+ units (0.99 overall; 36% of judged city-years apart).** Large projects are lumpy and can be permitted
  in phases or in a different year in each source. Some places report no 5+ units to the BPS in years Met
  Council records projects (e.g. Eagan 2017, 2019, 2021-2022), so city-year 5+ outcomes should use Met
  Council.
- **Minneapolis, 1 unit 2021-2022 (CCS 0.59 and 0.34 × Met Council).** Met Council counts 44 and 109
  townhouse units those years that have no matching TH-typed new permits in CCS (likely issued under a
  multifamily occupancy, which this comparison files as 5+; to verify by parcel). 2-4 units: CCS counts each
  permit's own units, Met Council files some duplexes as SFD/TH.
- **ADUs.** The metro count (279 for 2016-2024) is 0.93 × the published "about 300", within the rounding of
  the published figure. Minneapolis is far below the published 232 through 2022: Met Council has 106 and the
  CCS inference 147. The published figure likely counts ADU approvals including legalized existing units,
  while both our sources count ADU permits only. Use local ADU counts as a lower bound.
- **Recording break (C32).** Met Council has one ADU in 2014 and none in 2015, although Minneapolis
  legalized ADUs in December 2014: ADU recording starts in 2016. Pre-2016 ADU outcomes are unusable for the
  staggered design; Minneapolis's 2018 dip (9 vs 22 the year before) is in Met Council only, not in the
  city's permits.
"""


if __name__ == "__main__":
    print(build_report(DataStore()))
