"""The shared permit-to-theme classifier (D-082 §6) on hand-built rows shaped like `schemas.Permits`.

Each case states the theme a careful reader would give the permit and why; nothing here is real data.
"""

import pandas as pd
import pytest

from lotline.build import permit_theme as pt


def row(**kw):
    base = dict(
        state="TX",
        permit_id="P",
        source="synthetic_permits",
        issue_year=2025,
        issue_date=pd.Timestamp("2025-06-01"),
        building_type_std="SFD",
        adu_type=pd.NA,
        permit_class_raw=pd.NA,
        reform_flag_raw=pd.NA,
        units_new=1,
        units_removed=0,
        is_demolition=False,
        is_conversion=False,
    )
    base.update(kw)
    return base


def frame(*rows):
    df = pd.DataFrame(rows)
    df["units_new"] = df["units_new"].astype("Int64")
    for c in ("is_demolition", "is_conversion"):
        df[c] = df[c].astype("boolean")
    df["issue_year"] = df["issue_year"].astype("Int64")
    return df


# One row per case in the brief: (case, row, expected theme, expected rule)
CASES = [
    (
        "Austin post-HOME two-family permit that is a second home (ADU)",
        row(
            source="austin_permits",
            permit_id="2025-001 BP",
            building_type_std="U2",
            units_new=1,
            permit_class_raw="R- 103 Two Family Bldgs|New",
            reform_flag_raw="TWO UNIT RES",
            issue_date=pd.Timestamp("2025-03-10"),
        ),
        pt.ADU,
        "austin_home_two_unit",
    ),
    (
        "Rochester 103 house + attached ADU: the adapter's house row",
        row(
            state="MN",
            source="rochester_permits",
            permit_id="R22-1",
            building_type_std="SFD",
            units_new=1,
            permit_class_raw="Building:New:103",
        ),
        pt.OTHER,
        "other_type",
    ),
    (
        "Rochester 103 house + attached ADU: the adapter's ADU row",
        row(
            state="MN",
            source="rochester_permits",
            permit_id="R22-1-ADU",
            building_type_std="ADU",
            adu_type="attached",
            units_new=1,
            permit_class_raw="Building:New:103",
        ),
        pt.ADU,
        "adu_signal",
    ),
    (
        "A 103 filed as one U2 row that names an attached ADU (a source that does not split it)",
        row(state="MN", source="other_mn_permits", building_type_std="U2", adu_type="attached", units_new=2),
        pt.ADU,
        "adu_signal",
    ),
    (
        "A real duplex (Raleigh code 103, D-074's deviation: not an ADU)",
        row(
            state="NC",
            source="raleigh_permits",
            building_type_std="U2",
            units_new=2,
            permit_class_raw="103|New",
        ),
        pt.MM_2_4,
        "new_2_4",
    ),
    (
        "A fourplex",
        row(building_type_std="U3_4", units_new=4, permit_class_raw="104"),
        pt.MM_2_4,
        "new_2_4",
    ),
    (
        "Met Council DTQ (2-4 units, kept whole)",
        row(state="MN", source="metc_permits", building_type_std="DTQ", units_new=3),
        pt.MM_2_4,
        "new_2_4",
    ),
    (
        "A house converted to a triplex (Austin class 436)",
        row(
            source="austin_permits",
            building_type_std="OTHER",
            is_conversion=True,
            units_new=2,
            permit_class_raw="R- 436 Addn to increase housing units|Addition",
        ),
        pt.CONVERSION,
        "conversion",
    ),
    (
        "A conversion typed by its result (house → triplex as U3_4) is a conversion, not a new building",
        row(building_type_std="U3_4", is_conversion=True, units_new=2),
        pt.CONVERSION,
        "conversion",
    ),
    (
        "A garage converted into an ADU stays an ADU (ADU over conversion)",
        row(building_type_std="ADU", adu_type="internal_conversion", is_conversion=True, units_new=1),
        pt.ADU,
        "adu_signal",
    ),
    (
        "A legalized existing ADU as the parser emits it (D-080: no type, no new home)",
        row(source="fw_permits", building_type_std="UNKNOWN", units_new=0),
        pt.OTHER,
        "no_new_home",
    ),
    (
        "A legalized existing ADU typed ADU with no new home (D-080)",
        row(building_type_std="ADU", adu_type="detached", units_new=0),
        pt.OTHER,
        "legalized_adu",
    ),
    (
        "A legalized existing ADU counted as a new unit by its adapter but flagged is_legalization (D-080)",
        row(
            state="MN",
            source="rochester_permits",
            building_type_std="ADU",
            adu_type="detached",
            units_new=1,
            is_legalization=True,
        ),
        pt.OTHER,
        "legalized_adu",
    ),
    (
        "A 5+ unit building",
        row(building_type_std="MF5", units_new=24),
        pt.OTHER,
        "other_type",
    ),
    (
        "A demolition of a duplex (Austin class 646)",
        row(
            source="austin_permits", building_type_std="U2", units_new=0, units_removed=2, is_demolition=True
        ),
        pt.OTHER,
        "demolition",
    ),
    (
        "A demolition of an ADU is still a demolition",
        row(building_type_std="ADU", adu_type="detached", units_new=0, units_removed=1, is_demolition=True),
        pt.OTHER,
        "demolition",
    ),
    (
        "A new house",
        row(building_type_std="SFD", units_new=1),
        pt.OTHER,
        "other_type",
    ),
    (
        "A typed duplex with an unknown unit count is still a 2-4 building",
        row(building_type_std="U2", units_new=pd.NA),
        pt.MM_2_4,
        "new_2_4",
    ),
]


@pytest.mark.parametrize("case,r,theme,rule", CASES, ids=[c[0] for c in CASES])
def test_case(case, r, theme, rule):
    out = pt.classify(frame(r))
    assert out["permit_theme"].iloc[0] == theme, case
    assert out["theme_rule"].iloc[0] == rule, case


def test_every_row_gets_exactly_one_theme():
    df = frame(*[c[1] for c in CASES])
    out = pt.classify(df)
    assert out.index.equals(df.index)
    assert out["permit_theme"].notna().all()
    assert set(out["permit_theme"].unique()) <= set(pt.THEMES)
    # the counts add up: no permit is in two themes
    assert out["permit_theme"].value_counts().sum() == len(df)


def test_austin_two_unit_only_after_home_and_only_one_home():
    base = dict(source="austin_permits", building_type_std="U2", reform_flag_raw="TWO UNIT RES")
    df = frame(
        row(**base, units_new=1, issue_date=pd.Timestamp("2024-02-04"), issue_year=2024),  # before HOME
        row(**base, units_new=1, issue_date=pd.Timestamp("2024-02-05"), issue_year=2024),  # first day
        row(**base, units_new=2, issue_date=pd.Timestamp("2025-01-10")),  # both units at once: a duplex
        row(**base, units_new=pd.NA, issue_date=pd.Timestamp("2025-01-10")),  # unknown units: one home
        row(**dict(base, reform_flag_raw=pd.NA), units_new=1),  # no HOME use named: a duplex side
        row(**dict(base, source="raleigh_permits"), units_new=1),  # another source: no rule
        row(**dict(base, reform_flag_raw="THREE UNIT RES"), units_new=1),  # third unit: not an ADU
    )
    M, A = pt.MM_2_4, pt.ADU
    assert list(pt.permit_theme(df)) == [M, A, M, A, M, M, M]


def test_austin_year_only_row_in_home_year_counts_as_before_home():
    df = frame(row(source="austin_permits", building_type_std="U2", reform_flag_raw="two unit res ",
                   units_new=1, issue_date=pd.NaT, issue_year=2024))  # fmt: skip
    assert pt.permit_theme(df).iloc[0] == pt.MM_2_4
    df.loc[0, "issue_year"] = 2025
    assert pt.permit_theme(df).iloc[0] == pt.ADU


def test_source_rules_can_be_switched_off():
    df = frame(CASES[0][1])
    assert pt.permit_theme(df, source_rules=()).iloc[0] == pt.MM_2_4
    with pytest.raises(ValueError):
        pt.classify(df, source_rules=("no_such_rule",))


def test_optional_columns_may_be_absent():
    df = frame(row(building_type_std="U3_4", units_new=3)).drop(columns=["adu_type", "reform_flag_raw"])
    assert pt.permit_theme(df).iloc[0] == pt.MM_2_4


def test_adu_signal_matches_the_adu_fit_and_mm_types_match_estimate_mm():
    """The classifier's ADU test is the ADU fit's `_is_adu`, and its 2-4 types are estimate_mm's, so wiring
    it in changes counts only through precedence and source rules, not through a different definition."""
    from lotline.model import estimate_mm
    from lotline.model.scenarios import adu

    assert pt.MM_TYPES == estimate_mm.MM_TYPES
    df = frame(*[c[1] for c in CASES])
    out = pt.classify(df)
    assert (out["theme_rule"] == "adu_signal").sum() <= adu._is_adu(df).sum()
    assert (adu._is_adu(df) | (out["theme_rule"] != "adu_signal")).all()


def test_precedence_order_is_documented():
    assert [name for name, _ in pt.RULES] == [
        "demolition", "legalized_adu", "no_new_home", "adu_signal", "austin_home_two_unit", "conversion",
        "new_2_4", "other_type",
    ]  # fmt: skip
    for name, _ in pt.RULES:
        assert f"`{name}`" in pt.__doc__
