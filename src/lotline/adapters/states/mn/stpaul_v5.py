"""St. Paul V5 inputs: the lots zoned H1 or H2 when the 1-4 unit reform took effect, and what they held.

V5 (`docs/research/lotline-validation-plan.md`; holdout V5-MN-STPAUL in `config/states/mn.yaml`) predicts St.
Paul's 2-4 unit (DTQ) and 5+ unit (MF5) homes on H1/H2 lots, 2024-2026, from data up to 2023. The reform
(`MN-2758000-missing_middle-2023`, effective 2023-11-26) rezoned the former R1-R4, RT1, RT2 and low-density PD
districts to H1 and H2. This helper finds those lots and counts what they held. It reads no St. Paul outcome
from the holdout window.

**Zoning.** The city's "Principal Zoning Archive Over Time" service keeps complete dated snapshots of its
principal zoning layer, one sublayer per date (`ARCHIVE_URL`). Two are used:

- `REFORM_LAYER`, "Principal Zoning - November 26th, 2023": the first snapshot with H1 and H2 (the reform's
  effective date), dated before the window opens on 2024-01-01;
- `PRE_REFORM_LAYER`, "November 25th, 2023": the last snapshot with R1-R4, RT1 and RT2, used as a check
  (`FORMER_DISTRICTS`).

**Window guard.** The archive's `editingInfo` and its features' edit dates show when the archive was
republished (2026-10-19), not what the snapshot shows, so the snapshot's date is read from the sublayer's
name.
`snapshot_date` parses it and `check_window` stops before anything is downloaded if it is on or after the
window. A snapshot that differs from the current layer is the evidence that it is a real dated copy: from
November 2023 to October 2026 the T2 district goes from 118 to 123 polygons (checked 2026-11-01).

**Lots.** St. Paul's newest roll before the window is the Met Council "2023" roll, Ramsey's part exported
2023-12-26 (`metc_parcels`, vintage 2023); `holdout.apply(..., snapshot=True)` is applied again here. Each
parcel's point (`lon`/`lat`) is placed in a district by `lotline.geo.assign`. Eligibility is rule 1.1 for
missing middle (`build.eligible.classify`: a single-family house or a vacant residential lot, D-014).

**Fields.** Only `Zoning` and the polygons are requested; the archive layers hold no personal fields.
"""

from __future__ import annotations

import datetime as dt
import re

import pandas as pd

from lotline.io import DataStore
from lotline.validation import holdout

# Not `SOURCE`/`PROVENANCE`: the registry would take a state module with those names for a `lotline fetch`
# source and require a canonical table. Until WS-CORE lets a state module be documented only (#258,
# contract-change), the names carry an ARCHIVE_ prefix, and the provenance below is not yet in
# docs/data_provenance.md.
ARCHIVE_SOURCE = "stpaul_zoning_archive"
ADAPTER = "states.mn.stpaul_v5"
VERSION = "1.0"
ARCHIVE_URL = "https://services1.arcgis.com/9meaaHE3uiba0zr8/arcgis/rest/services/PrincipalZoning_OverTime/FeatureServer"
LICENSE = "City of Saint Paul GIS data, Minnesota Government Data Practices Act (Minn. Stat. ch. 13), as is"
REFORM_LAYER = 36  # "Principal Zoning - November 26th, 2023"
PRE_REFORM_LAYER = 35  # "Principal Zoning - November 25th, 2023"
ST_PAUL = "2758000"
H_DISTRICTS = ("H1", "H2")
FORMER_DISTRICTS = ("R1", "R2", "R3", "R4", "RT1", "RT2")  # the reform row; low-density PD is not split out
ROLL_VINTAGE = 2023
ARCHIVE_PROVENANCE = {
    "title": "City of Saint Paul Principal Zoning Archive Over Time (snapshots of 2023-11-25 and 2023-11-26)",
    "landing_url": ARCHIVE_URL,
    "table": "none (V5 helper; district per parcel computed on the fly)",
    "cleaning": [
        "Window guard: each snapshot's date is read from its sublayer name, and nothing is downloaded "
        "unless it falls before the St. Paul holdout window (2024-01-01)",
        "Only the Zoning field and the polygons (WGS84) are requested",
        "District codes trimmed and upper-cased; rows without a district or polygon dropped",
        "Parcels on Met Council's 2023 roll (St. Paul part exported 2023-12-26) are placed in a district "
        "by their point",
    ],
    "limitations": [
        "The archive's edit dates show its 2026 republication, not the snapshot's content; the date in the "
        "sublayer name is the only date",
        "A parcel's point decides its district, so a lot split by a district line takes its point's district",
    ],
}

_NAME_DATE = re.compile(r"([A-Z][a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,\s*(\d{4})")


def window_opens(state: str = "MN") -> pd.Timestamp:
    return min(pd.Timestamp(h.outcome_from) for h in holdout.holdouts_for(state) if h.geoid == ST_PAUL)


def snapshot_date(layer_name: str) -> pd.Timestamp:
    """The date in a sublayer name such as "Principal Zoning - November 26th, 2023"."""
    m = _NAME_DATE.search(layer_name)
    if not m:
        raise ValueError(f"{ARCHIVE_SOURCE}: no day-month-year date in the layer name {layer_name!r}")
    month, day, year = m.groups()
    return pd.Timestamp(dt.datetime.strptime(f"{month} {day} {year}", "%B %d %Y"))


def check_window(layer_name: str, opens: pd.Timestamp) -> pd.Timestamp:
    """The snapshot's date, or ValueError when it is not strictly before the holdout window."""
    when = snapshot_date(layer_name)
    if when >= opens:
        raise ValueError(
            f"{ARCHIVE_SOURCE}: {layer_name!r} is dated {when.date()}, on or after the St. Paul holdout "
            f"window ({opens.date()}): it may show zoning changed inside the window and must not be fetched"
        )
    return when


def layer_name(layer: int) -> str:
    """The sublayer's name, read over HTTP and not saved (the window is checked before anything is saved)."""
    from lotline.io.http import client

    with client(timeout=60) as http:
        resp = http.get(f"{ARCHIVE_URL}/{layer}", params={"f": "json"})
        resp.raise_for_status()
        return resp.json()["name"]


def download_districts(store: DataStore, layer: int, *, refresh: bool = False) -> pd.DataFrame:
    """One dated snapshot's polygons: columns `district` and `rings` (WGS84), after the window guard."""
    from lotline.io.arcgis import download_layer

    when = check_window(layer_name(layer), window_opens())
    raw = download_layer(
        f"{ARCHIVE_URL}/{layer}",
        store=store,
        source=ARCHIVE_SOURCE,
        license=LICENSE,
        adapter=ADAPTER,
        adapter_version=VERSION,
        name=f"layer_{layer}",
        out_fields="Zoning",
        geometry="polygon",
        vintage=when.date().isoformat(),
        refresh=refresh,
    )
    return districts(raw)


def districts(raw: pd.DataFrame) -> pd.DataFrame:
    """Layer rows → `district` (trimmed, upper case) and `rings`; drops rows without a district or polygon."""
    d = raw["Zoning"].astype("string").str.strip().str.upper().replace("", pd.NA)
    out = pd.DataFrame({"district": d, "rings": raw["rings"]})
    return out.loc[out["district"].notna() & out["rings"].map(bool)].reset_index(drop=True)


def roll_2023(parcels: pd.DataFrame, state: str = "MN") -> pd.DataFrame:
    """St. Paul's parcels on the pre-window roll, with the snapshot holdout rule applied again."""
    p = parcels.loc[(parcels["jurisdiction_geoid"] == ST_PAUL) & (parcels["vintage"] == ROLL_VINTAGE)]
    p = holdout.apply(
        p, state, geoid_col="jurisdiction_geoid", date_col="vintage_date", year_col="vintage", snapshot=True
    )
    if p.empty:
        raise ValueError(
            f"{ARCHIVE_SOURCE}: no St. Paul parcels on the {ROLL_VINTAGE} roll survive the holdout filter"
        )
    return p


def assign_district(parcels: pd.DataFrame, polygons: pd.DataFrame) -> pd.Series:
    """Each parcel's district from its point (None outside every polygon)."""
    from lotline import geo

    shapes = polygons.rename(columns={"district": "geoid"})
    out = geo.assign(parcels["lon"].to_numpy(), parcels["lat"].to_numpy(), shapes)
    return pd.Series(out, index=parcels.index, dtype="string", name="district")


def h_lots(parcels: pd.DataFrame, polygons: pd.DataFrame) -> pd.DataFrame:
    """H1/H2 lots on the pre-window roll by district and land use, with rule 1.1 eligibility.

    Columns: district, land_use_std, parcels, eligible (missing-middle rule 1.1), median_lot_sqft.
    """
    from lotline.build.eligible import classify

    p = parcels.assign(district=assign_district(parcels, polygons))
    p = p.loc[p["district"].isin(H_DISTRICTS)].copy()
    p["eligible"] = classify(p, "missing_middle")["eligible"].to_numpy()
    out = (
        p.groupby(["district", "land_use_std"])
        .agg(
            parcels=("parcel_id", "size"),
            eligible=("eligible", "sum"),
            median_lot_sqft=("lot_sqft", "median"),
        )
        .reset_index()
    )
    out["eligible"] = out["eligible"].astype("int64")
    return out


def former_district_check(parcels: pd.DataFrame, before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    """Cross-tab of each parcel's district the day before the reform against the day it took effect."""
    p = parcels.assign(before=assign_district(parcels, before), after=assign_district(parcels, after))
    p = p.loc[p["before"].isin(FORMER_DISTRICTS) | p["after"].isin(H_DISTRICTS)]
    return p.groupby(["before", "after"], dropna=False).size().rename("parcels").reset_index()


def load(store: DataStore, *, refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Download both snapshots (cached in raw/); return the H1/H2 lot table and the former-district check."""
    parcels = roll_2023(pd.read_parquet(store.processed("MN", "parcels", "metc_parcels")))
    after = download_districts(store, REFORM_LAYER, refresh=refresh)
    before = download_districts(store, PRE_REFORM_LAYER, refresh=refresh)
    return {"h_lots": h_lots(parcels, after), "check": former_district_check(parcels, before, after)}
