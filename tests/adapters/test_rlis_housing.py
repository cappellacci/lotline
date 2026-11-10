"""RLIS Housing check: tax-lot keys, the independent list R and Portland's k comparison (synthetic rows only).

Checks the rule in `reports/or/adu-coverage-and-undercount.md` §2.2 against a hand-worked example.
"""

import math

import pandas as pd

from lotline.adapters.checks import rlis_housing as rh
from lotline.adapters.states.nc import wake_roll_diff as wd


def test_taxlot_key_matches_rlis_and_portland_spellings():
    s = pd.Series(["1S2E22BA  -03305", "1S2E22BA 3305", "1n1w23b 1300", "1S1E21DC 13300", "garbage", None])
    assert rh.taxlot_key(s).tolist()[:4] == [
        "1S2E22BA-3305",
        "1S2E22BA-3305",
        "1N1W23B-1300",
        "1S1E21DC-13300",
    ]
    assert rh.taxlot_key(s).isna().tolist()[4:] == [True, True]


def housing():
    # TLID, JURIS_CITY, DATASOURCE, CONFIDENCE, YEARBUILT
    rows = [
        ("1N1E01AA  -00100", "PORTLAND", "Multnomah County Assessor", "HIGH", 2018),  # in P
        ("1N1E01AA  -00200", "Portland", "RLIS TAXLOTS", "HIGH", 2019),  # in P
        ("1N1E01AA  -00300", "Portland", "METRO - Master Address File", "LOW", 2020),  # (a): unflagged SFD
        (
            "1N1E01AA  -00400",
            "Portland",
            "METRO - Field check",
            "MEDIUM",
            1928,
        ),  # duplex only: (a) as written
        ("1N1E01AA  -00500", "Portland", "METRO - Accesory Dwelling Unit Study", "HIGH", 2010),  # (b)
        ("1N1E01AA  -00500", "Portland", "Multnomah County Assessor", "HIGH", 2010),  # same lot, once
        (
            "1N1E01AA  -00600",
            "Portland",
            "City of Portland Building Permits",
            "HIGH",
            2017,
        ),  # permit-based: out
        ("1N1E01AA  -00700", "Gresham", "Multnomah County Assessor", "HIGH", 2017),  # other city: out
    ]
    df = pd.DataFrame(rows, columns=["TLID", "JURIS_CITY", "DATASOURCE", "CONFIDENCE", "YEARBUILT"])
    return df.assign(UNIT_TYPE="ADU")


def permits():
    # parcel_id, issue_year, adu_type, building_type_std
    rows = [
        ("1N1E01AA 100", 2017, "detached", "ADU"),
        ("1N1E01AA 200", 2018, "internal_conversion", "ADU"),
        ("1N1E01AA 300", 2015, None, "SFD"),
        ("1N1E01AA 400", 2012, None, "U2"),
        ("1N1E01AA 600", 2016, "detached", "ADU"),  # flagged, its R row is permit-based: P \ R
        ("1N1E01AA 800", 2026, "detached", "ADU"),  # after the window
        ("1N1E01AA 900", 1990, "detached", "ADU"),  # before the window
    ]
    return pd.DataFrame(rows, columns=["parcel_id", "issue_year", "adu_type", "building_type_std"])


def test_independent_lots_drops_permit_sources_other_cities_and_repeats():
    r = rh.independent_lots(housing())
    assert sorted(r) == ["1N1E01AA-100", "1N1E01AA-200", "1N1E01AA-300", "1N1E01AA-400", "1N1E01AA-500"]
    # lot 500 also has an assessor row, so dropping the ADU Study keeps it
    assert len(rh.independent_lots(housing(), drop_study=True)) == 5
    assert sorted(rh.independent_lots(housing(), high_only=True)) == [
        "1N1E01AA-100",
        "1N1E01AA-200",
        "1N1E01AA-500",
    ]
    assert sorted(rh.independent_lots(housing(), built_from=2016)) == [
        "1N1E01AA-100",
        "1N1E01AA-200",
        "1N1E01AA-300",
    ]


def test_compare_by_hand():
    # R = {100, 200, 300, 400, 500}; P (1995-2025) = {100, 200, 600}; P∩R = {100, 200}
    # R \ P = {300, 400, 500}: 300 has an unflagged SFD (a, central); 400 only a duplex (a as written);
    # 500 none (b)
    out = rh.compare(rh.independent_lots(housing()), permits())
    assert (out["R"], out["P"], out["both"]) == (5, 3, 2)
    assert (out["a_central"], out["a_as_written"], out["b"], out["permits_only"]) == (1, 2, 1, 1)
    assert math.isclose(out["k"], 1.5) and math.isclose(out["k_as_written"], 2.0)
    assert (out["k_lo90"], out["k_hi90"]) == wd.k_undercount(2, 1)[1:]
    # Chapman: (5 + 1)(3 + 1) / (2 + 1) - 1 = 7
    assert math.isclose(out["chapman"], 7.0)


def test_compare_window_moves_permits():
    out = rh.compare(rh.independent_lots(housing()), permits(), first_year=2016)
    # the 2015 SFD and 2012 duplex fall out: 300 and 400 become (b)
    assert (out["P"], out["a_central"], out["a_as_written"], out["b"]) == (3, 0, 0, 3)
    assert math.isclose(out["k"], 1.0)


def test_no_personal_fields_requested():
    assert not set(rh.FIELDS) & rh.PERSONAL
