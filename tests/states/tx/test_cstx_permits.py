# ruff: noqa: E501  (synthetic permit rows, one per line)
"""College Station permits adapter on synthetic Socrata rows (no network, no real data).

Checks the module table: types and units by permit type and subtype, the city's 'Living Quarters' ADU subtype,
parser ADUs on accessory and addition permits only, demolitions, dropped statuses, the College Station
GEOID, the Brazos parcel ID, that the description is never kept, and schema validity.
"""

import pandas as pd

from lotline.adapters.states.tx import cstx_permits as cs
from lotline.schemas import assert_conforms

ROWS = [
    # permit, type, subtype, description, issued, status, units, apn
    ("P1", "Residential", "Single Family Detached", "New SFR", "2021-03-04T00:00:00.000", "Final", "1", "12345"),
    ("P2", "Residential Accessory", "Living Quarters", "Detached living quarters 600 sf", "2022-05-01T00:00:00.000", "Final", "", "222"),
    ("P3", "Residential Addition Attached", "Living Space", "Add attached ADU with kitchen, owner Jane 555-1234", "2023-01-02T00:00:00.000", "Issued", "", ""),
    ("P4", "Residential Addition Attached", "Living Space", "Add master bedroom", "2023-01-03T00:00:00.000", "Final", "", ""),
    ("P5", "Residential Accessory", "Pool House", "Pool house with half bath", "2023-02-01T00:00:00.000", "Final", "", ""),
    ("P6", "Residential", "Duplex", "Duplex", "2019-07-07T00:00:00.000", "Final", "2", ""),
    ("P7", "Multi-Family", "4 Dwelling Units", "Fourplex", "2020-01-01T00:00:00.000", "Final", "1", ""),
    ("P8", "Multi-Family", "5 Dwelling Units Or More", "Apartments", "2020-01-01T00:00:00.000", "Final", "48", ""),
    ("P9", "Demolition", "Single-Family", "Demo house", "2020-06-01T00:00:00.000", "Final", "", ""),
    ("P10", "Residential", "Single Family Detached", "New SFR", "2021-03-04T00:00:00.000", "Void", "1", ""),
    ("P11", "Residential", "Single Family Detached", "New SFR", None, "Pending", "1", ""),
    ("P12", "Residential", "Single-Family", "New house and detached ADU", "2014-01-01T00:00:00.000", "Final", "1", ""),
    ("P13", "Residential Accessory", "Living Quarters", "Garage apartment above attached garage, attached ADU", "2024-01-01T00:00:00.000", "Final", "", ""),
]  # fmt: skip
COLS = ["permit_number", "permit_type", "permit_subtype", "permit_description", "issued_date", "current_status",
        "number_units", "site_apn"]  # fmt: skip


def built() -> pd.DataFrame:
    return cs.build(pd.DataFrame(ROWS, columns=COLS)).set_index("permit_id")


def test_types_units_and_adus():
    b = built()
    assert (b.loc["P1", "building_type_std"], b.loc["P1", "units_new"]) == ("SFD", 1)
    assert b.loc["P2", "building_type_std"] == "ADU" and b.loc["P2", "adu_type"] == "detached"
    assert b.loc["P2", "type_confidence"] == "high"
    assert b.loc["P3", "building_type_std"] == "ADU" and b.loc["P3", "type_confidence"] == "inferred"
    assert b.loc["P3", "adu_type"] == "attached"
    assert b.loc["P4", "building_type_std"] == "OTHER" and b.loc["P4", "units_new"] == 0
    assert b.loc["P5", "building_type_std"] == "OTHER"  # pool house is not an ADU
    assert (b.loc["P6", "building_type_std"], b.loc["P6", "units_new"]) == ("U2", 2)
    assert (b.loc["P7", "building_type_std"], b.loc["P7", "units_new"]) == ("U3_4", 4)
    assert b.loc["P7", "units_confidence"] == "derived"
    assert (b.loc["P8", "building_type_std"], b.loc["P8", "units_new"]) == ("MF5", 48)
    assert (
        b.loc["P9", "is_demolition"] and b.loc["P9", "units_removed"] == 1 and b.loc["P9", "units_new"] == 0
    )
    # a new-house permit is never turned into an ADU by the parser (only accessory and addition permits)
    assert b.loc["P12", "building_type_std"] == "SFD"
    assert b.loc["P13", "adu_type"] == "attached"  # the subtype says ADU; the parser gives its kind


def test_dropped_rows_ids_and_privacy():
    b = built()
    assert "P10" not in b.index and "P11" not in b.index
    assert (b["jurisdiction_geoid"] == "4815976").all()
    assert b.loc["P1", "parcel_id"] == "4804112345" and pd.isna(b.loc["P3", "parcel_id"])
    assert b.loc["P1", "issue_year"] == 2021
    assert "555-1234" not in b.reset_index().to_string() and "permit_description" not in b.columns
    assert not (set(cs.SELECT) & cs.PERSONAL)


def test_schema():
    assert_conforms(built().reset_index(), "permits")
