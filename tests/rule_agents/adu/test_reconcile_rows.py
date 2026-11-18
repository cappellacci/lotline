"""Second-coder comparison, verifier merge, and reconciled coding -> schema-valid `reforms` rows."""

import datetime as dt

import pandas as pd

from lotline.rule_agents.adu import reconcile as R
from lotline.rule_agents.adu import rows as W
from lotline.rule_agents.adu.coding import Era

from .fixtures import DAY, MIRROR, coding, date, era_2020, fv, none_era


def statuses(diffs):
    return {(d.era_key, d.field): d.status for d in diffs}


def test_identical_codings_agree():
    diffs = R.compare(coding(), coding(coder="blind"))
    assert all(d.status == "agree" for d in diffs)
    assert R.coder_agreement(diffs, verified=False) == "agree"


def test_value_difference_goes_to_verifier_and_take_b_is_applied():
    a, b = coding(), coding(coder="blind", eras=[none_era(), era_2020(sqft=1000)])
    diffs = R.compare(a, b)
    assert statuses(diffs)[("2020-07-22", "adu_max_sqft")] == "disagree"
    assert [d.field for d in R.needs_verifier(diffs)] == ["adu_max_sqft"]
    final, unresolved = R.merge(
        a, b, [R.Decision("2020-07-22", "adu_max_sqft", "b", "Sec. 5.3(c)")], "v", DAY
    )
    assert unresolved == []
    assert final.eras[1].value("adu_max_sqft") == 1000
    assert "Sec. 5.3(c)" in final.eras[1].fields["adu_max_sqft"].note
    assert R.coder_agreement(diffs, verified=True) == "adjudicated"


def test_undecided_disagreement_is_blanked_and_returned():
    a, b = coding(), coding(coder="blind", eras=[none_era(), era_2020(detached=False)])
    final, unresolved = R.merge(a, b, [], "v", DAY)
    assert [u.field for u in unresolved] == ["adu_detached_allowed"]
    assert final.eras[1].value("adu_detached_allowed") is None
    assert R.coder_agreement(R.compare(a, b), verified=False) == "single_coder"


def test_era_found_by_one_coder_only_is_a_disagreement():
    a, b = coding(eras=[era_2020()]), coding(coder="blind")
    diffs = R.compare(a, b)
    assert ("2016-01-01", "era") in statuses(diffs)
    assert statuses(diffs)[("2016-01-01", "era")] == "era_b_only"
    final, unresolved = R.merge(a, b, [R.Decision("2016-01-01", "era", "b")], "v", DAY)
    assert len(final.eras) == 2 and unresolved == []


def test_agreement_on_mirror_only_evidence_is_not_agreement():
    def mirrored():
        e = era_2020()
        e.fields["adu_max_sqft"] = fv(800, "800 sq ft", kind="mirror", url=MIRROR, confidence="medium")
        return e

    a, b = coding(eras=[mirrored()]), coding(coder="blind", eras=[mirrored()])
    diffs = R.compare(a, b)
    assert statuses(diffs)[("2020-07-22", "adu_max_sqft")] == "agree_secondary"
    assert R.coder_agreement(diffs, verified=False) == "single_coder"


def test_rows_validate_and_follow_conventions():
    df = W.to_frame(W.build(coding(), "agree", DAY))
    assert list(df["reform_id"]) == ["NC-3799999-adu-2016", "NC-3799999-adu-2020"]
    none, rule = df.iloc[0], df.iloc[1]
    assert none["adus_per_lot"] == 0 and not none["by_right"]
    assert none["coding_notes"].startswith("NO ADU RULE") and "[predates]" in none["coding_notes"]
    assert none["end_date"] == pd.Timestamp("2020-07-22")
    assert rule["supersedes"] == "NC-3799999-adu-2016"
    assert rule["adoption_date"] == pd.Timestamp("2020-07-07")
    assert rule["source_quote"] == "One accessory dwelling unit is permitted per lot."
    assert rule["coder_2"] == W.CODER_2 and rule["verified_by"] == W.VERIFIER
    assert "https://example.gov/ordinances/2020-12.pdf" in rule["source_url"].split(";")


def test_single_coder_rows_name_no_second_coder_or_verifier():
    df = W.to_frame(W.build(coding(), "single_coder"))
    assert df["coder_2"].isna().all() and df["verified_by"].isna().all()


def test_two_eras_in_one_year_get_distinct_ids():
    late = Era(
        era_id="2020b",
        component="Ord. 2020-30 raises the cap",
        dates=[date("2020-11-01")],
        fields={"adu_max_sqft": fv(1000, "shall not exceed 1,000 square feet")},
    )
    ids = [r["reform_id"] for r in W.build(coding(eras=[era_2020(), late]), "agree")]
    assert ids == ["NC-3799999-adu-2020", "NC-3799999-adu-2020b"]


def test_compare_with_config_reports_matches_and_differences():
    proposed = W.to_frame(W.build(coding(), "agree", DAY))
    existing = pd.DataFrame(
        [
            {
                "reform_id": "NC-3799999-adu-2020",
                "jurisdiction_geoid": "3799999",
                "theme": "adu",
                "effective_date": "2020-07-22",
                "adoption_date": "2020-07-07",
                "adus_per_lot": "1",
                "by_right": "True",
                "owner_occ": "False",
                "adu_detached_allowed": "True",
                "adu_max_sqft": "900",
                "parking_min_per_unit": "0",
                "min_lot_sqft": None,
            },
        ]
    )
    cmp = W.compare_with_config(proposed, existing, ["3799999"])
    by = {(r.year, r.field): r.match for r in cmp.itertuples()}
    assert by[(2020, "adu_max_sqft")] == "differs"
    assert by[(2020, "effective_date")] == "match" and by[(2020, "by_right")] == "match"
    assert by[(2016, "era")] == "era missing"
    assert dt.date(2020, 7, 22).isoformat() in set(cmp["proposed"].astype(str))


def test_rows_csv_is_accepted_by_the_shared_import(tmp_path):
    """The run's rows.csv goes through `python -m lotline.rule_agents import RUN/rows.csv reforms ST`."""
    from lotline.rule_agents.common import importer

    df = W.to_frame(W.build(coding(), "single_coder"))
    W.write_csv(df, tmp_path / "rows.csv")
    p = importer.plan(tmp_path / "rows.csv", "reforms", "NC", tmp_path / "config")
    assert len(p.added) == len(df) and not p.changed
    importer.validate_text(importer.merged_text(p), "reforms")
