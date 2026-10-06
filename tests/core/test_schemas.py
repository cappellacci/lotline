import pandas as pd
import pandera.errors
import pytest

from lotline.schemas import SCHEMAS_VERSION, TABLES, assert_conforms, validate


def _permit(**over):
    row = {
        "state": "MN",
        "permit_id": "P1",
        "jurisdiction_geoid": "2743000",
        "issue_date": "2024-03-01",
        "building_type_std": "ADU",
        "units_new": 1,
        "units_removed": 0,
        "is_demolition": False,
        "is_conversion": False,
        "source": "test",
        "type_confidence": "high",
    }
    return pd.DataFrame([row | over])


def test_all_seven_tables_registered():
    assert SCHEMAS_VERSION == "1.0"
    assert set(TABLES) == {
        "jurisdictions",
        "parcels",
        "permits",
        "bps_place_year",
        "market_geo_year",
        "reforms",
        "fees",
    }


def test_valid_permit_passes_and_optional_columns_may_be_absent():
    out = validate(_permit(raw_extra="kept upstream only"), "permits")
    assert "raw_extra" not in out.columns  # non-canonical columns are dropped
    assert "parcel_id" not in out.columns  # optional column absent is fine
    assert out["issue_date"].dtype.kind == "M"


@pytest.mark.parametrize(
    "bad",
    [
        {"building_type_std": "DUPLEX"},  # not in the enum: never invent categories
        {"units_new": -1},
        {"state": "Minnesota"},
        {"type_confidence": "maybe"},
    ],
)
def test_invalid_permits_fail(bad):
    with pytest.raises(pandera.errors.SchemaErrors):
        assert_conforms(_permit(**bad), "permits")


def test_bps_rejects_duplicate_place_years():
    row = {
        "state": "MN",
        "bps_id": "27497800",
        "geoid": "2743000",
        "county_geoid": "27053",
        "name": "Minneapolis",
        "year": 2020,
        "months_reported": 12,
        "imputed": False,
        **{f"{k}_{s}": 0 for k in ("bldgs", "units") for s in ("1", "2", "3_4", "5p")},
        **{f"units_{s}_rep": 0 for s in ("1", "2", "3_4", "5p")},
    }
    assert_conforms(pd.DataFrame([row]), "bps_place_year")
    with pytest.raises(pandera.errors.SchemaErrors):
        assert_conforms(pd.DataFrame([row, row]), "bps_place_year")


def test_unknown_table():
    with pytest.raises(KeyError):
        validate(pd.DataFrame(), "nope")
