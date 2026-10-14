"""County to metro/micro crosswalk (OMB 2023 delineation) and its use in the jurisdictions table."""

import pandas as pd
import pytest

from lotline.adapters.national import cbsa
from lotline.build import jurisdictions
from lotline.schemas import assert_conforms

COLUMNS = [
    "CBSA Code",
    "Metropolitan Division Code",
    "CSA Code",
    "CBSA Title",
    "Metropolitan/Micropolitan Statistical Area",
    "Metropolitan Division Title",
    "CSA Title",
    "County/County Equivalent",
    "State Name",
    "FIPS State Code",
    "FIPS County Code",
    "Central/Outlying County",
]


def _file(tmp_path, rows):
    """Shaped like Census List 1: two title rows, the header, data, then footnotes."""
    title = [["Table with row headers in column A"], ["List 1. CORE BASED STATISTICAL AREAS"]]
    notes = [[None], ["Note: OMB 2020 standards"], ["Source: Census Bureau"]]
    path = tmp_path / "list1.xlsx"
    pd.DataFrame(title + [COLUMNS] + rows + notes).to_excel(path, header=False, index=False)
    return path


ROWS = [
    [
        "33460",
        None,
        "378",
        "Minneapolis-St. Paul-Bloomington, MN-WI",
        "Metropolitan Statistical Area",
        None,
        None,
        "Hennepin County",
        "Minnesota",
        "27",
        "053",
        "Central",
    ],
    [
        "10820",
        None,
        None,
        "Austin, MN",
        "Micropolitan Statistical Area",
        None,
        None,
        "Mower County",
        "Minnesota",
        "27",
        "099",
        "Central",
    ],
]


def test_parse_reads_past_titles_and_footnotes(tmp_path):
    df = cbsa.parse(_file(tmp_path, ROWS)).set_index("county_geoid")
    assert list(df.index) == ["27053", "27099"]
    assert df.loc["27053", "cbsa_code"] == "33460" and df.loc["27053", "cbsa_type"] == "metro"
    assert df.loc["27099", "cbsa_type"] == "micro" and bool(df.loc["27053", "central"])


def test_a_county_in_two_cbsas_is_an_error(tmp_path):
    dup = ROWS + [["99999"] + ROWS[0][1:]]
    with pytest.raises(ValueError, match="more than one CBSA"):
        cbsa.parse(_file(tmp_path, dup))


def test_jurisdictions_get_their_countys_cbsa_and_rural_stays_null():
    bps_table = pd.DataFrame(
        {
            "geoid": ["2743000", "27099", "27173"],
            "name": ["Minneapolis", "Mower County Uninc", "Lac qui Parle Uninc"],
            "bps_id": ["27497800", "27000001", "27000002"],
            "county_geoid": ["27053", "27099", "27073"],
            "year": [2024] * 3,
        }
    )
    census = pd.DataFrame(
        {"geoid": ["2743000"], "level": ["place"], "census_name": ["Minneapolis city"], "pop_2020": [429954]}
    ).astype({"pop_2020": "Int64"})
    cbsas = pd.DataFrame(
        {"county_geoid": ["27053", "27099"], "cbsa_code": ["33460", "10820"], "cbsa_type": ["metro", "micro"]}
    )
    out = jurisdictions.build("MN", bps_table, census, cbsas).set_index("geoid")
    assert_conforms(out.reset_index(), "jurisdictions")
    assert out.loc["2743000", "cbsa_code"] == "33460" and out.loc["27099", "cbsa_type"] == "micro"
    assert pd.isna(out.loc["27173", "cbsa_code"])  # rural county outside any CBSA
