"""First-pass scoring: only weak values get a blind second look; targeted merges compare only those fields."""

import datetime as dt

import pytest

from lotline.rule_agents.adu import reconcile as R
from lotline.rule_agents.adu import score as S
from lotline.rule_agents.adu.coding import Blocker, Evidence, FieldValue
from lotline.rule_agents.common.docstore import DocStore

from .fixtures import CODE, ORD, coding, era_2020, none_era
from .test_fetch import tiny_pdf

CODE_TXT = (
    "Sec. 5.3. One accessory dwelling unit is permitted per lot. "
    "ADUs are a permitted use subject to Sec. 5.3. "
    "Owner occupancy is not required. An ADU may be attached or detached. An ADU shall not exceed 800 square "
    "feet. No additional parking is required for an ADU. Permitted uses in R-1: single-family dwelling. "
    "History: effective 2012-03-01."
)
PAD = " Text continues." * 14  # a text PDF page has at least SCAN_CHARS_PER_PAGE characters
ORD_PAGES = [
    "History: effective 2012-03-01. Ordinance 2020-12, effective 2020-07-07 on adoption." + PAD,
    "Updated: effective 2020-07-22" + PAD,
]


@pytest.fixture
def docs(tmp_path):
    """A document store holding the code page (HTML) and the two-page ordinance PDF."""
    d = DocStore(tmp_path)
    (tmp_path / "code.html").write_text(f"<html><body><p>{CODE_TXT}</p></body></html>")
    (tmp_path / "ord.pdf").write_bytes(tiny_pdf(ORD_PAGES))
    d.code = d.ingest(tmp_path / "code.html", url=CODE, added_by="test").doc_id
    d.ord = d.ingest(tmp_path / "ord.pdf", url=ORD, added_by="test").doc_id
    return d


def cached(c, docs):
    """Point every evidence item at the stored copies (code page or ordinance PDF)."""
    for era in c.eras:
        for fv in era.fields.values():
            for e in fv.evidence:
                e.doc_id = docs.code
        for d in era.dates:
            for e in d.evidence:
                e.doc_id = docs.ord if e.source_kind == "ordinance" else docs.code
    return c


def test_strong_values_need_no_second_look(docs):
    card = S.score(cached(coding(), docs), docs, audit_rate=0)
    assert card.looks == [] and card.mode == "none"
    assert card.strong == 6 + 1  # six compared 2020 fields + the no-ADU era's adus_per_lot


def test_weak_reasons_secondary_low_confidence_missing_and_unchecked_quotes(docs):
    c = cached(coding(), docs)
    era = c.eras[1]
    era.fields["adu_max_sqft"].confidence = "medium"
    era.fields["owner_occ"].evidence[0].source_kind = "mirror"
    era.fields["by_right"].evidence[0].quote = "ADUs need a special use permit"
    era.fields["adus_per_lot"].evidence[0].quote_status = "image_read"
    card = S.score(c, docs, audit_rate=0)
    reasons = {lk.field: lk.reasons for lk in card.looks if lk.era_key == "2020-07-22"}
    assert reasons["adu_max_sqft"] == ["confidence medium"]
    assert reasons["owner_occ"] == ["no primary source"]
    assert reasons["by_right"] == ["quote not found in the cached source"]
    assert reasons["adus_per_lot"][0].startswith("quote not machine-checked")
    assert card.mode == "targeted"
    assert {"adu_max_sqft", "owner_occ", "by_right", "effective_date", "adoption_date"} <= set(card.fields)


def test_pdf_quote_must_be_on_the_page_the_coder_named(docs):
    e = Evidence(
        url=ORD,
        retrieved=dt.date(2026, 11, 17),
        quote="effective 2020-07-22",
        source_kind="ordinance",
        doc_id=docs.ord,
        page=2,
    )
    assert S.quote_check(e, docs) == ("found", 2)
    assert S.quote_check(e.model_copy(update={"page": 1}), docs) == ("missing", 2)
    assert S.quote_check(e.model_copy(update={"doc_id": None}), docs) == ("unchecked", None)


def test_unconfirmed_date_is_weak(docs):
    c = cached(coding(eras=[none_era(), era_2020()]), docs)
    c.eras[1].dates = [d for d in c.eras[1].dates if d.type == "adopted"]  # adoption only
    card = S.score(c, docs, audit_rate=0)
    eff = [lk for lk in card.looks if lk.field == "effective_date" and lk.era_key == "2020-07-07"]
    assert eff and "DATE UNCONFIRMED" in eff[0].reasons


def test_silent_core_field_is_looked_at_but_deliberate_and_rule_blanks_are_not(docs):
    c = cached(coding(), docs)
    del c.eras[1].fields["owner_occ"]  # not addressed at all
    c.eras[1].fields["adu_max_sqft"] = FieldValue(value=None, note="greater of 800 or 40%: a floor (L-F5)")
    card = S.score(c, docs, audit_rate=0)
    silent = {
        (lk.era_key, lk.field) for lk in card.looks if lk.reasons == ["not addressed and no blocked source"]
    }
    assert silent == {("2020-07-22", "owner_occ")}  # not min_lot_sqft/coverage_zones, not the no-ADU era
    c.blocked = [Blocker(url="https://x.gov/p", kind="http_403_waf", fields=["owner_occ"], look_for="x")]
    assert S.score(c, docs, audit_rate=0).looks == []


def test_uncoded_amendment_from_the_scout_triggers_a_look(docs):
    sources = {
        "sources": [
            {
                "url": "https://x.gov/o-2022-41.pdf",
                "what": "Ord. 2022-41 (ADU size cap)",
                "kind": "ordinance",
            },
            {"url": "https://x.gov/o-2020-12.pdf", "what": "Ord. 2020-12", "kind": "ordinance"},
            {"url": "https://x.gov/news", "what": "news story", "kind": "news", "dates_seen": ["2023-01-01"]},
        ]
    }
    card = S.score(cached(coding(), docs), docs, sources, audit_rate=0)
    assert len(card.uncoded_amendments) == 1 and "2022-41" in card.uncoded_amendments[0]
    assert card.mode == "targeted"


def test_audit_sample_is_reproducible_and_near_the_rate(tmp_path):
    picks = [S.in_audit(f"37{i:05d}") for i in range(2000)]
    assert picks == [S.in_audit(f"37{i:05d}") for i in range(2000)]
    assert 0.07 < sum(picks) / 2000 < 0.13
    assert S.score(coding(), DocStore(tmp_path), audit_rate=1).mode == "full"
    assert S.score(coding(eras=[]), DocStore(tmp_path), audit_rate=1).mode == "none"


def test_targeted_merge_compares_only_scoped_fields_but_keeps_new_eras():
    a = coding()
    b = coding(coder="claude-rules-adu-blind", eras=[none_era(), era_2020(sqft=900, detached=False)])
    b.eras[1].fields = {k: v for k, v in b.eras[1].fields.items() if k == "adu_max_sqft"}
    scope = {"adu_max_sqft", "effective_date", "adoption_date"}
    diffs = R.compare(a, b, scope)
    assert {d.field for d in diffs} <= scope | {"era"}
    sqft = [d.status for d in diffs if d.field == "adu_max_sqft" and d.era_key == "2020-07-22"]
    assert sqft == ["disagree"]
    # an unscoped field B left blank is not a difference, and A's value survives the merge
    final, unresolved = R.merge(a, b, [], "v", dt.date(2026, 11, 17), scope)
    assert final.eras[1].value("adu_detached_allowed") is True
    assert final.eras[1].value("adu_max_sqft") is None and len(unresolved) == 1
    assert R.coder_agreement(R.compare(a, a, scope), verified=False, targeted=True) == "single_coder"
    assert R.coder_agreement(diffs, verified=True, targeted=True) == "adjudicated"
