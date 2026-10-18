"""Austin permits adapter on a synthetic fixture (no network, no real data).

Checks the module docstring's rules: building type from the Census code in permit_class (R- or C- prefix,
R-102 = ADU), the housing_units plausibility rule, demolitions, the 436 conversion and plain-class
description fallbacks (inferred), the HOME two-/three-unit flag, status and jurisdiction filters, privacy,
and that load() runs the holdout filter.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.tx import austin_permits as ap
from lotline.schemas import assert_conforms
from lotline.validation import holdout

FULL, LTD, ETJ = "AUSTIN FULL PURPOSE", "AUSTIN LTD", "AUSTIN 2 MILE ETJ"

# permit, class, work class, issued, housing_units, status, jurisdiction, description
ROWS = [
    ("SFD-1", "R- 101 Single Family Houses", "New", "2023-03-02", "1", "Final", FULL, "New SFR"),
    ("SFD-0", "C- 101 Single Family Houses", "New", "2019-05-06", "0", "Final", LTD, None),
    (
        "ADU-1",
        "R- 102 Secondary Apartment",
        "New",
        "2022-01-10",
        "1",
        "Final",
        FULL,
        "New detached ADU behind existing house",
    ),
    ("DUP-SIDE", "R- 103 Two Family Bldgs", "New", "2025-02-01", "1", "Active", FULL, "Duplex unit A"),
    ("DUP-BAD", "R- 103 Two Family Bldgs", "New", "2013-07-01", "7", "Final", FULL, None),
    ("TQ-OK", "C- 104 Three & Four Family Bldgs", "New", "2016-08-08", "4", "Final", FULL, None),
    (
        "MF-TEXT",
        "C- 105 Five or More Family Bldgs",
        "New",
        "2021-02-11",
        None,
        "Final",
        FULL,
        "New 48 unit apartment building",
    ),
    ("MF-NULL", "C- 105 Five or More Family Bldgs", "Shell", "2021-02-12", "0", "Expired", FULL, None),
    ("MIXED", "C- 106 Mixed Use", "New", "2020-04-04", "200", "Final", FULL, None),
    (
        "ADDN",
        "R- 436 Addn to increase housing units",
        "Addition",
        "2018-01-01",
        "3",
        "Final",
        FULL,
        "Convert single family to duplex",
    ),
    ("PLAIN", "Residential", "New", "1999-06-01", None, "Final", FULL, "New single family residence"),
    (
        "HOME-3",
        "R- 101 Single Family Houses",
        "New",
        "2025-03-03",
        "1",
        "Active",
        FULL,
        "ePlan: Residential Expedited Review - New THREE UNIT RES.\nBldg 2 New construction of a 2-Story SFR",
    ),
    ("DEMO-SF", "R- 645 Demolition One Family Homes", "Demolition", "2014-12-30", None, "Final", FULL, None),
    (
        "DEMO-MF",
        "C- 648 Demolition 5 or More Family Bldgs",
        "Demolition",
        "2015-03-03",
        "24",
        "Final",
        FULL,
        None,
    ),
    (
        "DEMO-OTH",
        "R- 649 Demolition All Other Bldgs Res",
        "Demolition",
        "2015-04-04",
        "1",
        "Final",
        FULL,
        None,
    ),
    ("VOID-1", "R- 101 Single Family Houses", "New", "2020-01-02", "1", "VOID", FULL, None),
    ("WDRAWN", "R- 101 Single Family Houses", "New", "2020-01-03", "1", "Withdrawn", FULL, None),
    (
        "CANC",
        "R- 101 Single Family Houses",
        "New",
        "2020-01-04",
        "1",
        "Cancelled - Contractor Required",
        FULL,
        None,
    ),
    ("ETJ-1", "R- 101 Single Family Houses", "New", "2020-01-05", "1", "Final", ETJ, None),
    ("NOJUR", "R- 101 Single Family Houses", "New", "2020-01-06", "1", "Final", None, None),
    ("OLD", "R- 101 Single Family Houses", "New", "1955-01-06", "1", "Final", FULL, None),
    ("NOT-ISSUED", "R- 101 Single Family Houses", "New", None, "1", "Pending Permit", FULL, None),
]


@pytest.fixture
def raw() -> pd.DataFrame:
    cols = ["permit_number", "permit_class", "work_class", "issue_date", "housing_units", "status_current",
            "jurisdiction", "description"]  # fmt: skip
    df = pd.DataFrame(ROWS, columns=cols)
    df["permittype"] = "BP"
    df["permit_class_mapped"] = "Residential"
    df["condominium"] = "No"
    df["tcad_id"] = "0123456789"
    df["applieddate"] = "2012-01-01T00:00:00.000"
    df["calendar_year_issued"] = df["issue_date"].str[:4]
    df["completed_date"] = ["2026-01-15T00:00:00.000" if i % 2 else None for i in range(len(df))]
    df["total_new_add_sqft"] = "2000"
    df["total_job_valuation"] = "250000"
    df["project_id"] = [str(i) for i in range(len(df))]
    return df[ap.SELECT].astype("string")


@pytest.fixture
def permits(raw) -> pd.DataFrame:
    return ap.build(raw).set_index("permit_id")


def test_conforms_and_filters(permits):
    assert_conforms(permits.reset_index(), "permits")
    dropped = {"VOID-1", "WDRAWN", "CANC", "ETJ-1", "NOJUR", "OLD", "NOT-ISSUED"}
    assert not dropped & set(permits.index)
    assert "DUP-SIDE" in permits.index  # Active (issued) permits stay
    assert "SFD-0" in permits.index  # limited-purpose areas are Austin
    assert (permits.jurisdiction_geoid == ap.AUSTIN_GEOID).all()


@pytest.mark.parametrize(
    "label, code",
    [("R- 101 Single Family Houses", "101"), ("C- 105 Five or More Family Bldgs", "105"),
     ("R-2001 Relocation Residential", "2001"), ("Residential", None), (None, None)],
)  # fmt: skip
def test_class_code(label, code):
    assert ap.class_code(label) == code


def test_types_from_census_code(permits):
    t = permits.building_type_std
    assert t["SFD-1"] == t["SFD-0"] == t["HOME-3"] == "SFD"  # C- prefix is still a house
    assert t["ADU-1"] == "ADU" and permits.loc["ADU-1", "adu_type"] == "detached"
    assert t["DUP-SIDE"] == "U2" and t["TQ-OK"] == "U3_4" and t["MF-TEXT"] == "MF5"
    assert t["MIXED"] == "OTHER" and permits.loc["MIXED", "units_new"] == 200


def test_units_reported_when_plausible_else_derived(permits):
    p = permits
    assert (p.loc["SFD-1", "units_new"], p.loc["SFD-1", "units_confidence"]) == (1, "reported")
    assert (p.loc["SFD-0", "units_new"], p.loc["SFD-0", "units_confidence"]) == (1, "derived")
    assert (p.loc["DUP-SIDE", "units_new"], p.loc["DUP-SIDE", "units_confidence"]) == (1, "reported")
    assert (p.loc["DUP-BAD", "units_new"], p.loc["DUP-BAD", "units_confidence"]) == (2, "derived")
    assert (p.loc["TQ-OK", "units_new"], p.loc["TQ-OK", "units_confidence"]) == (4, "reported")


def test_description_fills_gaps_only_as_inferred(permits):
    p = permits
    assert (p.loc["MF-TEXT", "units_new"], p.loc["MF-TEXT", "units_confidence"]) == (48, "inferred")
    assert pd.isna(p.loc["MF-NULL", "units_new"]) and p.loc["MF-NULL", "units_confidence"] == "unknown"
    addn = p.loc["ADDN"]  # 436: housing_units (3) is the building's count, the text says one unit added
    assert addn.is_conversion and (addn.units_new, addn.units_confidence) == (1, "inferred")
    plain = p.loc["PLAIN"]
    assert (plain.building_type_std, plain.type_confidence) == ("SFD", "inferred")
    assert (plain.units_new, plain.units_confidence) == (1, "inferred")


def test_demolitions(permits):
    sf, mf, oth = permits.loc["DEMO-SF"], permits.loc["DEMO-MF"], permits.loc["DEMO-OTH"]
    assert sf.is_demolition and sf.units_new == 0
    assert (sf.units_removed, sf.units_confidence) == (1, "derived")
    assert (mf.building_type_std, mf.units_removed, mf.units_confidence) == ("MF5", 24, "reported")
    assert oth.is_demolition and pd.isna(oth.units_removed) and oth.units_confidence == "unknown"
    assert not permits.loc["SFD-1", "is_demolition"]


def test_home_use_flag(permits):
    assert permits.loc["HOME-3", "reform_flag_raw"] == "THREE UNIT RES"
    assert permits.reform_flag_raw.notna().sum() == 1


def test_dates_parcel_and_raw_class(permits):
    p = permits.loc["SFD-0"]  # odd row: completed
    assert p.final_date == pd.Timestamp("2026-01-15") and p.final_date_type == "completion"
    assert pd.isna(permits.loc["SFD-1", "final_date"]) and pd.isna(permits.loc["SFD-1", "final_date_type"])
    assert p.parcel_id == "484530123456789"
    assert permits.loc["MF-NULL", "permit_class_raw"] == "C- 105 Five or More Family Bldgs|Shell"
    assert (permits.issue_year == permits.issue_date.dt.year).all()


def test_personal_fields_never_requested():
    assert not ap.PERSONAL & set(ap.SELECT)
    assert not [f for f in ap.SELECT if f.startswith(ap.PERSONAL_PREFIXES)]


def test_load_applies_holdout_filter(raw, monkeypatch):
    monkeypatch.setattr(ap, "download", lambda store, refresh=False: raw)
    calls = []
    real_apply = holdout.apply

    def spy(df, state, **kw):
        calls.append((state, kw))
        return real_apply(df, state, **kw)

    monkeypatch.setattr(ap.holdout, "apply", spy)
    out = ap.load("TX", store=None)
    assert calls and calls[0][1]["geoid_col"] == "jurisdiction_geoid"
    assert_conforms(out, "permits")
    assert "description" not in out.columns
    holdout.assert_no_leak(out, "permits", "TX")


def test_registered_as_tx_source():
    assert "austin_permits" in registry.sources_for("TX")
