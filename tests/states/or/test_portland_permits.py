"""Portland residential permits adapter on synthetic fixtures (no network, no real data).

Checks the module docstring's method: the city's IS_ADU flag, the house + ADU split of one permit, ADU kinds
and conversions from the work class, types from NEWTYPE, the city-boundary filter, D-041 counts through
`calibrate_adu.adu_counts`, and that load() keeps Oregon blind unless V9-OR-TRANSFER is unblinded.
"""

import importlib

import pandas as pd
import pytest

from lotline import registry
from lotline.model import calibrate_adu as ca
from lotline.schemas import assert_conforms
from lotline.validation import holdout

pp = importlib.import_module("lotline.adapters.states.or.portland_permits")

D041 = {"exclude_cobuilt": True, "window": 1, "report_rate": 1.0}
# FOLDERNUMB, ISSUEDATE, NEWCLASS, NEWTYPE, IS_ADU, NEW_UNITS, PROPGISID1, PDXBND
ROWS = [
    (
        "H-1",
        "2015/03/02 00:00:00+00",
        "New Construction",
        "Single Family Dwelling",
        "False",
        "1",
        "1N1E A  100",
        "YES",
    ),
    (
        "A-DET",
        "2015/04/02 00:00:00+00",
        "New Construction",
        "Accessory Dwelling Unit",
        "True",
        "1",
        "1N1E B  200",
        "YES",
    ),
    (
        "A-CONV",
        "2016/05/02 00:00:00+00",
        "Alteration",
        "Single Family Dwelling",
        "True",
        "1",
        "1N1E C  300",
        "YES",
    ),
    (
        "A-ADD",
        "2016/06/02 00:00:00+00",
        "Addition",
        "Single Family Dwelling",
        "True",
        "1",
        "1N1E D  400",
        "YES",
    ),
    (
        "HA-SFD",
        "2016/07/02 00:00:00+00",
        "New Construction",
        "Single Family Dwelling",
        "True",
        "2",
        "1N1E E  500",
        "YES",
    ),
    ("HA-TH", "2016/08/02 00:00:00+00", "New Construction", "Townhouse", "True", "2", "1N1E F  600", "YES"),
    (
        "A-SEP",
        "2016/02/02 00:00:00+00",
        "New Construction",
        "Accessory Dwelling Unit",
        "True",
        "1",
        "1N1E A  100",
        "YES",
    ),
    (
        "A-NEWHOUSE1",
        "2017/02/02 00:00:00+00",
        "New Construction",
        "Single Family Dwelling",
        "True",
        "1",
        "1N1E G  700",
        "YES",
    ),
    (
        "APT",
        "2017/03/02 00:00:00+00",
        "New Construction",
        "Apartments/Condos",
        "False",
        "6",
        "1N1E H  800",
        "YES",
    ),
    ("DUP", "2017/04/02 00:00:00+00", "New Construction", "Duplex", "False", "2", "1N1E I  900", "YES"),
    (
        "OUTSIDE",
        "2016/09/02 00:00:00+00",
        "New Construction",
        "Accessory Dwelling Unit",
        "True",
        "1",
        "1S1W J  100",
        "NO",
    ),
    ("NODATE", None, "New Construction", "Accessory Dwelling Unit", "True", "1", "1N1E K  100", "YES"),
    (
        "LATE",
        "2019/09/02 00:00:00+00",
        "New Construction",
        "Accessory Dwelling Unit",
        "True",
        "1",
        "1N1E L  100",
        "YES",
    ),
]
COLS = ["FOLDERNUMB", "ISSUEDATE", "NEWCLASS", "NEWTYPE", "IS_ADU", "NEW_UNITS", "PROPGISID1", "PDXBND"]


@pytest.fixture
def raw() -> pd.DataFrame:
    df = pd.DataFrame(ROWS, columns=COLS)
    for c in set(pp.KEEP) - set(COLS):
        df[c] = None
    df["INDATE"] = "2015/01/01 00:00:00+00"
    df["SQFT"] = "800"
    return df[pp.KEEP]


@pytest.fixture
def permits(raw) -> pd.DataFrame:
    return pp.build(raw).set_index("permit_id")


def test_conforms_to_the_permits_schema(raw):
    assert_conforms(pp.build(raw), "permits")


def test_boundary_and_issue_date_filters(permits):
    assert "OUTSIDE" not in permits.index and "NODATE" not in permits.index
    assert set(permits["jurisdiction_geoid"]) == {"4159000"}


def test_a_new_house_with_an_adu_on_one_permit_becomes_two_rows(permits):
    assert "HA-SFD" not in permits.index
    house, adu = permits.loc["HA-SFD#house"], permits.loc["HA-SFD#adu"]
    assert house["building_type_std"] == "SFD" and house["units_new"] == 1 and pd.isna(house["adu_type"])
    assert adu["building_type_std"] == "ADU" and adu["units_new"] == 1
    assert house["parcel_id"] == adu["parcel_id"] == "1N1E E 500"  # spaces collapsed
    assert permits.loc["HA-TH#house", "building_type_std"] == "TH"


def test_adu_kind_and_conversion_from_the_work_class(permits):
    assert permits.loc["A-DET", "adu_type"] == "detached"
    assert permits.loc["A-CONV", "adu_type"] == "internal_conversion"
    assert permits.loc["A-ADD", "adu_type"] == "attached"
    assert permits.loc["A-NEWHOUSE1", "adu_type"] == "detached"  # a 1-unit new house-type permit is the ADU
    assert permits.loc["A-NEWHOUSE1", "building_type_std"] == "ADU"
    assert bool(permits.loc["A-CONV", "is_conversion"]) and bool(permits.loc["A-ADD", "is_conversion"])
    assert not bool(permits.loc["H-1", "is_conversion"])


def test_other_types_from_newtype(permits):
    assert permits.loc["APT", "building_type_std"] == "MF5" and permits.loc["APT", "units_new"] == 6
    assert permits.loc["DUP", "building_type_std"] == "U2"
    assert permits.loc["H-1", "building_type_std"] == "SFD"


def test_d041_counts_by_issue_year_without_cobuilt_adus(raw):
    """2015: A-DET (kept). 2016: A-CONV, A-ADD (kept); HA-SFD#adu (same permit as a new house: co-built);
    A-SEP (a new house on its parcel in 2015, within a year: co-built); HA-TH#adu (kept: D-041 recognises
    SFD houses only). 2017: A-NEWHOUSE1 (kept)."""
    p = pp.build(raw)
    got = ca.adu_counts(p, 2010, 2017, D041).set_index("year")["adu_permits"].to_dict()
    assert got == {2015: 1, 2016: 3, 2017: 1}
    flagged = ca.adu_counts(p, 2010, 2017, D041 | {"exclude_cobuilt": False})
    assert flagged.set_index("year")["adu_permits"].to_dict() == {2015: 1, 2016: 5, 2017: 1}
    assert not flagged["survey"].any()  # city records: report rate 1


def test_load_is_blind_by_default_and_unblinds_only_v9(raw, monkeypatch):
    monkeypatch.setattr(pp, "download", lambda store, refresh=False: raw)
    released = pp.load("OR", store=None)  # the real V9 was released on 2026-11-05
    assert released["issue_year"].max() >= 2018
    # the blind V9 as it was before the release
    (v9,) = holdout.holdouts_for("OR")
    unreleased = v9.model_copy(update={"released_on": None, "released_note": None})
    monkeypatch.setattr(holdout, "holdouts_for", lambda state: [unreleased])
    blind = pp.load("OR", store=None)
    assert_conforms(blind, "permits")
    assert blind["issue_year"].max() <= 2017  # V9-OR-TRANSFER hides every Oregon outcome from 2018
    checked = []
    monkeypatch.setattr(holdout, "check_unblind", lambda test_id, repo=None: checked.append(test_id))
    seen = pp.load("OR", store=None, unblind=("V9-OR-TRANSFER",))
    assert checked == ["V9-OR-TRANSFER"] and "LATE" in set(seen["permit_id"])
    with pytest.raises(holdout.UnblindError):
        pp.load("OR", store=None, unblind=("NOT-A-TEST",))


def test_registered_for_oregon():
    assert "portland_permits" in registry.sources_for("OR")
