# ruff: noqa: E501  (plain-language strings and notes)
"""Fee items -> `fees` rows: classify, price at the prototype, apply the group rule, check, validate.

Every number in a row is reproducible from the items file and config/params/proforma.yaml. Rows that do not
have read evidence (quote_status verbatim or image_read) or are rated low go to a separate frame for a person.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

import pandas as pd

from lotline.rule_agents.common.evidence import max_confidence
from lotline.rule_agents.fees import classify, groups
from lotline.rule_agents.fees.prototype import BASIS, Priced, Prototype, building_fee, price, prototypes
from lotline.rule_agents.fees.records import READ, FeeItem

_ZERO_OK = re.compile(
    r"exempt|waive|no (impact |system development |capacity )?fee|not (charged|required)|\$0\b|none", re.I
)
_FY = re.compile(r"FY\s*(\d{4})(?:\s*[-/]\s*(\d{2,4}))?", re.I)
_YEAR = re.compile(r"\b(19[7-9]\d|20\d\d)\b")


def schedule_year(item: FeeItem) -> tuple[int | None, str]:
    """(year, date_basis): the calendar year the schedule took effect (fees README; LESSONS D1)."""
    if item.effective_date:
        return item.effective_date.year, "effective_date"
    if item.fiscal_year_start:
        return item.fiscal_year_start.year, "fiscal_year_start"
    label = item.schedule_label or ""
    m = _FY.search(label)
    if m:
        if m.group(2):  # "FY2025-26": the fiscal year starts in the first year
            return int(m.group(1)), "fy_label_range"
        return int(m.group(1)) - 1, "fy_label_end_year_assumed"  # "FY2027" names the year it ends
    m = _YEAR.search(label)
    if m:
        return int(m.group(1)), "schedule_label"
    if item.retrieved_at:
        return item.retrieved_at.year, "read_date"
    return None, "unknown"


def price_all(items: Iterable[FeeItem], protos: dict[str, Prototype] | None = None) -> dict[str, Priced]:
    """Price every item; `share_of` items after their parent, at the child's prototype."""
    protos = protos or prototypes()
    items = list(items)
    by_id = {i.item_id: i for i in items}
    out: dict[str, Priced] = {}
    for it in items:
        proto = protos[it.building_type]
        parent_fee = None
        if it.basis_kind == "share_of":
            parent = by_id.get(it.share_of)
            if parent is not None:
                grand = by_id.get(parent.share_of) if parent.basis_kind == "share_of" else None
                gfee = building_fee(grand, proto) if grand else None
                parent_fee = building_fee(parent, proto, gfee)
        out[it.item_id] = price(it, proto, parent_fee)
    return out


_RANK = {"low": 0, "medium": 1, "high": 2}


def confidence(item: FeeItem) -> str:
    """The shared cap (`common.evidence.max_confidence`: high needs a primary source with a machine-found or
    person-read quote), and for fees high also needs the blind second coder's agreement (`verified_by`). A
    confidence the coder set can lower this, never raise it. By hand: fee_schedule + verbatim + verified ->
    high; same, unverified -> medium; mirror + verbatim + verified -> medium; no quote -> low."""
    if not item.has_evidence():
        return "low"
    cap = max_confidence(item.evidence())
    got = "high" if cap == "high" and item.verified_by else ("medium" if cap != "low" else "low")
    if item.confidence and _RANK[item.confidence] < _RANK[got]:
        return item.confidence
    return got


@dataclass
class BuildResult:
    rows: pd.DataFrame
    low_rows: pd.DataFrame
    excluded: list[FeeItem]
    warnings: list[str] = field(default_factory=list)


def build(items: Iterable[FeeItem], protos: dict[str, Prototype] | None = None) -> BuildResult:
    items = [i for i in items]
    protos = protos or prototypes()
    priced = price_all(items, protos)
    warnings: list[str] = []

    # group rule: only the central member keeps its per-unit amount, with the group's range
    central: dict[str, tuple[float, float]] = {}
    blank_in_group: dict[str, str] = {}
    members = defaultdict(list)
    for it in items:
        if it.group_id and priced[it.item_id].amount_per_unit is not None:
            members[(it.place_geoid, it.building_type, it.group_id)].append(it)
    for mem in members.values():
        amounts = [priced[m.item_id].amount_per_unit for m in mem]
        idx = groups.central_index(amounts, mem[0].group_kind, [m.cohort_start for m in mem])
        lo, hi = groups.group_range(amounts)
        for j, m in enumerate(mem):
            if j == idx:
                central[m.item_id] = (lo, hi)
            else:
                blank_in_group[m.item_id] = mem[idx].item_id

    rows, low, excluded = [], [], []
    for it in items:
        if it.basis_kind == "excluded":
            excluded.append(it)
            continue
        p = priced[it.item_id]
        comp, flag = classify.check(it.pays_for, it.fee_type)
        if flag:
            warnings.append(f"{it.item_id}: {flag}")
        year, date_basis = schedule_year(it)
        if year is None:
            warnings.append(f"{it.item_id}: no date at all; not written")
            continue
        per_unit, lo, hi = p.amount_per_unit, p.low, p.high
        how = p.how
        if it.item_id in central:
            lo, hi = central[it.item_id]
            how += f"; central row of group {it.group_id} ({it.group_kind}), range ${lo:,.2f}-${hi:,.2f}"
        elif it.item_id in blank_in_group:
            how += f"; group member, central row is {blank_in_group[it.item_id]}"
            per_unit, lo, hi = None, None, None
        if per_unit == 0 and not _ZERO_OK.search(it.quote or ""):
            warnings.append(f"{it.item_id}: amount 0 without a quote saying the fee is waived or not charged")
        conf = confidence(it)
        tokens = [
            f"body={it.levying_body} ({it.body_kind})",
            f"conf={conf}",
            f"quote_status={it.quote_status}",
            f"date_basis={date_basis}",
            f"coder={it.coder}",
            f"item={it.item_id}",
        ]
        text = "; ".join(tokens) + f". Rule {p.rule}: {how}."
        if it.applies_when:
            text += f" Applies: {it.applies_when}."
        if it.notes:
            text += f" {it.notes}"
        row = {
            "state": it.state,
            "jurisdiction_geoid": it.place_geoid,
            "year": year,
            "effective_date": it.effective_date,
            "in_force_through": it.in_force_through,
            "fee_component": comp,
            "fee_type": it.fee_type,
            "building_type_std": it.building_type,
            "basis": BASIS[it.basis_kind],
            "amount_usd": it.amount if it.amount is not None else it.bracket_base,
            "amount_per_unit_usd": None if per_unit is None else round(per_unit, 2),
            "amount_per_unit_low_usd": None if lo is None else round(lo, 2),
            "amount_per_unit_high_usd": None if hi is None else round(hi, 2),
            "pct_of_value": it.pct if it.basis_kind == "pct_of_value" else None,
            "dollar_year": year,
            "payment_timing": it.payment_timing,
            "source": it.url or "",
            "source_section": it.page_or_section,
            "source_quote": it.quote if it.quote_status in READ else None,
            "verified_by": it.verified_by,
            "verified_date": it.verified_date,
            "notes": text,
        }
        (low if conf == "low" else rows).append(row)

    df, low_df = _frame(rows), _frame(low)
    key = ["jurisdiction_geoid", "year", "fee_component", "fee_type", "building_type_std", "basis"]
    if not df.empty:
        dup = df.duplicated(key, keep=False)
        df.loc[dup, "fee_type"] = (
            df.loc[dup, "fee_type"]
            + " ("
            + df.loc[dup, "notes"].str.extract(r"body=([^;(]+)", expand=False).str.strip()
            + ")"
        )
        warnings += _mixed_other(df)
    return BuildResult(df, low_df, excluded, warnings)


def _frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for c in ("effective_date", "verified_date"):
        df[c] = pd.to_datetime(df[c])
    for c in ("year", "dollar_year", "in_force_through"):
        df[c] = df[c].astype("Int64")
    return df


def _mixed_other(df: pd.DataFrame) -> list[str]:
    """A type row for a component replaces the place's OTHER rows of that component in fee_levels (LESSONS N6)."""
    out = []
    for (g, comp), sub in df.groupby(["jurisdiction_geoid", "fee_component"]):
        types = set(sub["building_type_std"])
        if "OTHER" in types and types & {"U2", "U3_4", "ADU"}:
            out.append(
                f"{g} {comp}: OTHER rows next to plex/ADU rows; fee_levels uses the type rows only for those types"
            )
    return out


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """The `fees` schema check (raises pandera SchemaErrors listing every failure)."""
    from lotline.schemas import validate as _validate

    return _validate(df, "fees")
