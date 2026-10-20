"""Mecklenburg permits adapter on synthetic rows (no network, no real data).

Checks the module docstring: the server filter leaves held-out rows out, holdout.apply drops the rest
(D-012: Charlotte and the county GEOID from 2023-06-01), units from the Census item code, numunits and the
description parser, the town-spelling check, and that owner fields are never requested.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.nc import meck_permits as mp
from lotline.io import DataStore
from lotline.schemas import assert_conforms
from lotline.validation import holdout


def ms(day: str) -> int:
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


# permitnum, taxjuris, usdcdesc, numunits, issuedate, workdesc, place from the point
ROWS = [
    ("P1", "CHARLOTTE", "101 - SINGLE FAMILY HOUSES", 1, "2022-03-01", "NEW SFD", "3712000"),
    ("P2", "CHARLOTTE", "103 - TWO FAMILY BUILDINGS", 2, "2021-05-05", "NEW DUPLEX", "3712000"),
    ("P3", "HUNTERSVILLE", "104 - 3-4 FAMILY", 9, "2024-02-02", "NEW 4 UNIT BUILDING", "3733120"),
    ("P4", "MATTHEWS", "105 - FIVE OR MORE FAMILY", 48, "2025-01-10", "APARTMENTS", "3741960"),
    ("P5", "HUNTERSVILLE", "101 - SINGLE FAMILY HOUSES", 1, "2024-06-01", "NEW SFD", "3712000"),  # Charlotte
    ("P6", "", "101 - SINGLE FAMILY HOUSES", 1, "2023-07-01", "NEW SFD", None),  # unincorporated, later
    ("P7", "CHARLOTTE", "434 - RES ALTERATIONS", 0, "2020-01-01", "DETACHED ADU OVER GARAGE", "3712000"),
    ("P8", "CORNELIUS", "645 - ONE FAMILY HOMES", None, "2024-03-03", "DEMO SFD", "3714700"),
    ("P9", "DAVIDSON", "101 - SF HOUSES", None, "2024-04-04", "NEW 3 UNIT TOWNHOME BLDG", "3716400"),
    ("P10", "CHARLOTTE", "324 - OFFICE BUILDINGS", 0, "2019-09-09", "NEW OFFICE", "3712000"),
]  # fmt: skip


def raw_frame() -> tuple[pd.DataFrame, pd.Series]:
    df = pd.DataFrame(
        [r[:6] for r in ROWS],
        columns=["permitnum", "taxjuris", "usdcdesc", "numunits", "issuedate", "workdesc"],
    )
    df["issuedate"] = df["issuedate"].map(ms)
    for col in ["parcelnum", "zonecode", "typeofbldg", "compldate", "bldgcost", "heatsqft", "permitdesc"]:
        df[col] = None
    df["zonecode"] = "N1-A"
    df["parcelnum"] = "01234567"
    place = pd.Series([r[6] for r in ROWS], dtype="string")
    return df, place


def test_server_filter_reads_window_and_towns_from_config():
    where = mp.server_where()
    assert "issuedate < DATE '2023-06-01'" in where
    assert "'HUNTERSVILLE'" in where and "'MINT HILL'" in where
    assert "CHARLOTTE" not in where  # never asks for Charlotte after the window
    assert mp.held_out_geoids() >= {"3712000", "37119"}


def test_holdout_drops_charlotte_and_county_after_window():
    raw, place = raw_frame()
    out = holdout.apply(mp.build(raw, place), "NC", geoid_col="jurisdiction_geoid", date_col="issue_date",
                        year_col="issue_year")  # fmt: skip
    ids = set(out.permit_id)
    assert {"P1", "P2", "P7", "P10"} <= ids  # Charlotte before 2023-06-01 stays
    assert "P5" not in ids  # filed under a town but standing in Charlotte after the window
    assert "P6" not in ids  # unincorporated (37119) after the window, D-012
    assert {"P3", "P4", "P8", "P9"} <= ids
    holdout.assert_no_leak(out, "permits", "NC")
    assert_conforms(out, "permits")


def test_units_and_types():
    raw, place = raw_frame()
    p = mp.build(raw, place).set_index("permit_id")
    assert (p.loc["P1", "building_type_std"], p.loc["P1", "units_new"], p.loc["P1", "units_confidence"]) == (
        "SFD", 1, "reported")  # fmt: skip
    assert p.loc["P1", "type_confidence"] == "inferred"  # 101 includes attached houses
    assert p.loc["P2", "building_type_std"] == "U2" and p.loc["P2", "units_new"] == 2
    assert p.loc["P3", "building_type_std"] == "U3_4"
    assert p.loc["P3", "units_new"] == 4 and p.loc["P3", "units_confidence"] == "inferred"  # 9 does not fit
    assert p.loc["P4", "units_new"] == 48 and p.loc["P4", "building_type_std"] == "MF5"
    assert p.loc["P7", "building_type_std"] == "ADU" and p.loc["P7", "units_new"] == 1
    assert (
        p.loc["P8", "is_demolition"] and p.loc["P8", "units_removed"] == 1 and p.loc["P8", "units_new"] == 0
    )
    assert p.loc["P9", "building_type_std"] == "TH"
    assert p.loc["P10", "units_new"] == 0 and p.loc["P10", "units_confidence"] == "derived"
    assert p.loc["P1", "zoning_raw"] == "N1-A" and p.loc["P1", "parcel_id"] == "3711901234567"
    assert p.loc["P6", "jurisdiction_geoid"] == "37119"  # no point, no taxjuris → county


def test_check_town_rows_stops_on_missing_towns():
    raw, place = raw_frame()
    out = holdout.apply(mp.build(raw, place), "NC", geoid_col="jurisdiction_geoid", date_col="issue_date",
                        year_col="issue_year")  # fmt: skip
    mp.check_town_rows(out)
    with pytest.raises(ValueError, match="taxjuris spellings"):
        mp.check_town_rows(out[out.issue_date < pd.Timestamp("2023-06-01")])


def test_load_applies_holdout_before_returning(tmp_path, monkeypatch):
    raw, place = raw_frame()
    monkeypatch.setattr(mp, "download", lambda store, state="NC", refresh=False: raw)
    monkeypatch.setattr(mp, "places", lambda raw, state, store: place)
    out = mp.load("NC", DataStore(tmp_path))
    assert not {"P5", "P6"} & set(out.permit_id)
    holdout.assert_no_leak(out, "permits", "NC")


def test_crosswalks_and_privacy():
    codes = mp.usdc_codes()
    assert codes["103"]["building_type_std"] == "U2" and codes["645"]["activity"] == "demolition"
    j = mp.tax_jurisdictions()
    assert j["MATTHEWS"] == "3741960" and j["MINT HILL"] == "3743480" and j["CHARLOTTE"] == "3712000"
    assert not set(mp.OUT_FIELDS) & mp.PERSONAL
    assert "permitdesc" not in mp.build(*raw_frame()).columns


def test_registered():
    assert registry.sources_for("NC")["meck_permits"].module.TABLE == "permits"
