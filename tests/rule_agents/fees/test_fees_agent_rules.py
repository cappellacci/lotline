# ruff: noqa: E501  (hand-worked examples)
"""Component taxonomy, the group rule, and fee items on the shared core (LESSONS T1, D4, R1-R5).

robots.txt, block detection and the word-for-word quote rule are tested with the shared core
(tests/rule_agents/common/test_rule_core.py)."""

from datetime import date

import pytest

from lotline.rule_agents.fees import classify, groups


@pytest.mark.parametrize(
    "pays_for,name,comp,flagged",
    [
        (
            "water",
            "Water impact fee, lots platted after 2023-10-01",
            "water_sewer",
            False,
        ),  # TX: water, not impact
        ("sewer", "Sewer permit fee", "water_sewer", False),  # Columbus
        ("sewer", "Metropolitan SAC charge", "water_sewer", False),
        ("parks", "Park dedication cash-in-lieu - single family", "impact", False),
        ("stormwater", "Stormwater SDC, general capacity", "impact", False),
        ("plan_review", "Building permit plan review", "permit", False),
        ("conditional_use", "Conditional use permit application", "planning", False),  # planning words win
        ("parks", "Building permit", "impact", True),
        ("something_new", "Technology fee", "other", True),
    ],
)
def test_component(pays_for, name, comp, flagged):
    got, flag = classify.check(pays_for, name)
    assert got == comp
    assert (flag is not None) == flagged


def test_area_group_median():
    # odd count: the middle row (SAWS-like elevation areas)
    assert groups.central_index([4749, 4908, 5100], "area") == 1
    # even count: median 250 is equally near 200 and 300 -> the lower one (Ben, 2026-10-30)
    assert groups.central_index([400, 300, 200, 100], "area") == 2
    assert groups.group_range([400, 300, 200, 100]) == (100, 400)


def test_plat_date_group_newest():
    starts = [date(2007, 10, 1), date(2023, 10, 1), date(2015, 1, 1)]
    assert groups.central_index([1100, 4800, 2000], "plat_date", starts) == 1
    with pytest.raises(ValueError):
        groups.central_index([1, 2], "plat_date", [None, date(2020, 1, 1)])


def _stored(tmp_path, name, body):
    from lotline.rule_agents.common.docstore import DocStore

    docs = DocStore(tmp_path)
    p = docs.data_root / "raw" / "rule_docs" / "2026-11-17" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body if isinstance(body, bytes) else body.encode())
    rec = docs.ingest(p, url=f"https://city.example.gov/{name}", added_by="run:fees:t", category="fees")
    return docs, rec


def test_quote_checked_against_the_document_store(tmp_path, make_item):
    from lotline.rule_agents.fees.cli import check_quote

    docs, rec = _stored(
        tmp_path, "fees.html", "<html><script>x()</script><p>Water&nbsp;tap fee: $1,828</p></html>"
    )
    ok = make_item(item_id="ok", quote="Water tap fee: $1,828", doc_id=rec.doc_id, quote_status="not_checked")
    bad = make_item(item_id="bad", quote="Water tap fee: $1,900", doc_id=rec.doc_id, quote_status="verbatim")
    assert check_quote(ok, docs)[0] == "verbatim"
    assert check_quote(bad, docs)[0] == "not_checked"  # an unmatched verbatim claim is held back


def test_damaged_pdf_leaves_quote_unchecked(tmp_path, make_item):
    from lotline.rule_agents.fees.cli import check_quote

    pdf = tmp_path / "s.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")  # damaged: no crash
    it = make_item(item_id="p", quote="anything", quote_status="verbatim", local_path=str(pdf))
    status, note = check_quote(it, None)
    assert status == "image_read" and "unreadable" in note


def test_old_item_files_still_load(make_item):
    from lotline.rule_agents.fees.records import FeeItem

    base = make_item(item_id="o").model_dump(mode="json", exclude_none=True)
    base.pop("doc_id", None)
    old = {**base, "sha256": "a" * 64, "quote_status": "summariser", "source_kind": "official"}
    it = FeeItem.model_validate(old)
    assert (it.doc_id, it.quote_status, it.source_kind) == ("a" * 64, "not_checked", "search_summary")
    assert FeeItem.model_validate({**base, "source_kind": "wayback"}).source_kind == "archive"


def test_evidence_and_confidence_use_the_shared_cap(make_item):
    from lotline.rule_agents.fees.build import confidence

    it = make_item(item_id="c")  # fee_schedule, verbatim quote
    assert it.evidence()[0].source_kind == "fee_schedule"
    assert confidence(it) == "medium"  # unverified
    assert confidence(it.model_copy(update={"verified_by": "rules-fees-second-coder"})) == "high"
    mirror = it.model_copy(update={"verified_by": "x", "source_kind": "mirror"})
    assert confidence(mirror) == "medium"  # a mirror never reaches high
    assert confidence(it.model_copy(update={"verified_by": "x", "confidence": "low"})) == "low"
