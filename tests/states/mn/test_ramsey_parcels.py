"""Ramsey County parcel points adapter on a synthetic fixture (no network, no real data)."""

from pathlib import Path

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.mn import ramsey_parcels as rp
from lotline.schemas import assert_conforms
from lotline.validation import holdout

FIX = Path(__file__).parent / "fixtures" / "ramsey_parcels_synthetic.csv"
ST_PAUL, ROSEVILLE, NORTH_ST_PAUL = "2758000", "2755852", "2747221"
JURIS = pd.DataFrame(
    {
        "geoid": [ST_PAUL, ROSEVILLE, NORTH_ST_PAUL],
        "name": ["St. Paul city", "Roseville city", "North St. Paul city"],
        "kind": ["place", "place", "place"],
    }
)
POINTS = {-93.10: ST_PAUL, -93.15: ROSEVILLE}


def locate(lon: pd.Series, lat: pd.Series) -> pd.Series:
    return lon.map(lambda x: POINTS.get(round(x, 2))).astype(object)


@pytest.fixture
def parcels() -> pd.DataFrame:
    raw = pd.read_csv(FIX, dtype=str, keep_default_na=False).drop(columns="note").replace({"": None})
    for col in ("OBJECTID", "LastSaleDate", "PropertyDataJoinDate", "lon", "lat"):
        raw[col] = pd.to_numeric(raw[col])
    return rp.to_parcels(raw, JURIS, locate)[0].set_index("parcel_id")


def test_conforms_registered_and_blind(parcels):
    assert_conforms(parcels.reset_index(), "parcels")
    assert "ramsey_parcels" in registry.sources_for("MN")
    holdout.assert_no_leak(parcels.reset_index(), "parcels", "MN")
    assert ST_PAUL not in set(parcels.jurisdiction_geoid)
    assert "27123012923110001" not in parcels.index  # point in St. Paul, no site city: hidden


def test_st_paul_never_requested():
    assert rp.WHERES == ["SiteCityName <> 'SAINT PAUL'", "SiteCityName IS NULL"]
    assert not rp.PERSONAL & set(rp.FIELDS)


def test_rows_vintage_and_jurisdictions(parcels):
    assert len(parcels) == 4
    assert (parcels.vintage == 2026).all()
    assert (parcels.vintage_date == pd.Timestamp("2026-10-08")).all()
    assert parcels.loc["27123262923110001"].jurisdiction_geoid == NORTH_ST_PAUL  # by site city


def test_attributes(parcels):
    lu = parcels.land_use_std
    assert lu["27123162923220005"] == "SF_DETACHED"
    assert lu["27123162923220006"] == "DUPLEX"
    assert lu["27123162923220007"] == "TRI_QUAD"
    assert lu["27123262923110001"] == "INSTITUTIONAL"
    house = parcels.loc["27123162923220005"]
    assert house.lot_width_ft == 70 and house.units == 1 and house.year_built == 1954
    assert house.lot_sqft == pytest.approx(0.2 * 43_560)
    assert (
        house.last_sale_price == 350_000 and house.sale_multi_parcel is False or not house.sale_multi_parcel
    )
    assert pd.isna(parcels.loc["27123162923220006"].lot_width_ft)
    assert bool(parcels.loc["27123162923220007"].homestead)  # P (partial)
    assert parcels.loc["27123162923220005"].land_use_raw == "510: SINGLE FAMILY DWELLING, PLATTED LOT"


@pytest.mark.parametrize(
    ("desc", "expected"),
    [
        ("TOWNHOME - OUTER UNIT", "SF_ATTACHED"),
        ("TOWNHOME - GARAGE ONLY", "OTHER"),
        ("TOWNHOME - VACANT LOT", "VACANT_RESIDENTIAL"),
        ("CONDO", "CONDO_UNIT"),
        ("CONDOMINIUM OFFICE UNIT", "COMMERCIAL"),
        ("THREE FAMILY DWELLING, PLATTED LOT", "TRI_QUAD"),
        ("APT OR COMPLEX 100+ UNITS", "MULTIFAMILY_5P"),
        ("MIXED RESID/COMMERCIAL", "MIXED_USE"),
        ("MH INVENTORY WITH UNIT", "MOBILE_HOME"),
        ("EXEMPT PROP. OWNED BY MUNICIPALS", "OTHER"),
        ("SMALL STRIP CENTER", "COMMERCIAL"),
        ("IND WAREHOUSE", "INDUSTRIAL"),
        (None, "UNKNOWN"),
    ],
)
def test_crosswalk(desc, expected):
    from lotline.adapters.states.mn import metc_parcels as metc

    got = metc.land_use(
        pd.Series(["Ramsey"]),
        pd.Series([desc], dtype="string"),
        pd.Series([None], dtype="string"),
        pd.Series([None], dtype="Int64"),
        use_rules=metc.load_rules(rp.CROSSWALK),
        dwell_rules=[],
    )
    assert got.iloc[0] == expected
