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
    # vacant SF-zoned lot: no house for an ADU, but missing middle counts it (Handbook; D-014)
    ("p8", "VACANT_RESIDENTIAL", None, 6000.0, True, None, None, False, True),
    ("p9", "VACANT_RESIDENTIAL", None, 6000.0, False, None, None, False, False),  # vacant, not SF-only zoned
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
    {
        "state": ["MN"],
        "geoid": ["2743000"],
        "name": ["Minneapolis city"],
        "kind": ["place"],
        "data_tier": [1],
        "county_geoid": ["27053"],
    }
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
    # ADU: p1, p2, p3 eligible, 1 of 3 assumed (33%) -> medium
    # MM: p1, p3 and the vacant SF-zoned lot p8; only p3 rests on an unknown, 1 of 3 (33%) -> medium
    assert out.loc["adu", "eligible_parcels"] == 3 and out.loc["adu", "denominator_quality"] == "medium"
    assert (
        out.loc["missing_middle", "eligible_parcels"] == 3
        and out.loc["missing_middle", "denominator_quality"] == "medium"
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
                    "county_geoid": ["27001"],
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


def test_rest_of_county_is_the_county_minus_its_permit_issuing_places():
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
            "county_geoid": ["37183", "37183"],
        }
    )
    out = eligible.from_acs(acs, juris, themes=("adu",)).set_index("jurisdiction_geoid")
    assert out.loc["3755000", "eligible_parcels"] == 120000
    assert out.loc["37183", "eligible_parcels"] == 180000  # never the whole county total of 300,000


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
                    "county_geoid": ["27001"],
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


def test_load_builds_from_processed_tables(tmp_path, monkeypatch):
    from lotline.adapters.national import geoparts
    from lotline.io import DataStore

    # no network in tests: stand-ins for the 2020 Census share lookups
    monkeypatch.setattr(
        geoparts,
        "county_shares",
        lambda fips, places, store, refresh=False: pd.DataFrame(
            {"place_geoid": places, "county_geoid": ["27053"] * len(places), "share": 1.0}
        ),
    )
    monkeypatch.setattr(
        geoparts,
        "township_shares",
        lambda *a, **k: pd.DataFrame(columns=["place_geoid", "township_geoid", "share"]),
    )

    # the test's parcels have source "t": don't let the real MN config's `parcel_sources` filter them out
    import lotline.config as config

    real = config.load_state
    monkeypatch.setattr(config, "load_state", lambda st: real(st).model_copy(update={"parcel_sources": {}}))

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


def test_allocation_hand_worked_ohio_style_county():
    """County 39001 has 1,000 one-unit homes. Inside it:
    - City A (independent, its own county subdivision): 300 homes, 2/3 of its 2020 housing in 39001 and
      1/3 in county 39003 -> contributes 200 to 39001.
    - Township T (3900110000): 250 homes by ACS, *including* village V (dependent), 60 homes, wholly in T.
      T's net homes = 250 - 60 = 190.
    - Village V: 60 homes, all in 39001.
    Rest of 39001 = 1,000 - 200 (A) - 60 (V) - 190 (T) = 550.
    County 39003 has 120 homes and only A's other third (100) in it: rest = 20.
    """
    acs = pd.DataFrame(
        {
            "geo": ["county:39001", "county:39003", "place:3900100", "cousub:3900110000", "place:3900200"],
            "end_year": [2023] * 5,
            "estimate": [1000.0, 120.0, 300.0, 250.0, 60.0],
        }
    )
    juris = pd.DataFrame(
        {
            "geoid": ["3900100", "3900110000", "3900200", "39001", "39003"],
            "kind": ["place", "township", "place", "county_unincorporated", "county_unincorporated"],
        }
    )
    county_shares = pd.DataFrame(
        {
            "place_geoid": ["3900100", "3900100", "3900200"],
            "county_geoid": ["39001", "39003", "39001"],
            "share": [2 / 3, 1 / 3, 1.0],
        }
    )
    township_shares = pd.DataFrame(
        {"place_geoid": ["3900200"], "township_geoid": ["3900110000"], "share": [1.0]}
    )
    homes = eligible.allocate_homes(acs, juris, county_shares, township_shares).set_index(
        "jurisdiction_geoid"
    )
    assert homes.loc["3900100", "homes"] == pytest.approx(300)  # a place keeps its whole total
    assert homes.loc["3900110000", "homes"] == pytest.approx(190)  # township net of its village
    assert homes.loc["3900200", "homes"] == pytest.approx(60)
    assert homes.loc["39001", "homes"] == pytest.approx(550)
    assert homes.loc["39003", "homes"] == pytest.approx(20)
    # nothing counted twice: jurisdictions add back up to the two county totals
    assert homes["homes"].sum() == pytest.approx(1000 + 120)


def test_negative_remainder_is_clipped_and_flagged():
    acs = pd.DataFrame(
        {"geo": ["county:39001", "place:3900100"], "end_year": [2023, 2023], "estimate": [100.0, 130.0]}
    )  # sampling noise: the place exceeds its county
    juris = pd.DataFrame({"geoid": ["3900100", "39001"], "kind": ["place", "county_unincorporated"]})
    shares = pd.DataFrame({"place_geoid": ["3900100"], "county_geoid": ["39001"], "share": [1.0]})
    empty = pd.DataFrame(columns=["place_geoid", "township_geoid", "share"])
    homes = eligible.allocate_homes(acs, juris, shares, empty).set_index("jurisdiction_geoid")
    assert homes.loc["39001", "homes"] == 0 and bool(homes.loc["39001", "clipped"])


def test_local_only_township_stays_in_its_county_remainder():
    """County 27139 has 1,000 homes. Empire township (local-only, not in BPS) has 100. BPS files Empire's
    permits in the county's unincorporated row, so the remainder keeps them: 1,000, not 900. Empire still
    gets its own 100 for rates built from the local permit source."""
    acs = pd.DataFrame(
        {"geo": ["county:27139", "cousub:2713919036"], "end_year": [2023, 2023], "estimate": [1000.0, 100.0]}
    )
    juris = pd.DataFrame(
        {
            "geoid": ["27139", "2713919036"],
            "kind": ["county_unincorporated", "township"],
            "in_bps": [True, False],
        }
    )
    empty_c = pd.DataFrame(columns=["place_geoid", "county_geoid", "share"])
    empty_t = pd.DataFrame(columns=["place_geoid", "township_geoid", "share"])
    homes = eligible.allocate_homes(acs, juris, empty_c, empty_t).set_index("jurisdiction_geoid")["homes"]
    assert homes["27139"] == 1000 and homes["2713919036"] == 100


@pytest.mark.parametrize("theme", ["adu", "missing_middle"])
def test_lot_size_floor_is_inclusive(theme):
    # with a 5,000 sq ft floor, a lot of exactly 5,000 qualifies and one of 4,999 does not
    params = load_params("eligibility")
    key = f"min_lot_sqft_{theme}"
    params = {**params, key: params[key].model_copy(update={"value": 5000.0})}
    lots = _parcels().iloc[[0, 0]].copy()
    lots["parcel_id"] = ["at", "below"]
    lots["lot_sqft"] = [5000.0, 4999.0]
    assert eligible.classify(lots, theme, params)["eligible"].tolist() == [True, False]


def test_overlapping_parcel_sources_are_never_double_counted():
    a = _parcels()
    b = a.assign(source="city_assessor")
    both = pd.concat([a, b], ignore_index=True)
    with pytest.raises(ValueError, match="parcel_sources"):
        eligible.single_source(both, {})
    kept = eligible.single_source(both, {"2743000": "city_assessor", "*": "t"})
    assert len(kept) == len(a) and set(kept["source"]) == {"city_assessor"}
    assert len(eligible.single_source(a, {})) == len(a)  # one source: unchanged
