"""Greensboro permits adapter on synthetic rows (no network, no real data).

Checks the module docstring: activity from the application type, building type and units from the occupancy
crosswalk and NumUnits, ADUs from the description parser, cancelled permits dropped, final dates, and that
personal fields are never requested or kept.
"""

import pandas as pd

from lotline import registry
from lotline.adapters.states.nc import greensboro_permits as gp
from lotline.io import DataStore
from lotline.schemas import assert_conforms


def ms(day: str | None) -> int | None:
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000) if isinstance(day, str) else None


# PermitNum, PermitType, ApplicationType, OccupancyDesc, NumUnits, IssuedDate, CancelDate, Description
ROWS = [
    ("G1", "Residential", "New Construction", "One Family Residence", 1, "2022-03-01", None, "New SFD"),
    ("G2", "Residential", "New Construction", "Townhouse", 0, "2022-04-01", None, "Townhome unit 3"),
    ("G3", "Residential", "New Construction", "Duplex", 1, "2023-05-05", None, "duplex, left side"),
    ("G4", "Residential", "New Construction", "Duplex", 0, "2023-05-06", None, "new duplex"),
    ("G5", "Commercial", "New Construction", "Apartment Building - Shell", 24, "2024-01-10", None, "Bldg 3"),
    ("G6", "Commercial", "New Construction", "Apartment-Individual Units", 0, "2024-02-10", None, "Unit 301"),
    ("G7", "Commercial", "New Construction", "Apartment-Individual Units", 4, "2015-02-10", None, "4 units"),
    ("G8", "Residential", "New Construction", "Foundation Only", 1, "2021-06-01", None, "footings"),
    ("G9", "Residential", "New Construction", "One Family Residence", 1, "2026-09-11", None,
     "Construct a 740 square foot accessory Dwelling Unit (ADU)"),
    ("G10", "Residential", "Int/Ext Alteration", "One Family Residence", 0, "2025-11-21", None,
     "Convert the garage to accessory dwelling unit (ADU) with kitchen and laundry."),
    ("G11", "Residential", "New Construction", "Accessory Building/Carport-detached", 0, "2024-02-22", None,
     "New Accessory Dwelling Unit - 420 SF"),
    ("G12", "Commercial", "Miscellaneous", "Daycare", 0, "2026-08-05", None, "adult daycare center"),
    ("G13", "Residential", "Total Demolish", "One Family Residence", 0, "2020-01-01", None, "demo house"),
    ("G14", "Residential", "New Construction", "One Family Residence", 1, "2019-01-01", "2019-02-01", "x"),
    ("G15", "Residential", "Place on Lot", "Mobile Home", 0, "2018-01-01", None, "double wide"),
    ("G16", "Residential", "Deck", "One Family Residence", 0, "2018-03-03", None, "rear deck"),
    ("G17", "Residential", "New Construction", "Accessory Building/Carport-detached", 0, "2018-04-04", None,
     "Guest/Pool House"),
    ("G18", "Commercial", "New Construction", "Business", 0, "2017-05-05", None, "new office"),
    ("G19", "Commercial", "New Construction", "Condominiums", 4, "2022-05-05", None, "4 condos"),
]  # fmt: skip


def raw_frame() -> pd.DataFrame:
    df = pd.DataFrame(
        ROWS,
        columns=["PermitNum", "PermitType", "ApplicationType", "OccupancyDesc", "NumUnits", "IssuedDate",
                 "CancelDate", "Description"],
    )  # fmt: skip
    # The service pads text fields to a fixed width.
    for col in ["PermitType", "ApplicationType", "OccupancyDesc"]:
        df[col] = df[col].str.ljust(60)
    df["IssuedDate"] = df["IssuedDate"].map(ms)
    df["CancelDate"] = df["CancelDate"].map(ms)
    df["Sakey"] = range(len(df))
    df["BuildingSqFt"] = 1200
    df["TotalCost"] = 150000.0
    df["Zoning"] = "R-5"
    df["FinalInspectionDate"] = None
    df["FinalCODate"] = None
    df.loc[0, "FinalCODate"] = ms("2022-10-01")
    df.loc[0, "FinalInspectionDate"] = ms("2022-09-25")
    df.loc[1, "FinalInspectionDate"] = ms("2022-12-01")
    return df


def permits() -> pd.DataFrame:
    return gp.build(raw_frame()).set_index("permit_id")


def row(p: pd.DataFrame, pid: str) -> tuple:
    r = p.loc[pid]
    return (r.building_type_std, r.units_new, r.units_confidence)


def test_conforms_and_cancelled_dropped():
    out = gp.build(raw_frame())
    assert_conforms(out, "permits")
    assert "G14" not in set(out.permit_id)
    assert (out.jurisdiction_geoid == "3728000").all()


def test_dwellings_use_numunits_when_it_fits_else_the_type():
    p = permits()
    assert row(p, "G1") == ("SFD", 1, "reported")
    assert row(p, "G2") == ("TH", 1, "derived")  # NumUnits 0 does not fit a townhouse
    assert row(p, "G3") == ("U2", 1, "reported")  # one permit per half of the building
    assert row(p, "G4") == ("U2", 2, "derived")
    assert row(p, "G15") == ("OTHER", 1, "derived")  # manufactured home, out of BPS types


def test_apartments_counted_from_shell_permits_only():
    p = permits()
    assert row(p, "G5") == ("MF5", 24, "reported")
    assert row(p, "G19") == ("U3_4", 4, "reported")
    for pid in ["G6", "G7"]:  # per-apartment permits never count, even with the building's NumUnits
        t, n, c = row(p, pid)
        assert t == "UNKNOWN" and pd.isna(n) and c == "unknown"


def test_foundation_accessory_and_nonresidential_add_no_units():
    p = permits()
    assert row(p, "G8") == ("UNKNOWN", 0, "derived")
    assert row(p, "G17") == ("OTHER", 0, "derived")  # "guest house" is not read as an ADU
    assert row(p, "G18") == ("OTHER", 0, "derived")
    assert row(p, "G12") == ("OTHER", 0, "derived")  # "adult" is not "ADU"
    assert row(p, "G16") == ("SFD", 0, "derived")  # a deck on a house


def test_adus_from_the_description():
    p = permits()
    for pid in ["G9", "G10", "G11"]:
        assert row(p, pid) == ("ADU", 1, "inferred")
        assert p.loc[pid, "type_confidence"] == "inferred"
    assert bool(p.loc["G10", "is_conversion"])


def test_demolition_and_dates():
    p = permits()
    assert bool(p.loc["G13", "is_demolition"])
    assert p.loc["G13", "units_new"] == 0 and p.loc["G13", "units_removed"] == 1
    assert p.loc["G1", "final_date"] == pd.Timestamp("2022-10-01")
    assert p.loc["G1", "final_date_type"] == "certificate_of_occupancy"
    assert p.loc["G2", "final_date_type"] == "final_inspection"
    assert p.loc["G1", "issue_year"] == 2022 and p.loc["G1", "zoning_raw"] == "R-5"


def test_privacy():
    assert not set(gp.OUT_FIELDS) & gp.PERSONAL
    out = gp.build(raw_frame())
    assert "Description" not in out.columns
    assert not out.astype(str).apply(lambda c: c.str.contains("Townhome unit")).any().any()


def test_load_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(gp, "download", lambda store, refresh=False: raw_frame())
    out = gp.load("NC", DataStore(tmp_path))
    assert len(out) == len(ROWS) - 1


def test_registered():
    assert registry.sources_for("NC")["greensboro_permits"].module.TABLE == "permits"
