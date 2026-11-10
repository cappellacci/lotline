"""Wake roll diff on a hand-built synthetic fixture (no real data).

Checks the detection rule in `reports/nc/wake-roll-adu-diff.md` §1: dwelling cards, the single-family
denominator, each group (new card new/old, unit change, rebuild, merge, none), new REIDs never counted,
the rate per 1,000 a year with its Wilson interval, and the Raleigh permit match and Chapman total.
"""

import math

import pandas as pd
import pytest

from lotline.adapters.states.nc import wake_roll_diff as wd

COLS = ["REAL_ESTATE_ID", "CARD_NUMBER", "TYPE_AND_USE", "UNITS", "HEATED_AREA", "Year_Built",
        "Deeded_Acreage", "Parcel_Identification"]  # fmt: skip

# REID, card, use, units, heated, year, acres, PIN
BEFORE = [
    ("A", "01", "01", "1", "1500", "1950", "0.25", "1714.09 05 9993 000"),  # gains a 2021 cottage
    ("B", "01", "01", "1", "1800", "1960", "0.30", "1714.09 05 9994 000"),  # old garage newly carded
    ("C", "01", "01", "1", "2000", "1970", "0.20", "1714.09 05 9995 000"),  # becomes two family
    ("D", "01", "01", "1", "1200", "1940", "0.25", "1714.09 05 9996 000"),  # torn down, house + ADU
    ("E", "01", "01", "1", "1600", "1980", "0.25", "1714.09 05 9997 000"),  # merges with neighbour
    ("F", "01", "01", "1", "1700", "1990", "0.25", "1714.09 05 9998 000"),  # no change
    ("G", "01", "01", "1", "1400", "1955", "0.25", "1714.09 05 9999 000"),  # torn down, one house
    ("H", "01", "01", "1", "1500", "1950", "0.50", "1714.09 06 0001 000"),  # already two homes
    ("H", "02", "01", "1", "600", "1950", "0.50", "1714.09 06 0001 000"),
    ("I", "01", "01", "1", "1500", "1950", "0.25", "1714.09 06 0002 000"),  # townhouse (land use)
    ("J", "01", None, "0", "0", "0", "0.25", "1714.09 06 0003 000"),  # vacant, then house + ADU
    ("K", "01", "01", "1", "1500", "1950", "0.25", "1714.09 06 0004 000"),  # gone by 2023
    ("L", "01", "01", "1", "1500", "1950", "0.25", "1714.09 06 0005 000"),  # shed card: not a dwelling
]  # fmt: skip
AFTER = [
    ("A", "01", "01", "1", "1500", "1950", "0.25", "1714.09 05 9993 000"),
    ("A", "02", "01", "1", "700", "2021", "0.25", "1714.09 05 9993 000"),
    ("B", "01", "01", "1", "1800", "1960", "0.30", "1714.09 05 9994 000"),
    ("B", "02", "01", "1", "500", "1975", "0.30", "1714.09 05 9994 000"),
    ("C", "01", "02", "2", "2000", "1970", "0.20", "1714.09 05 9995 000"),
    ("D", "01", "01", "1", "2400", "2022", "0.25", "1714.09 05 9996 000"),
    ("D", "02", "01", "1", "600", "2022", "0.25", "1714.09 05 9996 000"),
    ("E", "01", "01", "1", "1600", "1980", "0.50", "1714.09 05 9997 000"),
    ("E", "02", "01", "1", "1500", "1985", "0.50", "1714.09 05 9997 000"),
    ("F", "01", "01", "1", "1700", "1990", "0.25", "1714.09 05 9998 000"),
    ("G", "01", "01", "1", "3000", "2021", "0.25", "1714.09 05 9999 000"),
    ("H", "01", "01", "1", "1500", "1950", "0.50", "1714.09 06 0001 000"),
    ("H", "02", "01", "1", "600", "1950", "0.50", "1714.09 06 0001 000"),
    ("I", "01", "01", "1", "1500", "1950", "0.25", "1714.09 06 0002 000"),
    ("I", "02", "01", "1", "500", "2021", "0.25", "1714.09 06 0002 000"),
    ("J", "01", "01", "1", "2000", "2021", "0.25", "1714.09 06 0003 000"),
    ("J", "02", "01", "1", "700", "2022", "0.25", "1714.09 06 0003 000"),
    ("L", "01", "01", "1", "1500", "1950", "0.25", "1714.09 06 0005 000"),
    ("L", "02", "34", "0", "200", "2021", "0.25", "1714.09 06 0005 000"),
    ("N", "01", "01", "1", "2000", "2022", "0.10", "1714.09 06 0007 000"),  # new subdivision lot
    ("N", "02", "01", "1", "500", "2022", "0.10", "1714.09 06 0007 000"),
]  # fmt: skip
LAND_USE = pd.Series(
    {r: "SF_DETACHED" for r in "ABCDEFGHKL"} | {"I": "SF_ATTACHED", "J": "VACANT_RESIDENTIAL"}
)
JUR = pd.Series({r: ("3755000" if r in "ABCDE" else "37183") for r in "ABCDEFGHIJKL"})


@pytest.fixture
def rolls():
    b = wd.summarize_cards(pd.DataFrame(BEFORE, columns=COLS))
    a = wd.summarize_cards(pd.DataFrame(AFTER, columns=COLS))
    return b, a


@pytest.fixture
def diff(rolls):
    b, a = rolls
    return wd.diff_rolls(b, a, LAND_USE, JUR)


def test_pin10():
    assert wd.pin10(pd.Series(["1714.09 05 9993 000", "0778.03 40 5654 000", "bad"])).tolist()[:2] == [
        "1714059993",
        "0778405654",
    ]
    assert pd.isna(wd.pin10(pd.Series(["bad"]))[0])


def test_summarize_counts_dwelling_cards_only(rolls):
    _, a = rolls
    assert a.loc["A", "dwelling_cards"] == 2 and a.loc["A", "extra_year"] == 2021
    assert a.loc["L", "dwelling_cards"] == 1  # Type & Use 34 is not a dwelling
    assert a.loc["C", "dwelling_units"] == 2 and a.loc["C", "main_use"] == "02"


def test_denominator(diff):
    # H (two homes already) and I (townhouse) and J (vacant) are out; K is gone by the later roll
    assert set(diff.index) == set("ABCDEFGL")
    assert diff.attrs["sf_2019"] == 9  # A B C D E F G K L
    assert diff.attrs["sf_2019_dropped"] == 1


def test_groups(diff):
    g = diff["group"].to_dict()
    assert g == {
        "A": "new_card_new",
        "B": "new_card_old",
        "C": "unit_change",
        "D": "rebuild",
        "E": "merge",
        "F": "none",
        "G": "none",  # rebuilt with one house: not a gain
        "L": "none",
    }
    assert diff["gained"].sum() == 4 and diff["strict"].sum() == 1


def test_new_lots_never_counted(diff, rolls):
    assert "N" not in diff.index
    b, a = rolls
    assert list(wd.vacant_two_homes(b, a, LAND_USE)) == ["J"]


def test_rates_hand_worked(diff):
    r = wd.rates(diff, years=4.0)
    ral = r.loc["3755000"]  # A B C D E: 5 parcels; A-D gained, E is a merge (set aside)
    assert ral["sf_parcels"] == 5 and ral["gained"] == 4 and ral["merge"] == 1
    assert ral["rate"] == pytest.approx(4 / 5 * 1000 / 4)  # 200 per 1,000 a year
    assert ral["rate_strict"] == pytest.approx(1 / 5 * 1000 / 4)
    lo, hi = wd.wilson(4, 5)
    assert ral["rate_lo"] == pytest.approx(lo * 250) and ral["rate_hi"] == pytest.approx(hi * 250)
    assert r.loc["37183", "gained"] == 0


def test_wilson_hand_worked():
    lo, hi = wd.wilson(3, 5)  # p=0.6, z=1.96: centre 0.5520, half 0.3214
    assert lo == pytest.approx(0.2307, abs=1e-4) and hi == pytest.approx(0.8824, abs=1e-4)
    assert all(math.isnan(x) for x in wd.wilson(0, 0))


def test_match_permits():
    roll = pd.Series(["p1", "p2", "p3"])
    permits = pd.Series(["p2", "p3", "p4", "p9", "p2"])  # p9 is not a denominator parcel; p2 twice
    denom = pd.Series(["p1", "p2", "p3", "p4", "p5"])
    m = wd.match_permits(roll, permits, denom)
    assert m == {
        "both": 2,
        "roll_only": 1,
        "permits_only": 1,
        "permits_outside": 1,
        "permits_in_denominator": 3,
    }


def test_chapman_hand_worked():
    n, lo, hi = wd.chapman(roll=60, permits=40, both=30)
    assert n == pytest.approx(61 * 41 / 31 - 1)  # 79.677
    var = 61 * 41 * 30 * 10 / (31**2 * 32)
    assert hi == pytest.approx(n + 1.96 * math.sqrt(var))
    assert lo >= 70  # never below the 70 parcels actually seen


def test_flag_share_hand_worked():
    share, lo, hi = wd.flag_share(both=3, roll=5)
    assert share == pytest.approx(0.6)
    assert (lo, hi) == pytest.approx(wd.wilson(3, 5))  # 0.2307-0.8824: 1.13-4.33 real ADUs per flagged one
    assert math.isnan(wd.flag_share(0, 0)[0])
