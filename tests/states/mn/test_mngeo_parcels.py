"""MnGeo opt-in parcels on synthetic rows: outstate crosswalk, schema mapping, field list and county table."""

import pandas as pd
import pytest

from lotline.adapters.states.mn import metc_parcels as metc
from lotline.adapters.states.mn import mngeo_parcels as mg

CASES = [  # (county, useclass1, expected land_use_std) from labels seen in the 2026-11-01 inventory
    ("St. Louis", "Residential 1 Unit", "SF_DETACHED"),
    ("St. Louis", "Non-Homestead Qualifying Single Res Unit", "SF_DETACHED"),
    ("Stearns", "1a/1b/4bb Residential Single Unit", "SF_DETACHED"),
    ("Isanti", "1A-Residential Homestead", "SF_DETACHED"),
    ("Isanti", "4BB1-Residential Non-Homestead Single Unit", "SF_DETACHED"),
    ("Mille Lacs", "Residential\\single Unit, Rural Vacant Land", "SF_DETACHED"),
    ("Pipestone", "201 - Residential, Single Unit Dwelling", "SF_DETACHED"),
    ("Clay", "100 Res 1 Unit", "SF_DETACHED"),
    ("Crow Wing", "201", "SF_DETACHED"),
    ("Mower", "Ag Dwelling", "SF_DETACHED"),
    ("Stearns", "4b4 Unimproved Residential Land", "VACANT_RESIDENTIAL"),
    ("Olmsted", "4b(4) UNIMPROVED RESIDENTIAL LAND", "VACANT_RESIDENTIAL"),
    ("Clay", "140 Res V Land", "VACANT_RESIDENTIAL"),
    ("Wabasha", "Res 1-3 Unimpr Land", "VACANT_RESIDENTIAL"),
    ("Pipestone", "200 - Residential Vacant Land", "VACANT_RESIDENTIAL"),
    ("Stearns", "1a/1b/4b1 Residential 1-3 Units", "DUPLEX"),
    ("Aitkin", "Residential 1-3 Units Previously SRR", "DUPLEX"),
    ("Pipestone", "204 - 1 To 3 Unit Dwelling", "DUPLEX"),
    ("Olmsted", "4a APARTMENT 4 OR MORE UNITS", "MULTIFAMILY_5P"),
    ("Sherburne", "Apartment (4 Or More Units)", "MULTIFAMILY_5P"),
    ("Cass", "Non-Comm Seasonal Residential Recreational", "OTHER"),
    ("Otter Tail", "4c12 Seasonal Residential Recreation", "OTHER"),
    ("Becker", "Srr", "OTHER"),
    ("Isanti", "3A-Commercial/Industrial/Public Utility", "COMMERCIAL"),
    ("Stearns", "3a Industrial Land And Building", "INDUSTRIAL"),
    ("Stearns", "2a/1b/4bb Agricultural", "AGRICULTURAL"),
    ("Isanti", "2AHGA-Agricultural Homestead - HGA", "AGRICULTURAL"),
    ("Aitkin", "Rural Vacant Land", "AGRICULTURAL"),
    ("St. Louis", "Tax Forfeited County Administered/PILT", "OTHER"),
    ("Lake", "Federal National Forest", "OTHER"),
    ("Pipestone", "958 - Municipal Other", "OTHER"),
    ("Crow Wing", "958", "OTHER"),
    ("Crow Wing", "151", "UNKNOWN"),  # unlabelled bare code
    ("Koochiching", "765", "UNKNOWN"),
    ("Jackson", "20a", "UNKNOWN"),
    ("Lake of the Woods", "0", "UNKNOWN"),
    ("Wilkin", "Res 2", "UNKNOWN"),  # Wilkin's own short codes
    ("Cook", "Short Term Rental", "UNKNOWN"),
]


@pytest.mark.parametrize(("county", "label", "expected"), CASES)
def test_outstate_crosswalk(county, label, expected):
    blank = pd.Series([pd.NA], dtype="string")
    got = metc.land_use(pd.Series([county]), pd.Series([label]), blank, blank, mg.use_rules())
    assert got.iloc[0] == expected


def test_units_refine_a_one_to_three_unit_class():
    county = pd.Series(["Stearns"] * 3)
    label = pd.Series(["1a/1b/4b1 Residential 1-3 Units"] * 3)
    units = pd.Series([1, 3, pd.NA], dtype="Int64")
    got = metc.land_use(county, label, pd.Series([pd.NA] * 3, dtype="string"), units, mg.use_rules())
    assert got.tolist() == ["SF_DETACHED", "TRI_QUAD", "DUPLEX"]


def test_metro_rules_unchanged_by_the_outstate_file():
    # A metro label keeps its metro reading: the outstate rules live in their own file, used only by MnGeo.
    blank = pd.Series([pd.NA], dtype="string")
    got = metc.land_use(pd.Series(["Hennepin"]), pd.Series(["Double Bungalow"]), blank, blank)
    assert got.iloc[0] == "DUPLEX"


def test_personal_fields_never_requested():
    assert not set(mg.FIELDS) & mg.PERSONAL
    assert "*" not in mg.FIELDS


def test_to_metc_schema_renames_and_fills_export_date():
    raw = pd.DataFrame(
        {
            "co_code": ["27145", "27145"],
            "exp_date": [1_700_000_000_000, None],
            "owner_name": ["X", "Y"],
            "useclass1": ["Residential 1 Unit", "Srr"],
            "lon": [-94.1, -94.2],
            "lat": [45.5, 45.6],
        }
    )
    out = mg.to_metc_schema(raw, {"27145": "2026-07-15"})
    assert "OWNER_NAME" not in out and "owner_name" not in out
    assert {"CO_CODE", "EXP_DATE", "USECLASS1", "lon", "lat"} <= set(out.columns)
    assert out["EXP_DATE"].iloc[0] == 1_700_000_000_000
    assert out["EXP_DATE"].iloc[1] == pd.Timestamp("2026-07-15", tz="UTC").timestamp() * 1000


def test_county_table_is_consistent():
    t = mg.counties(status=None)
    assert len(t) == 52 and t["county_fips"].str.fullmatch(r"27\d{3}").all()
    assert not set(t["county_fips"]) & set(metc.METRO_COUNTIES)
    loaded = t[t["status"] == "loaded"]
    assert loaded["ratio"].astype(float).between(0.6, 1.4).all()
    assert (t.loc[t["status"] == "acs_check", "ratio"].astype(float) < 0.6).all()
    assert (t.loc[t["status"] == "no_land_use", "sf_detached_parcels"] == 0).all()
    assert set(mg.counties()["county_fips"]) == set(loaded["county_fips"])


def test_build_drops_parcels_outside_every_jurisdiction():
    raw = pd.DataFrame(
        {
            "objectid": [1, 2],
            "county_pin": ["A1", "A2"],
            "co_code": ["27111", "27111"],
            "co_name": ["Otter Tail", "Otter Tail"],
            "ctu_name": [None, None],
            "useclass1": ["1a/1b/4bb Residential Single Unit"] * 2,
            "exp_date": [None, None],
            "lon": [-96.0, -95.5],
            "lat": [46.3, 46.4],
        }
    )
    for c in mg.FIELDS:
        raw[c] = raw.get(c, pd.Series([None, None]))
    juris = pd.DataFrame(
        {"geoid": ["2724308"], "name": ["Fergus Falls city"], "kind": ["place"], "county_geoid": ["27111"]}
    )

    def locate(lon, lat):  # first point in Fergus Falls, second in a township that issues no permits
        return pd.Series(["2724308", None], index=lon.index, dtype="string")

    out = mg.build(raw, juris, locate, {"27111": "2026-02-25"})
    assert out["jurisdiction_geoid"].tolist() == ["2724308"]
    assert out["land_use_std"].tolist() == ["SF_DETACHED"]
    assert out["vintage_date"].iloc[0] == pd.Timestamp("2026-02-25")


def test_build_leaves_out_places_whose_main_county_is_not_loaded():
    raw = pd.DataFrame({c: [None, None] for c in mg.FIELDS})
    raw = raw.assign(
        county_pin=["A1", "A2"],
        co_code=["27109", "27109"],
        co_name=["Olmsted", "Olmsted"],
        useclass1=["1a/4bb(1) RESIDENTIAL SINGLE UNIT"] * 2,
        lon=[-92.5, -92.6],
        lat=[44.0, 44.2],
    )
    juris = pd.DataFrame(
        {
            "geoid": ["2754880", "2751118"],
            "name": ["Rochester city", "Pine Island city"],
            "kind": ["place", "place"],
            "county_geoid": ["27109", "27049"],  # Pine Island's main county is Goodhue (not loaded)
        }
    )

    def locate(lon, lat):
        return pd.Series(["2754880", "2751118"], index=lon.index, dtype="string")

    out = mg.build(raw, juris, locate, {"27109": "2026-06-23"})
    assert out["jurisdiction_geoid"].tolist() == ["2754880"]
