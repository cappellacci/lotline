"""Durham permits adapter on a synthetic fixture (no network, no real data).

Checks the methodology in the module docstring: kept statuses, building type from BLD_Type (with re-typing
by a contradicting multifamily count), the DWELLING_UNITS rule (reported if plausible, else derived, else
null; only for new construction), demolitions, the city/county rule (point in polygon, PIN-prefix and
parent-parcel fallbacks, default), the even-odd polygon test with a hole, and that load() runs the holdout
filter.
"""

import numpy as np
import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.nc import durham_permits as dp
from lotline.schemas import assert_conforms

# A 2x2 "city" with a 0.5x0.5 unincorporated hole in the middle (lon/lat units are arbitrary here).
CITY = [[[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]], [[0.75, 0.75], [1.25, 0.75], [1.25, 1.25], [0.75, 1.25]]]
IN, OUT, HOLE = (0.5, 0.5), (3.0, 3.0), (1.0, 1.0)


def _ms(day: str) -> int:
    return int(pd.Timestamp(day).value // 1_000_000)


SFH, MF, R2, R3 = "Single Family House", "5+ Residential Units", "Residential (2)", "Residential (3)"

# PermitNum, BLD_Type, activity, status, units, issued, point, PIN15, PID, Occupancy
ROWS = [
    ("SFD-1", SFH, "NEW", "CO Issued", 1, "2023-03-02", IN, "0822-15-53-5325", "1", "Single Family"),
    ("SFD-2", SFH, "NEW", "Issued", 2, "2024-05-06", IN, "0822530923", "2", "Single Family"),
    ("SFD-NOU", SFH, "NEW", "Issued", None, "2024-05-06", OUT, "0900000000", "3", None),
    ("TH-ROW", "Townhouse", "NEW", "CO Issued", 6, "2023-11-20", IN, "0822530924", "4", "Townhouse"),
    ("DUP-SIDE", "Duplex", "NEW", "CO Issued", 1, "2022-09-15", IN, "0822530925", "5", "Duplex"),
    ("DUP-3", "Duplex", "NEW", "CO Issued", 3, "2025-02-01", IN, "0822530926", "6", "Duplex"),
    ("DUP-NOU", "Duplex", "NEW", "CO Issued", None, "2025-02-01", IN, "0822530927", "7", "Duplex"),
    ("MF-OK", MF, "NEW", "CO Issued", 79, "2018-04-04", OUT, "0747096580", "8", R2),
    ("MF-4", MF, "NEW", "Issued", 4, "2025-06-01", IN, "0822530928", "9", R2),
    ("MF-1", MF, "NEW", "Issued", 1, "2017-06-01", IN, "0822530929", "10", R3),
    ("ADU-1", "Accessory Dwelling", "NEW", "Issued", None, "2021-07-01", HOLE, "0822530930", "11", None),
    ("ADU-ALT", "Accessory Dwelling", "ALT", "Issued", 1, "2021-07-01", IN, "0822530931", "12", None),
    ("MOD-SF", "Modular Unit", "NEW", "Issued", 1, "2016-01-04", IN, "0822530932", "13", "Single Family"),
    ("MOD-SCH", "Modular Unit", "NEW", "Issued", 1, "2016-01-04", IN, "0822530933", "14", "Educational"),
    ("NONRES", "Non-Residential", "NEW", "Issued", 120, "2020-01-04", IN, "0822530934", "15", "Storage (1)"),
    ("ALT-SFD", SFH, "ALT", "CO Issued", 1, "2019-08-08", IN, "0822530935", "16", None),
    ("DEMO-SFD", SFH, "DEM", "CO Issued", None, "2021-12-30", IN, "0822530936", "17", None),
    ("DEMO-MF", MF, "DEM", "CO Issued", None, "2021-12-30", IN, "0822530937", "18", None),
    ("DEMO-REP", "Duplex", "DEM", "CO Issued", 2, "2021-12-30", IN, "0822530938", "19", None),
    ("VOID", SFH, "NEW", "Void", 1, "2023-03-02", IN, "0822530939", "20", None),
    ("UNISSUED", SFH, "NEW", "CO Issued", 1, None, IN, "0822530940", "21", None),
    # No point: PIN prefix shared with located city permits (0822 53 09 ..) → city
    ("NOPT-PIN", SFH, "NEW", "Issued", 1, "2025-03-01", None, "0822-77-53-0999", "22", None),
    # No point: PIN prefix shared with the located county permit 0747096580 → county
    ("NOPT-CTY", MF, "NEW", "Issued", 40, "2025-03-01", None, "0747098856", "23", None),
    # No point, pending plat: parent parcel 8 is the county apartment site → county
    ("NOPT-PP", "Townhouse", "NEW", "Issued", 1, "2025-03-01", None, "8-PP251000", "8-PP251000", None),
    # No point, no usable PIN or parent → UNLOCATED_GEOID
    ("NOPT-NONE", "Townhouse", "NEW", "Issued", 1, "2025-03-01", None, None, "999-PP1-PP2", None),
    ("MULTI", "Non-Residential", "ADD", "CO Issued", None, "2015-05-05", OUT, "0900000001", "24", None),
    ("MULTI", "Non-Residential", "ADD", "CO Issued", None, "2015-05-05", OUT, "0900000002", "25", None),
]  # fmt: skip


@pytest.fixture
def raw() -> pd.DataFrame:
    cols = ["PermitNum", "BLD_Type", "BLDB_ACTIVITY", "PmtStatus", "DWELLING_UNITS", "issued", "pt", "PIN15"]
    df = pd.DataFrame(ROWS, columns=[*cols, "PID", "Occupancy"])
    df["ISSUE_DATE"] = [_ms(d) if isinstance(d, str) else None for d in df.pop("issued")]
    pts = df.pop("pt")
    df["lon"] = [p[0] if p else np.nan for p in pts]
    df["lat"] = [p[1] if p else np.nan for p in pts]
    df["CO_SIGNOFF_DATE"] = [_ms("2024-01-02") if i == 0 else None for i in range(len(df))]
    df["TYPE"] = "RESI"
    df["BLD_Cost"] = 250_000.0
    df["SQFT_FLOOR"] = 0.0
    df["OBJECTID"] = range(1, len(df) + 1)
    return df


@pytest.fixture
def out(raw) -> pd.DataFrame:
    return dp.build(raw, CITY).set_index("permit_id")


def test_conforms_and_keeps_only_issued(raw):
    built = dp.build(raw, CITY)
    assert_conforms(built, "permits")
    assert not {"VOID", "UNISSUED"} & set(built.permit_id)
    assert built.permit_id.is_unique  # MULTI (one permit on two parcels) appears once
    assert (built.date_precision == "day").all()


def test_points_in_rings_even_odd_with_hole():
    got = dp.points_in_rings([0.5, 3.0, 1.0, 1.9, -0.1], [0.5, 3.0, 1.0, 1.9, 1.0], CITY)
    assert got.tolist() == [True, False, False, True, False]


def test_normalise_pin_drops_durham_block_digits():
    s = pd.Series(["0822-15-53-5325", "0822530923", "154829-PP221052", None, "12345"])
    assert dp.normalise_pin(s).tolist()[:2] == ["0822535325", "0822530923"]
    assert dp.normalise_pin(s)[2:].isna().all()


def test_jurisdiction_by_point_pin_prefix_parent_and_default(out):
    assert out.at["SFD-1", "jurisdiction_geoid"] == dp.DURHAM_CITY_GEOID
    assert out.at["SFD-NOU", "jurisdiction_geoid"] == dp.DURHAM_COUNTY_GEOID
    assert out.at["ADU-1", "jurisdiction_geoid"] == dp.DURHAM_COUNTY_GEOID  # in the hole
    assert out.at["NOPT-PIN", "jurisdiction_geoid"] == dp.DURHAM_CITY_GEOID
    assert out.at["NOPT-CTY", "jurisdiction_geoid"] == dp.DURHAM_COUNTY_GEOID
    assert out.at["NOPT-PP", "jurisdiction_geoid"] == dp.DURHAM_COUNTY_GEOID
    assert out.at["NOPT-NONE", "jurisdiction_geoid"] == dp.UNLOCATED_GEOID


@pytest.mark.parametrize(
    "pid, btype, units, conf",
    [
        ("SFD-1", "SFD", 1, "reported"),
        ("SFD-2", "SFD", 1, "derived"),  # 2 units on a single-family house is implausible
        ("SFD-NOU", "SFD", 1, "derived"),
        ("TH-ROW", "TH", 6, "reported"),  # a permit for a whole townhouse row
        ("DUP-SIDE", "U2", 1, "reported"),  # one side of a duplex
        ("DUP-NOU", "U2", None, "unknown"),
        ("MF-OK", "MF5", 79, "reported"),
        ("MF-1", "MF5", None, "unknown"),
        ("ADU-1", "ADU", 1, "derived"),
        ("MOD-SF", "SFD", 1, "reported"),
        ("MOD-SCH", "OTHER", None, "unknown"),
        ("NONRES", "OTHER", None, "unknown"),  # non-residential DWELLING_UNITS are not read
        ("ALT-SFD", "SFD", None, "unknown"),  # alterations never add units
        ("ADU-ALT", "ADU", None, "unknown"),
    ],
)
def test_units_rule(out, pid, btype, units, conf):
    row = out.loc[pid]
    assert row.building_type_std == btype
    assert (pd.isna(row.units_new) and units is None) or row.units_new == units
    assert row.units_confidence == conf


def test_contradicting_multifamily_count_retypes(out):
    assert (out.at["MF-4", "building_type_std"], out.at["MF-4", "type_confidence"]) == ("U3_4", "inferred")
    assert out.at["MF-4", "units_new"] == 4 and out.at["MF-4", "units_confidence"] == "reported"
    assert out.at["DUP-3", "building_type_std"] == "U3_4" and out.at["DUP-3", "units_new"] == 3
    assert out.at["MOD-SF", "type_confidence"] == "inferred"
    assert out.at["SFD-1", "type_confidence"] == "high"


def test_adu_type_unknown_and_demolitions(out):
    assert out.at["ADU-1", "adu_type"] == "unknown" and pd.isna(out.at["SFD-1", "adu_type"])
    sfd = out.loc["DEMO-SFD"]
    assert sfd.is_demolition and sfd.units_new == 0 and sfd.units_removed == 1
    assert sfd.units_confidence == "derived"
    assert pd.isna(out.at["DEMO-MF", "units_removed"]) and out.at["DEMO-MF", "units_confidence"] == "unknown"
    assert out.at["DEMO-REP", "units_removed"] == 2 and out.at["DEMO-REP", "units_confidence"] == "reported"


def test_final_date_is_certificate_of_occupancy(out):
    assert out.at["SFD-1", "final_date"] == pd.Timestamp("2024-01-02")
    assert out.at["SFD-1", "final_date_type"] == "certificate_of_occupancy"
    assert pd.isna(out.at["SFD-2", "final_date_type"])


def test_out_fields_are_non_personal():
    personal = {"COMMENTS", "DESCRIPTION", "PROJECT_NAME", "PROJECT_TYPE"}
    assert not personal & set(dp.OUT_FIELDS)
    assert not any("OWN" in f.upper() or "CONTR" in f.upper() or "ADDR" in f.upper() for f in dp.OUT_FIELDS)


def test_registered_as_nc_source():
    registry.check_module(dp)
    assert registry.sources_for("NC")["durham_permits"].table == "permits"


def test_load_applies_holdout(monkeypatch, raw, tmp_path):
    calls = {}

    def fake_apply(df, state, **cols):
        calls.update(state=state, **cols)
        return df

    monkeypatch.setattr(dp, "download", lambda store, **kw: raw)
    monkeypatch.setattr(dp, "download_city_limits", lambda store, **kw: CITY)
    monkeypatch.setattr(dp.holdout, "apply", fake_apply)
    out = dp.load("NC", store=None)
    assert calls == {
        "state": "NC",
        "geoid_col": "jurisdiction_geoid",
        "date_col": "issue_date",
        "year_col": "issue_year",
    }
    assert_conforms(out, "permits")
