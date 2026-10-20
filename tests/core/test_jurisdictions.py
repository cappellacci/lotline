import pandas as pd
import pytest

from lotline.adapters.national import decennial
from lotline.build import jurisdictions
from lotline.schemas import assert_conforms


def _bps(rows):
    cols = ["geoid", "name", "bps_id", "county_geoid", "year"]
    return pd.DataFrame(rows, columns=cols)


def test_decennial_parse_builds_geoids_and_short_names():
    payload = [
        ["NAME", "P1_001N", "state", "county", "county subdivision"],
        ["Ball Bluff township, Aitkin County, Minnesota", "272", "27", "001", "03358"],
    ]
    df = decennial.parse(payload, "cousub")
    assert df.geoid.tolist() == ["2700103358"] and df.census_name.tolist() == ["Ball Bluff township"]
    assert df.pop_2020.tolist() == [272]


def test_build_combines_bps_universe_with_census_names_and_population():
    bps_table = _bps(
        [
            ["2743000", "Minneapolis", "27497800", "27053", 2019],
            ["2743000", "Minneapolis", "27497800", "27053", 2024],
            ["2700102224", "Arna township", "27140500", "27001", 2024],
            ["27003", "Anoka County Unincorporated Area", "27999901", "27003", 2024],
            ["2799999", "Old Town", "27888800", "27053", 1999],  # gone before 2020
            [None, "Unmatched", "27777700", "27053", 1995],  # no GEOID: not a jurisdiction
        ]
    )
    census = pd.DataFrame(
        {
            "geoid": ["2743000", "2700102224", "27003"],
            "level": ["place", "cousub", "county"],
            "census_name": ["Minneapolis city", "Arna township", "Anoka County"],
            "pop_2020": [429954, 120, 363887],
        }
    ).astype({"pop_2020": "Int64"})
    df = jurisdictions.build("MN", bps_table, census).set_index("geoid")
    assert_conforms(df.reset_index(), "jurisdictions")
    assert len(df) == 4
    assert df.loc["2743000", "kind"] == "place" and df.loc["2743000", "pop_2020"] == 429954
    assert df.loc["2743000", "name"] == "Minneapolis city"
    assert df.loc["2700102224", "kind"] == "township"
    assert df.loc["27003", "kind"] == "county_unincorporated"
    assert pd.isna(df.loc["27003", "pop_2020"])  # never the whole county's population
    assert df.loc["2799999", "name"] == "Old Town" and pd.isna(df.loc["2799999", "pop_2020"])
    assert (df.data_tier == 3).all()


def test_local_only_jurisdictions_are_added_from_the_census_and_flagged():
    bps_table = _bps([["2743000", "Minneapolis", "27497800", "27053", 2024]])
    census = pd.DataFrame(
        {
            "geoid": ["2743000", "2713919036"],
            "level": ["place", "cousub"],
            "census_name": ["Minneapolis city", "Empire township"],
            "pop_2020": [429954, 3200],
        }
    ).astype({"pop_2020": "Int64"})
    with pytest.warns(UserWarning, match="unknown to the 2020 Census"):
        df = jurisdictions.build("MN", bps_table, census, local_geoids=["2713919036", "2799999999"])
    df = df.set_index("geoid")
    assert_conforms(df.reset_index(), "jurisdictions")
    assert bool(df.loc["2743000", "in_bps"]) and not bool(df.loc["2713919036", "in_bps"])
    assert df.loc["2713919036", "name"] == "Empire township" and df.loc["2713919036", "kind"] == "township"
    assert df.loc["2713919036", "county_geoid"] == "27139"
    assert "2799999999" not in df.index  # never invented


def test_holdout_places_and_parcel_places_are_always_local_jurisdictions(tmp_path):
    from lotline.build.jurisdictions import local_geoids
    from lotline.io import DataStore

    store = DataStore(tmp_path)
    out = store.processed("NC", "parcels", "onemap_parcels")
    out.parent.mkdir(parents=True)
    pd.DataFrame({"jurisdiction_geoid": ["3743480", "37119", None]}).to_parquet(out)  # Matthews, county
    local = local_geoids("NC", store)
    assert {"3712000", "3743480", "37119"} <= local  # Charlotte even with no Charlotte rows anywhere


def test_tiers_follow_the_loaded_parcels():
    from lotline.build.jurisdictions import tiers_from_parcels

    def roll(geoid, n, land_use, year_share):
        known = int(n * year_share)
        return pd.DataFrame(
            {
                "jurisdiction_geoid": [geoid] * n,
                "vintage": [2026] * n,
                "land_use_std": [land_use] * n,
                "year_built": pd.array([1990] * known + [None] * (n - known), dtype="Int64"),
            }
        )

    parcels = pd.concat(
        [
            roll("4805000", 10, "SF_DETACHED", 1.0),  # land use and year built: tier 1
            roll("3918000", 10, "SF_DETACHED", 0.0),  # land use only: tier 2
            roll("3915000", 10, "UNKNOWN", 1.0),  # no usable land use: tier 3
            roll("3901000", 10, "SF_DETACHED", 0.7),  # year built for 70% only (< 80%): tier 2
        ]
    )
    old = roll("4805000", 10, "UNKNOWN", 0.0).assign(vintage=2020)  # an older roll doesn't count
    tiers = tiers_from_parcels(pd.concat([parcels, old]))
    assert tiers == {"4805000": 1, "3918000": 2, "3915000": 3, "3901000": 2}
    assert tiers_from_parcels(None) == {}


def test_parcel_tiers_and_place_counties_reach_the_right_columns():
    # load() passes both maps; a place-to-county map must never be read as tiers (bug fixed 2026-10-20)
    bps_table = _bps([["2743000", "Minneapolis", "27497800", "27053", 2024]])
    census = pd.DataFrame(
        {"geoid": ["2743000"], "level": ["place"], "census_name": ["Minneapolis city"], "pop_2020": [429954]}
    ).astype({"pop_2020": "Int64"})
    df = jurisdictions.build(
        "MN", bps_table, census, place_counties={"2743000": "27053"}, parcel_tiers={"2743000": 1}
    ).set_index("geoid")
    assert df.loc["2743000", "data_tier"] == 1
