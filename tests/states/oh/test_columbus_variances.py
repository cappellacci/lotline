"""Columbus Council variance adapter on synthetic Legistar titles (no network, no real data).

Checks the methodology in the module docstring: each named rule, each exclusion, the variance-number id and
passed date, one row per variance, that titles are never stored, and that load() runs the holdout filter.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.oh import columbus_variances as cv
from lotline.schemas import assert_conforms
from lotline.validation import holdout

LEAD = "To grant a Variance from the provisions of Sections 3332.039, R-4, Residential District use, for the "
LEAD += "property located at 1 EXAMPLE STREET (43201), "


@pytest.mark.parametrize(
    ("clause", "expected"),
    [
        (
            "to permit a single-unit dwelling (a carriage house) on the rear of a lot developed with a "
            "single-unit dwelling in the R-4, Residential District (Council Variance #CV19-030).",
            ("carriage_house", "detached"),
        ),
        (
            "to allow two single-unit dwellings on one lot with reduced development standards in the R-3, "
            "Residential District (Council Variance #CV24-060).",
            ("two_houses_one_lot", "detached"),
        ),
        (
            "to permit a three-unit dwelling and a single-family dwelling above a garage on a lot zoned in "
            "the R-4, Residential District.",
            ("above_garage_dwelling", "detached"),
        ),
        (
            "to allow habitable space above a detached garage in the R-2F, Residential District "
            "(Council Variance #CV23-061).",
            ("habitable_space_above_garage", "detached"),
        ),
        # conform + permit: the new dwelling counts
        (
            "to conform an existing single-family dwelling and permit a second single-family dwelling "
            "(carriage house) on one lot in the R-4, Residential District.",
            ("carriage_house", "detached"),
        ),
        # exclusions
        ("to conform two single-unit dwellings on one lot in the R-3, Residential District.", None),
        (
            "to permit two single-unit dwellings on one lot with a reduced building line in the M, "
            "Manufacturing District (Council Variance # CV14-052).",
            None,
        ),
        (
            "to conform an existing single-unit dwelling and permit a three-unit dwelling (carriage house) "
            "on the same lot in the R-4, Residential District.",
            None,
        ),
        (
            "to permit two mixed-use buildings and one rear single-unit dwelling on two lots in the R-4, "
            "Residential District.",
            None,
        ),
        ("to permit a single-unit dwelling in the C-4, Commercial District (CV10-012).", None),
        ("to permit a restaurant in the C-4, Commercial District.", None),
    ],
)
def test_named_rules_and_exclusions(clause, expected):
    assert cv.classify(LEAD + clause, "Passed", "2020-01-01T00:00:00") == expected


@pytest.mark.parametrize(
    ("status", "passed"), [("Defeated", "2014-03-03"), ("Passed", None), ("Tabled", "2020")]
)
def test_only_passed_ordinances_count(status, passed):
    title = LEAD + "to allow two single-unit dwellings on one lot in the R-3, Residential District."
    assert cv.classify(title, status, passed) is None


def test_repealed_variances_do_not_count():
    title = LEAD + (
        "to permit two single-unit dwellings on one lot in the R-2F, Residential District (Council Variance "
        "# CV17-054). (REPEALED BY ORD. 1592-2018)"
    )
    assert cv.classify(title, "Passed", "2017-06-01") is None


def _raw(rows):
    return pd.DataFrame(rows, columns=cv.FIELDS.split(","))


RAW = _raw(
    [
        (
            1,
            "0001-2019",
            LEAD + "to permit a carriage house in the R-4, Residential District (Council "
            "Variance #CV19-033).",
            "2019-06-27T00:00:00",
            "Passed",
        ),
        # re-passed under a new ordinance with the same variance number: the first passage stays
        (
            2,
            "0002-2020",
            LEAD + "to permit a carriage house in the R-4, Residential District (Council "
            "Variance #CV19-033).",
            "2020-02-05T00:00:00",
            "Passed",
        ),
        (
            3,
            "0003-2008",
            LEAD + "to permit a second single-family dwelling in the R-2F, Residential District.",
            "2008-01-16T00:00:00",
            "Consent",
        ),
        (
            4,
            "0004-2021",
            LEAD + "to permit a restaurant in the C-4, Commercial District.",
            "2021-01-01T00:00:00",
            "Passed",
        ),
    ]
)


def test_build_rows():
    out = cv.build(RAW).set_index("permit_id")
    assert_conforms(out.reset_index(), "permits")
    assert list(out.index) == ["ORD-0003-2008", "CV-19-033"]
    row = out.loc["CV-19-033"]
    assert row.issue_date == pd.Timestamp("2019-06-27") and row.issue_year == 2019
    assert row.jurisdiction_geoid == cv.COLUMBUS_GEOID and row.zoning_raw == "R-4"
    assert row.building_type_std == "ADU" and row.units_new == 1 and row.type_confidence == "inferred"
    assert row.permit_class_raw == "council variance: carriage_house (Ord. 0001-2019)"
    assert out.loc["ORD-0003-2008", "adu_type"] == "unknown"  # second_dwelling: type not stated


def test_titles_are_not_stored():
    out = cv.build(RAW)
    assert not any(out[c].astype(str).str.contains("EXAMPLE STREET").any() for c in out.columns)


def test_page_url_requests_only_the_needed_fields():
    url = cv.page_url(1000)
    assert "%24skip=1000" in url and "%24top=1000" in url
    assert "MatterTitle" in url and "Sponsor" not in url


def test_load_applies_holdout_filter(monkeypatch):
    monkeypatch.setattr(cv, "download", lambda store, refresh=False: RAW)
    calls = []
    real_apply = holdout.apply

    def spy(df, state, **kw):
        calls.append(kw)
        return real_apply(df, state, **kw)

    monkeypatch.setattr(cv.holdout, "apply", spy)
    out = cv.load("OH", store=None)
    assert calls and calls[0]["geoid_col"] == "jurisdiction_geoid"
    assert_conforms(out, "permits")
    holdout.assert_no_leak(out, "permits", "OH")


def test_registered_as_oh_source():
    assert "columbus_variances" in registry.sources_for("OH")
