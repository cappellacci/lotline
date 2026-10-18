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
