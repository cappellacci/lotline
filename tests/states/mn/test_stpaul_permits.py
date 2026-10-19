"""St. Paul building permits adapter on a synthetic fixture (no network, no real data)."""

from pathlib import Path

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.mn import stpaul_permits as sp
from lotline.schemas import assert_conforms
from lotline.validation import holdout

FIX = Path(__file__).parent / "fixtures" / "stpaul_permits_synthetic.csv"


def _raw() -> pd.DataFrame:
    df = pd.read_csv(FIX, dtype=str, keep_default_na=False).drop(columns="note")
    for col in ("OBJECTID", "ISSUEDATE", "FINALDATE", "STATE_VALUATION"):
        df[col] = pd.to_numeric(df[col].replace("", None))
    return df.replace({"": None})


@pytest.fixture
def permits() -> pd.DataFrame:
    return sp.to_permits(_raw()).set_index("permit_id")


def test_conforms_registered_and_blind(permits):
    assert_conforms(permits.reset_index(), "permits")
    assert "stpaul_permits" in registry.sources_for("MN")
    holdout.assert_no_leak(permits.reset_index(), "permits", "MN")
    assert (permits.jurisdiction_geoid == "2758000").all()
    assert permits.issue_date.max() < pd.Timestamp("2024-01-01")


def test_held_out_and_unissued_rows_are_gone(permits):
    assert {"stp-20 900008", "stp-20 900009", "stp-20 900010"}.isdisjoint(permits.index)
    # 03:00 UTC on 2024-01-01 is still 2023-12-31 in St. Paul: kept
    assert permits.loc["stp-20 900007"].issue_date == pd.Timestamp("2023-12-31")
    assert len(permits) == 7


def test_holdout_runs_before_anything_else(monkeypatch):
    seen = {}
    real = holdout.apply

    def spy(df, state, **cols):
        seen["cols"] = list(df.columns)
        return real(df, state, **cols)

    monkeypatch.setattr(sp.holdout, "apply", spy)
    sp.to_permits(_raw())
    # the filter gets the raw fields plus dates only: no derived column exists yet
    assert "building_type_std" not in seen["cols"] and "SUB_TYPE" in seen["cols"]


def test_personal_and_free_text_never_requested_nor_kept(permits):
    assert not sp.PERSONAL & set(sp.FIELDS)
    text = permits.to_csv()
    assert "Testperson" not in text and "555-0100" not in text and "ADU" not in text


def test_units_derived_only_where_the_permit_fixes_them(permits):
    sfd, duplex = permits.loc["stp-20 900001"], permits.loc["stp-20 900002"]
    assert (sfd.units_new, sfd.units_removed, sfd.building_type_std) == (1, 0, "SFD")
    assert (duplex.units_new, duplex.building_type_std, duplex.units_confidence) == (2, "U2", "derived")
    multi = permits.loc["stp-20 900003"]
    assert pd.isna(multi.units_new) and multi.building_type_std == "UNKNOWN"
    assert multi.type_confidence == "unknown" and multi.units_confidence == "unknown"
    repair = permits.loc["stp-20 900004"]
    assert (repair.units_new, repair.units_removed) == (0, 0)
    assert pd.isna(permits.loc["stp-20 900006"].units_new)  # remodel: unknown
    assert permits.loc["stp-20 900005"].building_type_std == "OTHER"


def test_pins_dates_and_values(permits):
    assert permits.loc["stp-20 900001"].parcel_id == "27123032823220116"
    assert pd.isna(permits.loc["stp-20 900004"].parcel_id)
    assert pd.isna(permits.loc["stp-20 900005"].parcel_id)
    sfd = permits.loc["stp-20 900001"]
    assert sfd.final_date == pd.Timestamp("2018-11-01") and sfd.final_date_type == "final_inspection"
    assert pd.isna(permits.loc["stp-20 900006"].final_date)  # Inspected, not Finaled
    assert sfd.valuation_usd == 350000.0
    assert sfd.permit_class_raw == "Single Family Dwelling:New:Finaled"
