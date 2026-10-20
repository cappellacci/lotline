"""Met Council regional parcels adapter on a synthetic fixture (no network, no real data)."""

from pathlib import Path

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.mn import metc_parcels as mp
from lotline.schemas import assert_conforms
from lotline.validation import holdout

FIX = Path(__file__).parent / "fixtures" / "metc_parcels_synthetic.csv"
ST_PAUL, ROSEVILLE, MPLS, EDEN_PRAIRIE = "2758000", "2755852", "2743000", "2718116"
JURIS = pd.DataFrame(
    {
        "geoid": [ST_PAUL, ROSEVILLE, MPLS, EDEN_PRAIRIE, "27053", "2712369916"],
        "name": [
            "St. Paul city",
            "Roseville city",
            "Minneapolis city",
            "Eden Prairie city",
            "Hennepin County Unincorporated Area",
            "White Bear township",
        ],
        "kind": ["place", "place", "place", "place", "county_unincorporated", "township"],
    }
)
POINTS = {-93.10: ST_PAUL, -93.15: ROSEVILLE, -93.27: MPLS, -93.40: "2712399999"}


def locate(lon: pd.Series, lat: pd.Series) -> pd.Series:
    return lon.map(lambda x: POINTS.get(round(x, 2))).astype(object)


def _raw(export_shift_days: int = 0) -> pd.DataFrame:
    df = pd.read_csv(FIX, dtype=str, keep_default_na=False).drop(columns="note").replace({"": None})
    for col in ("OBJECTID", "SALE_DATE", "EXP_DATE", "lon", "lat"):
        df[col] = pd.to_numeric(df[col])
    df["EXP_DATE"] = df["EXP_DATE"] + export_shift_days * 86_400_000
    return df


def _parcels(label: str = "2023", shift: int = 0) -> tuple[pd.DataFrame, pd.Series]:
    table, how = mp.to_parcels(_raw(shift), label, JURIS, locate)
    return table.set_index("parcel_id"), how


@pytest.fixture
def parcels() -> pd.DataFrame:
    return _parcels()[0]


def test_conforms_registered_and_blind(parcels):
    assert_conforms(parcels.reset_index(), "parcels")
    assert "metc_parcels" in registry.sources_for("MN")
    holdout.assert_no_leak(parcels.reset_index(), "parcels", "MN")


def test_personal_fields_never_requested():
    assert not mp.PERSONAL & set(mp.FIELDS)
    assert "*" not in mp.FIELDS


def test_ids_vintage_and_dates(parcels):
    assert len(parcels) == 8  # 10 rows - 1 without a PIN - 1 repeated PIN
    row = parcels.loc["27123012923110001"]
    assert row.vintage == 2023
    assert row.vintage_date == pd.Timestamp("2023-12-26")  # Ramsey's latest export in the roll
    assert parcels.loc["270531234567890123"].vintage_date == pd.Timestamp("2024-01-08")
    assert parcels.loc["270531234567890123"].vintage == 2023  # the service-name year, not the export year


def test_st_paul_kept_from_a_2023_export_hidden_from_a_2024_one(parcels):
    assert (parcels.jurisdiction_geoid == ST_PAUL).sum() == 3
    later, _ = _parcels("2024", shift=370)  # Ramsey exported 2024-12-31
    assert not (later.jurisdiction_geoid == ST_PAUL).any()
    # the church point the locator can't place is still hidden: CTU_NAME says St. Paul
    assert "27123022923110009" not in later.index
    assert "27123012923110003" in later.index  # Roseville stays


def test_jurisdiction_point_then_ctu_name_then_county():
    table, how = _parcels()
    by_id = dict(zip(table.index, how, strict=True))
    assert by_id["27123012923110001"] == "point"
    ep = table.loc["270531234567890125"]
    assert ep.jurisdiction_geoid == EDEN_PRAIRIE and by_id["270531234567890125"] == "ctu_name"
    assert table.loc["27123022923110009"].jurisdiction_geoid == ST_PAUL


def test_land_use_from_class_dwelling_type_and_units(parcels):
    lu = parcels.land_use_std
    assert lu["27123012923110001"] == "SF_DETACHED"
    assert lu["27123012923110002"] == "DUPLEX"  # dwelling type
    assert lu["27123012923110003"] == "TRI_QUAD"  # 1-3 unit class refined by 3 units
    assert lu["27123132923230057"] == "SF_ATTACHED"  # single-unit class, townhome dwelling type
    assert lu["270531234567890123"] == "SF_DETACHED"
    assert lu["270531234567890124"] == "DUPLEX"
    assert lu["270531234567890125"] == "MULTIFAMILY_5P"
    assert lu["27123022923110009"] == "INSTITUTIONAL"
    assert parcels.loc["27123012923110002"].land_use_raw == "1A/1B/4B1 RESIDENTIAL 1-3 UNITS"


def test_attributes(parcels):
    assert pd.isna(parcels.loc["270531234567890123"].units)  # Hennepin: never populated
    assert parcels.loc["27123012923110002"].units == 2
    assert pd.isna(parcels.loc["27123012923110003"].year_built)  # 0 is not a year
    assert parcels.loc["27123132923230057"].lot_sqft == pytest.approx(0.5 * 43_560)  # deed acres
    assert pd.isna(parcels.loc["27123012923110003"].bldg_sqft)
    row = parcels.loc["27123012923110001"]
    assert row.land_value == 50_000 and row.value_basis == "market" and bool(row.homestead)
    assert bool(parcels.loc["27123012923110003"].homestead)  # Partial
    assert row.last_sale_price == 300_000 and row.last_sale_date == pd.Timestamp("2022-05-03")
    assert bool(row.sale_multi_parcel) and bool(parcels.loc["27123012923110002"].sale_multi_parcel)
    assert pd.isna(parcels.loc["27123012923110003"].sale_multi_parcel)  # no sale


def test_month_only_sale_dates_are_not_flagged():
    county = pd.Series(["27053"] * 3)
    date = pd.to_datetime(pd.Series(["2022-05-01", "2022-05-01", "2022-05-02"]))
    price = pd.Series([300_000.0, 300_000.0, 300_000.0])
    multi = mp.multi_parcel_sales(county, date, price)
    assert multi.isna().tolist() == [True, True, False] and not multi.iloc[2]


@pytest.mark.parametrize(
    ("county", "useclass", "dwelling", "units", "expected"),
    [
        ("Anoka", "1a RESIDENTIAL SINGLE UNIT", "01", None, "SF_DETACHED"),
        ("Anoka", "RESIDENTIAL 1 TO 3 UNITS", None, None, "DUPLEX"),
        ("Anoka", "TOWNHOMES-VACANT", None, None, "VACANT_RESIDENTIAL"),
        ("Carver", "Res 1 unit                     ", None, None, "SF_DETACHED"),
        ("Carver", "Apt 4+ units", None, 4, "TRI_QUAD"),
        ("Carver", "Apt 4+ units", None, 40, "MULTIFAMILY_5P"),
        ("Dakota", "Residential-townhouse", "Townhouse", 1, "SF_ATTACHED"),
        ("Dakota", "Residential", "Duplex", 2, "DUPLEX"),
        ("Dakota", "Residential-condominium-storage", None, 0, "OTHER"),
        ("Hennepin", "Condominium (also Market Rate Cooperative)", None, None, "CONDO_UNIT"),
        ("Hennepin", "Vacant Land - Residential", None, None, "VACANT_RESIDENTIAL"),
        ("Ramsey", "1A/1B/4BB RESIDENTIAL SINGLE UNIT", "CONDO", 1, "CONDO_UNIT"),
        ("Ramsey", "4A APARTMENT 4 OR MORE UNITS", "APARTMENTS 4-6 RENTAL UNITS", 4, "TRI_QUAD"),
        ("Ramsey", "3A COMMERCIAL LAND AND BUILDING", "SINGLE FAMILY DWELLING, PLATT", 1, "COMMERCIAL"),
        ("Scott", "201 1A/1B/4BB RESIDENTIAL SINGLE UNIT", None, None, "SF_DETACHED"),
        ("Scott", "209", None, None, "DUPLEX"),
        ("Scott", "105 2A ACTIVELY FARMING", None, None, "AGRICULTURAL"),
        ("Washington", "100", "Single-Family / Owner Occupied", 1, "SF_DETACHED"),
        ("Washington", "155 Res 2-3 Unit Short Term Rental", None, 3, "TRI_QUAD"),
        ("Washington", "962 T E Misc Co D 3", None, None, "OTHER"),
        ("Washington", None, None, None, "UNKNOWN"),
    ],
)
def test_crosswalk_rules(county, useclass, dwelling, units, expected):
    got = mp.land_use(
        pd.Series([county]),
        pd.Series([useclass], dtype="string"),
        pd.Series([dwelling], dtype="string"),
        pd.Series([units], dtype="Int64"),
    )
    assert got.iloc[0] == expected


def test_crosswalks_are_sourced_and_valid():
    from lotline.schemas import LAND_USES

    for path in (mp.USE_CROSSWALK, mp.DWELLING_CROSSWALK):
        df = pd.read_csv(path, dtype=str)
        assert df["land_use_std"].isin(LAND_USES).all()
        assert df["source_url"].str.startswith("https://").all()
        assert df["refine_by_units"].isin(["yes", "no"]).all()


def test_oid_chunks():
    assert mp.chunks(138_760, 185_409) == [(100_000, 200_000)]
    assert mp.chunks(1, 138_759) == [(0, 100_000), (100_000, 200_000)]
