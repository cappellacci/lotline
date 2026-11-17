# ruff: noqa: E501  (hand-worked examples)
"""Items -> schema-valid fee rows; reconciliation; human tasks; comparison (synthetic places only)."""

from datetime import date

import pandas as pd
import pytest

from lotline.rule_agents.fees import build, compare, handoff, reconcile


def _items(make_item):
    return [
        make_item(
            item_id="p1",
            basis_kind="valuation_table",
            amount=None,
            bracket_base=1302.5,
            bracket_start=100_000,
            bracket_end=500_000,
            rate_per_1000=7.40,
            building_type="OTHER",
            fee_type="Building permit (valuation table)",
            quote="$1,302.50 for the first $100,000.00",
        ),
        make_item(
            item_id="p2",
            basis_kind="share_of",
            amount=None,
            pct=65,
            share_of="p1",
            building_type="OTHER",
            fee_type="Plan review",
            pays_for="plan_review",
            quote="Plan review 65% of permit fee",
        ),
        make_item(
            item_id="w1",
            fee_type="Water impact fee, area A",
            pays_for="water",
            amount=4749,
            group_id="saws",
            group_kind="area",
            quote="Low $4,749",
        ),
        make_item(
            item_id="w2",
            fee_type="Water impact fee, area B",
            pays_for="water",
            amount=4908,
            group_id="saws",
            group_kind="area",
            quote="Middle $4,908",
        ),
        make_item(
            item_id="w3",
            fee_type="Water impact fee, area C",
            pays_for="water",
            amount=5100,
            group_id="saws",
            group_kind="area",
            quote="Upper $5,100",
        ),
        make_item(
            item_id="e1",
            basis_kind="excluded",
            amount=None,
            fee_type="Escrow",
            applies_when="refundable escrow",
        ),
        make_item(
            item_id="s1", fee_type="Park fee", pays_for="parks", amount=8000, quote_status="summariser"
        ),
        make_item(
            item_id="z1",
            fee_type="School impact fee",
            pays_for="schools",
            amount=0,
            quote="School impact fee, see Table 2",
        ),
    ]


def test_build_prices_groups_and_validates(make_item, protos):
    res = build.build(_items(make_item), protos)
    rows = res.rows.set_index("notes").sort_index()
    out = build.validate(res.rows)
    assert len(out) == 6  # p1, p2, three group rows, z1; escrow excluded; summariser row to low
    by = res.rows.set_index(res.rows["notes"].str.extract(r"item=(\w+)", expand=False))
    assert by.loc["p1", "amount_per_unit_usd"] == 3189.50
    assert by.loc["p2", "amount_per_unit_usd"] == 2073.18  # 65% of the priced parent, rounded
    assert by.loc["p1", "fee_component"] == "permit" and by.loc["w2", "fee_component"] == "water_sewer"
    # group: the median area is central and carries the range; the others are blank
    assert by.loc["w2", "amount_per_unit_usd"] == 4908
    assert (by.loc["w2", "amount_per_unit_low_usd"], by.loc["w2", "amount_per_unit_high_usd"]) == (4749, 5100)
    assert pd.isna(by.loc["w1", "amount_per_unit_usd"]) and pd.isna(by.loc["w3", "amount_per_unit_usd"])
    assert [i.item_id for i in res.excluded] == ["e1"]
    assert len(res.low_rows) == 1 and pd.isna(res.low_rows.loc[0, "source_quote"])
    assert any("z1" in w and "amount 0" in w for w in res.warnings)
    assert "conf=medium" in by.loc["p1", "notes"] and "date_basis=effective_date" in by.loc["p1", "notes"]
    assert rows.shape[0] == 6


def test_schedule_year(make_item):
    assert build.schedule_year(make_item(effective_date=date(2026, 7, 1))) == (2026, "effective_date")
    assert build.schedule_year(make_item(effective_date=None, fiscal_year_start=date(2025, 10, 1)))[0] == 2025
    assert build.schedule_year(make_item(effective_date=None, schedule_label="FY2025-26")) == (
        2025,
        "fy_label_range",
    )
    assert build.schedule_year(make_item(effective_date=None, schedule_label="FY2027"))[0] == 2026
    assert build.schedule_year(make_item(effective_date=None, schedule_label="2026 fee schedule"))[0] == 2026
    assert build.schedule_year(make_item(effective_date=None))[1] == "read_date"


def test_duplicate_names_from_two_bodies_get_the_body(make_item, protos):
    items = [
        make_item(item_id="a", fee_type="Connection charge", pays_for="water", levying_body="City water"),
        make_item(item_id="b", fee_type="Connection charge", pays_for="sewer", levying_body="Regional sewer"),
    ]
    res = build.build(items, protos)
    build.validate(res.rows)
    assert sorted(res.rows["fee_type"]) == [
        "Connection charge (City water)",
        "Connection charge (Regional sewer)",
    ]


def test_reconcile(make_item):
    c1 = [
        make_item(item_id="a1", amount=1828.0),
        make_item(item_id="a2", fee_type="Sewer tap", pays_for="sewer", amount=3892),
        make_item(item_id="a3", fee_type="Park fee", pays_for="parks", amount=500),
    ]
    c2 = [
        make_item(item_id="b1", amount=1828.4, coder="c2"),  # within $1
        make_item(item_id="b2", fee_type="Sewer capacity", pays_for="sewer", amount=6116, coder="c2"),
        make_item(item_id="b3", fee_type="Plumbing", pays_for="trade_permit", amount=90, coder="c2"),
    ]
    pairs = reconcile.pair(c1, c2)
    got = {(p["coder1"], p["coder2"]): p["outcome"] for p in pairs}
    # a3's key (parks) has no partner; b3 (trade_permit -> permit) pairs only if a1 is taken, so it is left over
    assert got[("a1", "b1")] == "agree"
    assert got[("a2", "b2")] == "differ"
    assert got[("a3", None)] == "only_coder1"
    assert got[(None, "b3")] == "only_coder2"
    merged = reconcile.merge(c1, c2, pairs, date(2026, 11, 17))
    v = {i.item_id: i.verified_by for i in merged}
    assert v == {"a1": reconcile.VERIFIER, "a2": None, "a3": None, "b3": None}


def test_summariser_never_verifies(make_item):
    c1 = [make_item(item_id="a1", quote_status="summariser")]
    c2 = [make_item(item_id="b1", coder="c2")]
    merged = reconcile.merge(c1, c2, reconcile.pair(c1, c2), date(2026, 11, 17))
    assert merged[0].verified_by is None


def _task(**kw):
    base = dict(
        state="TX",
        place_name="Fort Worth",
        place_geoid="4827000",
        levying_body="Fort Worth Water",
        body_kind="utility",
        component="water_sewer",
        pays_for="water",
        reason="http_403_waf",
        start_url="https://www.fortworthtexas.gov/impact-fees",
        look_for="Water impact fee per service unit",
        priority=1,
    )
    base.update(kw)
    return base


def test_tasks_roundtrip_and_ingest(tmp_path):
    t = handoff.make_task(1, **_task())
    assert t.task_id == "FEES-TX-4827000-01"
    with pytest.raises(ValueError):
        handoff.make_task(2, **_task(reason="records_request_only"))  # Ben files no records requests
    with pytest.raises(ValueError):
        handoff.make_task(2, **_task(reason="call_staff"))
    done = t.model_copy(
        update={
            "status": "done",
            "answer_amount": 3500.0,
            "answer_quote": "Water $3,500 per SU",
            "answer_basis_kind": "per_lue",
            "answer_units_per_dwelling": 1.0,
            "answered_by": "BC",
            "answered_date": date(2026, 11, 18),
            "answer_page_or_section": "Table 1",
        }
    )
    path = tmp_path / "human_tasks.csv"
    handoff.write_csv([t, done], path)
    back = handoff.read_csv(path)
    assert back[1].answer_amount == 3500.0
    items = handoff.answers_to_items(back)
    assert len(items) == 1 and items[0].coder == "human:BC" and items[0].body_kind == "utility"
    assert items[0].has_evidence()
    assert "FEES-TX-4827000-01" in handoff.to_markdown(back)


def test_compare():
    def frame(rows):
        return pd.DataFrame(
            rows,
            columns=[
                "jurisdiction_geoid",
                "year",
                "fee_component",
                "building_type_std",
                "amount_per_unit_usd",
                "fee_type",
            ],
        )

    existing = frame(
        [
            ("1", 2025, "permit", "SFD", 900.0, "a"),
            ("1", 2026, "permit", "SFD", 1000.0, "b"),
            ("1", 2026, "water_sewer", "SFD", 5000.0, "c"),
            ("2", 2026, "impact", "SFD", 7.0, "z"),
        ]
    )
    run = frame(
        [
            ("1", 2026, "permit", "SFD", 1010.0, "b"),
            ("1", 2026, "water_sewer", "SFD", 4000.0, "c"),
            ("1", 2026, "impact", "SFD", 300.0, "p"),
        ]
    )
    c = compare.compare(run, existing, ["1"]).set_index("fee_component")["status"].to_dict()
    assert c == {"impact": "run_only", "permit": "match", "water_sewer": "differ"}
