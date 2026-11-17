"""Pair the first coder's items with the blind second coder's and mark what they agree on (LESSONS S1-S4).

Items are paired within (place, building type, component), most similar first (per-unit amount, then name).
Outcomes: `agree` (same per-unit amount within tolerance and same schedule year), `partly` (same amount, other
year), `differ`, `only_coder1`, `only_coder2`. Only `agree` sets `verified_by`; everything else goes to the
reconciler agent, which may fix a transcription slip with a quote but sends judgment calls to Ben.
"""

from __future__ import annotations

import difflib
from collections import defaultdict
from datetime import date

from lotline.rule_agents.fees import classify
from lotline.rule_agents.fees.build import price_all, schedule_year
from lotline.rule_agents.fees.prototype import assumptions
from lotline.rule_agents.fees.records import FeeItem

VERIFIER = "rules-fees-second-coder"


def _close(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is None and b is None
    tol = assumptions()["agree_tolerance"]
    return abs(a - b) <= max(tol["absolute_usd"], tol["relative"] * max(abs(a), abs(b)))


def _key(it: FeeItem) -> tuple:
    return (it.place_geoid, it.building_type, classify.component(it.pays_for))


def pair(coder1: list[FeeItem], coder2: list[FeeItem]) -> list[dict]:
    p1, p2 = price_all(coder1), price_all(coder2)
    pool = defaultdict(list)
    for it in coder2:
        pool[_key(it)].append(it)
    out = []
    for a in coder1:
        cands = pool.get(_key(a), [])
        if not cands:
            out.append(
                {
                    "outcome": "only_coder1",
                    "coder1": a.item_id,
                    "coder2": None,
                    "value1": p1[a.item_id].amount_per_unit,
                    "value2": None,
                }
            )
            continue
        va = p1[a.item_id].amount_per_unit

        def score(b: FeeItem, a: FeeItem = a, va: float | None = va) -> tuple:
            vb = p2[b.item_id].amount_per_unit
            gap = 0.0 if _close(va, vb) else (abs(va - vb) if va is not None and vb is not None else 1e12)
            sim = difflib.SequenceMatcher(None, a.fee_type.lower(), b.fee_type.lower()).ratio()
            return (gap, -sim)

        b = min(cands, key=score)
        cands.remove(b)
        vb = p2[b.item_id].amount_per_unit
        if _close(va, vb):
            outcome = "agree" if schedule_year(a)[0] == schedule_year(b)[0] else "partly"
        else:
            outcome = "differ"
        out.append(
            {
                "outcome": outcome,
                "coder1": a.item_id,
                "coder2": b.item_id,
                "value1": va,
                "value2": vb,
                "year1": schedule_year(a)[0],
                "year2": schedule_year(b)[0],
            }
        )
    for rest in pool.values():
        for b in rest:
            out.append(
                {
                    "outcome": "only_coder2",
                    "coder1": None,
                    "coder2": b.item_id,
                    "value1": None,
                    "value2": p2[b.item_id].amount_per_unit,
                }
            )
    return out


def merge(coder1: list[FeeItem], coder2: list[FeeItem], pairs: list[dict], today: date) -> list[FeeItem]:
    """Coder 1's items with `verified_by` set where the pair agrees, plus coder 2's extra items (unverified).

    Agreement lifts an `image_read` or `verbatim` item to `high` confidence; a summariser read never verifies.
    """
    agree = {p["coder1"] for p in pairs if p["outcome"] == "agree"}
    out = []
    for it in coder1:
        if it.item_id in agree and it.quote_status in ("verbatim", "image_read"):
            it = it.model_copy(update={"verified_by": VERIFIER, "verified_date": today})
        out.append(it)
    by2 = {b.item_id: b for b in coder2}
    for p in pairs:
        if p["outcome"] == "only_coder2":
            b = by2[p["coder2"]]
            note = ((b.notes or "") + " Found only by the second coder; reconciler to confirm.").strip()
            out.append(b.model_copy(update={"notes": note}))
    return out


def summary(pairs: list[dict]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for p in pairs:
        out[p["outcome"]] += 1
    return dict(out)
