"""Charlotte V5 inputs: which lots became N1 under the UDO, and what those lots held before June 2023.

V5 (`docs/research/lotline-validation-plan.md`) predicts duplex and triplex units on lots that became N1
when Charlotte's UDO took effect on 2023-06-01. It needs, for each Charlotte parcel *as it stood before that
day*: (1) whether it became N1, and (2) whether it held a single-family house, was vacant, or held something
else. This helper module answers (1) exactly and (2) with a labelled prior. It reads no Charlotte or
Mecklenburg outcome from the holdout window.

**(1) N1 lots.** UDO §3.2 Table 3-1 translates the conventional pre-UDO districts R-3, R-4, R-5, R-6, R-8
and UR-1 to N1-A … N1-E (`config/crosswalks/nc_clt_udo_n1.csv`, with the citation). The pre-UDO district of
every parcel comes from the `clt_udo_translation` roll (data last edited 2023-05-31, before the window).
The table applies to *conventional* districts only, so a conditional or optional district such as
"R-5(CD)" keeps its approved plan and is not N1 (exact match on the district code).

**(2) What the lots held (option (b), approved by Ben 2026-10-21).** No public Charlotte roll from before
2023-06-01 has land use (`reports/nc/charlotte_pre_udo_parcels.md`); reading the current roll would break
the snapshot holdout rule. Until Mecklenburg County sends an archived roll (option (a)), the share of N1
lots holding a single-family house, and the share vacant, are taken from the six other Mecklenburg towns on
the current NC OneMap roll (they are not held out):

- parcels whose land use an N1 district would not hold are left out (commercial, industrial, apartments,
  condominium units, mixed use, unknown);
- a house, townhouse or duplex built in 2023 or later counts as a vacant lot (the roll is from 2026, the
  prior describes 2023);
- the central value is the pooled share over the six towns; the range is the lowest and highest town.

The values used live in `config/params/v5_charlotte.yaml`; `town_prior` reproduces them from the parcels
table.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR

N1_CSV = CONFIG_DIR / "crosswalks" / "nc_clt_udo_n1.csv"
CHARLOTTE = "3712000"
TOWNS = {
    "3714700": "Cornelius",
    "3716400": "Davidson",
    "3733120": "Huntersville",
    "3741960": "Matthews",
    "3743480": "Mint Hill",
    "3752220": "Pineville",
}
NOT_N1_USES = {"COMMERCIAL", "INDUSTRIAL", "MULTIFAMILY_5P", "CONDO_UNIT", "MIXED_USE", "UNKNOWN"}
RECENT_HOMES = {"SF_DETACHED", "SF_ATTACHED", "DUPLEX"}
WINDOW_YEAR = 2023  # V5 window opens 2023-06-01 (config/states/nc.yaml); homes built from then were lots


def n1_translation(path: Path = N1_CSV) -> dict[str, str]:
    """Pre-UDO conventional district → its N1 district (UDO Table 3-1)."""
    with path.open(newline="") as f:
        return {r["pre_udo_district"].strip().upper(): r["udo_district"] for r in csv.DictReader(f)}


def n1_district(zoning_raw: pd.Series, table: dict[str, str] | None = None) -> pd.Series:
    """The N1 district each pre-UDO district became, or NA (conditional districts never match)."""
    table = n1_translation() if table is None else table
    return zoning_raw.astype("string").str.strip().str.upper().map(table).astype("string")


def n1_lots(clt_parcels: pd.DataFrame) -> pd.DataFrame:
    """Charlotte parcels that became N1, by N1 district: count and median lot size (sq ft)."""
    df = clt_parcels.loc[clt_parcels["jurisdiction_geoid"] == CHARLOTTE]
    df = df.assign(n1=n1_district(df["zoning_raw"])).dropna(subset=["n1"])
    return (
        df.groupby("n1").agg(lots=("parcel_id", "size"), median_lot_sqft=("lot_sqft", "median")).reset_index()
    )


def town_prior(parcels: pd.DataFrame, towns: dict[str, str] = TOWNS) -> pd.DataFrame:
    """Shares of single-family and vacant lots among N1-type parcels in each town, plus a pooled row.

    `parcels`: land_use_std, year_built and jurisdiction_geoid (a current roll). Columns: town, parcels,
    sf_share, vacant_share. The last row is "pooled" (all towns together).
    """
    df = parcels.loc[parcels["jurisdiction_geoid"].isin(towns)].copy()
    recent = df["land_use_std"].isin(RECENT_HOMES) & (df["year_built"] >= WINDOW_YEAR).fillna(False)
    df["lu"] = df["land_use_std"].mask(recent, "VACANT_RESIDENTIAL")
    df = df.loc[~df["lu"].isin(NOT_N1_USES)]

    def shares(g: pd.DataFrame) -> pd.Series:
        return pd.Series(
            {
                "parcels": len(g),
                "sf_share": (g["lu"] == "SF_DETACHED").mean(),
                "vacant_share": (g["lu"] == "VACANT_RESIDENTIAL").mean(),
            }
        )

    rows = [shares(g).rename(towns[t]) for t, g in df.groupby("jurisdiction_geoid")]
    rows.append(shares(df).rename("pooled"))
    out = pd.DataFrame(rows)
    out["parcels"] = out["parcels"].astype("int64")
    return out.rename_axis("town").reset_index()
