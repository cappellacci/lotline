"""Fort Worth permits adapter on synthetic rows (no network, no real data).

Checks the module docstring: status snapshots collapsed to one permit (units counted once), which statuses
are kept, filing-year dates, building type and units from the use crosswalk and Units, apartment buildings
from Units of 2 or more, ADUs from the description parser, and that personal fields are never requested or
kept.
"""

import pandas as pd

from lotline import registry
from lotline.adapters.states.tx import fw_permits as fw
from lotline.io import DataStore
from lotline.schemas import assert_conforms

R, A, C = fw.RESIDENTIAL, fw.ACCESSORY, fw.COMMERCIAL
NONE = "1900-01-01"  # the source's "no date"


def ms(day: str | None) -> int | None:
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000) if isinstance(day, str) else None


# Permit_No, Permit_Type, SubType, Use_Type, Specific_Use, Units, File_Date, Status, Status_Date, description
ROWS = [
    ("P1", R, "New", "Single Family Residence", None, "1",
     "2022-03-01", "Finaled", "2022-11-01", "new house"),
    ("P2", R, "New", "Single Family Residence", None, "0", "2022-12-28", "Issued", "2023-01-09", "new SFR"),
    ("P3", R, "New", "Duplex", None, "2", "2023-05-05", "Finaled", "2024-02-01", "new duplex"),
    ("P4", R, "New", "Duplex", None, "0", "2023-05-06", "Expired", "2024-05-06", "duplex"),
    ("P5", R, "New", "Townhouse", None, "1", "2024-01-10", "Void", "2024-01-20", "townhome"),
    # P6: three status snapshots of one apartment building permit, each repeating its 23 units
    ("P6", C, "New", "Residential", "APARTMENT", "23",
     "2022-01-07", "Awaiting Client Reply", "2022-02-01", "bldg 1"),
    ("P6", C, "New", "Residential", "Apartment", "23", "2022-01-07", "Issued", "2022-03-01", "bldg 1"),
    ("P6", C, "New", "Residential", "Apartment", "23", "2022-01-07", "Finaled", "2023-06-01", "bldg 1"),
    ("P7", C, "New", "Residential", "Townhouse Apartments", "4",
     "2021-02-02", "Finaled", "2022-01-01", "4 plex"),
    ("P8", C, "New", "Residential", "Apartment", "1", "2021-03-03", "Finaled", "2022-01-01", "unit"),
    ("P9", C, "New", "Residential", "Detached Multi-Family", "1",
     "2021-04-04", "Finaled", "2022-01-01", "cottage"),
    ("P10", C, "New", "Residential", "Hotel", "120", "2020-05-05", "Finaled", "2021-01-01", "hotel"),
    ("P11", A, "New", "Accessory Dwelling", None, "0", "2020-06-06", "Finaled", "2021-01-01",
     "New accessory dwelling unit 600 sf behind the house"),
    ("P12", A, "New", "Accessory Dwelling", None, "1",
     "2019-07-07", "Finaled", "2020-01-01", "RES/NEW STORM SHELTER"),
    ("P13", A, "New", "Storage Shed", None, "0", "2019-08-08", "Finaled", NONE, "shed"),
    ("P14", R, "Remodel", "Single Family Residence", None, "1", "2018-09-09", "Finaled", "2019-01-01",
     "kitchen remodel"),
    ("P15", R, "Remodel", "Single Family Residence", None, "1", "2018-10-10", "Finaled", "2019-01-01",
     "convert garage to accessory dwelling unit"),
    ("P16", R, "New", "Single Family Residence", None, "175000",
     "2017-11-11", "Finaled", "2018-06-01", "SFR"),
    ("P17", R, "New", "Single Family Residence", None, "1", "2017-12-12", "Withdrawn", "2018-01-01", "SFR"),
    ("P18", R, "New", "Foundation Only", None, "0", "2016-01-01", "Finaled", "2016-06-01", "slab"),
    ("P19", R, "New", "Community Homes", None, "1", "2016-02-02", "Finaled", "2016-06-01", "group home"),
    ("P21", C, "New", "Residential", "Detached Multi-Family", None,
     "2021-04-05", "Finaled", "2022-01-01", "cottage"),
    ("P20", R, "New", None, None, "0",
     "2016-03-03", "Finaled", "2016-06-01", "NEW 4-UNIT APARTMENT BUILDING"),
]  # fmt: skip


def raw_frame() -> pd.DataFrame:
    df = pd.DataFrame(
        ROWS,
        columns=["Permit_No", "Permit_Type", "Permit_SubType", "Use_Type", "Specific_Use", "Units",
                 "File_Date", "Current_Status", "Status_Date", "B1_WORK_DESC"],
    )  # fmt: skip
    df["File_Date"] = df["File_Date"].map(ms)
    df["Status_Date"] = df["Status_Date"].map(ms)
    df["ObjectId"] = range(len(df))
    df["SqFt"] = "1500"
    df["JobValue"] = "250000"
    return df


def permits() -> pd.DataFrame:
    return fw.build(raw_frame()).set_index("permit_id")


def row(p: pd.DataFrame, pid: str) -> tuple:
    r = p.loc[pid]
    return (r.building_type_std, r.units_new, r.units_confidence)


def test_conforms_and_statuses():
    out = fw.build(raw_frame())
    assert_conforms(out, "permits")
    ids = set(out.permit_id)
    assert {"P5", "P17"}.isdisjoint(ids)  # void and withdrawn
    assert {"P2", "P4"} <= ids  # issued, and expired (an issued permit that lapsed)
    assert (out.jurisdiction_geoid == "4827000").all()


def test_status_snapshots_count_once():
    out = fw.build(raw_frame())
    assert (out.permit_id == "P6").sum() == 1
    p = out.set_index("permit_id")
    assert row(p, "P6") == ("MF5", 23, "reported")
    assert p.loc["P6", "final_date"] == pd.Timestamp("2023-06-01")


def test_filing_year_dates():
    p = permits()
    assert p.loc["P2", "issue_year"] == 2022  # filed 2022-12-28, issued 2023: dated by filing
    assert pd.isna(p.loc["P2", "issue_date"]) and p.loc["P2", "date_precision"] == "year"
    assert p.loc["P2", "application_date"] == pd.Timestamp("2022-12-28")
    assert pd.isna(p.loc["P2", "final_date"])  # issued, not finaled
    assert p.loc["P1", "final_date_type"] == "final_inspection"
    assert pd.isna(p.loc["P13", "final_date"])  # 1900-01-01 is "no date"


def test_dwellings_use_units_when_it_fits_else_the_type():
    p = permits()
    assert row(p, "P1") == ("SFD", 1, "reported")
    assert row(p, "P2") == ("SFD", 1, "derived")  # Units 0 does not fit a house
    assert row(p, "P3") == ("U2", 2, "reported")
    assert row(p, "P4") == ("U2", 2, "derived")
    assert row(p, "P16") == ("SFD", 1, "derived")  # a job value typed into Units


def test_apartment_buildings_from_units():
    p = permits()
    assert row(p, "P7") == ("U3_4", 4, "reported")
    t, n, c = row(p, "P8")  # an apartment permit with Units 1 says nothing about the building
    assert t == "UNKNOWN" and pd.isna(n) and c == "unknown"
    assert row(p, "P9") == ("SFD", 1, "reported")  # a detached rental cottage is a one-unit building
    t, n, c = row(p, "P21")  # no unit count: unknown
    assert t == "UNKNOWN" and pd.isna(n) and c == "unknown"
    assert row(p, "P10") == ("OTHER", 0, "derived")  # hotel rooms are not homes


def test_adus_from_the_description_only():
    p = permits()
    assert row(p, "P11") == ("ADU", 1, "inferred")
    assert row(p, "P12") == ("OTHER", 0, "derived")  # the "Accessory Dwelling" use alone is not an ADU
    assert row(p, "P13") == ("OTHER", 0, "derived")
    assert row(p, "P15") == ("ADU", 1, "inferred")
    assert bool(p.loc["P15", "is_conversion"])


def test_alterations_foundations_groups_and_unknown_uses():
    p = permits()
    assert row(p, "P14") == ("SFD", 0, "derived")
    assert row(p, "P18") == ("UNKNOWN", 0, "derived")
    t, n, c = row(p, "P19")
    assert t == "OTHER" and pd.isna(n) and c == "unknown"
    assert row(p, "P20") == ("U3_4", 4, "inferred")  # no use: the parser's type and count


def test_privacy():
    assert not set(fw.OUT_FIELDS) & fw.PERSONAL
    out = fw.build(raw_frame())
    assert "B1_WORK_DESC" not in out.columns
    assert not out.astype(str).apply(lambda c: c.str.contains("behind the house")).any().any()


def test_load_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(fw, "download", lambda store, refresh=False: raw_frame())
    out = fw.load("TX", DataStore(tmp_path))
    assert len(out) == 21 - 2  # 23 rows, P6 thrice; P5 and P17 dropped


def test_registered():
    assert registry.sources_for("TX")["fw_permits"].module.TABLE == "permits"
