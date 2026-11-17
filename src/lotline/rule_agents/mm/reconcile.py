"""Compare two blind coders' findings for one place, field by field.

Rules are paired by effective year (the reform_id year), then by nearest effective date. The reconciler
agent only adjudicates the `Diff`s this returns; fields both coders agree on pass straight through.
Tolerances follow the Oct-Nov 2026 second-coder practice (docs/build/rule-agents/mm/LESSONS.md): dates
must match to the day, except that adoption dates within 7 days are a "minor" difference (minutes vs signed
ordinance), and zone lists are compared as sets after normalising "R-1"/"R1".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lotline.rule_agents.mm.findings import KEY_FIELDS, PlaceFinding, RuleFinding


@dataclass(frozen=True)
class Diff:
    rule_key: str  # effective year, or "unpaired"
    field: str
    a: object
    b: object
    severity: str  # "major" (changes the event or dose) or "minor"


def _zones(z: list[str]) -> frozenset[str]:
    return frozenset(re.sub(r"[\s\-_.]", "", s).upper() for s in z)


def pair(
    a: list[RuleFinding], b: list[RuleFinding]
) -> tuple[list[tuple[RuleFinding, RuleFinding]], list[RuleFinding], list[RuleFinding]]:
    """Pairs by effective date (nearest first, within 3 years), plus the rules left unpaired in a and in b."""
    left = list(a)
    right = list(b)
    pairs = []
    cands = sorted(
        (
            (abs((x.effective_date - y.effective_date).days), i, j)
            for i, x in enumerate(left)
            for j, y in enumerate(right)
        ),
    )
    used_i: set[int] = set()
    used_j: set[int] = set()
    for d, i, j in cands:
        if i in used_i or j in used_j or d > 3 * 366:
            continue
        pairs.append((left[i], right[j]))
        used_i.add(i)
        used_j.add(j)
    only_a = [x for i, x in enumerate(left) if i not in used_i]
    only_b = [y for j, y in enumerate(right) if j not in used_j]
    return pairs, only_a, only_b


def compare(fa: PlaceFinding, fb: PlaceFinding) -> list[Diff]:
    """Every disagreement between two findings of the same place. By hand: coder A cap 3 effective
    2020-01-01, coder B cap 3 effective 2020-01-01 adopted 2019-11-08 vs A's 2019-11-12 -> one minor
    adoption_date diff; B adds a 2023 rule A lacks -> one major 'unpaired' diff."""
    if fa.jurisdiction_geoid != fb.jurisdiction_geoid:
        raise ValueError("findings are for different places")
    pairs, only_a, only_b = pair(fa.rules, fb.rules)
    out: list[Diff] = []
    for x, y in pairs:
        key = str(x.effective_date.year)
        for f in KEY_FIELDS:
            va, vb = getattr(x, f), getattr(y, f)
            if f == "coverage_zones":
                if _zones(va) != _zones(vb) and va and vb:
                    out.append(Diff(key, f, sorted(va), sorted(vb), "minor"))
                continue
            if va == vb:
                continue
            sev = "major"
            if f == "adoption_date" and va and vb and abs((va - vb).days) <= 7:
                sev = "minor"
            if f == "by_right" and (va is None or vb is None):
                sev = "minor"  # one coder left it blank
            if x.unit_cap == 1 and y.unit_cap == 1 and f in ("effective_date", "adoption_date", "date_basis"):
                sev = "minor"  # two "none" rows: a control, never an event, so its date moves nothing
            out.append(Diff(key, f, va, vb, sev))
    out += [Diff("unpaired", "rule", r.component, None, "major") for r in only_a]
    out += [Diff("unpaired", "rule", None, r.component, "major") for r in only_b]
    return out


def agreement(diffs: list[Diff]) -> str:
    """The reforms schema's `coder_agreement` for a reconciled place: 'agree' when there is no diff,
    else 'adjudicated' (the reconciler decided)."""
    return "agree" if not diffs else "adjudicated"
