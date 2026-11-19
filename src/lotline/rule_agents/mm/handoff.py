"""Human lookup tasks: one row per source the swarm could not read, and reading the answers back.

The sheet (`human-lookups.csv`, plus the same tasks as a Markdown checklist) follows the shape of the
`*-mm-lookups-todo.csv` sheets Ben filled in Oct-Nov 2026, with the lessons from them built in: a direct
start URL, a browser tip for the code host, the exact fields to fill (one column each, closed choices where
possible), an acceptance rule, and a `result` column with three closed answers so "nothing usable" is a
recorded outcome rather than a blank. `records_request_only` sources become optional tasks (priority 3): the
user may file the request or mark it `no_usable_source`; agents never file one.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from pathlib import Path

from lotline.rule_agents.common import handoff as H
from lotline.rule_agents.common.handoff import RESULTS, read_answers, to_markdown  # noqa: F401
from lotline.rule_agents.mm.findings import Blocker, Evidence, PlaceFinding

TASK_COLUMNS = [
    "task_id",
    "state",
    "place",
    "geoid",
    "priority",
    "blocker",
    "start_url",
    "browser_tip",
    "look_for",
    "fields_to_fill",
    "acceptance",
    "held_docs",  # documents already in the store for this place: no need to download them again
    "optional",  # yes = only a public-records request reaches it; the user may skip it
]
ANSWER_COLUMNS = [
    "result",  # found / not_found / no_usable_source
    "max_homes_per_single_family_lot",  # 1, 2, 3 or 4 (4 = four or more)
    "by_right",  # yes / no (no = needs a special or conditional use permit, or a rezoning)
    "adopted_date",  # YYYY-MM-DD, the council vote
    "effective_date",  # YYYY-MM-DD; blank if the source gives none
    "districts",  # district codes, ";"-separated
    "ordinance",  # ordinance number or file
    "source_url",  # the page that shows it (may differ from start_url)
    "quote",  # verbatim, at most 300 characters
    "saved_file",  # a file the person saved into the rule_docs inbox (taken into the store on ingest)
    "checked_by",
    "checked_on",  # YYYY-MM-DD
    "notes",
]
COLUMNS = TASK_COLUMNS + ANSWER_COLUMNS

_FIELD_COLUMN = {
    "unit_cap": "max_homes_per_single_family_lot",
    "by_right": "by_right",
    "adoption_date": "adopted_date",
    "effective_date": "effective_date",
    "coverage_zones": "districts",
}
_LOOK_FOR = {
    "unit_cap": "the most homes allowed on one lot in the single-family districts (a duplex = 2)",
    "by_right": "whether that is allowed by right or needs a special/conditional use permit or rezoning",
    "adoption_date": "the date council adopted the ordinance that first allowed it",
    "effective_date": "the date it took effect (often 'effective upon adoption' or a set date)",
    "coverage_zones": "which zoning districts it applies to",
}


def task_for(f: PlaceFinding, b: Blocker, n: int, *, pop: int | None = None, docs=None) -> dict | None:
    """One lookup task for blocker `b` of finding `f` (`n` numbers tasks within the place). Priority 1 (do
    first) when the blocker hides a date or cap that decides whether the place has an event; 2 for
    context-only fields (by_right, zones); 3 and `optional` for a source only a records request reaches."""
    fields = b.fields or ["unit_cap", "by_right", "adoption_date", "effective_date"]
    priority = 1 if {"unit_cap", "effective_date", "adoption_date"} & set(fields) else 2
    optional = b.kind == "records_request_only"
    if optional:
        priority = 3
    tip = H.browser_tip(b.url, b.kind)
    look = b.look_for or "; ".join(_LOOK_FOR.get(x, x) for x in fields)
    cols = sorted({_FIELD_COLUMN.get(x, "notes") for x in fields} | {"result", "source_url", "quote"})
    return {
        "task_id": f"{f.state}-{f.jurisdiction_geoid}-mm-{n:02d}",
        "state": f.state,
        "place": f.place,
        "geoid": f.jurisdiction_geoid,
        "priority": priority,
        "blocker": f"{b.kind}: {b.detail}".strip(": "),
        "start_url": b.url,
        "browser_tip": tip,
        "look_for": look + (f" (population {pop:,})" if pop else ""),
        "fields_to_fill": ";".join(cols),
        "acceptance": H.ACCEPTANCE,
        "held_docs": H.held_docs(docs, f.jurisdiction_geoid, "mm"),
        "optional": "yes" if optional else "",
        **{c: "" for c in ANSWER_COLUMNS},
    }


def tasks(findings: Iterable[PlaceFinding], pops: dict[str, int] | None = None, docs=None) -> list[dict]:
    """All tasks for a run, deduplicated on (geoid, start_url) and sorted by priority then population."""
    pops = pops or {}
    out: dict[tuple[str, str], dict] = {}
    for f in findings:
        n = 0
        for b in f.blockers:
            key = (f.jurisdiction_geoid, H.url_key(b.url))
            if key in out:
                prev = set(out[key]["fields_to_fill"].split(";"))
                t = task_for(f, b, 99, pop=pops.get(f.jurisdiction_geoid), docs=docs)
                if t:
                    out[key]["fields_to_fill"] = ";".join(sorted(prev | set(t["fields_to_fill"].split(";"))))
                    out[key]["priority"] = min(out[key]["priority"], t["priority"])
                continue
            n += 1
            t = task_for(f, b, n, pop=pops.get(f.jurisdiction_geoid), docs=docs)
            if t:
                out[key] = t
    return sorted(out.values(), key=lambda t: (t["priority"], -pops.get(t["geoid"], 0), t["task_id"]))


def write_csv(rows: list[dict], path: Path) -> None:
    H.write_csv(rows, path, COLUMNS)


def answer_problems(row: dict) -> list[str]:
    """Why an answered row can't be used yet (empty: usable). By hand: result 'found' with no quote ->
    'found needs a quote'; result 'maybe' -> not one of the three answers; a quote of 400 characters ->
    too long."""
    out = H.base_problems(row, ("adopted_date", "effective_date"))
    if (row.get("result") or "").strip() == "found":
        cap = (row.get("max_homes_per_single_family_lot") or "").strip()
        if cap and cap not in ("1", "2", "3", "4"):
            out.append(f"max_homes_per_single_family_lot {cap!r} must be 1-4")
        br = (row.get("by_right") or "").strip().lower()
        if br and br not in ("yes", "no"):
            out.append(f"by_right {br!r} must be yes or no")
    return out


def answer_to_evidence(
    row: dict, today: date | None = None, doc_id: str | None = None
) -> tuple[dict, list[Evidence]]:
    """A usable 'found' answer -> (field values, evidence entries citing the human lookup). Values use
    finding field names (unit_cap, by_right, adoption_date, effective_date, coverage_zones). Other results
    -> ({}, [])."""
    if (row.get("result") or "").strip() != "found" or answer_problems(row):
        return {}, []
    vals: dict = {}
    if row.get("max_homes_per_single_family_lot"):
        vals["unit_cap"] = int(row["max_homes_per_single_family_lot"])
    if row.get("by_right"):
        vals["by_right"] = row["by_right"].strip().lower() == "yes"
    if row.get("adopted_date"):
        vals["adoption_date"] = date.fromisoformat(row["adopted_date"])
    if row.get("effective_date"):
        vals["effective_date"] = date.fromisoformat(row["effective_date"])
    if row.get("districts"):
        vals["coverage_zones"] = [z.strip() for z in row["districts"].split(";") if z.strip()]
    checked = row.get("checked_on") or ""
    when = date.fromisoformat(checked) if checked else (today or date.today())
    url = row.get("source_url") or row["start_url"]
    ev = [
        Evidence(
            field=f,
            url=url,
            quote=row["quote"].strip(),
            retrieved=when,
            section=row.get("ordinance") or None,
            source_kind="human_lookup",
            quote_status="human",
            doc_id=doc_id,
        )
        for f in vals
    ]
    return vals, ev
