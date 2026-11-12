"""Date tags on coded rules (model/rule_tags.py) and how both panels read them: synthetic rows only."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lotline.build import eligible as eligible_rule
from lotline.config import CONFIG_DIR
from lotline.model import estimate_adu, estimate_mm, rule_tags
from lotline.model.scenarios import adu

COLUMNS = list(pd.read_csv(CONFIG_DIR / "reforms" / "mn.csv", nrows=0).columns)
PANEL = list(range(2016, 2026))


def reforms(*rows: dict) -> pd.DataFrame:
    """Coded reforms with the real CSV columns (blank where a row doesn't say) and parsed dates."""
    df = pd.DataFrame([{c: r.get(c, np.nan) for c in COLUMNS} for r in rows], columns=COLUMNS)
    for col in ("announced_date", "adoption_date", "effective_date", "end_date"):
        df[col] = pd.to_datetime(df[col])
    df["jurisdiction_geoid"] = df["jurisdiction_geoid"].astype(str)
    return df


def row(geoid, theme, effective, notes="", adopted="same", **kw) -> dict:
    return {
        "reform_id": f"MN-{geoid}-{theme}-{effective[:4]}",
        "state": "MN",
        "jurisdiction_geoid": geoid,
        "theme": theme,
        "status": "in_force",
        "adoption_date": effective if adopted == "same" else adopted,
        "effective_date": effective,
        "coding_notes": notes,
        "coverage": "Citywide",
        **kw,
    }


# ---------------------------------------------------------------------------------------------------------
# The helper
# ---------------------------------------------------------------------------------------------------------


def test_flags_by_hand():
    r = reforms(
        row(
            "1",
            "adu",
            "2018-05-01",
            "[earliest-known] effective_date is the earliest ... [predates] the rule",
        ),
        row("2", "adu", "2018-05-01", adopted=None),  # blank adoption date
        row("3", "adu", "2018-05-01", "DATE UNCONFIRMED: no signed ordinance found"),
        row("4", "adu", "2018-05-01", adus_per_lot=0),  # "no ADUs"
        row("5", "missing_middle", "2018-05-01", unit_cap=1),  # one home per lot
        row("6", "missing_middle", "2018-05-01", unit_cap=2),
        row("7", "adu", "2018-05-01", status="repealed"),
    )
    f = rule_tags.flags(r)
    assert f["predates"].tolist() == [True, False, False, False, False, False, False]
    assert f["earliest_known"].tolist() == [True, True, False, False, False, False, False]
    assert f["unconfirmed"].tolist() == [False, False, True, False, False, False, False]
    assert f["none_row"].tolist() == [False, False, False, True, True, False, False]
    assert f["event"].tolist() == [False, True, True, False, False, True, False]
    assert not f["before_window"].any()


def test_placeholder_dates_before_the_window():
    r = reforms(
        row("1", "missing_middle", "2010-01-01", "[earliest-known] placeholder", unit_cap=2),
        row("2", "missing_middle", "2010-01-01", adopted=None, unit_cap=2),  # blank adoption date
        row("3", "missing_middle", "2010-01-01", unit_cap=2),  # a firm date of 2010-01-01 stays an event
        row("4", "missing_middle", "2010-01-02", "[earliest-known]", unit_cap=2),  # inside the window
    )
    f = rule_tags.flags(r)
    assert f["before_window"].tolist() == [True, True, False, False]
    assert f["event"].tolist() == [False, False, True, True]
    out = rule_tags.apply(r)
    assert (out.loc[[0, 1], "effective_date"] == rule_tags.ALWAYS_IN_FORCE).all()
    assert out.loc[2, "effective_date"] == out.loc[3, "effective_date"] - pd.Timedelta(days=1)
    assert rule_tags.dropped_places(r, range(2010, 2026), ["earliest_known"]) == {"4"}


def test_apply_moves_predates_rows_before_any_panel():
    r = reforms(
        row("1", "adu", "2021-03-01", "[predates] older code", announced_date="2020-11-01"),
        row("2", "adu", "2021-03-01", "[earliest-known]"),
    )
    out = rule_tags.apply(r)
    assert out.loc[0, "effective_date"] == out.loc[0, "adoption_date"] == pd.Timestamp("1990-01-01")
    assert pd.isna(out.loc[0, "announced_date"])
    assert out.loc[1, "effective_date"] == pd.Timestamp("2021-03-01")  # other rows unchanged
    assert r.loc[0, "effective_date"] == pd.Timestamp("2021-03-01")  # the input is not modified
    pd.testing.assert_frame_equal(rule_tags.apply(out), out)  # applying twice changes nothing


def test_dropped_places_window_by_hand():
    r = reforms(
        row("1", "adu", "2018-05-01", "[earliest-known]"),  # inside the panel -> dropped
        row("2", "adu", "2015-06-30", "[earliest-known]"),  # in force on 1 July 2015: all panel long -> kept
        row("3", "adu", "2015-07-02", "[earliest-known]"),  # first counts on 1 July 2016 -> dropped
        row("4", "adu", "2025-07-02", "[earliest-known]"),  # after the last 1 July -> kept
        row("5", "adu", "2019-01-01", "[earliest-known] [predates]"),  # never an event -> kept
        row("6", "adu", "2019-01-01", adopted=None, adus_per_lot=0),  # a "none" row -> kept
        row("7", "adu", "2019-01-01", "DATE UNCONFIRMED"),
        row("8", "adu", "2019-01-01"),  # firm date
    )
    assert rule_tags.dropped_places(r, PANEL, ["earliest_known"]) == {"1", "3"}
    assert rule_tags.dropped_places(r, PANEL, ["unconfirmed"]) == {"7"}
    assert rule_tags.dropped_places(r, PANEL, ["earliest_known", "unconfirmed"]) == {"1", "3", "7"}
    assert rule_tags.dropped_places(r, PANEL) == set()  # the main run drops nothing
    with pytest.raises(ValueError, match="unknown tag sensitivity"):
        rule_tags.dropped_places(r, PANEL, ["firm"])


# ---------------------------------------------------------------------------------------------------------
# The D-024 panel (estimate_mm.build_panel)
# ---------------------------------------------------------------------------------------------------------

FIRM, PRE, EK, UNCONF, NONE_ = "2700011", "2700012", "2700013", "2700014", "2700015"
PLACES = [FIRM, PRE, EK, UNCONF, NONE_]
YEARS = list(range(2014, 2022))


class FakeStore:
    def __init__(self, tables: dict[str, pd.DataFrame]):
        self.tables = tables

    def read(self, state: str, table: str):
        return self.tables.get(table).copy() if table in self.tables else None


def store() -> FakeStore:
    juris = pd.DataFrame(
        {
            "state": "MN",
            "geoid": PLACES,
            "name": PLACES,
            "kind": "place",
            "pop_2020": 50000,
            "county_geoid": "27053",
        }
    )
    elig = pd.DataFrame(
        [
            {"state": "MN", "jurisdiction_geoid": g, "year": 2016, "theme": th,
             "rule_version": eligible_rule.RULE_VERSION, "eligible_parcels": 1000, "data_tier": 1,
             "denominator_source": "parcels", "denominator_quality": "high"}
            for g in PLACES
            for th in ("adu", "missing_middle")
        ]
    )  # fmt: skip
    bps = pd.DataFrame(
        [
            {"geoid": g, "year": yr, "units_1": 10, "units_2": 2, "units_3_4": 0, "units_5p": 5, "bldgs_2": 1,
             "bldgs_3_4": 0}
            for g in PLACES
            for yr in range(2008, 2026)
        ]
    )  # fmt: skip
    yrs = range(2005, 2026)
    market = pd.DataFrame(
        {"geo": "national:US", "year": list(yrs), "cpi_u": [100.0] * len(yrs),
         "mortgage_rate": [4.0] * len(yrs), "ppi_resid_inputs": [100.0] * len(yrs)}
    )  # fmt: skip
    acs = pd.DataFrame(
        [
            {"geo": f"place:{g}", "end_year": yr, "table_id": v[:6], "variable": v, "label": "",
             "estimate": e, "moe": 0.0}
            for g in PLACES
            for yr in range(2010, 2024)
            for v, e in (("B25064_001", 1200.0), ("B25077_001", 3e5), ("B25003_001", 1000.0 + yr))
        ]
    )  # fmt: skip
    permits = pd.DataFrame(
        {"source": "src", "jurisdiction_geoid": PLACES, "issue_year": 2019, "building_type_std": "ADU",
         "adu_type": None, "units_new": 1}
    )  # fmt: skip
    return FakeStore(
        {"jurisdictions": juris, "eligible_parcels": elig, "bps_place_year": bps, "market_geo_year": market,
         "acs_geo_year": acs, "permits": permits}
    )  # fmt: skip


def tagged(theme: str, **none_fields) -> pd.DataFrame:
    """One rule per place: firm 2019, [predates] dated 2019, [earliest-known] 2019, DATE UNCONFIRMED 2019,
    and a "none" row."""
    rule = {"by_right": "True", "unit_cap": 3} if theme == "missing_middle" else {"by_right": "True"}
    return reforms(
        row(FIRM, theme, "2019-01-01", **rule),
        row(PRE, theme, "2019-01-01", "[predates] code rewrite", **rule),
        row(EK, theme, "2019-01-01", "[earliest-known]", **rule),
        row(UNCONF, theme, "2019-01-01", "DATE UNCONFIRMED", **rule),
        row(NONE_, theme, "2019-01-01", **none_fields),
    )


def test_mm_panel_reads_the_tags():
    p = estimate_mm.build_panel(
        store(), states=("MN",), years=YEARS, reforms={"MN": tagged("missing_middle", unit_cap=1)}
    )
    d = p.data.drop_duplicates("place").set_index("place")
    assert d.loc[FIRM, "T"] == d.loc[EK, "T"] == d.loc[UNCONF, "T"] == 2019  # events at their coded date
    assert d.loc[PRE, "T"] == 1990 and d.loc[PRE, "status"] == "treated"  # in force before the panel
    pre = p.data[p.data["place"] == PRE]
    assert np.allclose(pre["dose"], 2 / 3)  # treated in every panel year, 2014 included
    assert np.isnan(d.loc[NONE_, "T"]) and d.loc[NONE_, "status"] == "coded_not_treated"  # a control
    assert p.excluded["dropped by tag sensitivity"] == []


@pytest.mark.parametrize(
    "drop, gone",
    [
        (["earliest_known"], {EK}),
        (["unconfirmed"], {UNCONF}),
        (["earliest_known", "unconfirmed"], {EK, UNCONF}),
    ],
)
def test_mm_panel_tag_sensitivities(drop, gone):
    p = estimate_mm.build_panel(
        store(),
        states=("MN",),
        years=YEARS,
        reforms={"MN": tagged("missing_middle", unit_cap=1)},
        drop_tags=drop,
    )
    assert set(p.excluded["dropped by tag sensitivity"]) == gone
    assert set(p.data["place"]) == set(PLACES) - gone


# ---------------------------------------------------------------------------------------------------------
# The D-025 panel (estimate_adu.build_panel)
# ---------------------------------------------------------------------------------------------------------


@pytest.fixture
def adu_rules(monkeypatch):
    rules = {"MN": tagged("adu", adus_per_lot=0)}
    monkeypatch.setattr(adu, "load_reforms", lambda st: rules.get(st, reforms()))


def test_adu_panel_reads_the_tags(adu_rules):
    p = estimate_adu.build_panel("MN", store(), years=PANEL, geoids=PLACES)
    d = p.data.drop_duplicates("place").set_index("place")
    assert d.loc[FIRM, "T"] == d.loc[EK, "T"] == d.loc[UNCONF, "T"] == 2019
    assert d.loc[PRE, "T"] == d.loc[PRE, "T_announce"] == 1990  # announced with its (moved) adoption
    assert (p.data.loc[p.data["place"] == PRE, "dose"] > 0).all()  # in force all panel long
    assert np.isnan(d.loc[NONE_, "T"]) and (p.data.loc[p.data["place"] == NONE_, "dose"] == 0).all()
    assert p.excluded_by_tags == []


def test_adu_panel_tag_sensitivities(adu_rules):
    p = estimate_adu.build_panel("MN", store(), years=PANEL, geoids=PLACES, drop_tags=["earliest_known"])
    assert p.excluded_by_tags == [EK] and EK not in set(p.data["place"])
    p = estimate_adu.build_panel("MN", store(), years=PANEL, geoids=PLACES, drop_tags=["unconfirmed"])
    assert p.excluded_by_tags == [UNCONF] and set(p.data["place"]) == set(PLACES) - {UNCONF}


# ---------------------------------------------------------------------------------------------------------
# D-082 §1 (proposed): tags count only on the event-setting row
# ---------------------------------------------------------------------------------------------------------

EVENTS = range(2013, 2026)  # D-042's event window


def _oregon_city(geoid, cap_row_adopted="2021-07-01", cap_notes=""):
    """A dated (or not) cap-4 row and a blank-dated, capless SB 458 land-division row (as or.csv)."""
    return [
        row(geoid, "missing_middle", "2021-08-01", cap_notes, adopted=cap_row_adopted, unit_cap=4),
        row(geoid, "missing_middle", "2022-06-30", adopted=None, lot_split=True,
            reform_id=f"OR-{geoid}-missing_middle-2022-landdiv"),
    ]  # fmt: skip


def test_cap_in_force_and_event_setting_rows_by_hand():
    r = reforms(
        row("1", "missing_middle", "2010-01-01", "[predates]", unit_cap=2),
        row("1", "missing_middle", "2021-08-01", unit_cap=4, reform_id="cap4"),
        row("1", "missing_middle", "2022-06-30", adopted=None, reform_id="landdiv"),
    )
    r = rule_tags.apply(r)
    assert rule_tags.cap_in_force(r, 2021) == 2  # the cap-4 row starts after 1 July 2021
    assert rule_tags.cap_in_force(r, 2022) == 4
    assert rule_tags.event_setting_rows(r, EVENTS) == [1]  # the cap-4 row, never the capless one
    assert rule_tags.cap_in_force(r, 2022, {"cap4": 0.3}) == 1  # under half the parcels: not counted
    assert rule_tags.event_setting_rows(r.iloc[[0, 2]], EVENTS) == []  # the cap never rises


def test_event_setting_row_rule_keeps_oregon_land_division_places():
    r = reforms(
        *_oregon_city("1"),  # dated cap row, blank-dated land division -> kept under D-082
        *_oregon_city("2", cap_row_adopted=None),  # the cap row itself is blank-dated -> dropped
        *_oregon_city("3", cap_notes="DATE UNCONFIRMED"),
        *_oregon_city("4", cap_notes="[earliest-known] earliest source"),
    )
    old = rule_tags.dropped_places(r, PANEL, ["earliest_known"])
    assert old == {"1", "2", "3", "4"}  # the D-024 reading: a blank date anywhere drops every place
    new = rule_tags.dropped_places(r, EVENTS, ["earliest_known"], rule="event_setting_row")
    assert new == {"2", "4"}
    assert rule_tags.dropped_places(r, EVENTS, ["unconfirmed"], rule="event_setting_row") == {"3"}
    assert rule_tags.dropped_places(r, EVENTS, [], rule="event_setting_row") == set()
    with pytest.raises(ValueError, match="unknown drop rule"):
        rule_tags.dropped_places(r, EVENTS, ["unconfirmed"], rule="first")


def test_event_setting_row_ignores_tags_on_the_prior_rule():
    # A tag on the row in force before the event doesn't drop the place; on the event row it does
    r = reforms(
        row("1", "missing_middle", "2016-03-01", "[earliest-known]", unit_cap=2, reform_id="a"),
        row("1", "missing_middle", "2021-08-01", unit_cap=4, reform_id="b"),
    )
    # first rise is 2016 (1 -> 2), set by the tagged row, so the place is dropped
    assert rule_tags.dropped_places(r, EVENTS, ["earliest_known"], rule="event_setting_row") == {"1"}
    # with the cap-2 row before the window, the first in-window rise is 2022, set by the firm row
    assert (
        rule_tags.dropped_places(r, range(2017, 2026), ["earliest_known"], rule="event_setting_row") == set()
    )


def test_standards_flag_always_allowed_and_none_places():
    r = reforms(
        row("1", "missing_middle", "2023-11-27", "[standards] MUR route", unit_cap=4),
        row("2", "missing_middle", "2021-03-01", "[predates] older code", unit_cap=2),
        row("3", "missing_middle", "2010-01-01", "[earliest-known] placeholder", unit_cap=3),
        row("4", "missing_middle", "2010-01-01", "[predates]", unit_cap=1),
        row("5", "missing_middle", "2021-03-01", unit_cap=4),
        row("6", "missing_middle", "2015-01-01", unit_cap=1),
        row("7", "missing_middle", "2015-01-01", unit_cap=1),
        row("7", "missing_middle", "2022-01-01", unit_cap=2),
        row("8", "missing_middle", "2015-01-01"),  # blank cap
    )
    assert rule_tags.flags(r)["standards"].tolist() == [True] + [False] * 8
    assert rule_tags.always_allowed_places(r) == {"2", "3"}
    assert rule_tags.none_places(r) == {"4", "6"}
