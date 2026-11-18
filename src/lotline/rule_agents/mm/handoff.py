"""Human lookup tasks: one row per source the swarm could not read, and reading the answers back.

The sheet (`human-lookups.csv`, plus the same tasks as a Markdown checklist) follows the shape of the
`*-mm-lookups-todo.csv` sheets Ben filled in Oct-Nov 2026, with the lessons from them built in: a direct
start URL, a browser tip for the code host, the exact fields to fill (one column each, closed choices where
possible), an acceptance rule, and a `result` column with three closed answers so "nothing usable" is a
recorded outcome rather than a blank. `records_request_only` tasks are never written: Ben files no records
requests, so those close as `no_usable_source` at once (`task_for` returns None).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from datetime import date
from pathlib import Path

from lotline.rule_agents.mm.access import host_label
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
    "checked_by",
    "checked_on",  # YYYY-MM-DD
    "notes",
]
COLUMNS = TASK_COLUMNS + ANSWER_COLUMNS
RESULTS = ("found", "not_found", "no_usable_source")

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


def task_for(f: PlaceFinding, b: Blocker, n: int, *, pop: int | None = None) -> dict | None:
    """One lookup task for blocker `b` of finding `f` (`n` numbers tasks within the place). None for a
    records-request-only source. Priority 1 (do first) when the blocker hides a date or cap that decides
    whether the place has an event; 2 for context-only fields (by_right, zones)."""
    if b.kind == "records_request_only":
        return None
    fields = b.fields or ["unit_cap", "by_right", "adoption_date", "effective_date"]
    priority = 1 if {"unit_cap", "effective_date", "adoption_date"} & set(fields) else 2
    host = host_label(b.url)
    tip = (
        host[1]
        if host
        else {
            "robots_disallow": "The site asks robots not to fetch this path; open it yourself in a browser.",
            "http_403_waf": "The site refuses scripts (bot wall); it opens in a normal browser.",
            "scanned_pdf": "The PDF is a scan; read the page(s) by eye.",
            "js_only": "The page needs JavaScript; open it in a browser.",
            "login_required": "Needs a login: mark no_usable_source unless you already have access.",
            "not_found": "Dead link: try the Wayback Machine (web.archive.org) or the city's site search.",
            "unreachable": "The host did not answer (timeout or connection error); try it in a browser.",
        }.get(b.kind, "Open in a browser.")
    )
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
        "acceptance": (
            "Done when result is filled. 'found': fill the listed columns and paste a verbatim quote "
            "(<=300 chars) from source_url that shows the value; dates as YYYY-MM-DD. 'not_found': the page "
            "is readable but does not answer it. 'no_usable_source': only by records request, login, or gone."
        ),
        **{c: "" for c in ANSWER_COLUMNS},
    }


def tasks(findings: Iterable[PlaceFinding], pops: dict[str, int] | None = None) -> list[dict]:
    """All tasks for a run, deduplicated on (geoid, start_url) and sorted by priority then population."""
    pops = pops or {}
    out: dict[tuple[str, str], dict] = {}
    for f in findings:
        n = 0
        for b in f.blockers:
            key = (f.jurisdiction_geoid, b.url)
            if key in out:
                prev = set(out[key]["fields_to_fill"].split(";"))
                t = task_for(f, b, 99, pop=pops.get(f.jurisdiction_geoid))
                if t:
                    out[key]["fields_to_fill"] = ";".join(sorted(prev | set(t["fields_to_fill"].split(";"))))
                    out[key]["priority"] = min(out[key]["priority"], t["priority"])
                continue
            n += 1
            t = task_for(f, b, n, pop=pops.get(f.jurisdiction_geoid))
            if t:
                out[key] = t
    return sorted(out.values(), key=lambda t: (t["priority"], -pops.get(t["geoid"], 0), t["task_id"]))


def write_csv(rows: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})


def to_markdown(rows: list[dict], title: str) -> str:
    """A checklist a person can work top to bottom; the CSV is where the answers go."""
    buf = io.StringIO()
    buf.write(f"# {title}\n\nFill answers in the CSV with the same task_id. Priority 1 first.\n\n")
    for r in rows:
        buf.write(f"- [ ] **{r['task_id']}** · {r['place']} · priority {r['priority']} · `{r['blocker']}`\n")
        buf.write(f"  - Open: {r['start_url']}\n  - Tip: {r['browser_tip']}\n")
        buf.write(f"  - Look for: {r['look_for']}\n  - Fill: `{r['fields_to_fill']}`\n")
    return buf.getvalue()


def read_answers(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def answer_problems(row: dict) -> list[str]:
    """Why an answered row can't be used yet (empty: usable). By hand: result 'found' with no quote ->
    'found needs a quote'; result 'maybe' -> not one of the three answers; a quote of 400 characters ->
    too long."""
    res = (row.get("result") or "").strip()
    if not res:
        return []  # not answered yet: stays open
    out = []
    if res not in RESULTS:
        out.append(f"result {res!r} is not one of {RESULTS}")
    if res == "found":
        if not (row.get("quote") or "").strip():
            out.append("found needs a quote")
        if not (row.get("source_url") or row.get("start_url") or "").startswith("http"):
            out.append("found needs a source_url")
        cap = (row.get("max_homes_per_single_family_lot") or "").strip()
        if cap and cap not in ("1", "2", "3", "4"):
            out.append(f"max_homes_per_single_family_lot {cap!r} must be 1-4")
        br = (row.get("by_right") or "").strip().lower()
        if br and br not in ("yes", "no"):
            out.append(f"by_right {br!r} must be yes or no")
        for c in ("adopted_date", "effective_date", "checked_on"):
            v = (row.get(c) or "").strip()
            if v:
                try:
                    date.fromisoformat(v)
                except ValueError:
                    out.append(f"{c} {v!r} is not YYYY-MM-DD")
    if len(row.get("quote") or "") > 300:
        out.append("quote longer than 300 characters")
    return out


def answer_to_evidence(row: dict, today: date | None = None) -> tuple[dict, list[Evidence]]:
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
        )
        for f in vals
    ]
    return vals, ev
