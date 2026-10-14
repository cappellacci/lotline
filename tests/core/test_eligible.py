"""Eligible-parcel rule, checked parcel by parcel against a hand-worked example (BUILD_PLAN §5.3)."""

import pandas as pd
import pytest

from lotline.build import eligible
from lotline.config import load_params
from lotline.schemas import assert_conforms

# id, land use, units, lot sq ft, sf_only_zoned, hoa, floodplain  -> ADU?  MM?  (why)
CASES = [
    ("p1", "SF_DETACHED", 1, 6000.0, True, False, False, True, True),  # plain SF house on SF zoning
    (
        "p2",
        "SF_DETACHED",
        1,
        6000.0,
        False,
        False,
        False,
        True,
        False,
    ),  # SF house, zoning allows more: ADU only
    ("p3", "SF_DETACHED", None, None, None, None, None, True, True),  # all unknown: kept, flagged as assumed
    ("p4", "SF_DETACHED", 2, 6000.0, True, False, False, False, False),  # already 2 units: not single-family
    ("p5", "DUPLEX", 2, 6000.0, True, False, False, False, False),  # not a SF house
    ("p6", "SF_DETACHED", 1, 6000.0, True, True, False, False, False),  # HOA: excluded
    ("p7", "SF_DETACHED", 1, 6000.0, True, False, True, False, False),  # floodplain: excluded
    ("p8", "VACANT_RESIDENTIAL", None, 6000.0, True, None, None, False, False),  # no existing house
]


def _parcels():
    rows = [
        {
            "state": "MN",
            "parcel_id": c[0],
            "vintage": 2024,
            "jurisdiction_geoid": "2743000",
            "lot_sqft": c[3],
            "land_use_std": c[1],
            "land_use_raw": "x",
            "units": c[2],
            "sf_only_zoned": c[4],
            "hoa": c[5],
            "in_floodplain": c[6],
            "source": "t",
        }
        for c in CASES
    ]
    df = pd.DataFrame(rows).astype(
        {"units": "Int64", "sf_only_zoned": "boolean", "hoa": "boolean", "in_floodplain": "boolean"}
    )
    assert_conforms(df, "parcels")
    return df


JURIS = pd.DataFrame(
    {"state": ["MN"], "geoid": ["2743000"], "name": ["Minneapolis city"], "kind": ["place"], "data_tier": [1]}
)


@pytest.mark.parametrize("theme, col", [("adu", 7), ("missing_middle", 8)])
def test_each_parcel_matches_the_hand_worked_answer(theme, col):
    flags = eligible.classify(_parcels(), theme)
    expected = [c[col] for c in CASES]
    assert flags["eligible"].tolist() == expected, theme


def test_unknowns_are_kept_but_flagged():
    flags = eligible.classify(_parcels(), "missing_middle").set_index(_parcels()["parcel_id"])
    assert flags.loc["p3", "eligible"] and flags.loc["p3", "assumed"]
    assert not flags.loc["p1", "assumed"]


def test_counts_and_quality_per_jurisdiction():
    out = eligible.from_parcels(_parcels(), JURIS).set_index("theme")
    assert_conforms(out.reset_index(), "eligible_parcels")
    # ADU: p1, p2, p3 eligible, 1 of 3 assumed (33%) -> medium; MM: p1, p3, 1 of 2 assumed (50%) -> low
    assert out.loc["adu", "eligible_parcels"] == 3 and out.loc["adu", "denominator_quality"] == "medium"
    assert (
        out.loc["missing_middle", "eligible_parcels"] == 2
        and out.loc["missing_middle", "denominator_quality"] == "low"
    )
    assert set(out["rule_version"]) == {eligible.RULE_VERSION} and set(out["data_tier"]) == {1}
    assert set(out["denominator_source"]) == {"parcels"}


def test_lot_floor_comes_from_params():
    params = load_params("eligibility")
    params["min_lot_sqft_adu"] = params["min_lot_sqft_adu"].model_copy(
        update={"value": 7000.0, "high": 7000.0}
    )
    flags = eligible.classify(_parcels(), "adu", params)
    assert not flags["eligible"].any()  # every known lot is 6,000 sq ft; p3's unknown lot no longer passes


def test_exclusion_toggles_off_keep_hoa_parcels():
    params = load_params("eligibility")
    params["exclude_hoa"] = params["exclude_hoa"].model_copy(update={"value": 0.0})
    flags = eligible.classify(_parcels(), "adu", params).set_index(_parcels()["parcel_id"])
    assert flags.loc["p6", "eligible"]


def test_quality_bands():
    p = load_params("eligibility")
    assert eligible.quality(0.0, p) == "high" and eligible.quality(0.05, p) == "high"
    assert eligible.quality(0.06, p) == "medium" and eligible.quality(0.5, p) == "low"


def test_acs_fallback_is_low_quality_and_skips_unknown_places():
    acs = pd.DataFrame(
        {
            "geo": ["place:2743000", "place:2743000", "place:2799999", "cousub:2700102224"],
            "end_year": [2023, 2023, 2023, 2023],
            "table_id": ["B25024"] * 4,
            "variable": ["B25024_002", "B25024_004", "B25024_002", "B25024_002"],
            "label": ["Total:!!1, detached", "Total:!!2", "Total:!!1, detached", "Total:!!1, detached"],
            "estimate": [82307.0, 17048.0, 50.0, 120.0],
            "moe": [1356.0, 937.0, 10.0, 30.0],
        }
    )
    juris = pd.concat(
        [
            JURIS,
            pd.DataFrame(
                {
                    "state": ["MN"],
                    "geoid": ["2700102224"],
                    "name": ["Arna township"],
                    "kind": ["township"],
                    "data_tier": [3],
                }
            ),
        ],
        ignore_index=True,
    )
    out = eligible.from_acs(acs, juris)
    assert_conforms(out, "eligible_parcels")
    assert set(out["jurisdiction_geoid"]) == {"2743000", "2700102224"}  # 2799999 isn't a jurisdiction
    mpls = out[(out.jurisdiction_geoid == "2743000") & (out.theme == "adu")].iloc[0]
    assert mpls.eligible_parcels == 82307 and mpls.denominator_quality == "low"
    assert set(out["denominator_source"]) == {"acs_sf_fallback"}


def test_unknown_theme_is_an_error():
    with pytest.raises(ValueError, match="no eligibility rule"):
        eligible.classify(_parcels(), "tod")


def test_acs_fallback_never_gives_a_county_total_to_an_unincorporated_area():
    acs = pd.DataFrame(
        {
            "geo": ["county:37183", "place:3755000"],
            "end_year": [2023, 2023],
            "table_id": ["B25024"] * 2,
            "variable": ["B25024_002"] * 2,
            "label": ["Total:!!1, detached"] * 2,
            "estimate": [300000.0, 120000.0],
            "moe": [1.0, 1.0],
        }
    )
    juris = pd.DataFrame(
        {
            "state": ["NC", "NC"],
            "geoid": ["37183", "3755000"],
            "name": ["Wake County Unincorporated Area", "Raleigh city"],
            "kind": ["county_unincorporated", "place"],
            "data_tier": [3, 3],
        }
    )
    out = eligible.from_acs(acs, juris, themes=("adu",))
    assert out.jurisdiction_geoid.tolist() == ["3755000"]  # Wake's county total includes Raleigh


def _acs_rows():
    acs = pd.DataFrame(
        {
            "geo": ["place:2743000", "cousub:2700102224"],
            "end_year": [2023, 2023],
            "table_id": ["B25024"] * 2,
            "variable": ["B25024_002"] * 2,
            "label": ["Total:!!1, detached"] * 2,
            "estimate": [82307.0, 120.0],
            "moe": [1.0, 1.0],
        }
    )
    juris = pd.concat(
        [
            JURIS,
            pd.DataFrame(
                {
                    "state": ["MN"],
                    "geoid": ["2700102224"],
                    "name": ["Arna township"],
                    "kind": ["township"],
                    "data_tier": [3],
                }
            ),
        ],
        ignore_index=True,
    )
    return acs, juris


def test_combine_uses_one_source_per_jurisdiction():
    acs, juris = _acs_rows()
    out = eligible.combine(eligible.from_parcels(_parcels(), juris), eligible.from_acs(acs, juris))
    by_place = out.groupby("jurisdiction_geoid")["denominator_source"].unique()
    assert list(by_place["2743000"]) == ["parcels"]  # Minneapolis has parcels: no ACS row kept
    assert list(by_place["2700102224"]) == ["acs_sf_fallback"]  # Arna township doesn't: fallback


def test_load_builds_from_processed_tables(tmp_path):
    from lotline.io import DataStore

    store = DataStore(tmp_path)
    acs, juris = _acs_rows()
    for table, df in (("acs_geo_year", acs), ("jurisdictions", juris)):
        path = store.processed("MN", table, "x")
        path.parent.mkdir(parents=True)
        df.to_parquet(path)
    out = eligible.load("MN", store)
    assert set(out["denominator_source"]) == {"acs_sf_fallback"} and len(out) == 4  # 2 places x 2 themes
    parcels_path = store.processed("MN", "parcels", "x")
    parcels_path.parent.mkdir(parents=True)
    _parcels().to_parquet(parcels_path)
    out = eligible.load("MN", store)
    assert set(out.loc[out.jurisdiction_geoid == "2743000", "denominator_source"]) == {"parcels"}
