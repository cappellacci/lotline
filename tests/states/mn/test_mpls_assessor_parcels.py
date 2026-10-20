"""Minneapolis assessor parcel tables adapter on synthetic rows (no network, no real data)."""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.mn import mpls_assessor_parcels as ma
from lotline.schemas import assert_conforms
from lotline.validation import holdout


def _rows(roll: ma.Roll, records: list[dict]) -> pd.DataFrame:
    """Canonical-named records → the roll's own field names (plus a personal field that must be dropped)."""
    f = roll.fields
    df = pd.DataFrame([{f[k]: v for k, v in r.items()} for r in records])
    df["OWNERNAME"] = "Testperson"
    return df


HOUSE = dict(
    pin="0302824440033",
    asmt_year=2023,
    zoning="UN2",
    area_sqft=5240,
    prop_type="RESIDENTIAL",
    land_value=73400,
    bldg_value=250000,
    homestead="HOMESTEADED",
    building_use="SINGLE FAMILY HOUSE",
    year_built=1911,
    above_ground_sqft=1400,
    units=1,
)


def test_conforms_registered_and_blind():
    roll = ma.Roll(2023)
    t = ma.to_parcels(_rows(roll, [HOUSE]), roll)
    assert_conforms(t, "parcels")
    assert "mpls_assessor_parcels" in registry.sources_for("MN")
    holdout.assert_no_leak(t, "parcels", "MN")
    row = t.iloc[0]
    assert row.parcel_id == "270530302824440033" and row.jurisdiction_geoid == "2743000"
    assert row.vintage == 2023 and row.vintage_date == pd.Timestamp("2023-01-02")
    assert row.land_use_std == "SF_DETACHED" and row.units == 1 and bool(row.homestead)
    assert row.zoning_raw == "UN2" and row.lot_sqft == 5240
    assert "Testperson" not in t.to_csv()


def test_personal_fields_never_requested():
    for year in ma.YEARS:
        assert not ma.PERSONAL & set(ma.Roll(year).fields.values())


@pytest.mark.parametrize(
    ("year", "pin_field"),
    [(2017, "APN"), (2021, "PIN"), (2025, "TAX_MAP_UFMT"), (2026, "F_No_column_name_")],
)
def test_layouts(year, pin_field):
    assert ma.Roll(year).fields["pin"] == pin_field


def test_2025_layout_pins_units_and_land_use():
    roll = ma.Roll(2025)
    recs = [
        HOUSE
        | dict(pin="p3502924430227", asmt_year=2025, prop_type="RESIDENTIAL 1 UNIT", units=0, homestead="Y"),
        HOUSE
        | dict(
            pin="p3502924430228",
            asmt_year=2025,
            prop_type="APARTMENT",
            building_use="Apartment 4 or 5 Unit",
            units=4,
            homestead="N",
        ),
        HOUSE
        | dict(
            pin="p3502924430229",
            asmt_year=2025,
            prop_type="RESIDENTIAL 1 UNIT",
            building_use="SF House w/ADU",
        ),
        HOUSE | dict(pin="p3502924430230", asmt_year=2025, prop_type="VACANT LAND - COMMERCIAL", units=0),
        HOUSE | dict(pin="bad", asmt_year=2025),
    ]
    t = ma.to_parcels(_rows(roll, recs), roll).set_index("parcel_id")
    assert len(t) == 4  # malformed PIN dropped
    house = t.loc["270533502924430227"]
    assert house.land_use_std == "SF_DETACHED" and pd.isna(house.units)  # 0 units on a house: unknown
    assert t.loc["270533502924430228"].land_use_std == "TRI_QUAD"  # 4-unit apartment by units
    assert t.loc["270533502924430229"].land_use_std == "SF_DETACHED"  # house with ADU
    vacant = t.loc["270533502924430230"]
    assert vacant.land_use_std == "COMMERCIAL" and vacant.units == 0
    assert not bool(t.loc["270533502924430228"].homestead)


@pytest.mark.parametrize(
    ("ptype", "use", "units", "expected"),
    [
        ("CONDOMINIUM", "CONDOMINIUM", 1, "CONDO_UNIT"),
        ("2 UNIT RESIDENTIAL", "DUPLEX", 2, "DUPLEX"),
        ("2 UNIT RESIDENTIAL", "DUPLEX W/ADU", 3, "DUPLEX"),
        ("3 UNIT RESIDENTIAL", "TRIPLEX", 3, "TRI_QUAD"),
        ("APARTMENT", "APARTMENT 6+ UNIT", 40, "MULTIFAMILY_5P"),
        ("RES - ZERO LOT LINE", "RES ZERO LOT LINE", 1, "SF_ATTACHED"),
        ("CONDO - GARAGE/MISC", "CONDOMINIUM GARAGE", 0, "OTHER"),
        ("MIXED USE - COMMERCIAL IND/APARTMENT", "STORE & OFFICE", 10, "MIXED_USE"),
        ("VACANT LAND - RESIDENTIAL", None, 0, "VACANT_RESIDENTIAL"),
        ("SORORITY/FRATERNITY HOUSE", "FRATERNITY OR SORORITY", 0, "INSTITUTIONAL"),
        (None, None, None, "UNKNOWN"),
    ],
)
def test_crosswalk(ptype, use, units, expected):
    roll = ma.Roll(2023)
    rec = HOUSE | dict(prop_type=ptype, building_use=use, units=units)
    assert ma.to_parcels(_rows(roll, [rec]), roll).iloc[0].land_use_std == expected


def test_buildings_collapse_to_one_parcel():
    roll = ma.Roll(2025)
    base = HOUSE | dict(pin="p0102824130108", asmt_year=2025, prop_type="APARTMENT")
    recs = [
        base | dict(building_use="Apartment 6+ Unit", units=30, year_built=1997, above_ground_sqft=20000),
        base | dict(building_use="Apartment 6+ Unit", units=12, year_built=1965, above_ground_sqft=9000),
        base | dict(building_use="Private Garage", units=0, year_built=1990, above_ground_sqft=400),
    ]
    row = ma.to_parcels(_rows(roll, recs), roll).iloc[0]
    assert (row.units, row.year_built, row.bldg_sqft) == (42, 1965, 29400.0)
    assert row.land_use_std == "MULTIFAMILY_5P" and "APARTMENT 6+ UNIT" in row.land_use_raw
