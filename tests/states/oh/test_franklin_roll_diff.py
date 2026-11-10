"""Franklin roll diff on a hand-built synthetic fixture (no real data).

Checks the detection rule in `reports/oh/adu-coverage-and-undercount.md` §2.1: dwelling cards with living
area, the single-family denominator, each group, the merge set-aside, new garages (envelope only) and the
D-074 quantities with k and the Chapman total worked by hand.
"""

import math

import pandas as pd
import pytest

from lotline.adapters.states.oh import franklin_roll_diff as fd

D_COLS = ["PARCEL ID", "CARD", "LIVUNITS", "YRBLT", "SFLA"]
P_COLS = ["PARCEL ID", "LUC", "ACRES"]

# parcel, card, units, year, living area
BEFORE_D = [
    ("A", "1", "1", "1950", "1500"),  # gains a 2022 card (strict)
    ("B", "1", "1", "1960", "1800"),  # old building newly carded
    ("C", "1", "1", "1970", "2000"),  # LUC 510 -> 520
    ("D", "1", "1", "1940", "1200"),  # rebuilt 2021 with two cards
    ("E", "1", "1", "1980", "1600"),  # merge: acreage doubles, gains a card
    ("F", "1", "1", "1990", "1700"),  # no change; adds 300 sq ft
    ("G", "1", "2", "1950", "1500"),  # two units already: out of denominator
    ("H", "1", "1", "1950", "1500"),  # land use 520: out of denominator
]
BEFORE_P = [("A", "510", "0.2"), ("B", "510", "0.2"), ("C", "510", "0.2"), ("D", "510", "0.2"),
            ("E", "510", "0.2"), ("F", "510", "0.2"), ("G", "510", "0.2"), ("H", "520", "0.2"),
            ("V", "500", "0.2")]  # fmt: skip
AFTER_D = [
    ("A", "1", "1", "1950", "1500"), ("A", "2", "1", "2022", "600"),
    ("B", "1", "1", "1960", "1800"), ("B", "2", "1", "1925", "500"),
    ("C", "1", "1", "1970", "2000"),
    ("D", "1", "1", "2021", "2200"), ("D", "2", "1", "2021", "700"),
    ("E", "1", "1", "1980", "1600"), ("E", "2", "1", "1975", "1400"),
    ("F", "1", "1", "1990", "2000"),
    ("F", "2", "1", "2023", "0"),  # card without living area: not a dwelling
    ("G", "1", "2", "1950", "1500"), ("H", "1", "1", "1950", "1500"),
    ("N", "1", "1", "2023", "1500"), ("N", "2", "1", "2023", "500"),  # new parcel: never compared
]  # fmt: skip
AFTER_P = [("A", "510", "0.2"), ("B", "510", "0.2"), ("C", "520", "0.2"), ("D", "510", "0.2"),
           ("E", "510", "0.45"), ("F", "510", "0.2"), ("G", "510", "0.2"), ("H", "520", "0.2"),
           ("N", "510", "0.2")]  # fmt: skip


def _roll(d, p):
    return fd.summarize(pd.DataFrame(d, columns=D_COLS), pd.DataFrame(p, columns=P_COLS))


@pytest.fixture
def diff():
    b, a = _roll(BEFORE_D, BEFORE_P), _roll(AFTER_D, AFTER_P)
    lu = b["luc"].map({"510": "SF_DETACHED", "520": "DUPLEX", "500": "VACANT_RESIDENTIAL"})
    return fd.diff_rolls(b, a, lu, pd.Series("3918000", index=b.index), first_new_year=2020)


def test_summary_counts_only_cards_with_living_area():
    a = _roll(AFTER_D, AFTER_P)
    assert a.loc["F", "dwelling_cards"] == 1
    assert a.loc["A", "dwelling_cards"] == 2 and a.loc["A", "extra_year"] == 2022
    assert a.loc["N", "dwelling_cards"] == 2
    b = _roll(BEFORE_D, BEFORE_P)
    assert b.loc["V", "dwelling_cards"] == 0  # vacant parcel: on the parcel file, no dwelling card


def test_denominator_and_groups(diff):
    assert diff.attrs["sf_before"] == 6  # A-F: G has two units, H is two family, V vacant
    assert diff.attrs["sf_dropped"] == 0
    assert diff["group"].to_dict() == {
        "A": "new_card_new",
        "B": "new_card_old",
        "C": "unit_change",
        "D": "rebuild",
        "E": "merge",
        "F": "none",
    }
    assert diff["gained"].sum() == 4 and diff["strict"].sum() == 1
    assert diff.loc["F", "added_area"] and not diff.loc["A", "added_area"]


def test_new_garages_envelope():
    cols = ["PARCEL ID", "CARD", "CODE", "YRBLT"]
    before = pd.DataFrame([("A", "1", "RG1 - FRAME DETACHED GARAGE", "1960")], columns=cols)
    after = pd.DataFrame(
        [
            ("A", "1", "RG2 - CB DETACHED GARAGE", "1960"),  # recoded old garage: not new
            ("B", "1", "RG1 - FRAME DETACHED GARAGE", "2021"),  # new garage
            ("C", "1", "RS1 - FRAME UTILITY SHED", "2021"),  # shed: not a garage
            ("D", "1", "RG1 - FRAME DETACHED GARAGE", "2019"),  # before the window
        ],
        columns=cols,
    )
    assert list(fd.new_garages(before, after, 2020, 2024)) == ["B"]


def test_undercount_by_hand():
    # R = {1,2,3,4}, P = {1,2,5,9}; denominator holds 1-8; unflagged new-structure permits on 3 and 7.
    out = fd.undercount({"1", "2", "3", "4"}, {"1", "2", "5", "9"}, {str(i) for i in range(1, 9)}, {"3", "7"})
    assert (out["P_and_R"], out["a"], out["b"], out["P_not_R"]) == (2, 1, 1, 2)
    assert out["P_in_denominator"] == 3 and out["P_not_R_in_denominator"] == 1
    assert out["k"] == pytest.approx(1.5)  # (2 + 1) / 2
    # Chapman with P on denominator parcels: (4+1)(3+1)/(2+1) - 1 = 17/3
    assert out["chapman"] == pytest.approx(20 / 3 - 1)
    assert out["k_lo90"] < 1.5 < out["k_hi90"]


def test_undercount_without_overlap_is_undefined():
    out = fd.undercount({"1"}, {"2"}, {"1", "2"}, set())
    assert out["P_and_R"] == 0 and math.isnan(out["k"])
