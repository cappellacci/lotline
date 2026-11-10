"""D-074 step 2 in the ADU fit panels: county remainders whose ADU counts come from local permit files use
permit-level eligible lots (`eligible.permit_level`, #375); BPS outcomes keep the BPS-kind lots.

Synthetic fixture, worked by hand (the same counties as tests/core/test_eligible.py):
- 37119 has 1,000 ACS one-unit detached homes, Charlotte (local-only, all in 37119) 600, Town T (local-only)
  200, half in 37119 and half in 37025; 37025 has 400.
- BPS kind: 37119 1,000, 37025 400. Permit kind: 37119 = 1,000 - 600 - 100 = 300; 37025 = 400 - 100 = 300.
- 27139's remainder is counted from a parcel roll (950): it never overlaps a place, so it is never swapped.
"""

from __future__ import annotations

import pandas as pd
import pytest

from lotline.build import eligible
from lotline.model import estimate_adu


def _fixture():
    acs = pd.DataFrame(
        {
            "geo": [
                "county:37119",
                "county:37025",
                "place:3712000",
                "place:3799990",
                "county:27139",
                "cousub:2713919036",
            ],
            "variable": eligible.ACS_SF_DETACHED,
            "end_year": 2024,
            "estimate": [1000.0, 400.0, 600.0, 200.0, 1000.0, 100.0],
        }
    )
    juris = pd.DataFrame(
        {
            "geoid": ["37119", "37025", "3712000", "3799990", "27139", "2713919036"],
            "state": ["NC", "NC", "NC", "NC", "MN", "MN"],
            "kind": [
                "county_unincorporated",
                "county_unincorporated",
                "place",
                "place",
                "county_unincorporated",
                "township",
            ],
            "county_geoid": ["37119", "37025", "37119", "37119", "27139", "27139"],
            "data_tier": 3,
            "in_bps": [True, True, False, False, True, False],
        }
    )
    c_shares = pd.DataFrame(
        {
            "place_geoid": ["3712000", "3799990", "3799990"],
            "county_geoid": ["37119", "37119", "37025"],
            "share": [1.0, 0.5, 0.5],
        }
    )
    t_shares = pd.DataFrame(columns=["place_geoid", "township_geoid", "share"])
    kw = {"themes": ("adu",), "county_shares": c_shares, "township_shares": t_shares}
    stored = eligible.from_acs(acs, juris, **kw)
    roll = stored["jurisdiction_geoid"] == "27139"
    stored.loc[roll, ["eligible_parcels", "denominator_source"]] = [950, "parcels"]
    permit_rows = eligible.from_acs(acs, juris, remainder="permits", **kw)
    return stored, permit_rows, juris


def _lots(df):
    return df.set_index("jurisdiction_geoid")["eligible_parcels"]


def test_counted_remainder_takes_permit_level_lots_by_hand():
    stored, permit_rows, juris = _fixture()
    counted = {"37119", "3712000", "27139"}
    out = estimate_adu.permit_level_eligible(stored, juris.set_index("geoid"), counted, permit_rows)
    got = _lots(out)
    assert got["37119"] == 300  # counted from permit files: Charlotte and half of Town T taken out
    assert got["37025"] == 400  # not counted from permits: the stored BPS-kind lots
    assert got["27139"] == 950  # parcel-roll remainder: never overlaps, never swapped
    assert got[["3712000", "3799990"]].tolist() == [600, 200]  # places untouched
    kinds = out.set_index("jurisdiction_geoid")["remainder_kind"]
    assert kinds["37119"] == "permits" and kinds["37025"] == "bps" and kinds["27139"] == "bps"
    # no lot counted twice: the 37119 remainder, Charlotte and T's 37119 half add back up to 1,000
    assert got["37119"] + got["3712000"] + 0.5 * got["3799990"] == pytest.approx(1000)
    assert _lots(stored)["37119"] == 1000  # input untouched


def test_nothing_changes_without_a_counted_acs_remainder(monkeypatch):
    stored, _, juris = _fixture()

    def boom(*a, **k):
        raise AssertionError("permit-level rows must not be built when nothing needs them")

    monkeypatch.setattr(estimate_adu, "permit_acs_rows", boom)
    for counted in ({"3712000"}, {"27139"}, set()):  # a place, a parcel-roll remainder, nothing
        assert not estimate_adu.needs_permit_level(stored, juris, counted)
        out = estimate_adu.adu_panel_eligible("NC", None, stored, juris, counted)
        assert out is stored


def test_panel_eligible_switch(monkeypatch):
    stored, permit_rows, juris = _fixture()
    monkeypatch.setattr(estimate_adu, "permit_acs_rows", lambda state, store, j: permit_rows)
    on = estimate_adu.adu_panel_eligible("NC", None, stored, juris, {"37119", "37025"})
    assert _lots(on)[["37119", "37025"]].tolist() == [300, 300]
    off = estimate_adu.adu_panel_eligible("NC", None, stored, juris, {"37119"}, remainder="bps")
    assert _lots(off)["37119"] == 1000  # BPS kind: the stored lots, as BPS outcomes use
    with pytest.raises(ValueError, match="remainder"):
        estimate_adu.adu_panel_eligible("NC", None, stored, juris, {"37119"}, remainder="county")


def test_scenario_floor_keeps_non_overlapping_only():
    """The D-070 floor's lots come from `adu.non_overlapping`, which already takes the local-only places out
    of ACS remainders; the permit-level swap is for the fit panels only, so the two never stack."""
    import inspect

    from lotline.model.scenarios import adu

    src = inspect.getsource(adu.places_from_store)
    assert "non_overlapping" in src and "adu_panel_eligible" not in src and "permit_level" not in src
