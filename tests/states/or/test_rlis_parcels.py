"""Metro RLIS tax-lot adapter on a synthetic fixture (no network, no real data).

Checks the module docstring's method by hand-worked rows: dropped non-tax-lot features and repeated TLIDs,
DOR property class → land use (zero padding, first rule wins, unknown codes), jurisdiction from JURIS_CITY
with the county-remainder fallback, lot size (assessor acres, else polygon area), year built, sale dates, and
what `build/eligible.py` then counts for Portland.
"""

import importlib

import pandas as pd
import pytest

from lotline import registry
from lotline.build import eligible
from lotline.build.jurisdictions import tiers_from_parcels
from lotline.schemas import assert_conforms
from lotline.validation import holdout

rp = importlib.import_module("lotline.adapters.states.or.rlis_parcels")

PORTLAND, BEAVERTON, LAKE_OSWEGO = "4159000", "4105350", "4140550"
JURIS = pd.DataFrame(
    {
        "geoid": [PORTLAND, BEAVERTON, LAKE_OSWEGO, "41051", "41067", "41005"],
        "name": [
            "Portland city",
            "Beaverton city",
            "Lake Oswego city",
            "Multnomah County Part 2 Unincorporated Area",
            "Washington County Unincorporated Area",
            "Clackamas County Unincorporated Area",
        ],
        "kind": ["place"] * 3 + ["county_unincorporated"] * 3,
        "data_tier": [3] * 6,
    }
)
ROLL = pd.Timestamp("2026-11-04")

COLS = [
    "FID", "TLID", "PRIMACCNUM", "COUNTY", "JURIS_CITY", "PROP_CODE", "A_T_ACRES", "AREA", "YEARBUILT",
    "BLDGSQFT", "LANDVAL", "BLDGVAL", "SALEDATE", "SALEPRICE",
]  # fmt: skip
# fmt: off
ROWS = [
    # Portland house: 0.11 ac × 43,560 = 4,791.6 sq ft; sale month only → 1st of the month
    (1, "1S1E04AC  -04700", "R246943", "M", "PORTLAND", "101", 0.11, 5000.07, 1910, 1400, 325000, 24250,
     "199506", 127900),
    # Portland house, no assessor acres → polygon area; year built 0 → unknown; no sale
    (2, "1N1E03AC  -00500", "R314341", "M", "PORTLAND", "101", 0, 3200.0, 0, 0, 80070, 0, " ", 0),
    # Portland vacant residential lot
    (3, "1N1E03AC  -00600", "R314342", "M", "PORTLAND", "100", 0.10, 4356.0, 0, 0, 90000, 0, " ", 0),
    # Portland condominium and apartments
    (4, "1N1E03AC  -00700", "R314343", "M", "PORTLAND", "102", 0, 900.0, 2005, 850, 50000, 200000,
     "20190315", 400000),
    (5, "1N1E03AC  -00800", "R314344", "M", "PORTLAND", "701", 0.5, 21780.0, 1970, 30000, 1e6, 4e6, " ", 0),
    # Portland exempt (city park)
    (6, "1N1E03AC  -00900", "R314345", "M", "PORTLAND", "940", 2.0, 87120.0, 0, 0, 0, 0, " ", 0),
    # unincorporated Washington County, unclassified (000)
    (7, "1N1W01AA00100", "R900001", "W", "UNINCORPORATED", "000", 0.1, 4356.0, 0, 0, 0, 0, " ", 0),
    # right of way: no assessor account → not a tax lot, dropped
    (8, "1N1E03AC  -ROADS", " ", "M", "PORTLAND", " ", 0, 50000.0, 0, 0, 0, 0, " ", 0),
    # the same TLID again (a second polygon piece): the lowest FID (1) is kept
    (9, "1S1E04AC  -04700", "R246943", "M", "PORTLAND", "101", 0.11, 120.0, 1910, 1400, 325000, 24250,
     "199506", 127900),
    # Beaverton (Washington County) house
    (10, "1S116AB00100", "R100001", "W", "BEAVERTON", "101", 0.15, 6534.0, 1995, 1800, 200000, 300000,
     "202104", 550000),
    # Gladstone is not a permit issuer in the table → Clackamas remainder; Metro's '81' → '081' (recreation)
    (11, "22E17BD00802", "00497787", "C", "GLADSTONE", "101", 0.4, 17475.38, 1966, 1960, 300551, 240380,
     "199307", 127900),
    (12, "22E17BD00900", "00497788", "C", "UNINCORPORATED", "81", 1.0, 43560.0, 1960, 600, 50000, 40000,
     " ", 0),
    # unincorporated Clackamas acreage homesite (tract land, improved) → a house
    (13, "33E10A00100", "00500001", "C", "UNINCORPORATED", "401", 5.0, 217800.0, 1978, 2200, 400000,
     300000, " ", 0),
    # Lake Oswego: a code no rule lists (119) → UNKNOWN; multi-family vacant land (700) → OTHER
    (14, "21E03BA00100", "00600001", "C", "LAKE OSWEGO", "119", 0.2, 8712.0, 0, 0, 0, 0, " ", 0),
    (15, "21E03BA00200", "00600002", "C", "LAKE OSWEGO", "700", 1.0, 43560.0, 0, 0, 0, 0, " ", 0),
]
# fmt: on


def raw() -> pd.DataFrame:
    df = pd.DataFrame(ROWS, columns=COLS)
    return df.assign(lon=-122.6, lat=45.5, SITEADDR="123 MAIN ST")


@pytest.fixture
def placed() -> tuple[pd.DataFrame, pd.Series]:
    table, how = rp.to_parcels(raw(), ROLL, JURIS)
    return table, how


@pytest.fixture
def parcels(placed) -> pd.DataFrame:
    return placed[0].set_index("parcel_id")


def test_conforms_registered_and_blind(parcels):
    assert_conforms(parcels.reset_index(), "parcels")
    assert "rlis_parcels" in registry.sources_for("OR")
    assert "rlis_parcels" not in registry.sources_for("MN")
    holdout.assert_no_leak(parcels.reset_index(), "parcels", "OR")


def test_personal_fields_never_requested_or_kept(parcels):
    assert not rp.PERSONAL & set(rp.FIELDS)
    assert "*" not in rp.FIELDS
    assert "SITEADDR" not in parcels.columns


def test_rows_ids_and_vintage(parcels):
    assert len(parcels) == 13  # 15 features - 1 right of way - 1 repeated TLID
    assert parcels.index.is_unique
    row = parcels.loc["410511S1E04AC04700"]  # county GEOID + TLID, letters and digits only
    assert row.lot_sqft == pytest.approx(0.11 * 43_560)  # FID 1, not FID 9's 120 sq ft
    assert (parcels.vintage == 2026).all()
    assert (parcels.vintage_date == ROLL).all()
    assert set(parcels.county_geoid) == {"41051", "41067", "41005"}


def test_land_use_from_the_dor_class(parcels):
    use = parcels.land_use_std
    assert use["410511S1E04AC04700"] == "SF_DETACHED"  # 101
    assert use["410511N1E03AC00600"] == "VACANT_RESIDENTIAL"  # 100
    assert use["410511N1E03AC00700"] == "CONDO_UNIT"  # 102
    assert use["410511N1E03AC00800"] == "MULTIFAMILY_5P"  # 701
    assert use["410511N1E03AC00900"] == "INSTITUTIONAL"  # 940
    assert use["410671N1W01AA00100"] == "UNKNOWN"  # 000
    assert use["4100522E17BD00900"] == "OTHER"  # '81' padded to 081
    assert parcels.land_use_raw["4100522E17BD00900"] == "081"
    assert use["4100533E10A00100"] == "SF_DETACHED"  # 401 tract land, improved
    assert use["4100521E03BA00100"] == "UNKNOWN"  # 119: no rule lists it
    assert use["4100521E03BA00200"] == "OTHER"  # 700: multi-family land, vacant


@pytest.mark.parametrize(
    "code, expected",
    [
        ("101", "SF_DETACHED"),
        ("191", "SF_DETACHED"),
        ("190", "VACANT_RESIDENTIAL"),
        ("122", "CONDO_UNIT"),
        ("707", "MOBILE_HOME"),  # manufactured structure park, before the 7x1 rule
        ("721", "MULTIFAMILY_5P"),
        ("201", "COMMERCIAL"),
        ("21", "COMMERCIAL"),  # 021 misc commercial zone
        ("331", "INDUSTRIAL"),
        ("551", "AGRICULTURAL"),
        ("641", "AGRICULTURAL"),
        ("801", "OTHER"),
        ("999", "INSTITUTIONAL"),
        ("106", "OTHER"),
        ("3", "OTHER"),  # 003 misc operating assessed
        ("", "UNKNOWN"),
        ("ABC", "UNKNOWN"),
    ],
)
def test_crosswalk_rules(code, expected):
    assert rp.land_use(pd.Series([code])).iloc[0] == expected


def test_jurisdiction_from_juris_city_else_county_remainder(placed):
    table, how = placed
    geoid = table.set_index("parcel_id").jurisdiction_geoid
    assert geoid["410511S1E04AC04700"] == PORTLAND
    assert geoid["410671S116AB00100"] == BEAVERTON
    assert geoid["4100521E03BA00100"] == LAKE_OSWEGO
    assert geoid["4100522E17BD00802"] == "41005"  # GLADSTONE: not in the table
    assert geoid["4100533E10A00100"] == "41005"  # UNINCORPORATED
    assert geoid["410671N1W01AA00100"] == "41067"
    assert how.value_counts().to_dict() == {"juris_city": 9, "county_remainder": 4}


def test_lot_size_year_built_values_and_sales(parcels):
    p = parcels
    assert p.lot_sqft["410511N1E03AC00500"] == pytest.approx(3200.0)  # A_T_ACRES 0 → polygon AREA
    assert pd.isna(p.year_built["410511N1E03AC00500"])  # YEARBUILT 0
    assert p.year_built["410511S1E04AC04700"] == 1910
    assert pd.isna(p.bldg_sqft["410511N1E03AC00500"])  # BLDGSQFT 0
    assert p.land_value["410511S1E04AC04700"] == 325000
    assert (p.value_basis == "market").all()
    assert p.last_sale_date["410511S1E04AC04700"] == pd.Timestamp("1995-06-01")  # YYYYMM
    assert p.last_sale_price["410511S1E04AC04700"] == 127900
    assert p.last_sale_date["410511N1E03AC00700"] == pd.Timestamp("2019-03-15")  # YYYYMMDD
    assert pd.isna(p.last_sale_date["410511N1E03AC00500"])  # blank date, price 0
    assert pd.isna(p.last_sale_price["410511N1E03AC00500"])


def test_city_names_ending_in_city():
    """Census names carry the suffix ('Oregon City city'); RLIS writes the bare name ('OREGON CITY'). Only the
    Census suffix is stripped, so 'OREGON CITY' must not shrink to 'oregon'."""
    juris = pd.DataFrame(
        {
            "geoid": ["4155200", "4139150", "41005"],
            "name": ["Oregon City city", "King City city", "Clackamas County Unincorporated Area"],
            "kind": ["place", "place", "county_unincorporated"],
        }
    )
    geoid, how = rp.resolve(
        pd.Series(["OREGON CITY", "KING CITY", "OREGON", "Oregon City"]), pd.Series(["41005"] * 4), juris
    )
    assert geoid.tolist() == ["4155200", "4139150", "41005", "4155200"]
    assert how.tolist() == ["juris_city", "juris_city", "county_remainder", "juris_city"]


def test_sale_dates_bounds():
    got = rp.sale_dates(pd.Series(["189912", "202713", "202712", "2026", None]), latest_year=2027)
    assert pd.isna(got[0]) and pd.isna(got[1]) and pd.isna(got[3]) and pd.isna(got[4])
    assert got[2] == pd.Timestamp("2027-12-01")


def test_eligible_counts_for_portland(parcels):
    """By hand: Portland keeps 6 lots (FIDs 1-6; FID 8 is a right of way, FID 9 repeats FID 1), all with a
    known land use. Houses: FIDs 1, 2 → 2 ADU-eligible lots; missing middle adds the vacant lot (FID 3) → 3.
    RLIS has no unit counts or zoning, so every eligible lot rests on an assumption and the quality is 'low'.
    Clackamas remainder: the Gladstone house and the 401 acreage homesite → 2. Lake Oswego (1 of 2 lots
    UNKNOWN) and the Washington remainder (its one lot UNKNOWN) fall below the 90% land-use bar (D-016), so
    they get no parcel count and stay on the ACS fallback."""
    rows = eligible.from_parcels(parcels.reset_index(), JURIS)
    pdx = rows[rows.jurisdiction_geoid == PORTLAND].set_index("theme")
    assert pdx.loc["adu", "eligible_parcels"] == 2
    assert pdx.loc["missing_middle", "eligible_parcels"] == 3
    assert (pdx.denominator_source == "parcels").all()
    assert (pdx.denominator_quality == "low").all()
    assert (pdx.year == 2026).all()
    clack = rows[rows.jurisdiction_geoid == "41005"].set_index("theme")
    assert clack.loc["adu", "eligible_parcels"] == 2
    assert not rows.jurisdiction_geoid.isin([LAKE_OSWEGO, "41067"]).any()


def test_tiers_from_the_roll(parcels):
    """Tier 1 needs land use on 90% of lots and year built on 80% of built ones (D-016)."""
    tiers = tiers_from_parcels(parcels.reset_index())
    assert tiers[BEAVERTON] == 1
    assert tiers[LAKE_OSWEGO] == 3  # half its lots UNKNOWN


def test_load_rejects_other_states():
    with pytest.raises(ValueError, match="Oregon Metro"):
        rp.load("MN", store=None)


def test_chunks_cover_the_range():
    assert rp.chunks(5, 250_000) == [(0, 100_000), (100_000, 200_000), (200_000, 300_000)]
