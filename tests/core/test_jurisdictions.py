import pandas as pd

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
