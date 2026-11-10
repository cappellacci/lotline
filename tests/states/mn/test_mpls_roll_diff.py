"""Minneapolis roll diff and permit undercount on a hand-built synthetic fixture (no real data).

Checks the rule in `reports/mn/adu-coverage-and-undercount.md` §2: the single-family denominator, each group
(ADU added, rebuild, duplex with ADU, merge, duplex only, none), a DETACHED ADU building row on a per-building
table, new PINs never counted, the permit parcel sets for each version of group (a), and k / Chapman by hand.
"""

import math

import pandas as pd
import pytest

from lotline.adapters.states.mn import mpls_roll_diff as md

COLS = ["pin", "building_use", "units", "year_built", "area_sqft"]


def pin(n: int) -> str:
    return f"p{n:013d}"


def pid(n: int) -> str:
    return "27053" + f"{n:013d}"


BEFORE = [
    (pin(1), "SINGLE FAM. DWLG.", 1, 1920, 5000),  # gains an ADU (label)
    (pin(2), "SINGLE FAM. DWLG.", 1, 1925, 5000),  # torn down, rebuilt 2020 with an ADU
    (pin(3), "SINGLE FAM. DWLG.", 1, 1930, 5000),  # becomes a duplex with an ADU
    (pin(4), "SINGLE FAM. DWLG.", 1, 1940, 5000),  # merges with a neighbour, labelled ADU
    (pin(5), "SINGLE FAM. DWLG.", 1, 1950, 5000),  # becomes a duplex, no ADU
    (pin(6), "SINGLE FAM. DWLG.", 1, 1960, 5000),  # no change
    (pin(7), "R WITH ACCESSORY DWELLING", 1, 1910, 5000),  # already has an ADU: out
    (pin(8), "SINGLE FAM. DWLG.", 2, 1910, 5000),  # two units in 2017: out
    (pin(9), "SINGLE FAM. DWLG.", 1, 1915, 5000),  # gone by the later roll
    (pin(10), "SINGLE FAM. DWLG.", 1, 1918, 5000),  # per-building table: DETACHED ADU row
]
AFTER = [
    (pin(1), "SF HOUSE W/ADU", 0, 1920, 5000),
    (pin(2), "SF HOUSE W/ADU", 0, 2020, 5000),
    (pin(3), "DUPLEX W/ADU", 2, 1930, 5000),
    (pin(4), "SF HOUSE W/ADU", 0, 1940, 9000),
    (pin(5), "DUPLEX", 2, 1950, 5000),
    (pin(6), "SINGLE FAMILY HOUSE", 0, 1960, 5000),
    (pin(7), "SF HOUSE W/ADU", 0, 1910, 5000),
    (pin(8), "DUPLEX", 2, 1910, 5000),
    (pin(10), "SINGLE FAMILY HOUSE", 0, 1918, 5000),
    (pin(10), "DETACHED ADU", 0, 2022, 5000),
    (pin(11), "SF HOUSE W/ADU", 0, 2021, 4000),  # new PIN (split): never counted
]
LAND_USE = pd.Series({pid(n): "SF_DETACHED" for n in range(1, 12)})


@pytest.fixture
def diff() -> pd.DataFrame:
    b = md.summarize_roll(pd.DataFrame(BEFORE, columns=COLS))
    a = md.summarize_roll(pd.DataFrame(AFTER, columns=COLS))
    return md.diff_rolls(b, a, LAND_USE)


def test_parcel_id_matches_adapter_key():
    s = md.parcel_id(pd.Series(["p0102924110001", "01-029-24-11-0001", "123", None]))
    assert s.tolist()[:2] == ["270530102924110001", "270530102924110001"]
    assert s.isna().tolist()[2:] == [True, True]


def test_summarize_collapses_buildings_and_sees_detached_row():
    a = md.summarize_roll(pd.DataFrame(AFTER, columns=COLS))
    assert a.loc[pid(10), "adu"]
    assert a.loc[pid(10), "buildings"] == 2
    assert a.loc[pid(10), "year_built"] == 1918  # earliest building: the ADU does not move it
    assert a.loc[pid(3), "duplex_adu"] and not a.loc[pid(3), "duplex_label"]
    assert a.loc[pid(5), "duplex_label"]


def test_denominator_and_groups(diff):
    # 1-6 and 10 are single-family on both rolls; 7 (ADU already), 8 (2 units) out; 9 gone; 11 new
    assert set(diff.index) == {pid(n) for n in (1, 2, 3, 4, 5, 6, 10)}
    assert diff.attrs["sf_before"] == 8
    assert diff.attrs["sf_before_dropped"] == 1
    g = diff["group"].to_dict()
    assert g == {
        pid(1): "adu_added",
        pid(2): "rebuild",
        pid(3): "duplex_adu",
        pid(4): "merge",
        pid(5): "duplex_only",
        pid(6): "none",
        pid(10): "adu_added",
    }
    assert set(diff.index[diff["in_r"]]) == {pid(1), pid(2), pid(3), pid(10)}
    assert set(diff.index[diff["strict"]]) == {pid(1), pid(10)}


PERMIT_COLS = ["parcel_id", "issue_date", "building_type_std", "permit_class_raw", "units_new"]
PERMITS = [
    (pid(1), "2019-05-01", "ADU", "Res:SFD:Remodel:Closed", 1),  # P, in R
    (pid(10), "2025-09-01", "ADU", "Res:Accessory:New:Issued", 1),  # ADU-typed after the lag cut-off
    (pid(10), "2021-03-01", "OTHER", "Res:Accessory:New:Closed", 0),  # garage build: wide (a) only
    (pid(2), "2019-07-01", "SFD", "Res:SFD:New:Closed", 1),  # new house: (a) in every version
    (pid(3), "2020-01-01", "DTQ", "Res:TFD:New:Closed", 2),  # duplex rebuild: (a) as written only
    (pid(6), "2018-01-01", "ADU", "Res:SFD:Conversion:Cancelled", 1),  # P, not in R, cancelled
    (pid(7), "2018-02-01", "ADU", "Res:SFD:Remodel:Closed", 1),  # P, outside the denominator
    (pid(5), "2019-01-01", "OTHER", "Wrecking:SFD:Private:Closed", 0),  # wrecking never counts
    (None, "2019-01-01", "ADU", "Res:SFD:Remodel:Closed", 1),  # no parcel: dropped
]


@pytest.fixture
def sets() -> dict[str, set[str]]:
    p = pd.DataFrame(PERMITS, columns=PERMIT_COLS)
    return md.permit_parcels(p, "2017-01-01", "2025-06-30")


def test_permit_sets(sets):
    assert sets["P"] == {pid(1), pid(6), pid(7)}
    assert sets["P_outside"] == {pid(10)}
    assert sets["P_live"] == {pid(1), pid(7)}
    assert sets["a_written"] == {pid(2), pid(3)}
    assert sets["a_noduplex"] == {pid(2)}
    assert sets["a_wide"] == {pid(2), pid(10)}
    assert pid(10) in sets["seen_by_parser"] and pid(5) not in sets["seen_by_parser"]


def test_undercount_by_hand(diff, sets):
    r = set(diff.index[diff["in_r"]])  # {1, 2, 3, 10}
    denom = set(diff.index)
    out = md.undercount(r, sets["P"], sets["a_written"], denom)
    # P∩R = {1}; R \ P = {2, 3, 10}; (a) = {2, 3}; (b) = {10}
    assert (out["P_and_R"], out["a"], out["b"]) == (1, 2, 1)
    # P \ R = {6, 7}: 6 in the denominator, 7 outside
    assert (out["P_not_R"], out["P_not_R_in_denominator"], out["P_not_R_outside"]) == (2, 1, 1)
    assert out["k"] == pytest.approx(3.0)  # (1 + 2) / 1
    # Chapman with P on denominator parcels {1, 6}: (4+1)(2+1)/(1+1) - 1 = 6.5
    assert out["chapman"] == pytest.approx(6.5)
    assert out["chapman_over_P"] == pytest.approx(3.25)


def test_undercount_duplex_removed(diff, sets):
    r = set(diff.index[diff["in_r"] & (diff["group"] != "duplex_adu")])  # {1, 2, 10}
    out = md.undercount(r, sets["P"], sets["a_noduplex"], set(diff.index))
    assert (out["P_and_R"], out["a"], out["b"]) == (1, 1, 1)
    assert out["k"] == pytest.approx(2.0)
    assert out["k_lo90"] <= 2.0 <= out["k_hi90"]


def test_k_is_nan_without_matches():
    out = md.undercount({"x"}, {"y"}, {"x"}, {"x", "y"})
    assert out["P_and_R"] == 0 and math.isnan(out["k"])
