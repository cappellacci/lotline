"""Coding checks (every value cites evidence; conventions enforced) and the effective-date rules."""

import datetime as dt

import pytest
from pydantic import ValidationError

from lotline.rule_agents.adu import coding as C
from lotline.rule_agents.adu import dates as D

from .fixtures import MIRROR, coding, date, era_2020, ev, fv, none_era


def test_a_well_formed_coding_passes():
    assert C.check(coding()) == []


def test_round_trip_through_json(tmp_path):
    C.dump(coding(), tmp_path / "x.json")
    assert C.load(tmp_path / "x.json") == coding()


def test_value_without_evidence_is_refused():
    era = era_2020()
    era.fields["owner_occ"] = C.FieldValue(value=True, evidence=[])
    assert any("owner_occ = True has no evidence" in p for p in C.check(coding(eras=[era])))


def test_mirror_only_value_cannot_be_high_confidence():
    era = era_2020()
    era.fields["adu_max_sqft"] = fv(800, "800 square feet", kind="mirror", url=MIRROR, confidence="high")
    assert any("secondary sources only" in p for p in C.check(coding(eras=[era])))
    era.fields["adu_max_sqft"].confidence = "medium"
    assert C.check(coding(eras=[era])) == []


def test_wrong_types_are_refused():
    era = era_2020()
    era.fields["by_right"] = fv("yes")
    era.fields["adus_per_lot"] = fv(1.5)
    probs = C.check(coding(eras=[era]))
    assert any("by_right must be true/false" in p for p in probs)
    assert any("adus_per_lot must be a whole number" in p for p in probs)


def test_no_adu_era_cannot_be_by_right_and_moratorium_is_a_no_adu_era():
    era = none_era()
    era.fields["by_right"] = fv(True)
    assert any("cannot have by_right = true" in p for p in C.check(coding(eras=[era])))
    mor = era_2020()
    mor.tags = ["[moratorium]"]
    assert any("[moratorium] era is coded as 'no ADUs'" in p for p in C.check(coding(eras=[mor])))
    with pytest.raises(ValidationError):
        C.Era(era_id="m", component="x", status="suspended", dates=[date("2025-05-19")])


def test_unknown_tag_and_duplicate_era_and_empty_era():
    a, b = era_2020(), era_2020()
    a.tags = ["[made-up]"]  # unknown
    empty = C.Era(era_id="e", component="x", dates=[date("2021-01-01")])
    probs = C.check(coding(eras=[a, b, empty]))
    assert any("unknown tag" in p for p in probs)
    assert any("duplicate era_id" in p for p in probs)
    assert any("no field coded" in p for p in probs)


def test_evidence_must_be_https_and_quote_at_most_300_chars():
    with pytest.raises(ValidationError):
        ev("x", url="http://example.gov/code")
    with pytest.raises(ValidationError):
        ev("x" * 301)


def test_block_reasons_must_come_from_the_task_vocabulary():
    c = coding()
    c.blocked = [C.BlockedSource(url="https://x.gov", reason="not_tried", what_to_look_for="x")]
    assert any("unknown reason 'not_tried'" in p for p in C.check(c))
    c.blocked[0].reason = "known_blocker"
    assert C.check(c) == []


def test_outcome_consistency():
    assert C.check(coding(eras=[])) == ["outcome 'coded' needs at least one era"]
    c = coding()
    c.outcome = "no_usable_source"
    assert "outcome 'no_usable_source' must not carry eras" in C.check(c)


# ---- dates ----------------------------------------------------------------------------------------------


def test_effective_date_beats_adoption():
    r = D.resolve([date("2020-07-07", "adopted"), date("2020-07-22", "effective")])
    assert (r.effective, r.adoption, r.tags) == (dt.date(2020, 7, 22), dt.date(2020, 7, 7), [])


def test_adoption_only_is_coded_as_effective_and_flagged():
    r = D.resolve([date("2019-09-03", "vote")])
    assert r.effective == r.adoption == dt.date(2019, 9, 3)
    assert r.tags == ["DATE UNCONFIRMED"]
    assert "coded as the adoption date" in r.rule


def test_adopted_preferred_over_vote_for_adoption_date():
    r = D.resolve([date("2019-09-03", "vote"), date("2019-09-17", "adopted")])
    assert r.adoption == dt.date(2019, 9, 17)


def test_bound_before_window_is_predates_at_window_start():
    r = D.resolve([date("2012-03-01", "codified")])
    assert r.effective == D.WINDOW_START and r.tags == ["[predates]"] and r.adoption is None


def test_recodification_inside_window_is_earliest_known_not_predates():
    r = D.resolve([date("2019-05-20", "codified"), date("2021-01-01", "first_seen")])
    assert r.effective == dt.date(2019, 5, 20) and r.tags == ["[earliest-known]"]
    assert "first-allowed date open" in r.rule


def test_conflicting_effective_dates_are_reported():
    r = D.resolve([date("2025-12-24", "effective"), date("2025-12-25", "effective")])
    assert r.effective == dt.date(2025, 12, 24) and "2025-12-25" in r.conflict


def test_month_precision_goes_to_first_of_month_and_is_noted():
    r = D.resolve([date("2022-09-15", "effective", precision="month")])
    assert r.effective == dt.date(2022, 9, 1) and "month only" in r.rule


def test_prior_state_is_dated_at_window_start_not_on_the_reform_day():
    r = D.resolve([date("2020-07-07", "prior_to")])
    assert r.effective == D.WINDOW_START and r.tags == ["[predates]"]
    old = D.resolve([date("2012-03-01", "prior_to")])
    assert old.effective == dt.date(2012, 2, 29)


def test_coders_cannot_set_date_quality_tags():
    era = era_2020()
    era.tags = ["[predates]"]
    assert any("set by the date rules" in p for p in C.check(coding(eras=[era])))


def test_announced_only_cannot_date_an_era():
    with pytest.raises(ValueError):
        D.resolve([date("2024-01-01", "announced")])
