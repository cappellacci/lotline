"""Bend permitting-table adapter on synthetic fixtures (no network, no real data).

Checks the module docstring's method: ADU = building use ADU on a building application (HB2001ADU is not the
flag), one row per application, dropped statuses, types and demolitions, D-041 counts through
`calibrate_adu.adu_counts` (co-built by taxlot), and that load() keeps Oregon blind unless V9-OR-TRANSFER is
unblinded.
"""

import importlib

import pandas as pd
import pytest

from lotline import registry
from lotline.model import calibrate_adu as ca
from lotline.schemas import assert_conforms
from lotline.validation import holdout

bp = importlib.import_module("lotline.adapters.states.or.bend_permits")

D041 = {"exclude_cobuilt": True, "window": 1, "report_rate": 1.0}


def ms(day: str | None) -> float:
    return float("nan") if day is None or pd.isna(day) else pd.Timestamp(day).value // 10**6


# OBJECTID, ApplicationNumber, IssueDate, ApplicationType, ApplicationStatus, BldgUse, Units, HB2001ADU,
# TAXLOT
ROWS = [
    (1, "NC-SFD", "2015-03-02", "NC", "CL", "SFD", 1, None, "T100"),
    (2, "NC-ADU-CB", "2015-09-02", "NC", "CL", "ADU", 1, None, "T100"),  # new house on the lot: co-built
    (3, "NC-ADU", "2016-04-02", "NC", "CL", "ADU", 1, None, "T200"),
    (4, "RE-ADU", "2016-05-02", "RE", "CL", "ADU", None, None, "T300"),  # conversion, no units recorded
    (5, "NC-ADU-N", "2017-02-02", "NC", "CL", "ADU", 1, "N", "T400"),  # 'N' does not unflag an ADU
    (6, "NC-DUP-Y", "2017-03-02", "NC", "CL", "DUP", 2, "Y", "T500"),  # 'Y' does not make a duplex an ADU
    (7, "NC-DUP-Y", "2017-03-02", "NC", "CL", "DUP", 2, "Y", "T501"),  # a repeated application
    (8, "NC-ADU-WD", "2016-06-02", "NC", "WDRN", "ADU", 1, None, "T600"),  # withdrawn
    (9, "NC-UNISSUED", None, "NC", "PI", "ADU", 1, None, "T700"),
    (10, "DE-SFD", "2016-07-02", "DE", "CL", "SFD", 1, None, "T800"),
    (11, "NC-MFD", "2016-08-02", "NC", "CL", "MFD", 12, None, "T900"),
    (12, "NC-TH", "2016-09-02", "NC", "CL", "SFDA", 1, None, "T950"),
    (13, "NC-ADU-LATE", "2020-09-02", "NC", "CL", "ADU", 1, "Y", "T990"),
]
COLS = [
    "OBJECTID",
    "ApplicationNumber",
    "IssueDate",
    "ApplicationType",
    "ApplicationStatus",
    "BldgUse",
    "Units",
    "HB2001ADU",
    "TAXLOT",
]


@pytest.fixture
def raw() -> pd.DataFrame:
    df = pd.DataFrame(ROWS, columns=COLS)
    df["IssueDate"] = df["IssueDate"].map(ms)
    df["ApplicationDate"] = ms("2014-01-01")
    df["DateFinaled"] = df["IssueDate"] + 86_400_000 * 200
    for c in set(bp.FIELDS) - set(df.columns):
        df[c] = None
    return df[bp.FIELDS]


@pytest.fixture
def permits(raw) -> pd.DataFrame:
    return bp.build(raw).set_index("permit_id")


def test_conforms_and_never_requests_personal_fields(raw):
    assert_conforms(bp.build(raw), "permits")
    assert not bp.PERSONAL & set(bp.FIELDS)


def test_one_row_per_application_and_dropped_statuses(permits):
    assert permits.index.is_unique
    assert permits.loc["NC-DUP-Y", "parcel_id"] == "T500"  # first taxlot in sort order
    assert "NC-ADU-WD" not in permits.index and "NC-UNISSUED" not in permits.index


def test_adu_is_the_building_use_not_hb2001adu(permits):
    adu = permits[permits["building_type_std"] == "ADU"].index
    assert set(adu) == {"NC-ADU-CB", "NC-ADU", "RE-ADU", "NC-ADU-N", "NC-ADU-LATE"}
    assert permits.loc["NC-DUP-Y", "building_type_std"] == "U2"
    assert permits.loc["NC-DUP-Y", "reform_flag_raw"].startswith("HB2001ADU=Y")
    assert permits.loc["RE-ADU", "adu_type"] == "internal_conversion" and bool(
        permits.loc["RE-ADU", "is_conversion"]
    )
    assert permits.loc["RE-ADU", "units_new"] == 1 and permits.loc["RE-ADU", "units_confidence"] == "inferred"
    assert permits.loc["NC-ADU", "adu_type"] == "unknown"


def test_types_demolitions_and_dates(permits):
    assert permits.loc["NC-MFD", "building_type_std"] == "MF5" and permits.loc["NC-MFD", "units_new"] == 12
    assert permits.loc["NC-TH", "building_type_std"] == "TH"
    demo = permits.loc["DE-SFD"]
    assert bool(demo["is_demolition"]) and demo["units_new"] == 0 and demo["units_removed"] == 1
    assert permits.loc["NC-SFD", "issue_date"] == pd.Timestamp("2015-03-02")
    assert permits.loc["NC-SFD", "final_date_type"] == "final_inspection"


def test_d041_counts_by_issue_year_without_cobuilt_adus(raw):
    """2015: NC-ADU-CB shares taxlot T100 with a new house the same year (co-built). 2016: NC-ADU, RE-ADU.
    2017: NC-ADU-N."""
    p = bp.build(raw)
    got = ca.adu_counts(p, 2010, 2017, D041).set_index("year")["adu_permits"].to_dict()
    assert got == {2015: 0, 2016: 2, 2017: 1}
    flagged = ca.adu_counts(p, 2010, 2017, D041 | {"exclude_cobuilt": False})
    assert flagged.set_index("year")["adu_permits"].to_dict() == {2015: 1, 2016: 2, 2017: 1}


def test_load_is_blind_by_default_and_unblinds_only_v9(raw, monkeypatch):
    monkeypatch.setattr(bp, "download", lambda store, refresh=False: raw)
    released = bp.load("OR", store=None)  # the real V9 was released on 2026-11-05
    assert released["issue_year"].max() >= 2018
    # the blind V9 as it was before the release
    (v9,) = holdout.holdouts_for("OR")
    unreleased = v9.model_copy(update={"released_on": None, "released_note": None})
    monkeypatch.setattr(holdout, "holdouts_for", lambda state: [unreleased])
    blind = bp.load("OR", store=None)
    assert_conforms(blind, "permits")
    assert blind["issue_year"].max() <= 2017
    checked = []
    monkeypatch.setattr(holdout, "check_unblind", lambda test_id, repo=None: checked.append(test_id))
    seen = bp.load("OR", store=None, unblind=("V9-OR-TRANSFER",))
    assert checked == ["V9-OR-TRANSFER"] and "NC-ADU-LATE" in set(seen["permit_id"])


def test_registered_for_oregon():
    assert "bend_permits" in registry.sources_for("OR")
