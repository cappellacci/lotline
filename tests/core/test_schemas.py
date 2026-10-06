"""Contract tests for schemas-v1: every table accepts a minimal valid row and rejects what the docs forbid."""

import pandas as pd
import pandera.errors
import pytest

from lotline import schemas
from lotline.schemas import SCHEMAS_VERSION, TABLES, ContractError, assert_conforms, validate

MINIMAL = {
    "jurisdictions": {
        "state": "MN",
        "geoid": "2743000",
        "name": "Minneapolis city",
        "kind": "place",
        "data_tier": 3,
    },
    "parcels": {
        "state": "MN",
        "parcel_id": "27053-0102924",
        "vintage": 2024,
        "jurisdiction_geoid": "2743000",
        "lot_sqft": 5000.0,
        "land_use_std": "SF_DETACHED",
        "land_use_raw": "R1",
        "source": "t",
    },
    "eligible_parcels": {
        "state": "MN",
        "jurisdiction_geoid": "2743000",
        "year": 2024,
        "theme": "adu",
        "rule_version": "1.0",
        "eligible_parcels": 70000,
        "data_tier": 1,
        "denominator_source": "parcels",
        "denominator_quality": "high",
    },
    "permits": {
        "state": "MN",
        "permit_id": "P1",
        "jurisdiction_geoid": "2743000",
        "issue_year": 2024,
        "issue_date": "2024-03-01",
        "date_precision": "day",
        "building_type_std": "ADU",
        "type_confidence": "high",
        "units_new": 1,
        "units_removed": None,
        "units_confidence": "reported",
        "is_demolition": None,
        "is_conversion": False,
        "source": "t",
    },
    "bps_place_year": {
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
    },
    "market_geo_year": {"geo": "place:2743000", "year": 2024, "median_rent": 1329.0},
    "acs_geo_year": {
        "geo": "place:2743000",
        "end_year": 2023,
        "table_id": "B25077",
        "variable": "B25077_001",
        "label": "Median value (dollars)",
        "estimate": 345600.0,
        "moe": 3908.0,
    },
    "reforms": {
        "reform_id": "MN-2743000-adu-2014",
        "state": "MN",
        "jurisdiction_geoid": "2743000",
        "theme": "adu",
        "component": "ADU allowed by right",
        "status": "in_force",
        "effective_date": "2014-12-01",
        "by_right": True,
        "owner_occ": True,
        "unit_cap": 1,
        "lot_split": False,
        "parking": None,
        "coverage": "citywide, single-family districts",
        "source_url": "https://example.org",
        "coder": "claude",
        "coder_2": "ben",
        "coder_agreement": "agree",
    },
    "fees": {
        "state": "NC",
        "jurisdiction_geoid": "3755000",
        "year": 2024,
        "fee_component": "water_sewer",
        "fee_type": "capacity fee",
        "building_type_std": "SFD",
        "basis": "per_unit",
        "amount_usd": 7400.0,
        "amount_per_unit_usd": 7400.0,
        "dollar_year": 2024,
        "source": "t",
    },
}


def _df(table, **over):
    return pd.DataFrame([MINIMAL[table] | over])


def test_every_table_has_a_minimal_valid_row():
    assert SCHEMAS_VERSION == "1.4"
    assert set(TABLES) == set(MINIMAL)
    for table in TABLES:
        assert_conforms(_df(table), table)


def test_unknown_stays_null_never_zero_or_false():
    out = validate(_df("permits"), "permits")
    assert pd.isna(out["units_removed"].iloc[0]) and pd.isna(out["is_demolition"].iloc[0])


def test_booleans_reject_strings_instead_of_coercing_them_to_true():
    with pytest.raises(pandera.errors.SchemaErrors):
        validate(_df("permits", is_conversion="False"), "permits")


def test_year_only_permits_are_allowed():
    out = validate(_df("permits", issue_date=None, date_precision="year"), "permits")
    assert pd.isna(out["issue_date"].iloc[0]) and out["issue_year"].iloc[0] == 2024


def test_issue_date_must_agree_with_issue_year():
    with pytest.raises(pandera.errors.SchemaErrors):
        validate(_df("permits", issue_year=2023), "permits")


def test_misspelled_column_is_an_error_but_raw_extras_are_dropped():
    out = validate(_df("permits", raw_extra="kept upstream only"), "permits")
    assert "raw_extra" not in out.columns
    with pytest.raises(ContractError, match="final_date"):
        validate(_df("permits", final_dat="2024-05-01"), "permits")


@pytest.mark.parametrize(
    ("table", "bad"),
    [
        ("permits", {"building_type_std": "DUPLEX"}),  # never invent categories
        ("permits", {"units_new": -1}),
        ("permits", {"state": "Minnesota"}),
        ("permits", {"units_confidence": "maybe"}),
        ("parcels", {"land_use_std": "single family"}),  # crosswalks must map to the fixed vocabulary
        ("eligible_parcels", {"denominator_source": "simulated"}),  # the SB 9 lesson (protocol §5.2)
        ("reforms", {"coder_agreement": "probably"}),
        ("reforms", {"theme": "zoning"}),
        ("fees", {"fee_component": "sewer"}),
        ("fees", {"pct_of_value": 150.0}),
        ("market_geo_year", {"geo": "27053"}),  # level prefix required
        ("jurisdictions", {"kind": "city"}),
    ],
)
def test_invalid_rows_fail(table, bad):
    with pytest.raises(pandera.errors.SchemaErrors):
        assert_conforms(_df(table, **bad), table)


@pytest.mark.parametrize(
    ("table", "key_over"),
    [
        ("permits", {}),
        ("parcels", {}),
        ("eligible_parcels", {}),
        ("bps_place_year", {}),
        ("fees", {}),
        ("reforms", {}),
    ],
)
def test_keys_reject_duplicates(table, key_over):
    with pytest.raises(pandera.errors.SchemaErrors):
        assert_conforms(pd.concat([_df(table), _df(table, **key_over)], ignore_index=True), table)


def test_eligible_parcels_keeps_rule_versions_side_by_side():
    two = pd.concat([_df("eligible_parcels"), _df("eligible_parcels", rule_version="1.1")], ignore_index=True)
    assert_conforms(two, "eligible_parcels")


def test_state_laws_and_regions_are_jurisdictions():
    assert {"state", "region"} <= set(schemas.JURISDICTION_KINDS)


def test_unknown_table():
    with pytest.raises(KeyError):
        validate(pd.DataFrame(), "nope")


def test_data_dictionary_is_current():
    from pathlib import Path

    doc = Path(__file__).resolve().parents[2] / "docs" / "schemas.md"
    assert doc.read_text() == schemas.data_dictionary(), "run `uv run lotline schemas --write`"
