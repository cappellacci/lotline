"""Columbus permits adapter on a synthetic fixture (no network, no real data).

Checks the methodology in the module docstring: building type from the Census code on new-structure permits
only, the UNITS plausibility rule (reported if it fits, else derived from the code, else null), demolitions,
void filtering, the CO/final proxy, privacy, and that load() runs the holdout filter.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.oh import columbus_permits as cp
from lotline.schemas import assert_conforms
from lotline.validation import holdout

NEW = "1,2,3 Family - New Structure"
MF_NEW = "Multi Family - New Structure"
FIN = "Final Inspection Approved"
CO = "Certificate of Occupancy Issued"


def _ms(day: str) -> int:
    return int(pd.Timestamp(day).value // 1_000_000)


# permit id, CONST_TYPE_CODE, GENERAL_TYPE, issued, UNITS, appl status, permit status
ROWS = [
    ("SFD-OK", "101", NEW, "2023-03-02", 1, "Closed", CO),
    ("SFD-ZERO", "101", NEW, "2024-05-06", 0, "Issued", "Permit Issued"),
    ("TH-ROW", "102", NEW, "2025-01-10", 6, "Closed", FIN),
    ("DUP-BAD", "103", NEW, "2013-07-01", 1, "Closed", FIN),
    ("MF-OK", "105", MF_NEW, "2022-04-04", 120, "Closed", CO),
    ("MF-NULL", "105", MF_NEW, "2021-02-11", None, "Expired Permit", "Expired Permit"),
    ("TQ-BAD", "104", NEW, "2016-08-08", 7, "Closed", FIN),
    ("SHOP", "327", "Commercial - New Structure", "2019-06-01", 40, "Closed", FIN),
    ("TRADE-105", "105", "Multi Family - Other", "2022-05-05", 120, "Closed", FIN),
    ("DEMO-SF", "645", "1,2,3 Family - Demolition", "2014-12-30", None, "Closed", FIN),
    ("DEMO-MF", "648", "Multi Family - Demolition", "2015-03-03", 24, "Closed", FIN),
    ("DEMO-OTH", "649", "Unspecified - Demolition", "2015-04-04", 3, "Closed", FIN),
    ("VOID-1", "101", NEW, "2020-01-02", 1, "VOID - Entered In Error", "Permit Issued"),
    ("WDRAWN", "101", NEW, "2020-01-03", 1, "Withdrawn", "Permit Issued"),
    ("NOT-ISSUED", "101", NEW, None, 1, "Issuance Pending", "Permit Issued"),
]


@pytest.fixture
def raw() -> pd.DataFrame:
    df = pd.DataFrame(
        ROWS,
        columns=[
            "B1_ALT_ID",
            "CONST_TYPE_CODE",
            "GENERAL_TYPE",
            "issued",
            "UNITS",
            "B1_APPL_STATUS",
            "PERMIT_STATUS",
        ],
    )
    df["ISSUED_DT"] = [_ms(d) if isinstance(d, str) else None for d in df.pop("issued")]
    df["LAST_STATUS_DT"] = _ms("2026-01-15")
    df["OBJECTID"] = range(1, len(df) + 1)
    df["B1_PARCEL_NBR"] = "010000001"
    df["SQFT"] = 2000.0
    df["G3_VALUE_TTL"] = 250_000.0
    return df


@pytest.fixture
def permits(raw) -> pd.DataFrame:
    return cp.build(raw).set_index("permit_id")


def test_conforms_and_drops_void_and_unissued(permits):
    assert_conforms(permits.reset_index(), "permits")
    assert not {"VOID-1", "WDRAWN", "NOT-ISSUED"} & set(permits.index)
    assert (permits.jurisdiction_geoid == cp.COLUMBUS_GEOID).all()
    assert permits.adu_type.isna().all()  # no ADU flag or description in the layer


def test_units_reported_when_plausible_else_derived(permits):
    p = permits
    assert (p.loc["SFD-OK", "units_new"], p.loc["SFD-OK", "units_confidence"]) == (1, "reported")
    assert (p.loc["SFD-ZERO", "units_new"], p.loc["SFD-ZERO", "units_confidence"]) == (1, "derived")
    assert permits.loc["TH-ROW", "units_new"] == 6 and permits.loc["TH-ROW", "building_type_std"] == "TH"
    assert (permits.loc["DUP-BAD", "units_new"], permits.loc["DUP-BAD", "units_confidence"]) == (2, "derived")
    assert permits.loc["MF-OK", "units_new"] == 120 and permits.loc["MF-OK", "building_type_std"] == "MF5"


@pytest.mark.parametrize("pid", ["MF-NULL", "TQ-BAD"])
def test_unknown_multifamily_units_stay_null_never_zero(permits, pid):
    assert pd.isna(permits.loc[pid, "units_new"])
    assert permits.loc[pid, "units_confidence"] == "unknown"


def test_only_new_structure_permits_add_dwellings(permits):
    # a trade permit with the project's code and unit count must not count the building twice
    assert permits.loc["TRADE-105", "building_type_std"] == "OTHER"
    assert pd.isna(permits.loc["TRADE-105", "units_new"])
    # nonresidential new buildings keep their type but their UNITS is not a dwelling count
    assert permits.loc["SHOP", "building_type_std"] == "OTHER" and pd.isna(permits.loc["SHOP", "units_new"])


def test_demolitions(permits):
    sf, mf, oth = permits.loc["DEMO-SF"], permits.loc["DEMO-MF"], permits.loc["DEMO-OTH"]
    assert sf.is_demolition and sf.units_new == 0
    assert (sf.units_removed, sf.units_confidence) == (1, "derived")
    assert (mf.building_type_std, mf.units_removed, mf.units_confidence) == ("MF5", 24, "reported")
    assert oth.is_demolition and pd.isna(oth.units_removed) and oth.units_confidence == "unknown"


def test_final_date_only_for_co_or_final_inspection(permits):
    assert permits.loc["SFD-OK", "final_date_type"] == "certificate_of_occupancy"
    assert permits.loc["TH-ROW", "final_date_type"] == "final_inspection"
    assert permits.loc["TH-ROW", "final_date"] == pd.Timestamp("2026-01-15")
    assert pd.isna(permits.loc["SFD-ZERO", "final_date"])


def test_personal_fields_never_requested():
    assert not cp.PERSONAL & set(cp.OUT_FIELDS)
    assert "APPLICANT" not in cp.WHERE


def test_load_applies_holdout_filter(raw, monkeypatch):
    monkeypatch.setattr(cp, "download", lambda store, refresh=False: raw)
    calls = []
    real_apply = holdout.apply

    def spy(df, state, **kw):
        calls.append((state, kw))
        return real_apply(df, state, **kw)

    monkeypatch.setattr(cp.holdout, "apply", spy)
    out = cp.load("OH", store=None)
    assert calls and calls[0][1]["geoid_col"] == "jurisdiction_geoid"
    assert_conforms(out, "permits")
    holdout.assert_no_leak(out, "permits", "OH")


def test_registered_as_oh_source():
    assert "columbus_permits" in registry.sources_for("OH")
