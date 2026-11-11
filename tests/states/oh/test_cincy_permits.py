"""Cincinnati permits adapter on synthetic fixtures (no network, no real data).

Checks the methodology in the module docstring: type from the use group and unit count, unknown units stay
null, wrecking permits, the combo-description ADU/townhouse fill, dropped statuses, CO dates, privacy and
that load() runs the holdout filter.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.oh import cincy_permits as cp
from lotline.schemas import assert_conforms
from lotline.validation import holdout

FM = '"1-2-3 FM"'
# permitnum, permittypemapped, workclass, proposeduse, units, issueddate, coissueddate, status
ROWS = [
    ("P-SFD", "Building", "RNEW", FM, "1", "2023-03-02", "2024-01-05", "Permit Finaled"),
    ("P-TH", "Building", "RNEW", FM, "1", "2025-05-02", None, "Permit Issued"),
    ("P-DUP", "Building", "RNEW", FM, "2", "2024-08-15", None, "Permit Issued"),
    ("P-QUAD", "Building", "RNEW", '"R-5"', "4", "2024-09-01", None, "Permit Issued"),
    ("P-APT", "Building", "CNEW", '"R-2"', "120", "2019-11-21", None, "Permit Finaled"),
    ("P-ZERO", "Building", "RNEW", FM, "0", "2020-02-02", None, "Permit Finaled"),
    ("P-HOTEL", "Building", "CNEW", '"R-1"', "150", "2019-05-05", None, "Permit Finaled"),
    ("P-WRECK", "Wrecking", "RDMO", FM, "2", "2015-06-06", None, "Permit Finaled"),
    ("P-WRECK-C", "Wrecking", "CDMO", '"B"', "0", "2016-07-07", None, "Permit Finaled"),
    ("P-GARAGE-ADU", "Building", "RACC", '"U"', "0", "2026-03-03", None, "Permit Issued"),
    ("P-WITHDRAWN", "Building", "RNEW", FM, "1", "2021-01-01", None, "Permit Withdrawn"),
    ("P-UNISSUED", "Building", "RNEW", FM, "1", None, None, "In Review"),
]
COMBO = [
    ("P-TH", "New Residential", "NEW 3 STORY TOWNHOUSE"),
    ("P-GARAGE-ADU", "Res Garage/Shed>=800", "NEW GARAGE W/ ADU ABOVE."),
    ("P-GARAGE-ADU", "Res Garage/Shed>=800", "NEW GARAGE W/ ADU ABOVE."),
]


@pytest.fixture
def raw() -> pd.DataFrame:
    cols = [
        "permitnum",
        "permittypemapped",
        "workclass",
        "proposeduse",
        "units",
        "issueddate",
        "coissueddate",
        "statuscurrentmapped",
    ]
    df = pd.DataFrame(ROWS, columns=cols)
    df["applieddate"] = "2019-01-01"
    df["permitclass"] = "RCO"
    df["totalsqft"] = None
    df["estprojectcostdec"] = "100000"
    df["pin"] = '"000100010001"'
    return df


@pytest.fixture
def combo() -> pd.DataFrame:
    return pd.DataFrame(COMBO, columns=["number_key", "sub_type_desc", "desc_of_work"])


@pytest.fixture
def permits(raw, combo) -> pd.DataFrame:
    return cp.build(raw, combo).set_index("permit_id")


def test_conforms_and_drops_withdrawn_and_unissued(permits):
    assert_conforms(permits.reset_index(), "permits")
    assert not {"P-WITHDRAWN", "P-UNISSUED"} & set(permits.index)
    assert (permits.jurisdiction_geoid == cp.CINCINNATI_GEOID).all()
    assert permits.loc["P-SFD", "parcel_id"] == "000100010001"


def test_type_from_use_group_and_units(permits):
    t = permits["building_type_std"]
    assert (t["P-SFD"], permits.loc["P-SFD", "type_confidence"]) == ("SFD", "inferred")
    assert (t["P-DUP"], permits.loc["P-DUP", "units_new"]) == ("U2", 2)
    assert (t["P-QUAD"], permits.loc["P-QUAD", "units_new"]) == ("U3_4", 4)
    assert (t["P-APT"], permits.loc["P-APT", "units_new"]) == ("MF5", 120)
    assert t["P-HOTEL"] == "OTHER" and pd.isna(permits.loc["P-HOTEL", "units_new"])


def test_zero_units_are_unknown_not_zero(permits):
    row = permits.loc["P-ZERO"]
    assert pd.isna(row.units_new) and row.units_confidence == "unknown" and row.building_type_std == "UNKNOWN"


def test_wrecking(permits):
    w, c = permits.loc["P-WRECK"], permits.loc["P-WRECK-C"]
    assert w.is_demolition and w.units_new == 0 and w.units_removed == 2 and w.building_type_std == "U2"
    assert c.is_demolition and pd.isna(c.units_removed) and c.units_confidence == "unknown"


def test_combo_description_fills_adu_and_townhouse(permits):
    adu = permits.loc["P-GARAGE-ADU"]
    assert (adu.building_type_std, adu.units_new, adu.units_confidence) == ("ADU", 1, "inferred")
    assert permits.loc["P-TH", "building_type_std"] == "TH"
    assert permits.loc["P-TH", "type_confidence"] == "inferred"


def test_co_date_is_the_final_date(permits):
    assert permits.loc["P-SFD", "final_date"] == pd.Timestamp("2024-01-05")
    assert permits.loc["P-SFD", "final_date_type"] == "certificate_of_occupancy"
    assert pd.isna(permits.loc["P-TH", "final_date"])


def test_personal_fields_never_requested():
    assert not cp.PERSONAL & set(cp.SELECT + cp.COMBO_SELECT)


def test_load_applies_holdout_and_registers(raw, combo, monkeypatch):
    monkeypatch.setattr(cp, "download", lambda store, refresh=False: (raw, combo))
    calls = []
    real = holdout.apply
    monkeypatch.setattr(
        cp.holdout, "apply", lambda df, state, **kw: calls.append(kw) or real(df, state, **kw)
    )
    out = cp.load("OH", store=None)
    assert_conforms(out, "permits")
    assert calls and calls[0]["geoid_col"] == "jurisdiction_geoid"
    assert "cincy_permits" in registry.sources_for("OH")


# --- Adapter rules from the 2026-11-11 hand check
# (reports/oh/parser-handcheck-2026-11-11.md §2, D-081 item 3).
# Synthetic permits that mirror each case; none is a real record.
R3, R2 = '"R-3"', '"R-2"'
COACH = "Two-story carriage house with 2 private garages at first floor and one-bedroom apartment unit above."
# permitnum, workclass, proposeduse, units, issueddate, pin
RULE_ROWS = [
    # a development: apartments and a coach unit on one parcel in one year
    ("D-APT", "CNEW", R2, "6", "2020-08-19", "PDEV"),
    ("D-COACH", "CNEW", R3, "1", "2020-08-19", "PDEV"),
    # the same coach unit text on a parcel where the apartments came another year: an ADU
    ("Y-APT", "CNEW", R2, "6", "2019-03-01", "PYEAR"),
    ("Y-COACH", "CNEW", R3, "1", "2020-08-19", "PYEAR"),
    # three carriage houses on one parcel in one year, nothing else: a development
    ("M-1", "CNEW", R3, "1", "2021-05-01", "PMANY"),
    ("M-2", "CNEW", R3, "1", "2021-05-01", "PMANY"),
    ("M-3", "CNEW", R3, "1", "2021-05-02", "PMANY"),
    # two on one parcel in one year: under the threshold, both stay ADUs
    ("T-1", "RNEW", FM, "1", "2021-05-01", "PTWO"),
    ("T-2", "RNEW", FM, "1", "2021-06-01", "PTWO"),
    # the text names the master plan; the parcel has nothing else
    ("N-COACH", "CNEW", R3, "1", "2020-08-19", "PNAMED"),
    # an alteration permit that reports 3 units on its own row is not its own multifamily neighbour
    ("A-ALT", "RALT", FM, "3", "2022-09-08", "PALT"),
    # a true ADU beside its new house, same parcel and year
    ("H-HOUSE", "RNEW", FM, "1", "2024-04-01", "PHOUSE"),
    ("H-ADU", "RACCESS", FM, "0", "2024-05-01", "PHOUSE"),
    # a pool shed, negated
    ("S-SHED", "RALT", FM, "1", "2025-01-29", "PSHED"),
    # garage with an ADU above; the house is permitted separately on the same lot
    ("G-HOUSE", "RNEW", FM, "1", "2026-06-01", "PGAR"),
    ("G-ADU", "RNEW", FM, "1", "2026-06-23", "PGAR"),
    # an ADU and a house named together, nothing said about a separate permit: still no type from the text
    ("C-BOTH", "RNEW", FM, "1", "2026-07-01", "PBOTH"),
]
RULE_COMBO = [
    ("D-COACH", COACH),
    ("Y-COACH", COACH),
    ("M-1", COACH),
    ("M-2", COACH),
    ("M-3", COACH),
    ("T-1", "NEW DETACHED GARAGE WITH ADU ON SECOND FLOOR"),
    ("T-2", "NEW DETACHED GARAGE WITH ADU ON SECOND FLOOR"),
    ("N-COACH", COACH[:-1] + ", within a 36 residential building masterplan."),
    ("A-ALT", "REBUILD CARRIAGE HOUSE FROM EXISTING SHELL"),
    ("H-ADU", "985SF ADU AT BASEMENT LEVEL"),
    (
        "S-SHED",
        "BUILDING AN ANCILLARY SHED FOR STORAGE AND PLUMBING. POOL INCLUDED.\n\nNOT A DWELLING UNIT/ADU",
    ),
    (
        "G-ADU",
        "New construction of a detached accessory structure consisting of a garage with accessory dwelling "
        "unit above. To be permitted as an accessory dwelling unit on a lot with an existing or proposed "
        "single-family dwelling that is being permitted separately under #G-HOUSE",
    ),
    (
        "C-BOTH",
        "New single-family dwelling with accessory dwelling unit on a lot with a single-family dwelling",
    ),
]


@pytest.fixture
def ruled() -> pd.DataFrame:
    raw = pd.DataFrame(
        RULE_ROWS, columns=["permitnum", "workclass", "proposeduse", "units", "issueddate", "pin"]
    )
    raw["permittypemapped"] = "Building"
    raw["statuscurrentmapped"] = "Permit Issued"
    raw["coissueddate"] = None
    raw["applieddate"] = "2019-01-01"
    raw["permitclass"] = "RCO"
    raw["totalsqft"] = None
    raw["estprojectcostdec"] = "100000"
    raw["pin"] = '"' + raw["pin"] + '"'
    combo = pd.DataFrame(RULE_COMBO, columns=["number_key", "desc_of_work"])
    combo["sub_type_desc"] = "x"
    return cp.build(raw, combo).set_index("permit_id")


def _adus(df: pd.DataFrame) -> set[str]:
    return set(df.index[df["building_type_std"].eq("ADU")])


def test_development_buildings_are_not_adus(ruled):
    # beside new apartments the same year, three on one parcel, or named in a master plan
    assert not {"D-COACH", "M-1", "M-2", "M-3", "N-COACH"} & _adus(ruled)
    # they keep the type their use group and units give: one-unit R-3 is a house, inferred
    assert (ruled.loc["D-COACH", "building_type_std"], ruled.loc["D-COACH", "units_new"]) == ("SFD", 1)
    assert pd.isna(ruled.loc["M-1", "adu_type"])
    assert ruled.loc["D-APT", "building_type_std"] == "MF5"


def test_lone_adus_survive_the_development_rule(ruled):
    # apartments another year, two on a parcel (under the threshold), a 3-unit alteration on its own row,
    # and an ADU beside its new house
    assert {"Y-COACH", "T-1", "T-2", "A-ALT", "H-ADU"} <= _adus(ruled)
    assert ruled.loc["H-HOUSE", "building_type_std"] == "SFD"


def test_development_rule_counts_distinct_permits():
    pid = pd.Series(["X", "X", "X", "Y"])
    parcel = pd.Series(["P"] * 4, dtype="string")
    year = pd.Series([2020] * 4)
    is_adu = pd.Series([True] * 4)
    base = pd.Series(["SFD"] * 4)
    new = pd.Series([True] * 4)
    named = pd.Series([False] * 4)
    # one permit repeated three times plus one more is 2 permits, under DEVELOPMENT_ADU_MIN = 3
    assert not cp.development_adus(pid, parcel, year, is_adu, base, new, named).any()


def test_not_a_dwelling_unit_negates(ruled):
    assert "S-SHED" not in _adus(ruled)
    assert ruled.loc["S-SHED", "building_type_std"] == "OTHER"  # an alteration permit with no unit
    facts, _ = cp.read_text("POOL HOUSE. NOT A DWELLING UNIT/ADU")
    # Since #389 the shared parser negates this itself, so the adapter's NOT_A_UNIT branch may not fire;
    # either way the permit is not an ADU.
    assert facts.building_type_std is None
    assert not facts.evidence or any("negated" in e for e in facts.evidence)


def test_house_permitted_separately_leaves_the_adu(ruled):
    adu = ruled.loc["G-ADU"]
    assert (adu.building_type_std, adu.units_new, adu.adu_type) == ("ADU", 1, "detached")
    assert ruled.loc["G-HOUSE", "building_type_std"] == "SFD"  # the house is counted once, on its own permit


def test_adu_and_house_conflict_stands_without_a_separate_permit(ruled):
    assert ruled.loc["C-BOTH", "building_type_std"] == "SFD"  # use group; the text gives no type
    facts, _ = cp.read_text(RULE_COMBO[-1][1])
    assert facts.building_type_std is None
