"""Raleigh permits adapter on a synthetic fixture (no network, no real data).

Checks the methodology in the module docstring: building type from the Census code, the city's ADU and
missing-middle flags, the housingunitstotal repair rule (reported if plausible, else derived from the code,
else null), demolitions, and that load() runs the holdout filter.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.nc import raleigh_permits as rp
from lotline.schemas import assert_conforms


def _ms(day: str) -> int:
    return int(pd.Timestamp(day).value // 1_000_000)


# permitnum, code, workclass, issued, units_total, units_exist, adu_type, missing_middle, permittype
ROWS = [
    ("ADU-1", 101, "New Residential Dwelling", "2023-03-02", None, None, "Detached ADU", None, "Building"),
    ("MM-1", 103, "New Residential Dwelling", "2022-09-15", 2, None, None, "Yes", "Building"),
    ("REPAIR-SFD", 101, "New Residential Dwelling", "2024-05-06", None, None, "", "", "Building"),
    ("REPAIR-DUP", 103, "New Building", "2013-07-01", 1, None, None, None, "Building"),
    ("TH-BLDG", 102, "Townhouse", "2023-11-20", 6, None, None, "No", "Building"),
    ("MF-EMPTY", 105, "New Building", "2025-01-10", None, None, None, None, "Building"),
    ("MF-ZERO", 105, "New Building", "2013-02-11", 0, None, None, None, "Building"),
    ("MF-OK", 105, "New Building", "2018-04-04", 79, None, None, None, "Building"),
    ("ALT-1", 434, "Alteration/Repairs", "2016-08-08", 3, 3, None, None, "Building"),
    ("DEMO-1", 645, "Demolish", "2021-12-30", None, None, None, None, "Demolition"),
    ("UNISSUED", 101, "New Residential Dwelling", None, 1, None, None, None, "Building"),
]


@pytest.fixture
def raw() -> pd.DataFrame:
    df = pd.DataFrame(
        ROWS,
        columns=[
            "permitnum",
            "censuslandusecode",
            "workclass",
            "issued",
            "housingunitstotal",
            "housingunitsexist",
            "adu_type",
            "missing_middle",
            "permittypemapped",
        ],
    )
    df["issueddate"] = [_ms(d) if isinstance(d, str) else None for d in df.pop("issued")]
    df["applieddate"] = None
    df["coissueddate"] = None
    df["permitclass"] = df["censuslandusecode"].astype(str)
    df["pin"] = "0000000000"
    df["estprojectcost"] = 100_000.0
    df["totalsqft"] = 0
    df["OBJECTID"] = range(1, len(df) + 1)
    return df


def _by_id(df: pd.DataFrame) -> pd.DataFrame:
    return df.set_index("permit_id")


def test_output_conforms_and_drops_unissued(raw):
    out = rp.build(raw)
    assert_conforms(out, "permits")
    assert "UNISSUED" not in set(out.permit_id)
    assert (out.jurisdiction_geoid == rp.RALEIGH_GEOID).all()
    assert (out.date_precision == "day").all()


def test_adu_flag_sets_type_and_one_derived_unit(raw):
    row = _by_id(rp.build(raw)).loc["ADU-1"]
    assert row.building_type_std == "ADU" and row.adu_type == "detached"
    assert row.units_new == 1 and row.units_confidence == "derived"


def test_missing_middle_flag_is_kept_raw(raw):
    out = _by_id(rp.build(raw))
    assert out.loc["MM-1", "reform_flag_raw"] == "Yes"
    assert out.loc["MM-1", "building_type_std"] == "U2"
    assert (out.loc["MM-1", "units_new"], out.loc["MM-1", "units_confidence"]) == (2, "reported")
    assert pd.isna(out.loc["REPAIR-SFD", "reform_flag_raw"])  # empty string is unknown, not a flag


def test_units_repaired_from_census_code(raw):
    out = _by_id(rp.build(raw))
    # 2024 SFD with no reported units -> 1 derived
    assert (out.loc["REPAIR-SFD", "units_new"], out.loc["REPAIR-SFD", "units_confidence"]) == (1, "derived")
    # duplex reported as 1 unit is implausible -> 2 derived
    assert (out.loc["REPAIR-DUP", "units_new"], out.loc["REPAIR-DUP", "units_confidence"]) == (2, "derived")
    # a townhouse permit covering a whole building keeps its reported count
    assert (out.loc["TH-BLDG", "units_new"], out.loc["TH-BLDG", "units_confidence"]) == (6, "reported")
    assert (out.loc["MF-OK", "units_new"], out.loc["MF-OK", "units_confidence"]) == (79, "reported")


@pytest.mark.parametrize("pid", ["MF-EMPTY", "MF-ZERO", "ALT-1"])
def test_unknown_units_stay_null_never_zero(raw, pid):
    row = _by_id(rp.build(raw)).loc[pid]
    assert pd.isna(row.units_new) and row.units_confidence == "unknown"


def test_demolition(raw):
    row = _by_id(rp.build(raw)).loc["DEMO-1"]
    assert bool(row.is_demolition) and row.building_type_std == "SFD"
    assert row.units_new == 0 and row.units_removed == 1 and row.units_confidence == "derived"


def test_load_applies_holdout_filter(raw, monkeypatch):
    """Pretend the rows are Charlotte's: everything from 2023-06-01 on must be removed."""
    monkeypatch.setattr(rp, "download", lambda store, refresh=False: raw)
    monkeypatch.setattr(rp, "RALEIGH_GEOID", "3712000")
    out = rp.load("NC", store=None)
    assert (out.issue_date < pd.Timestamp("2023-06-01")).all()
    assert {"ADU-1", "MM-1", "DEMO-1"} <= set(out.permit_id)


def test_registered_as_nc_source():
    registry.check_module(rp)
    assert registry.sources_for("NC")["raleigh_permits"].table == "permits"


# Description fallback: permit id -> work description (synthetic text in the style of the city's records)
DESCRIPTIONS = {
    "MF-EMPTY": "BUILDING 4 - 56 UNITS MAIN CASE# BLDNR-000001-2025",  # unknown 105 count -> 56 inferred
    "MF-ZERO": "NEW APT BLDG WITH 3 UNITS",  # 3 does not fit a 105 permit -> stays unknown
    "MF-OK": "NEW APT BLDG WITH 12 UNITS",  # reported 79 is never overridden
    "REPAIR-SFD": "NEW 4-UNIT TOWNHOME BLDG",  # code-derived value is never overridden
    "ALT-1": "INTERIOR ALTERATION",  # alterations stay null, not 0
    "DEMO-X": "DEMOLISH EXISTING 6 UNIT APARTMENT BUILDING",  # 648 demolition: units removed inferred
    "NOCODE": "NEW SINGLE FAMILY DWELLING",  # no type code -> SFD inferred, 1 unit inferred
}


@pytest.fixture
def raw_desc(raw) -> pd.DataFrame:
    extra = raw.iloc[[0, 0]].copy()
    extra["permitnum"] = ["DEMO-X", "NOCODE"]
    extra["censuslandusecode"] = [648, None]
    extra["permitclass"] = ["648", ""]
    extra["permittypemapped"] = ["Demolition", "Building"]
    extra["workclass"] = ["Demolish", "New"]
    extra["adu_type"] = None
    df = pd.concat([raw, extra], ignore_index=True)
    df[rp.DESCRIPTION_FIELD] = df["permitnum"].map(DESCRIPTIONS)
    return df


def test_description_fills_only_unknown_values(raw_desc):
    out = _by_id(rp.build(raw_desc))
    assert (out.loc["MF-EMPTY", "units_new"], out.loc["MF-EMPTY", "units_confidence"]) == (56, "inferred")
    assert out.loc["MF-EMPTY", "type_confidence"] == "high"  # the code's type is kept
    assert pd.isna(out.loc["MF-ZERO", "units_new"]) and out.loc["MF-ZERO", "units_confidence"] == "unknown"
    assert (out.loc["MF-OK", "units_new"], out.loc["MF-OK", "units_confidence"]) == (79, "reported")
    assert (out.loc["REPAIR-SFD", "units_new"], out.loc["REPAIR-SFD", "units_confidence"]) == (1, "derived")
    assert pd.isna(out.loc["ALT-1", "units_new"])
    demo = out.loc["DEMO-X"]
    assert demo.units_new == 0 and demo.units_removed == 6 and demo.units_confidence == "inferred"
    nocode = out.loc["NOCODE"]
    assert (nocode.building_type_std, nocode.type_confidence) == ("SFD", "inferred")
    assert (nocode.units_new, nocode.units_confidence) == (1, "inferred")
    assert_conforms(rp.build(raw_desc), "permits")


def test_description_fallback_can_be_switched_off(raw_desc, monkeypatch):
    monkeypatch.setattr(rp, "USE_DESCRIPTION", False)
    out = _by_id(rp.build(raw_desc))
    assert pd.isna(out.loc["MF-EMPTY", "units_new"]) and out.loc["NOCODE", "building_type_std"] == "UNKNOWN"


def test_description_is_the_only_free_text_field():
    assert rp.DESCRIPTION_FIELD in rp.OUT_FIELDS
    banned = ("name", "owner", "contractor", "comment", "address", "street", "tenant")
    assert not [f for f in rp.OUT_FIELDS if any(b in f.lower() for b in banned)]
