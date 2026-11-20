"""Compare the primary coder (A) with the blind second coder (B), field by field, and merge with the
verifier's decisions.

Eras are matched by resolved effective date: the same date, else the same year, else unmatched (an era one
coder found and the other did not is itself a disagreement: lesson L-S5, missing versions). Compared per era:
the resolved effective and adoption dates and every rubric field except free-text `parking` and `coverage`
(their wording differs harmlessly; `parking_min_per_unit` and `coverage_zones` carry the codable content).

Statuses: `agree` (same value, or both blank), `a_only` / `b_only` (one blank), `disagree`. Agreement on a
value that rests only on secondary sources on both sides is reported as `agree_secondary`, which never
counts as agreement in `coder_agreement` (README convention 3; TX lesson: a check that could not read the
source is not agreement).

**Targeted second look** (`score.py`): when the second coder coded only some fields, pass
those as `fields`; other fields are taken from A without a diff. Era-level diffs are always kept (an era only
one coder found is the most useful thing a second look can turn up). A targeted place is never `agree`: it is
`adjudicated` when the verifier ruled, else `single_coder`.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from lotline.rule_agents.adu import dates as D
from lotline.rule_agents.adu.coding import RUBRIC_FIELDS, Era, FieldValue, PlaceCoding

COMPARED = tuple(f for f in RUBRIC_FIELDS if f not in ("parking", "coverage"))
DATE_FIELDS = ("effective_date", "adoption_date")


@dataclass
class Diff:
    era_key: str
    field: str
    a: Any
    b: Any
    status: str  # agree | agree_secondary | a_only | b_only | disagree | era_a_only | era_b_only


def _norm(field: str, v: Any) -> Any:
    if v is None:
        return None
    if field == "coverage_zones":
        return frozenset(z.strip().upper() for z in str(v).split(";") if z.strip())
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def match_eras(a: list[Era], b: list[Era]) -> list[tuple[Era | None, Era | None]]:
    ra = {e.era_id: D.resolve(e.dates).effective for e in a}
    rb = {e.era_id: D.resolve(e.dates).effective for e in b}
    pairs, used = [], set()
    for ea in sorted(a, key=lambda e: ra[e.era_id]):
        da = ra[ea.era_id]
        cands = [eb for eb in b if eb.era_id not in used]
        hit = next((eb for eb in cands if rb[eb.era_id] == da), None)
        hit = hit or next((eb for eb in cands if rb[eb.era_id].year == da.year), None)
        if hit:
            used.add(hit.era_id)
        pairs.append((ea, hit))
    pairs += [(None, eb) for eb in b if eb.era_id not in used]
    return sorted(pairs, key=lambda p: ra[p[0].era_id] if p[0] else rb[p[1].era_id])


def _secondary_only(fv: FieldValue | None) -> bool:
    return fv is not None and fv.evidence and not any(e.primary for e in fv.evidence)


def compare(a: PlaceCoding, b: PlaceCoding, fields: set[str] | None = None) -> list[Diff]:
    """Field-by-field diffs; with `fields`, only those fields (plus era-level diffs) are compared."""
    out = _compare(a, b)
    if fields is None:
        return out
    return [d for d in out if d.field == "era" or d.field in fields]


def _compare(a: PlaceCoding, b: PlaceCoding) -> list[Diff]:
    out: list[Diff] = []
    for ea, eb in match_eras(a.eras, b.eras):
        if ea is None or eb is None:
            e = ea or eb
            key = f"{D.resolve(e.dates).effective}"
            out.append(
                Diff(
                    key,
                    "era",
                    e.era_id if ea else None,
                    e.era_id if eb else None,
                    "era_a_only" if ea else "era_b_only",
                )
            )
            continue
        rda, rdb = D.resolve(ea.dates), D.resolve(eb.dates)
        key = str(rda.effective)
        for f, va, vb in (
            ("effective_date", rda.effective, rdb.effective),
            ("adoption_date", rda.adoption, rdb.adoption),
        ):
            out.append(Diff(key, f, va, vb, _status(va, vb)))
        for f in COMPARED:
            va, vb = _norm(f, ea.value(f)), _norm(f, eb.value(f))
            st = _status(va, vb)
            if st == "agree" and va is not None:
                if _secondary_only(ea.fields.get(f)) and _secondary_only(eb.fields.get(f)):
                    st = "agree_secondary"
            out.append(Diff(key, f, ea.value(f), eb.value(f), st))
    return out


def _status(va, vb) -> str:
    if va == vb:
        return "agree"
    if vb is None:
        return "a_only"
    if va is None:
        return "b_only"
    return "disagree"


def needs_verifier(diffs: list[Diff]) -> list[Diff]:
    """Diffs the verifier must settle by re-opening the sources (everything that is not plain agreement)."""
    return [d for d in diffs if d.status not in ("agree",)]


def coder_agreement(diffs: list[Diff], verified: bool, targeted: bool = False) -> str:
    """Schema CODER_AGREEMENT for a place: 'agree' only when every value was second-coded and agreed on
    primary evidence; 'adjudicated' when the verifier settled the rest; else 'single_coder'."""
    if not targeted and all(d.status == "agree" for d in diffs):
        return "agree"
    return "adjudicated" if verified else "single_coder"


@dataclass
class Decision:
    """The verifier's ruling on one diff: take A, take B, blank it, or hand it to a human."""

    era_key: str
    field: str
    take: str  # "a" | "b" | "blank" | "human"
    note: str = ""


def merge(
    a: PlaceCoding,
    b: PlaceCoding,
    decisions: list[Decision],
    verifier: str,
    on: dt.date,
    fields: set[str] | None = None,
):
    """(final coding, unresolved diffs). Starts from A; applies decisions; any non-agree diff without a
    decision is unresolved and its field is blanked (blank = unknown, never a guess)."""
    final = a.model_copy(deep=True)
    final.coder = f"{a.coder}+{b.coder}"
    by_key = {(d.era_key, d.field): d for d in decisions}
    diffs = compare(a, b, fields)
    eras_a = {str(D.resolve(e.dates).effective): e for e in final.eras}
    pairs = {str(D.resolve(ea.dates).effective): eb for ea, eb in match_eras(a.eras, b.eras) if ea and eb}
    unresolved: list[Diff] = []
    for d in diffs:
        if d.status == "agree":
            continue
        dec = by_key.get((d.era_key, d.field))
        if d.status == "era_b_only":
            if dec and dec.take == "b":
                final.eras.append(next(e for e in b.eras if e.era_id == d.b).model_copy(deep=True))
            elif not dec or dec.take == "human":
                unresolved.append(d)
            continue
        if d.status == "era_a_only":
            if dec and dec.take == "blank":
                final.eras = [e for e in final.eras if e.era_id != d.a]
            elif not dec or dec.take == "human":
                unresolved.append(d)
            continue
        era = eras_a.get(d.era_key)
        if dec is None and d.status == "agree_secondary":
            continue  # kept, but coder_agreement stays below 'agree'
        if dec is None or dec.take == "human":
            unresolved.append(d)
            if era is not None and d.field in era.fields:
                era.fields[d.field] = FieldValue(value=None, note="unresolved between coders; see human task")
            continue
        if era is None or d.field in DATE_FIELDS:
            if d.field in DATE_FIELDS and dec.take == "b" and era is not None:
                era.dates = pairs[d.era_key].dates
            continue
        if dec.take == "b":
            era.fields[d.field] = pairs[d.era_key].fields.get(d.field, FieldValue())
        elif dec.take == "blank":
            era.fields[d.field] = FieldValue(value=None, note=dec.note or "blanked by verifier")
        if dec.note:
            era.fields[d.field].note = (era.fields[d.field].note or "") + f" verifier {on}: {dec.note}"
    final.eras.sort(key=lambda e: D.resolve(e.dates).effective)
    scope = f" (second look on: {', '.join(sorted(fields))})" if fields is not None else ""
    final.notes = ((final.notes or "") + f" Reconciled by {verifier} on {on}{scope}.").strip()
    return final, unresolved
