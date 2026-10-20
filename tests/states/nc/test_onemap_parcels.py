"""NC OneMap parcels adapter on a synthetic fixture (no network, no real data).

Checks the module docstring's method: county crosswalks read in each county's field order, the
vacant-when-unimproved rule, year built, lot size, transform-date vintages, parcel IDs and de-duplication,
jurisdiction placement (place kept even outside the BPS universe), the Charlotte snapshot holdout and privacy.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.nc import onemap_parcels as om
from lotline.schemas import LAND_USES, assert_conforms


def _ms(day: str) -> int:
    return int(pd.Timestamp(day).value // 1_000_000)


# cntyfips, parno, parusecode, parusedesc, parusecd2, gisacres, improvval, structyear
ROWS = [
    ("183", "0001", "RHS", "R", "01", 0.25, 300000, 1995),  # Wake house
    ("183", "0002", "RHS", "R", "", 0.30, 0, 0),  # Wake homesite class, no building → vacant
    ("183", "0003", "RHS", "R", "02", 0.20, 250000, 1960),  # Wake duplex
    ("183", "0004", "APT", "G", "07", 5.0, 9000000, 2001),  # garden apartments
    ("183", "0005", "VAC", "V", "", 1.0, 0, 0),  # vacant class
    ("183", "0005", "VAC", "V", "", 1.0, 0, 0),  # repeated parno: one row kept
    ("183", None, "RHS", "R", "01", 0.2, 1, 1990),  # no parno: dropped
    ("063", "D1", "RS-10", "RES/ 1-FAMILY", "", 0.2, 200000, 1950),  # Durham: zoning in parusecode
    ("063", "D2", "RU-5(2)", "RES/ 2-FAMILY", "", 0.15, 150000, 3000),  # implausible year → unknown
    ("063", "D3", "RS-20", "VAC RES/ LOT-SML TRA", "", 0.5, 0, 0),
    ("063", "D4", "RS-20", "SOMETHING NEW", "", 0.5, 0, 0),  # unmapped → UNKNOWN
    ("119", "M1", "", "SINGLE FAMILY RESIDENTIAL", "01", 0.2, 350000, 2005),  # Mecklenburg town house
    ("119", "M2", "", "SINGLE FAMILY RESIDENTIAL", "", 0.2, 0, 0),  # SF land use, no building → vacant
    ("119", "M3", "", "MULTI FAMILY DUPLEX/TRIPLEX", "62", 0.2, 200000, 1940),
    ("119", "M4", "", "SINGLE FAMILY RESIDENTIAL", "01", 0.2, 300000, 1980),  # in Charlotte: held out
]
DATES = pd.DataFrame(
    {
        "cntyname": ["WAKE", "DURHAM", "MECKLENBURG"],
        "cntyfips": ["183", "063", "119"],
        "transfdate": [_ms("2026-05-17T04:00"), _ms("2026-05-13T04:00"), _ms("2026-01-07T05:00")],
    }
)


@pytest.fixture
def raw() -> pd.DataFrame:
    cols = [
        "cntyfips",
        "parno",
        "parusecode",
        "parusedesc",
        "parusecd2",
        "gisacres",
        "improvval",
        "structyear",
    ]
    df = pd.DataFrame(ROWS, columns=cols)
    df["objectid"] = range(1, len(df) + 1)
    df["parusedsc2"] = ""
    df["landval"] = 50000.0
    df["saledate"] = _ms("2020-03-01")
    df["transfdate"] = None
    df["lon"] = -78.6
    df["lat"] = 35.8
    return df


@pytest.fixture
def parcels(raw) -> pd.DataFrame:
    return om.build(raw, om.vintage_dates(DATES)).set_index("parcel_id")


def test_ids_and_dedup(parcels):
    assert len(parcels) == 13  # repeated parno kept once, row without parno dropped
    assert "371830005" in parcels.index
    assert set(parcels.county_geoid) == {"37183", "37063", "37119"}


def test_land_use_by_county_field_order(parcels):
    lu = parcels["land_use_std"]
    assert lu["371830001"] == "SF_DETACHED"
    assert lu["371830003"] == "DUPLEX"
    assert lu["371830004"] == "MULTIFAMILY_5P"
    assert lu["371830005"] == "VACANT_RESIDENTIAL"
    assert lu["37063D1"] == "SF_DETACHED"
    assert lu["37063D2"] == "DUPLEX"
    assert lu["37063D3"] == "VACANT_RESIDENTIAL"
    assert lu["37063D4"] == "UNKNOWN"
    assert lu["37119M1"] == "SF_DETACHED"
    assert lu["37119M3"] == "DUPLEX"  # DUPLEX-TRIPLEX code
    assert parcels.loc["371830001", "land_use_raw"] == "parusecd2=01"
    assert parcels.loc["37063D4", "land_use_raw"] == "SOMETHING NEW"


def test_vacant_when_unimproved_only_from_the_land_use_field(parcels):
    # the land use says single-family but there is no building: vacant (Wake class R, Mecklenburg land use)
    assert parcels.loc["371830002", "land_use_std"] == "VACANT_RESIDENTIAL"
    assert parcels.loc["37119M2", "land_use_std"] == "VACANT_RESIDENTIAL"
    assert parcels.loc["371830002", "land_use_raw"] == "parusedesc=R"


def test_zoning_only_where_the_county_sends_it(parcels):
    assert parcels.loc["37063D1", "zoning_raw"] == "RS-10"
    assert parcels.loc["37063D2", "zoning_raw"] == "RU-5(2)"
    assert parcels.loc["371830001", "zoning_raw"] is pd.NA


def test_year_built_lot_size_and_vintage(parcels):
    assert parcels.loc["371830001", "year_built"] == 1995
    assert parcels.loc["371830002", "year_built"] is pd.NA  # 0 = unknown
    assert parcels.loc["37063D2", "year_built"] is pd.NA  # after the roll date
    assert parcels.loc["371830001", "lot_sqft"] == pytest.approx(0.25 * 43_560)
    assert (parcels.loc[parcels.county_geoid == "37119", "vintage_date"] == pd.Timestamp("2026-01-07")).all()
    assert (parcels.loc[parcels.county_geoid == "37183", "vintage_date"] == pd.Timestamp("2026-05-17")).all()
    assert (parcels.vintage == 2026).all()


def test_place_kept_outside_bps_and_charlotte_held_out(parcels):
    from lotline.validation import holdout

    df = parcels.reset_index()
    place = pd.Series([pd.NA] * len(df), index=df.index, dtype=object)
    place[df.parcel_id == "371830001"] = "3755000"  # Raleigh (in BPS)
    place[df.parcel_id == "37119M4"] = "3712000"  # Charlotte (BPS files it under the county)
    place[df.parcel_id == "37119M1"] = "3733120"  # Huntersville (also not a BPS place)
    geoid, how = om.resolve_jurisdictions(df.county_geoid, place, {"3755000", "37183", "37063", "37119"})
    df = df.assign(jurisdiction_geoid=geoid)
    assert how[df.parcel_id == "371830001"].item() == "place"
    assert geoid[df.parcel_id == "37119M4"].item() == "3712000"
    assert how[df.parcel_id == "37119M4"].item() == "place_not_in_bps"
    assert geoid[df.parcel_id == "37119M2"].item() == "37119"  # unincorporated → county row
    kept = holdout.apply(
        df, "NC", geoid_col="jurisdiction_geoid", date_col="vintage_date", year_col="vintage", snapshot=True
    )
    kept_ids = set(kept.parcel_id)
    assert "37119M4" not in kept_ids  # Charlotte: the 2026 roll is after 2023-06-01
    # D-012: BPS files Charlotte under 37119, so the county rows are held out over the same window
    assert not {"37119M2", "37119M3"} & kept_ids
    assert "37119M1" in kept_ids  # a Mecklenburg town (Huntersville) stays
    out = kept.drop(columns=["lon", "lat"]).assign(lon=-78.6, lat=35.8)
    assert_conforms(out, "parcels")


def test_crosswalks_are_valid_and_cover_configured_fields():
    for county in om.counties().values():
        xw = om.crosswalk(county.crosswalk)
        assert xw, county.name
        assert set(xw.values()) <= set(LAND_USES), county.name
        assert {f for f, _ in xw} <= set(county.fields), county.name
        assert set(county.fields) <= set(om.OUT_FIELDS)
        if county.zoning_field:
            assert county.zoning_field in om.OUT_FIELDS


def test_bad_flag_is_rejected(tmp_path):
    bad = tmp_path / "c.csv"
    bad.write_text(
        "county_fips,county,crosswalk,land_use_fields,vacant_when_unimproved,zoning_field,notes,source_url\n"
        "37183,Wake,x.csv,parusecd2,yes,,,\n"
    )
    with pytest.raises(ValueError, match="vacant_when_unimproved"):
        om.counties(bad)


def test_no_personal_fields_requested():
    assert not set(om.OUT_FIELDS) & om.PERSONAL
    assert {"ownname", "mailadd", "siteadd", "legdecfull"} <= om.PERSONAL


def test_registered():
    assert registry.sources_for("NC")["onemap_parcels"].module.TABLE == "parcels"


def test_vacant_rule_for_single_land_use_field_and_structyear_signal():
    xw = {("parusedesc", "RES"): "SF_DETACHED", ("parusedesc", "COM"): "COMMERCIAL"}
    df = pd.DataFrame(
        {
            "parusedesc": ["RES", "RES", "COM"],
            "improvval": [0, 0, 0],  # Union: no building values at all
            "structyear": [1998, 0, 0],
        }
    )
    std, raw = om.map_land_use(
        df, xw, ("parusedesc",), vacant_when_unimproved=True, building_fields=0, bldg_col="structyear"
    )
    assert list(std) == ["SF_DETACHED", "VACANT_RESIDENTIAL", "COMMERCIAL"]
    assert raw[1] == "parusedesc=RES"
    # with building_fields=1 the only field counts as a building type: never vacant
    std1, _ = om.map_land_use(df, xw, ("parusedesc",), vacant_when_unimproved=True, bldg_col="structyear")
    assert list(std1) == ["SF_DETACHED", "SF_DETACHED", "COMMERCIAL"]


def test_ten_largest_counties_configured():
    cfg = om.counties()
    ten = {"37183", "37119", "37081", "37067", "37051", "37063", "37021", "37179", "37071", "37025"}
    assert set(cfg) == ten
    assert cfg["37179"].built_signal == "structyear" and cfg["37063"].building_fields == 0
    assert cfg["37183"].building_fields == 1
    for c in cfg.values():
        xw = om.crosswalk(c.crosswalk)
        assert set(xw.values()) <= set(LAND_USES), c.name
        assert {f for f, _ in xw} <= set(c.fields), c.name


def test_county_tiers_follow_the_brief():
    tiers = pd.read_csv(om.COUNTIES_CSV, dtype=str).set_index("county")["data_tier"]
    assert set(tiers) <= {"1", "2", "3"}
    assert tiers["Wake"] == "1" and tiers["Durham"] == "2" and tiers["Cabarrus"] == "3"


def test_places_mostly_outside_loaded_counties_are_left_out(monkeypatch):
    shares = pd.DataFrame(
        {
            "place_geoid": ["3711800", "3711800", "3710740", "3710740", "3719000"],
            "county_geoid": ["37135", "37063", "37183", "37037", "37063"],
            "share": [0.934, 0.066, 0.972, 0.028, 1.0],
        }
    )
    loaded = {"37063", "37183"}
    assert om.undercovered(shares, loaded) == {"3711800"}  # Chapel Hill: 6.6% in Durham County
    from lotline.adapters.national import geoparts

    monkeypatch.setattr(geoparts, "county_shares", lambda fips, places, store, refresh=False: shares)
    df = pd.DataFrame(
        {
            "jurisdiction_geoid": ["3711800", "3710740", "3719000", "37063"],
            "county_geoid": ["37063", "37183", "37063", "37063"],
        }
    )
    kept = om.drop_undercovered(df, "NC", store=None)
    assert list(kept["jurisdiction_geoid"]) == ["3710740", "3719000", "37063"]
