"""Austin ADU roll rules (`reports/tx/adu-coverage-and-undercount.md` §0) on synthetic rows only.

Hand-worked cases: improvement year (living floor first), universe (pre-2019 house, no condo/townhome),
groups (alq / house / multi / none), the HOME rule (house stays, no demolition in three years), the R/P
match with the duplex deviation, and the fixed-width reader on a tiny zip (owner span never read).
"""

import zipfile

import pandas as pd

from lotline.adapters.states.nc import wake_roll_diff as wrd
from lotline.adapters.states.tx import austin_adu_roll as ar
from lotline.adapters.states.tx import tcad_parcels as tp

from .test_tcad_parcels import OWNER, OWNER_SPAN, prop, record


def seg(pid, iid, det, yr):
    return {"prop_id": str(pid), "imprv_id": str(iid), "det_type": det, "yr_built": str(yr)}


def test_improvement_year_prefers_living_floor():
    det = pd.DataFrame(
        [seg(1, 10, "1ST", 1985), seg(1, 10, "041", 1960), seg(1, 11, "031", 2021), seg(1, 12, "1ST", 0)]
    )
    y = ar.improvement_years(det, 2026)
    assert y[("1", "10")] == 1985  # the 1960 garage segment is not the living floor
    assert y[("1", "11")] == 2021  # no living floor: earliest segment
    assert ("1", "12") not in y.index  # year 0 is not a year


def roll_fixture():
    t = [
        # parcel A: 1950 house + 2021 ALQ → alq (in R)
        ("A", "1", "a1", "01", 1950), ("A", "1", "a2", "120", 2021),
        # B: 1970 house + 2020 second house → house (in R)
        ("B", "2", "b1", "01", 1970), ("B", "2", "b2", "01", 2020),
        # C: 1980 house + 2022 duplex → multi (not in R)
        ("C", "3", "c1", "01", 1980), ("C", "3", "c2", "02", 2022),
        # D: house rebuilt 2020 with a 2021 ALQ → not in universe
        ("D", "4", "d1", "01", 2020), ("D", "4", "d2", "120", 2021),
        # E: 1990 house + 1960 garage apartment (old, carded) → universe, none
        ("E", "5", "e1", "01", 1990), ("E", "5", "e2", "21", 1960),
        # F: townhome parcel → out
        ("F", "6", "f1", "16", 2000), ("F", "6", "f2", "01", 1990),
        # G: 1960 house + 2024 ALQ → universe, outside the window
        ("G", "7", "g1", "01", 1960), ("G", "7", "g2", "120", 2024),
    ]  # fmt: skip
    types = pd.DataFrame([(p, i, c) for _, p, i, c, _ in t], columns=["prop_id", "imprv_id", "type_cd"])
    types["parcel_id"] = [x[0] for x in t]
    years = pd.Series(
        [y for *_, y in t], index=pd.MultiIndex.from_tuples([(p, i) for _, p, i, _, _ in t]), name="year"
    )
    return types, years


def test_classify_groups_and_universe():
    types, years = roll_fixture()
    r = ar.classify_parcels(types, years)
    assert r.loc["A", "group"] == "alq" and r.loc["A", "in_r"]
    assert r.loc["B", "group"] == "house" and r.loc["B", "in_r"]
    assert r.loc["C", "group"] == "multi" and not r.loc["C", "in_r"]
    assert not r.loc["D", "universe"] and r.loc["D", "group"] == "none"
    assert r.loc["E", "universe"] and r.loc["E", "group"] == "none"
    assert not r.loc["F", "universe"]
    assert r.loc["G", "universe"] and r.loc["G", "group"] == "none"
    assert r["universe"].sum() == 5 and r["in_r"].sum() == 2
    assert ar.classify_parcels(types, years, window=(2024, 2025)).loc["G", "group"] == "alq"


def test_home_rule():
    types, years = roll_fixture()
    r = ar.classify_parcels(types, years)
    permits = pd.DataFrame(
        [
            ("A", "2024-06-01", "R- 101 Single Family Houses|New", False),  # house 1950 stays → ADU
            ("B", "2024-06-01", "R- 103 Two Family Bldgs|New", False),  # duplex behind a 1970 house → ADU
            ("C", "2024-06-01", "R- 101 Single Family Houses|New", False),  # demolished 2022 → not
            ("C", "2022-01-10", "R- 645 Demolition One Family Homes|Demolition", True),
            ("D", "2024-06-01", "R- 101 Single Family Houses|New", False),  # house built 2020 < 2024 → ADU
            ("F", "2024-06-01", "R- 101 Single Family Houses|New", False),  # townhome parcel → not
            ("Z", "2024-06-01", "R- 101 Single Family Houses|New", False),  # no roll house → not
            ("G", "2024-06-01", "R- 105 Five or More Family Bldgs|New", False),  # class 105 → not
            ("A", "2024-06-01", "R- 645 Demolition One Family Homes|Demolition", True),  # demolition row
        ],
        columns=["parcel_id", "issue_date", "permit_class_raw", "is_demolition"],
    )
    got = ar.home_adu(permits, r["main_year"], r["attached"]).tolist()
    # A's own demolition row is dated the same day: it is a demolition, so it is never an ADU; but it also
    # marks A's new-building permit as a rebuild (demolition within the lookback).
    assert got == [False, True, False, False, True, False, False, False, False]


def test_home_rule_lookback_three_years():
    main = pd.Series({"A": 1950.0})
    att = pd.Series({"A": False})
    p = pd.DataFrame(
        [
            ("A", "2025-03-01", "R- 102 Secondary Apartment|New", False),
            ("A", "2021-01-01", "R- 645 Demolition One Family Homes|Demolition", True),  # > 3 years before
        ],
        columns=["parcel_id", "issue_date", "permit_class_raw", "is_demolition"],
    )
    assert ar.home_adu(p, main, att).tolist() == [True, False]


def test_match_and_k():
    roll = pd.DataFrame(
        {
            "universe": [True] * 6 + [False],
            "in_r": [True, True, True, True, True, False, False],
        },
        index=["A", "B", "C", "D", "E", "F", "X"],
    )
    flagged = pd.Series(["A", "B", "F", "X"])  # A, B in R; F in universe not R; X outside
    unflagged = pd.DataFrame(
        {"parcel_id": ["C", "D", "D"], "permit_class_raw": ["R- 101 x|New", "R- 103 x|New", "R- 103 y|New"]}
    )
    m = ar.match(roll, flagged, unflagged)
    assert m == {
        "universe": 6, "R": 5, "P": 3, "P_outside_universe": 1, "both": 2, "a": 1, "a_as_written": 2,
        "b": 1, "P_not_R": 1,
    }  # fmt: skip
    k, lo, hi = wrd.k_undercount(m["both"], m["a"])
    assert k == 1.5 and lo < 1.5 < hi


def test_read_improvements_positions(tmp_path):
    info = [
        record(ar.INFO_FIELDS, {"prop_id": f"{p:012d}", "imprv_id": f"{i:012d}", "type_cd": t}, width=115)
        for p, i, t in [(1, 10, "01"), (1, 11, "120"), (2, 20, "01")]
    ]
    det = [
        record(ar.DET_FIELDS, {"prop_id": "000000000001", "imprv_id": "000000000010", "det_type": "1ST",
                               "yr_built": 1955}, width=200),
        record(ar.DET_FIELDS, {"prop_id": "000000000001", "imprv_id": "000000000011", "det_type": "1ST",
                               "yr_built": 2022}, width=200),
    ]  # fmt: skip
    props = [prop("000000000001", "0101010101"), prop("000000000002", "0202020202")]
    path = tmp_path / "tcad.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("PROP.TXT", "\r\n".join(props))
        zf.writestr("IMP_INFO.TXT", "\n".join(info))
        zf.writestr("IMP_DET.TXT", "\n".join(det))
    d, t = ar.read_improvements(path, {tp.TRAVIS_FIPS + "0101010101"})
    assert set(t["prop_id"]) == {"000000000001"}  # parcel 2 not asked for
    assert t["parcel_id"].unique().tolist() == ["484530101010101"]
    assert sorted(t["type_cd"]) == ["01", "120"]
    r = ar.classify_parcels(t, ar.improvement_years(d, 2026))
    assert r.loc["484530101010101", "group"] == "alq"
    assert OWNER not in d.to_string() + t.to_string()
    # no sliced PROP field overlaps the owner-name span
    o0, on = OWNER_SPAN
    assert all(s + n <= o0 or s >= o0 + on for s, n in ar.PROP_ID_FIELDS.values())
