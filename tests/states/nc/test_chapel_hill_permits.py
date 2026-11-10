"""Chapel Hill legacy permits adapter on synthetic rows (no network, no real data).

Checks the module docstring: only issued building-class permits are kept, building type from LandUse,
units from New Dwelling Units then the parser, the Chapel Hill ADU rule (named + created, not negated or
existing-only), final dates from the CO Date feature, the zipped geodatabase read end to end, and that
personal fields are never read or kept.
"""

import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.nc import chapel_hill_permits as ch
from lotline.io import DataStore
from lotline.schemas import assert_conforms

from .gdb_writer import DATETIME, FLOAT64, INT32, OBJECTID, STRING, write_gdb

# PrmtID, Num, Class, PrmtType, LandUse, D_Start, Deleted, Exit_Reason, Descr
ROWS = [
    (1, 201510001, "Building", "Residential Building", "Single Family", "6/1/15 9:00 AM", "No", "NULL",
     "NEW SINGLE FAMILY RESIDENCE BPME 2400 sqft"),
    (2, 201510002, "Building", "Residential Zoning-Building", "Single Family", "7/2/15 1:30 PM", "No", "NULL",
     "ADDITION - ADU  1-237 sf addition BPME"),
    (3, 201610003, "Building", "Residential Building", "Single Family", "3/3/16 10:00 AM", "No", "NULL",
     "Garage with 2 bedroom accessory apartment addition"),
    (4, 201610004, "Building", "Residential Building", "Single Family", "4/4/16 10:00 AM", "No", "NULL",
     "ADU atop EXISTING GARAGE"),
    (5, 201710005, "Building", "Residential Building", "Single Family", "5/5/17 10:00 AM", "No", "NULL",
     "Work is to turn downstairs 2 car garage into a new two bedroom apartment."),
    (6, 201710006, "Building", "Residential Building", "Single Family", "6/6/17 10:00 AM", "No", "NULL",
     "NEW SINGLE FAMILY RESIDENCE BPME 2-796sqft   With 612 sqft accessory dwelling unit"),
    # not new ADUs
    (7, 201710007, "Building", "Residential Building", "Single Family", "6/7/17 10:00 AM", "No", "NULL",
     "Finish/remodel basement- add 1 bedroom but NOT ADU  735 sf"),
    (8, 201810008, "Building", "Residential Building", "Single Family", "1/8/18 10:00 AM", "No", "NULL",
     "INTERIOR RENOVATION (B-M-E-P) 528sqft  Renovation of garage apartment"),
    (9, 201810009, "Building", "Residential Building", "Single Family", "1/9/18 10:00 AM", "No", "NULL",
     "ACCESSORY DWELLING UNIT (BPME- 546sqft)  Expand existing accessory dwelling unit"),
    (10, 201810010, "Building", "Residential Building", "Single Family", "1/10/18 10:00 AM", "No", "NULL",
     "REMODEL  Convert duplex into SFD with accessory apartment."),
    (11, 201810011, "Building", "Residential Building", "Single Family", "1/11/18 10:00 AM", "No", "NULL",
     "New pool- and guest cottage  4870 sf"),
    (12, 201810012, "Building", "Residential Building", "Single Family", "1/12/18 10:00 AM", "No", "NULL",
     "AFTER-THE-FACT ACCESSORY DWELLING UNIT (grandfathered)  Life safety permit"),
    (13, 201810013, "Building", "Commercial Building", "Commercial Office", "2/1/18 10:00 AM", "No", "NULL",
     "Upfit suite 200 for ADU Inc. offices"),
    # other rows
    (14, 201910014, "Building", "Commercial Building", "Apartment", "3/1/19 10:00 AM", "No", "NULL",
     "NEW BUILDING  Apartment building, community room"),
    (15, 201910015, "Building", "Residential Building", "Duplex", "3/2/19 10:00 AM", "No", "NULL",
     "Demolition of duplex"),
    (16, 201910016, "Building", "Residential Building", "Single Family", "3/3/19 10:00 AM", "No", "NULL",
     "NEW DECK  Adding a wood deck"),
    # dropped
    (17, 201910017, "Sub Permit", "Electrical", "Single Family", "3/4/19 10:00 AM", "No", "NULL", "New ADU"),
    (18, 201910018, "Zoning", "Residential Zoning", "Single Family", "3/5/19 10:00 AM", "No", "NULL",
     "New ADU"),
    (19, 201910019, "Building", "Residential Building", "Single Family", "NULL", "No", "NULL", "New ADU"),
    (20, 201910020, "Building", "Residential Building", "Single Family", "3/6/19 10:00 AM", "Yes", "NULL",
     "New ADU"),
    (21, 201910021, "Building", "Residential Building", "Single Family", "3/7/19 10:00 AM", "No", "Void",
     "New ADU"),
]  # fmt: skip
COLUMNS = ["PrmtID", "Num", "Class", "PrmtType", "LandUse", "D_Start", "Deleted", "Exit_Reason", "Descr"]
# PrmtID, Prop, Val, NumVal, DateVal
FEATURE_ROWS = [
    (1, "New Dwelling Units", "1", "1", "NULL"),
    (1, "Cost of Construction", "350000", "350000", "NULL"),
    (1, "New Total Heated Square Footage", "2400", "2400", "NULL"),
    (1, "CO Date", "NULL", "NULL", "12/1/15 3:00 PM"),
    (14, "New Dwelling Units", "48", "48", "NULL"),
    (15, "New Dwelling Units", "-2", "-2", "NULL"),
    (2, "New Dwelling Units", "0", "0", "NULL"),  # ignored for an ADU
    (16, "Lot Size (ft²)", "9000", "9000", "NULL"),  # not a feature the adapter reads
]


def raw() -> pd.DataFrame:
    df = pd.DataFrame(ROWS, columns=COLUMNS)
    df["D_Create"] = df["D_Start"].where(df["D_Start"] != "NULL", "3/1/19 9:00 AM")
    return df


def feats() -> pd.DataFrame:
    return ch.features(pd.DataFrame(FEATURE_ROWS, columns=["PrmtID", "Prop", "Val", "NumVal", "DateVal"]))


def permits() -> pd.DataFrame:
    return ch.build(raw(), feats()).set_index("permit_id")


def row(p: pd.DataFrame, pid: int) -> tuple:
    r = p.loc[str(pid)]
    return (r.building_type_std, r.units_new, r.units_confidence)


def test_conforms_and_rows_kept():
    out = ch.build(raw(), feats())
    assert_conforms(out, "permits")
    assert set(out.permit_id) == {
        str(r[1]) for r in ROWS[:16]
    }  # sub, zoning, unissued, deleted, void dropped
    assert (out.jurisdiction_geoid == "3711800").all() and out.parcel_id.isna().all()


def test_adu_rule_matches_created_adus():
    p = permits()
    for pid in [201510002, 201610003, 201610004, 201710005, 201710006]:
        assert row(p, pid) == ("ADU", 1, "inferred"), pid
        assert p.loc[str(pid), "type_confidence"] == "inferred"


def test_adu_rule_skips_negated_existing_and_excluded_words():
    p = permits()
    for pid in [201710007, 201810008, 201810009, 201810010, 201810011, 201810012, 201810013]:
        assert p.loc[str(pid), "building_type_std"] != "ADU", pid


def test_adu_named_new_unit_cases():
    assert ch.adu_named_new("New ADU   (750 sf)  and carport")
    assert ch.adu_named_new("ADU (BPME) 742sqft")  # starts with the ADU's name
    assert ch.adu_named_new(
        "Remodel interior and exterior  Addition of Master wing- den- garage and garage apartment"
    )
    assert not ch.adu_named_new("Basement renovation to include a new kitchen- no new ADU- 1599 sf")
    assert not ch.adu_named_new(
        "RENOVATION BPE 144sqft  Finishing 12x12 workshop  Pine Knolls NCD - ADU prohibited"
    )
    assert not ch.adu_named_new("Interior remodel of main house and ADU   3416 sf")
    assert not ch.adu_named_new("Finishing attic and turning basement into in-law suite")
    assert not ch.adu_named_new("")


def test_types_and_units():
    p = permits()
    assert row(p, 201510001) == ("SFD", 1, "reported")  # New Dwelling Units feature
    assert row(p, 201910014)[1:] == (48, "reported")
    assert p.loc["201910014", "building_type_std"] == "MF5"  # size class from the reported count
    assert bool(p.loc["201910015", "is_demolition"]) and p.loc["201910015", "units_new"] == 0
    assert row(p, 201810013) == ("OTHER", 0, "derived")  # non-residential use
    assert p.loc["201910016", "building_type_std"] == "SFD"


def test_dates_and_features():
    p = permits()
    r = p.loc["201510001"]
    assert r.issue_date == pd.Timestamp("2015-06-01") and r.issue_year == 2015
    assert r.final_date == pd.Timestamp("2015-12-01") and r.final_date_type == "certificate_of_occupancy"
    assert r.valuation_usd == 350000 and r.floor_area_sqft == 2400
    assert r.application_date == pd.Timestamp("2015-06-01")
    assert pd.isna(p.loc["201510002", "final_date"])


def test_privacy():
    assert not set(ch.PERMIT_FIELDS) & ch.PERSONAL
    out = ch.build(raw(), feats())
    assert "Descr" not in out.columns
    assert not out.astype(str).apply(lambda c: c.str.contains("accessory apartment", case=False)).any().any()


def _write_zip(tmp_path) -> Path:
    gdb = tmp_path / "src" / "LAMA Legacy Permit Data Production.gdb"
    text = ["Class", "PrmtType", "LandUse", "Descr", "Address", "D_Start", "D_Create", "Deleted"]
    text += ["Exit_Reason"]
    permit_fields = [("OBJECTID", OBJECTID), ("PrmtID", INT32), ("Num", INT32)] + [(c, STRING) for c in text]
    permit_rows = [dict(zip(COLUMNS, r, strict=True), Address="1 Fake St", D_Create=r[5]) for r in ROWS]
    feature_fields = [("OBJECTID", OBJECTID), ("Prop", STRING), ("Class", STRING), ("Val", STRING),
                      ("NumVal", STRING), ("DateVal", STRING), ("PrmtID", INT32), ("D_DateVal", DATETIME),
                      ("Spare", FLOAT64)]  # fmt: skip
    feature_rows = [dict(PrmtID=a, Prop=b, Val=c, NumVal=d, DateVal=e, D_DateVal=datetime(2015, 1, 1))
                    for a, b, c, d, e in FEATURE_ROWS]  # fmt: skip
    write_gdb(
        gdb, {ch.PERMIT_TABLE: (permit_fields, permit_rows), ch.FEATURE_TABLE: (feature_fields, feature_rows)}
    )
    path = tmp_path / "raw" / ch.FILE_NAME
    path.parent.mkdir(parents=True)
    with zipfile.ZipFile(path, "w") as z:
        for f in sorted(gdb.iterdir()):
            z.write(f, f"{gdb.name}/{f.name}")
    return path


def test_read_file_end_to_end(tmp_path):
    permits_raw, features_wide = ch.read_file(_write_zip(tmp_path))
    assert "Address" not in permits_raw.columns  # never read
    out = ch.build(permits_raw, features_wide)
    assert_conforms(out, "permits")
    assert (out.building_type_std == "ADU").sum() == 5


def test_read_file_rejects_unsafe_paths(tmp_path):
    path = tmp_path / ch.FILE_NAME
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("../evil.gdb/a00000001.gdbtable", b"x")
    with pytest.raises(ValueError, match="unsafe"):
        ch.read_file(path)


def test_load_validates(tmp_path, monkeypatch):
    zpath = _write_zip(tmp_path)
    monkeypatch.setattr(ch, "download", lambda store, refresh=False: zpath)
    out = ch.load("NC", DataStore(tmp_path))
    assert len(out) == 16
    with pytest.raises(ValueError):
        ch.load("MN", DataStore(tmp_path))


def test_registered():
    assert registry.sources_for("NC")["chapel_hill_permits"].module.TABLE == "permits"
