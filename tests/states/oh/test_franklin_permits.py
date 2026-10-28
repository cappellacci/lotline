"""Franklin County Auditor permits adapter on synthetic fixtures (no network, no real data).

Checks the methodology in the module docstring: each named ADU rule on a hand-written description, trade
permits marking the permit they cite, one ADU per parcel in two years, placement through the parcel roll
(with the taxing-district fallback), Columbus left to `columbus_permits`, and that load() runs the holdout
filter.
"""

import pandas as pd
import pytest

from lotline import registry
from lotline.adapters.states.oh import franklin_permits as fp
from lotline.schemas import assert_conforms
from lotline.validation import holdout

COLUMBUS, BEXLEY, WESTERVILLE = "3918000", "3906278", "3983342"


@pytest.mark.parametrize(
    ("text", "permit_no", "expected"),
    [
        # ADU_NOUN + ADU_CREATE
        ("CONVERSION OF A DETACHED GARAGE INTO AN ADU UNIT", "RB2025-1", True),
        (
            "Build 2 story frame, 1 family carriage house, 1 bedroom, council variance 1249-2015",
            "1521063",
            True,
        ),
        # the shared parser would call these new ADUs; the named rules don't
        ("REPL A/C - CARRIAGE HOUSE", "12279", False),  # no creation verb
        ("DEMOLITION OF A 360 SQ FT ACCESSORY DWELLING (GARAGE)", "RSWD1610951", False),
        # CARRIAGE_LIVING: a carriage house without living space is a garage
        ("NEW DUPLEX AND CARRIAGE HOUSE (DETACHED GARAGE).", "PR2025000127001", False),
        (
            "ADDITION TO CREATE A 3-CAR CARRIAGE HOUSE WITH A FULL BATHROOM AND OFFICE ABOVE",
            "RBLD1808418",
            False,
        ),
        ("CONSTRUCT 2 STY FRM CARRIAGE HOUSE, LIVING SPACE ABOVE GARAGE", "CBLD1529934", True),
        ("NEW CARRIAGE HOUSE W/ LQ", "2350", True),
        # NEW_BUILDING_PERMIT: a Columbus new residential building permit needs no verb
        ("CARRIAGE HOUSE WITH LIVING AREA ON 2ND FLOOR", "RBLD1627250", True),
        ("CARRIAGE HOUSE WITH LIVING AREA ON 2ND FLOOR", "ALTR1627250", False),
        # IN_LAW_UNIT: an in-law suite needs a kitchen, bedroom, fire separation or garage
        ("ADD MOTHER IN LAW SUITE", "910322", False),
        ("ADDITION OF A 4 CAR GARAGE WITH 2 BEDROOM IN-LAW SUITE ABOVE", "RBLD2562", True),
        ("BUILDING NEW 1-HOUR SEPARATED IN-LAW SUITE ADDITION", "ADDR2522466", True),
        # EXISTING_WORK, and the CONVERSION exception
        ("ALTER 2 STORY CARRIAGE HOUSE TO RENOVATE INTERIOR, NEW KITCHEN", "RBLD1806870", False),
        ("ALTER EXISTING ROOF, NEW CARRIAGE HOUSE SHINGLES, KITCHEN", "RSWDR2609176", False),
        (
            "BUILD 2 STORY FRAME, 1 FAMILY DWELLING, 2 BEDROOMS, CARRIAGE HOME STYLE SINGLE FAMILY",
            "NEWR1900804",
            False,
        ),
        ("ALTERATION OF THE EXISTING ATTACHED GARAGE, TURNING IT INTO AN IN-LAW SUITE", "22120140", True),
        # PROJECT_BUILDING: a home in a new development
        ("BUILDING 3 SUITE 102 - 2BDRM ONE FAMILY CARRIAGE HOUSE WITH 2 CAR GARAGE", "B20230323", False),
    ],
)
def test_named_adu_rules(text, permit_no, expected):
    assert fp.describes_new_adu(fp.clean_text(text), permit_no) is expected


def test_columbus_boilerplate_is_dropped_before_reading():
    t = fp.clean_text(
        "PLAN APPROVAL: FINAL USE/OCCUPANCY GROUP: 1, 2, 3 FAMILY DWELLING "
        "DESCRIPTION OF WORK: Build a 2 story frame"
    )
    assert t == "BUILD A 2 STORY FRAME"


@pytest.mark.parametrize(
    ("text", "own", "trade"),
    [
        (
            "BUILDING PERMIT/PLAN REVIEW: NEWR2006370 INSTALL GAS LINES TO CARRIAGE HOUSE",
            "MMEPR2107202",
            True,
        ),
        ("NEW GAS TO CARRIAGE HOUSE RBLD1516827", "FSUP1533889", True),  # cites a permit number
        ("734 JAEGER ST ADDING SEPARATE 200 AMP SERVICE AT CARRIAGE HOUSE", "14014", True),  # amperage
        (
            "RUN NEW DEDICATED LINE TO WALL HEATER GARAGE APARTMENT MLS",
            "1521259",
            True,
        ),  # Columbus MLS suffix
        ("WIRE NEW CARRIAGE HOUSE", "EM1", True),  # starts with a trade word
        ("BUILD 2 STORY FRAME, 1 FAMILY CARRIAGE HOUSE", "RBLD1806542", False),
        ("BUILD A CARRIAGE HOUSE PER PERMIT RBLD1806542", "RBLD1806542", False),  # its own number
    ],
)
def test_trade_permits(text, own, trade):
    assert fp.is_trade(fp.clean_text(text), own) is trade


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("NEW CARRIAGE HOUSE WITH KITCHEN", "detached"),
        ("CONVERSION OF A DETACHED GARAGE INTO AN ADU", "detached"),
        ("ADD SINGLE CAR GARAGE WITH IN-LAW SUITE, KITCHEN AND BEDROOM", "attached"),
        ("NEW GARAGE APARTMENT", "detached"),
        ("CONVERT BASEMENT INTO AN ACCESSORY DWELLING UNIT", "internal_conversion"),
        ("NEW ACCESSORY DWELLING UNIT", "unknown"),
    ],
)
def test_adu_kind(text, kind):
    assert fp.adu_kind(text) == kind


def _raw(rows) -> pd.DataFrame:
    return pd.DataFrame(
        rows, columns=["PARCEL ID", "PERMDT", "PERMITNUM", "PERMITTYPE", "AMOUNT", "DESCRIPTION"]
    )


RAW = _raw(
    [
        # Westerville: a new ADU, then a revision of the same unit a year later (not a new ADU)
        (
            "080-000001-00",
            "2025-07-21",
            "RB2025-112",
            None,
            40000,
            "CONVERSION OF A DETACHED GARAGE INTO AN ADU UNIT",
        ),
        (
            "080-000001-00",
            "2026-05-01",
            "RB2026-007",
            None,
            0,
            "NEW ADU UNIT IN DETACHED GARAGE, REVISED PLANS",
        ),
        # ... and the same permit repeated in the next snapshot (one row kept)
        (
            "080-000001-00",
            "2025-07-21",
            "RB2025-112",
            None,
            40000,
            "CONVERSION OF A DETACHED GARAGE INTO AN ADU UNIT",
        ),
        # Bexley: a parent alteration whose own text says nothing, marked by its plumbing permit
        (
            "020-000005-00",
            "2021-06-08",
            "ADDR2121229",
            None,
            90000,
            "ALTER A 2 STORY FRAME, 1 FAMILY DWELLING",
        ),
        (
            "020-000005-00",
            "2021-08-01",
            "PMEPR2446555",
            None,
            0,
            "BUILDING PERMIT/PLAN REVIEW: ADDR2121229 NEW CARRIAGE HOUSE FULL BATH, KITCHEN",
        ),
        # Bexley, parcel split after the roll: placed by its taxing district (020 is all Bexley)
        ("020-000099-00", "2024-01-09", "BX24-1", None, 0, "NEW ACCESSORY DWELLING UNIT ABOVE THE GARAGE"),
        # Columbus: flagged, but left to columbus_permits
        (
            "010-000002-00",
            "2019-03-08",
            "ALTR1901906",
            None,
            0,
            "ALTERATION OF EXISTING DETACHED GARAGE TO BECOME AN ACCESSORY DWELLING UNIT WITH A KITCHEN",
        ),
        # not ADUs: a trade permit's own row, a garage, a field note without a permit number, a typo date
        ("080-000003-00", "2022-02-02", "EL22-9", "ELEC", 0, "WIRE NEW CARRIAGE HOUSE"),
        ("080-000004-00", "2022-02-02", "RB22-10", None, 0, "NEW CARRIAGE HOUSE (DETACHED GARAGE)"),
        (
            "080-000005-00",
            "2022-02-02",
            None,
            None,
            0,
            "REALTOR REPORTS ONE OF THE GARAGES IS USED AS A GUEST HOUSE",
        ),
        ("080-000006-00", "3020-09-02", "RB30-1", None, 0, "NEW ACCESSORY DWELLING UNIT"),
    ]
)
PARCELS = pd.DataFrame(
    {
        "parcel_id": [
            "39049080-000001",
            "39049020-000005",
            "39049020-000006",
            "39049010-000002",
            "39049080-000003",
        ],
        "county_geoid": "39049",
        "jurisdiction_geoid": [WESTERVILLE, BEXLEY, BEXLEY, COLUMBUS, WESTERVILLE],
    }
)


@pytest.fixture
def permits() -> pd.DataFrame:
    return fp.build(RAW, PARCELS)


def test_build_conforms_and_keeps_adus_outside_columbus(permits):
    assert_conforms(permits, "permits")
    assert set(permits["permit_id"]) == {"FRA-080-RB2025-112", "FRA-020-ADDR2121229", "FRA-020-BX24-1"}
    assert (permits["building_type_std"] == "ADU").all() and (permits["units_new"] == 1).all()
    assert (permits["type_confidence"] == "inferred").all() and (
        permits["source"] == "franklin_permits"
    ).all()
    assert COLUMBUS not in set(permits["jurisdiction_geoid"])


def test_trade_permit_marks_its_parent(permits):
    row = permits.set_index("permit_id").loc["FRA-020-ADDR2121229"]
    assert row.jurisdiction_geoid == BEXLEY and row.issue_date == pd.Timestamp("2021-06-08")


def test_one_adu_per_parcel_in_two_years():
    flags = fp.adu_flags(RAW)
    westerville = flags[flags["parcel"] == "080-000001-00"]
    assert westerville["permit_no"].tolist() == ["RB2025-112"]  # the 2026 revision is the same unit
    two = _raw(
        [
            ("080-000007-00", "2021-01-05", "RB21-1", None, 0, "NEW ACCESSORY DWELLING UNIT"),
            (
                "080-000007-00",
                "2022-12-01",
                "RB22-1",
                None,
                0,
                "NEW ACCESSORY DWELLING UNIT",
            ),  # 695 days: same
            (
                "080-000007-00",
                "2023-02-01",
                "RB23-1",
                None,
                0,
                "NEW ACCESSORY DWELLING UNIT",
            ),  # 757 days: new
        ]
    )
    assert fp.adu_flags(two)["permit_no"].tolist() == ["RB21-1", "RB23-1"]


def test_parcel_key_and_district_fallback(permits):
    assert fp.parcel_key(pd.Series(["010-000002-00", "bad"])).tolist()[0] == "39049010-000002"
    assert pd.isna(fp.parcel_key(pd.Series(["bad"])).iloc[0])
    split = permits.set_index("permit_id").loc["FRA-020-BX24-1"]
    assert split.jurisdiction_geoid == BEXLEY and split.parcel_id == "39049020-000099"
    _, by_district = fp.jurisdiction_lookup(PARCELS)
    assert by_district["020"] == BEXLEY and by_district["080"] == WESTERVILLE


def test_columbus_flags_are_available_to_columbus_permits():
    flags = fp.adu_flags(RAW)
    assert "ALTR1901906" in set(flags["permit_no"])
    assert flags.set_index("permit_no").loc["ALTR1901906", "adu_type"] == "detached"


def test_descriptions_are_not_stored(permits):
    assert "DESCRIPTION" not in permits.columns and "text" not in permits.columns


def test_load_applies_holdout_filter(monkeypatch):
    class Store:
        def read(self, state, table):
            return PARCELS

    monkeypatch.setattr(fp, "download", lambda store, refresh=False: RAW)
    calls = []
    real_apply = holdout.apply

    def spy(df, state, **kw):
        calls.append((state, kw))
        return real_apply(df, state, **kw)

    monkeypatch.setattr(fp.holdout, "apply", spy)
    out = fp.load("OH", Store())
    assert calls and calls[0][1]["geoid_col"] == "jurisdiction_geoid"
    holdout.assert_no_leak(out, "permits", "OH")


def test_load_needs_parcels():
    class Store:
        def read(self, state, table):
            return None

    with pytest.raises(RuntimeError, match="oh_parcels"):
        fp.load("OH", Store())


def test_registered_as_oh_source():
    assert "franklin_permits" in registry.sources_for("OH")
