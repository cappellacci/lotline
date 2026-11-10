"""Asheville permits adapter on synthetic rows (no network, no real data).

Checks the module docstring: never-issued records dropped, years from the application date, ADUs from the
city's ADU categories and (on house, accessory and alteration permits only) from the description, work on
an existing ADU not read as a new one, a new house with an ADU kept as a house, building types and units
from the record categories, and that personal fields are never requested or kept.
"""

import pandas as pd

from lotline import registry
from lotline.adapters.states.nc import asheville_permits as ap
from lotline.io import DataStore
from lotline.schemas import assert_conforms


def ms(day: str) -> int:
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


# record_id, opened, status, type, subtype, category, description
ROWS = [
    ("A1", "2023-03-01", "CO Issued", "Residential", "New Building", "ADU Detached", "NEW DETACHED UNIT"),
    ("A2", "2023-04-01", "Issued", "Residential", "Existing Building", "ADU Attached",
     "BASEMENT ADU WITH 1 BEDROOM AND 1 BATHROOM"),
    ("A3", "2024-05-01", "CO Issued", "Residential", "Existing Building", "ADU Attached", "ADU OVER GARAGE"),
    ("A4", "2017-06-01", "CO Issued", "Residential", "New Building", "SFD",
     "CONSTRUCTION OF A NEW ACCESSORY DWELLING UNIT FOR A. OWNER"),
    ("A5", "2016-07-01", "Finaled", "Residential", "Accessory Structure", "Other",
     "NEW DETACHED GARAGE WITH ACCESSORY APARTMENT ABOVE"),
    ("A6", "2018-08-01", "Finaled", "Residential", "Trade", "Plumbing", "PLUMBING FOR NEW ADU"),
    ("A7", "2018-08-02", "Finaled", "Residential", "Site Work", "NA", "GRADING FOR NEW ADU"),
    ("A8", "2018-09-01", "CC Issued", "Residential", "Existing Building", "Alterations",
     "ENCLOSING A CARPORT BENEATH AN EXISTING PARTIALLY FINISHED ADU"),
    ("A9", "2022-10-01", "CO Issued", "Residential", "New Building", "SFD",
     "NEW SINGLE FAMILY RESIDENCE SITE BUILT WITH FINISHED BASEMENT THAT WILL BE FINISHED TO CREATE AN ADU"),
    ("A10", "2020-01-15", "CO Issued", "Residential", "New Building", "SFD", "NEW SINGLE FAMILY HOME"),
    ("A11", "2020-02-15", "CO Issued", "Residential", "New Building", "SFD Waiver", "NEW HOUSE"),
    ("A12", "2021-03-15", "CO Issued", "Residential", "New Building", "Townhome", "NEW TOWNHOME"),
    ("A13", "2021-04-15", "CO Issued", "Residential", "New Building", "Duplex", "NEW DUPLEX"),
    ("A14", "2021-05-15", "CO Issued", "Residential", "New Building", "Duplex", "NEW DUPLEX, LEFT SIDE"),
    ("A15", "2019-06-15", "CO Issued", "Commercial", "New Building", "Multi-Family",
     "NEW APARTMENT BUILDING WITH 48 UNITS"),
    ("A16", "2019-07-15", "CO Issued", "Commercial", "New Building", "Multi-Family",
     "NEW RESIDENTIAL BUILDING 8"),
    ("A17", "2019-08-15", "CO Issued", "Commercial", "New Building", "Shell Only", "NEW RETAIL SHELL"),
    ("A18", "2025-09-15", "Issued", "Residential", "Demolition", "NA", "DEMO DETACHED ADU STRUCTURE"),
    ("A19", "2025-10-15", "Revoked", "Residential", "New Building", "ADU Detached", "NEW ADU"),
    ("A20", "2025-11-15", "Plan Check", "Residential", "New Building", "SFD", "NEW HOUSE"),
    ("A21", "2015-12-15", "Expired", "Residential", "New Building", "SFD", "NEW HOUSE"),
    ("A22", "2015-01-20", "CO Issued", "Residential", "Manufactured Home", "Existing Park", "SET HOME"),
    ("A23", "2014-02-20", "CO Issued", "Residential", "New", "NA", "NEW SINGLE FAMILY DWELLING"),
    ("A24", "2014-03-20", "Finaled", "Residential", "Existing Building", "Alterations", "KITCHEN REMODEL"),
]  # fmt: skip


def raw_frame() -> pd.DataFrame:
    df = pd.DataFrame(
        ROWS,
        columns=["record_id", "date_opened", "record_status", "record_type_type", "record_type_subtype",
                 "record_type_category", "description"],
    )  # fmt: skip
    df["date_opened"] = df["date_opened"].map(ms)
    df["status"] = df["record_status"]
    df["record_type"] = df["record_type_type"].str[:3] + ": " + df["record_type_category"]
    df["objectid"] = range(len(df))
    df["job_value"] = 90000.0
    return df


def permits() -> pd.DataFrame:
    return ap.build(raw_frame()).set_index("permit_id")


def row(p: pd.DataFrame, pid: str) -> tuple:
    r = p.loc[pid]
    return (r.building_type_std, r.units_new, r.units_confidence)


def test_conforms_and_never_issued_dropped():
    out = ap.build(raw_frame())
    assert_conforms(out, "permits")
    assert {"A19", "A20"}.isdisjoint(out.permit_id)  # revoked, still in plan check
    assert "A21" in set(out.permit_id)  # expired permits were issued
    assert (out.jurisdiction_geoid == "3702140").all()


def test_years_are_application_years():
    p = permits()
    assert p.loc["A1", "issue_year"] == 2023 and pd.isna(p.loc["A1", "issue_date"])
    assert p.loc["A1", "application_date"] == pd.Timestamp("2023-03-01")
    assert (p.date_precision == "year").all()


def test_adus_from_the_city_categories():
    p = permits()
    for pid in ["A1", "A2", "A3"]:
        assert row(p, pid) == ("ADU", 1, "derived")
        assert p.loc[pid, "type_confidence"] == "high"
    assert p.loc["A1", "adu_type"] == "detached" and p.loc["A1", "reform_flag_raw"] == "ADU Detached"
    assert p.loc["A2", "adu_type"] == "internal_conversion"  # attached, in the basement
    assert p.loc["A3", "adu_type"] == "attached"


def test_adus_from_the_description_on_building_permits_only():
    p = permits()
    for pid in ["A4", "A5"]:
        assert row(p, pid) == ("ADU", 1, "inferred")
        assert p.loc[pid, "type_confidence"] == "inferred"
    for pid in ["A6", "A7"]:  # trade and site-work permits for an ADU are companions, not the ADU
        assert p.loc[pid, "building_type_std"] != "ADU" and p.loc[pid, "units_new"] == 0


def test_existing_adu_and_new_house_with_adu():
    p = permits()
    assert p.loc["A8", "building_type_std"] != "ADU" and p.loc["A8", "units_new"] == 0
    assert row(p, "A9") == ("SFD", 1, "derived")
    assert p.loc["A9", "reform_flag_raw"] == "adu_text_with_new_house"


def test_existing_adu_pattern():
    hit = ap.EXISTING_ADU.search
    assert hit("GARAGE WHERE THE ADU WAS BEFORE") and hit("CHANGE OF USE FROM A PERMITTED ADU TO STORAGE")
    assert not hit("CONVERTING AN EXISTING STRUCTURE INTO AN ADU")
    assert not hit("CONVERTING EXISTING DETACHED GARAGE TO ADU")
    assert not hit("EXISTING HOME AND ADU SHARING A DRIVEWAY")


def test_houses_townhouses_duplexes_and_manufactured_homes():
    p = permits()
    assert row(p, "A10") == ("SFD", 1, "derived")
    assert row(p, "A11") == ("SFD", 1, "derived")
    assert row(p, "A12") == ("TH", 1, "derived")
    assert row(p, "A13") == ("U2", 2, "derived")
    assert row(p, "A14") == ("U2", 1, "derived")  # one half of the building
    assert row(p, "A22") == ("OTHER", 1, "derived")


def test_multifamily_and_early_new_records_from_the_description():
    p = permits()
    assert row(p, "A15") == ("MF5", 48, "inferred")
    t, n, c = row(p, "A16")  # "residential building 8" is neither an ADU nor a count
    assert t == "UNKNOWN" and pd.isna(n) and c == "unknown"
    assert row(p, "A17") == ("OTHER", 0, "derived")
    assert row(p, "A23") == ("SFD", 1, "inferred")


def test_demolition_and_alterations():
    p = permits()
    assert bool(p.loc["A18", "is_demolition"]) and p.loc["A18", "building_type_std"] != "ADU"
    assert p.loc["A18", "units_new"] == 0
    assert row(p, "A24") == ("UNKNOWN", 0, "derived")


def test_privacy():
    assert not set(ap.OUT_FIELDS) & ap.PERSONAL
    out = ap.build(raw_frame())
    assert "description" not in out.columns
    assert not out.astype(str).apply(lambda c: c.str.contains("OWNER")).any().any()


def test_load_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, "download", lambda store, refresh=False: raw_frame())
    out = ap.load("NC", DataStore(tmp_path))
    assert len(out) == len(ROWS) - 2


def test_registered():
    assert registry.sources_for("NC")["asheville_permits"].module.TABLE == "permits"
