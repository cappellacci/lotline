"""Wake real estate roll adapter on a synthetic fixture (no network, no real data).

Checks the module docstring: cards collapsed to parcels, land use from Type & Use + Design Style then Land
Class (with the vacant rule), year built, lot size, last sale and qualifying flags, city codes to GEOIDs,
the December 2023 vintage and privacy.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.nc import wake_realestate as wr
from lotline.io import DataStore
from lotline.schemas import LAND_USES, assert_conforms
from lotline.validation import holdout

# REID, card, type&use, design, land class, year, units, heated, bldg value, acres, city, flag, price, date
ROWS = [
    ("0000001", "01", "01", "A", "R", "1995", "1", "2000", "300000", "0.25", "RAL", "A", "400000", "2021-05-03"),  # noqa: E501
    ("0000002", "01", "01", "C", "R", "2005", "1", "1500", "200000", "0.05", "CAR", "C", "250000", "2019-01-10"),  # noqa: E501
    ("0000003", "01", "01", "D", "N", "2010", "1", "900", "150000", "0", None, "E", "1000", "2018-02-02"),
    ("0000004", "01", None, None, "R", "0", "0", "0", "0", "0.5", "RAL", None, "0", None),  # vacant homesite
    ("0000005", "01", "07", "G", "G", "1980", "12", "9000", "900000", "2", "RAL", "A", "0", None),
    ("0000005", "02", "07", "G", "G", "1985", "12", "9000", "900000", "2", "RAL", "A", "0", None),  # 2nd card
    ("0000006", "01", "02", "B", "R", "1950", "2", "1800", "100000", "0.2", "OUT", "T", "90000", "2015-07-07"),  # noqa: E501
    ("0000007", "01", "47", None, "C", "1990", "0", "5000", "800000", "1", "APE", None, "0", None),
    ("0000008", "01", "01", "A", "R", "2001", "1", "1900", "250000", "0.3", "DUR", "A", "300000", "2020-02-02"),  # noqa: E501
]  # fmt: skip
COLS = [
    "REAL_ESTATE_ID", "CARD_NUMBER", "TYPE_AND_USE", "DESIGN_STYLE", "Land_classification", "Year_Built",
    "UNITS", "HEATED_AREA", "Assessed_Building_Value", "Deeded_Acreage", "CITY", "Disq_and_Qual_flag",
    "Total_sale_Price", "Total_Sale_Date",
]  # fmt: skip


@pytest.fixture
def parcels() -> pd.DataFrame:
    raw = pd.DataFrame(ROWS, columns=COLS)
    raw["Assessed_Land_Value"] = "50000"
    raw["Zoning"] = ["R-4", "R-6", "PD", "R-4", "RX-3", "RX-3", "R-30", "CX-3", "RS-10"]
    return wr.build(raw).set_index("parcel_id")


def test_cards_collapse_to_parcels(parcels):
    assert len(parcels) == 7
    apt = parcels.loc["371830000005"]
    assert apt["units"] == 24  # 12 + 12 over two cards
    assert apt["bldg_sqft"] == 18000
    assert apt["year_built"] == 1980  # card 01


def test_land_use_type_design_and_class(parcels):
    lu = parcels["land_use_std"]
    assert lu["371830000001"] == "SF_DETACHED"
    assert lu["371830000002"] == "SF_ATTACHED"  # ONE FAMILY styled TOWNHOUSE
    assert lu["371830000003"] == "CONDO_UNIT"  # ONE FAMILY styled CONDO
    assert lu["371830000004"] == "VACANT_RESIDENTIAL"  # homesite class, no building
    assert lu["371830000005"] == "MULTIFAMILY_5P"
    assert lu["371830000006"] == "DUPLEX"
    assert lu["371830000007"] == "COMMERCIAL"  # no Type & Use row for 47: falls to class C
    assert parcels.loc["371830000002", "land_use_raw"] == "TYPE_AND_USE|DESIGN_STYLE=01|C"


def test_jurisdictions_from_city_codes(parcels):
    j = parcels["jurisdiction_geoid"]
    assert j["371830000001"] == "3755000"  # Raleigh
    assert j["371830000002"] == "3710740"  # Cary
    assert j["371830000003"] == "37183"  # no city code
    assert j["371830000006"] == "37183"  # OUT: outside city limits
    assert j["371830000007"] == "3701520"  # Apex


def test_sales_values_and_vintage(parcels):
    p = parcels
    assert p.loc["371830000001", "last_sale_price"] == 400000
    assert p.loc["371830000001", "sale_qualified"]
    assert not p.loc["371830000001", "sale_multi_parcel"]
    assert p.loc["371830000002", "sale_multi_parcel"]  # flag C: qualified multi-property sale
    assert not p.loc["371830000003", "sale_qualified"]  # E: family transfer
    assert p.loc["371830000004", "sale_qualified"] is pd.NA
    assert pd.isna(p.loc["371830000004", "last_sale_price"])  # price 0 = no sale
    assert p.loc["371830000001", "lot_sqft"] == pytest.approx(0.25 * 43_560)
    assert pd.isna(p.loc["371830000003", "lot_sqft"])
    assert p.loc["371830000004", "year_built"] is pd.NA
    assert (p.vintage_date == pd.Timestamp("2023-12-31")).all() and (p.vintage == 2023).all()
    assert p.loc["371830000001", "zoning_raw"] == "R-4"
    assert_conforms(p.reset_index(), "parcels")


def test_crosswalks_valid():
    assert set(wr.land_use_crosswalk().values()) <= set(LAND_USES)
    assert {f for f, _ in wr.land_use_crosswalk()} == set(wr.LAND_USE_FIELDS)
    geoids = wr.city_geoids()
    assert geoids["RAL"] == "3755000" and "OUT" not in geoids
    assert all(g.startswith("37") and len(g) == 7 for g in geoids.values())


def test_no_personal_columns_read():
    assert not set(wr.USECOLS) & wr.PERSONAL
    assert {"OWNER1", "Mailing_address1", "PROPERTY_DESCRIPTION"} <= wr.PERSONAL


def test_registered():
    assert registry.sources_for("NC")["wake_realestate"].module.TABLE == "parcels"


def test_load_without_registered_roll_explains_register(tmp_path):
    with pytest.raises(FileNotFoundError, match="lotline manifest register .*--source wake_realestate"):
        wr.load("NC", DataStore(tmp_path))


def test_load_ignores_scripted_downloads_and_the_sales_file(tmp_path, monkeypatch):
    store = DataStore(tmp_path / "data")
    sales = tmp_path / wr.SALES_FILE
    sales.write_bytes(b"sales")
    store.register(
        sales, source=wr.SOURCE, url=f"{wr.BASE}/{wr.SALES_FILE}", license=wr.LICENSE, vintage="2026-10-19"
    )
    with pytest.raises(FileNotFoundError, match="No Wake real estate roll"):
        wr.load("NC", store)


def test_load_reads_registered_roll_with_snapshot_holdout(tmp_path, monkeypatch):
    store = DataStore(tmp_path / "data")
    roll = tmp_path / wr.ROLL_FILE
    roll.write_bytes(b"stand-in for the xlsx")
    store.register(
        roll, source=wr.SOURCE, url=f"{wr.BASE}/{wr.ROLL_FILE}", license=wr.LICENSE, vintage="2023-12-31"
    )
    raw = pd.DataFrame(ROWS, columns=COLS)
    raw["Assessed_Land_Value"] = "50000"
    raw["Zoning"] = "R-4"
    seen, calls = [], []
    monkeypatch.setattr(wr, "read", lambda path: seen.append(path.name) or raw)
    real_apply = holdout.apply
    monkeypatch.setattr(
        wr.holdout, "apply", lambda df, st, **kw: calls.append(kw) or real_apply(df, st, **kw)
    )
    out = wr.load("NC", store)
    assert seen == [wr.ROLL_FILE]
    assert calls and calls[0]["snapshot"] is True
    assert len(out) == 7
    assert_conforms(out, "parcels")


def test_cities_mostly_outside_wake_are_left_out(parcels):
    # Durham has 0.1% of its 2020 housing units in Wake: a sliver roll must not become its denominator
    assert "371830000008" not in parcels.index
    assert "3719000" not in set(parcels["jurisdiction_geoid"])
    assert wr.partial_cities() == {"DUR", "ANG", "CLA"}
