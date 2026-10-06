import pandas as pd
import pytest

from lotline.adapters.national import fhfa
from lotline.schemas import assert_conforms


def _xlsx(path, header, rows):
    """Write a file shaped like FHFA's: title rows, a blank row, notes, then the header and data."""
    title = [
        ["HPI for counties (All-Transactions Index)"],
        [None],
        ["* developmental"],
        ["Last updated: x"],
        ["NSA"],
    ]
    pd.DataFrame(title + [header] + rows).to_excel(path, header=False, index=False)
    return path


@pytest.fixture
def county_file(tmp_path):
    header = [
        "State",
        "County",
        "FIPS code",
        "Year",
        "Annual Change (%)",
        "HPI",
        "HPI with 1990 base",
        "HPI with 2000 base",
    ]
    rows = [
        ["MN", "Hennepin", "27053", "2024", "3.1", "500.5", "300", "210.2"],
        ["MN", "Hennepin", "27053", "2025", ".", None, None, None],  # suppressed year stays missing
        ["NC", "Wake", "37183", "2025", "2.0", "400", "250", "190"],
    ]
    return _xlsx(tmp_path / "hpi_at_county.xlsx", header, rows)


def test_reads_past_title_rows_and_filters_state(county_file):
    df = fhfa.for_state(fhfa.to_canonical(fhfa.read_table(county_file), "county"), "county", "MN", "27")
    assert_conforms(df, "market_geo_year")
    assert df.geo.tolist() == ["county:27053", "county:27053"]
    assert df.hpi.iloc[0] == 500.5 and df.hpi_base2000.iloc[0] == 210.2
    assert df.hpi.isna().iloc[1]  # never interpolated


def test_cbsa_kept_when_it_touches_the_state():
    assert fhfa.cbsa_states("Duluth, MN-WI", "20260") == {"MN", "WI"}
    assert fhfa.cbsa_states("Minnesota (non CBSA areas)", "27") == {"fips:27"}
    df = pd.DataFrame(
        {
            "geo": ["cbsa:20260", "cbsa:00027", "cbsa:39580", "cbsa:00037"],
            "year": [2025] * 4,
            "name": [
                "Duluth, MN-WI",
                "Minnesota (non CBSA areas)",
                "Raleigh-Cary, NC",
                "North Carolina (non CBSA areas)",
            ],
        }
    )
    assert fhfa.for_state(df, "cbsa", "MN", "27").geo.tolist() == ["cbsa:20260", "cbsa:00027"]


def test_zip5_assigned_by_prefix_ranges():
    df = pd.DataFrame(
        {"geo": ["zip5:55415", "zip5:56799", "zip5:73301", "zip5:88510", "zip5:27601"], "year": [2025] * 5}
    )
    tx = fhfa.for_state(df, "zip5", "TX", "48", [(733, 733), (750, 799), (885, 885)])
    assert tx.geo.tolist() == ["zip5:73301", "zip5:88510"]


def test_tract_csv_columns_are_mapped(tmp_path):
    path = tmp_path / "hpi_at_tract.csv"
    path.write_text(
        "tract,state_abbr,year,annual_change,hpi,hpi1990,hpi2000\n"
        "27053000100,MN,2025,2.5,180.0,,150.0\n37183052000,NC,2025,1.0,170.0,,140.0\n"
    )
    df = fhfa.for_state(fhfa.to_canonical(fhfa.read_table(path), "tract"), "tract", "MN", "27")
    assert_conforms(df, "market_geo_year")
    assert df.geo.tolist() == ["tract:27053000100"] and df.hpi_base2000.tolist() == [150.0]


def test_geo_codes_cannot_collide_across_levels():
    df = pd.DataFrame({"geo": ["county:27053", "zip5:27053"], "year": [2025, 2025]})
    assert_conforms(df, "market_geo_year")  # same digits, different levels: both allowed
