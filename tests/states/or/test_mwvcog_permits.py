"""MWVCOG residential permits adapter on synthetic fixtures (no network, no real data).

Checks the module docstring's method: jurisdiction from the permit's city before the issuing office (Marion
County issues Keizer's permits), dropped rows without a place, the COG's ADU type as the flag, units and
demolitions, year-only dates, and that load() keeps Oregon blind before V9's release.
"""

import importlib

import pandas as pd

from lotline import registry
from lotline.schemas import assert_conforms
from lotline.validation import holdout

mw = importlib.import_module("lotline.adapters.states.or.mwvcog_permits")

# FID, PERMIT, Type, UNITS, JURISD, City, YearNo
ROWS = [
    (1, "19-105056-BP", "ADU", 1, "SALEM", "Salem", 2019),
    (2, "21-000001-DW", "NSFD", 1, "SALEM", " ", 2021),  # blank city: the self-permitting office decides
    (3, "123-21-000002-DWL", "NSFD", None, "MC", "Keizer", 2021),  # Marion County permit in Keizer
    (4, "123-21-000003-DWL", "ADU", None, "MC", "MARION COUNTY", 2021),  # unincorporated Marion
    (5, "123-21-000004-DWL", "NSFD", 1, "MC", " ", 2021),  # county permit, no city: dropped
    (6, " ", "NSFD", 1, " ", " ", 2024),  # nothing says where: dropped
    (7, "B20-100", "MULT", 12, "POLK", "POLK COUNTY", 2020),
    (8, "20-000005-DW", "NDUP", None, "SALEM", "Salem", 2020),
    (9, "20-000006-DW", "DEMOSF", None, "SALEM", "Salem", 2020),
    (10, "20-000006-DW", "NSFD", 1, "SALEM", "Salem", 2020),  # same number as the demolition
    (11, "17-000007-DW", "NSFD", 1, "SALEM", "Salem", 2017),
]


def raw() -> pd.DataFrame:
    df = pd.DataFrame(ROWS, columns=["FID", "PERMIT", "Type", "UNITS", "JURISD", "City", "YearNo"])
    for c in set(mw.FIELDS) - set(df.columns):
        df[c] = None
    return df[mw.FIELDS]


def test_conforms_and_never_requests_personal_fields():
    assert_conforms(mw.build(raw()), "permits")
    assert not mw.PERSONAL & set(mw.FIELDS)


def test_jurisdiction_city_first_then_self_permitting_office():
    p = mw.build(raw(), keep=None).set_index("permit_id")
    assert p.loc["19-105056-BP", "jurisdiction_geoid"] == mw.SALEM
    assert p.loc["21-000001-DW", "jurisdiction_geoid"] == mw.SALEM
    assert p.loc["123-21-000002-DWL", "jurisdiction_geoid"] == mw.KEIZER
    assert p.loc["123-21-000003-DWL", "jurisdiction_geoid"] == mw.MARION
    assert p.loc["B20-100", "jurisdiction_geoid"] == mw.POLK
    assert "123-21-000004-DWL" not in p.index and len(p) == 9
    assert mw.build.unassigned == 2


def test_types_units_and_dates():
    p = mw.build(raw(), keep=None)
    adu = p[p["building_type_std"] == "ADU"]
    assert len(adu) == 2 and set(adu["adu_type"]) == {"unknown"}
    by = p.set_index("permit_id")
    assert by.loc["123-21-000003-DWL", "units_new"] == 1
    assert by.loc["123-21-000003-DWL", "units_confidence"] == "derived"
    assert by.loc["B20-100", "building_type_std"] == "MF5" and by.loc["B20-100", "units_new"] == 12
    assert by.loc["20-000005-DW", "building_type_std"] == "U2" and by.loc["20-000005-DW", "units_new"] == 2
    demo = p[p["is_demolition"].fillna(False)].iloc[0]
    assert demo["units_new"] == 0 and demo["units_removed"] == 1
    assert p["permit_id"].is_unique  # the repeated number gets the FID appended
    assert (p["date_precision"] == "year").all() and p["issue_date"].isna().all()


def test_only_salem_by_default():
    p = mw.build(raw())
    assert set(p["jurisdiction_geoid"]) == {mw.SALEM} and len(p) == 6


def test_load_respects_an_unreleased_holdout(monkeypatch):
    monkeypatch.setattr(mw, "download", lambda store, refresh=False: raw())
    assert mw.load("OR", store=None)["issue_year"].max() >= 2018  # V9 released 2026-11-05
    (v9,) = holdout.holdouts_for("OR")
    unreleased = v9.model_copy(update={"released_on": None, "released_note": None})
    monkeypatch.setattr(holdout, "holdouts_for", lambda state: [unreleased])
    assert mw.load("OR", store=None)["issue_year"].max() <= 2017


def test_registered_for_oregon():
    assert "mwvcog_permits" in registry.sources_for("OR")
