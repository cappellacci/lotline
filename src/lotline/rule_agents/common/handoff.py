"""The parts of the human lookup sheet that are the same for every category.

A category's `handoff` module supplies its own answer columns (MM: most homes per lot; ADU: allowed, size,
owner occupancy; fees: amount, basis, year) and builds tasks with these pieces: the browser tip for each
blocker kind, the closed `result` answers, the acceptance rule, the documents already held for the place,
the Markdown checklist and the base answer checks. Moved from the MM swarm's `mm/handoff.py` (master).

A source available only by public-records request becomes an **optional** task (priority 3, `optional` =
yes): the user may file the request themselves or mark it `no_usable_source`. Agents never file one.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

from lotline.rule_agents.common.access import host_label

RESULTS = ("found", "not_found", "no_usable_source")
QUOTE_MAX = 300

BLOCKER_TIPS = {
    "robots_disallow": "The site asks robots not to fetch this path; open it yourself in a browser.",
    "http_403_waf": "The site refuses scripts (bot wall); it opens in a normal browser.",
    "scanned_pdf": "The PDF is a scan; read the page(s) by eye.",
    "js_only": "The page needs JavaScript; open it in a browser.",
    "login_required": "Needs a login: mark no_usable_source unless you already have access.",
    "not_found": "Dead link: try the Wayback Machine (web.archive.org) or the city's site search.",
    "unreachable": "The host did not answer (timeout or connection error); try it in a browser.",
    "robots_unavailable": "The site's robots.txt did not answer, so scripts stay off; open it in a browser.",
    "budget_spent": "The agents used up this place's budget before reading this; a quick look may settle it.",
    "records_request_only": (
        "Optional: this record is only available by public-records request. File one with the city clerk "
        "if you want it (it can take weeks); otherwise mark no_usable_source."
    ),
}

ACCEPTANCE = (
    "Done when result is filled. 'found': fill the listed columns and paste a verbatim quote (<=300 chars) "
    "from source_url that shows the value; dates as YYYY-MM-DD. If you saved the document, drop it in the "
    "rule_docs inbox and put its file name in saved_file. 'not_found': the page is readable but does not "
    "answer it. 'no_usable_source': only by records request you chose not to file, login, or gone."
)
# Answer columns every category's sheet has (after its own value columns).
COMMON_ANSWER_COLUMNS = ["result", "source_url", "quote", "saved_file", "checked_by", "checked_on", "notes"]


def url_key(url: str) -> str:
    """One key for one page however its address was written: the host lower-cased without `www.`, the
    rest as given. By hand: 'https://www.BurlingtonVT.gov/a.pdf' and 'https://burlingtonvt.gov/a.pdf' ->
    'burlingtonvt.gov/a.pdf' (two tasks for one file in the Burlington VT run)."""
    from urllib.parse import urlparse

    p = urlparse((url or "").strip())
    host = (p.hostname or "").lower().removeprefix("www.")
    rest = p.path.rstrip("/") + (f"?{p.query}" if p.query else "")
    return host + rest if host else (url or "").strip()


def browser_tip(url: str, kind: str) -> str:
    host = host_label(url)
    return host[1] if host else BLOCKER_TIPS.get(kind, "Open in a browser.")


def held_docs(
    docs, geoid: str, category: str | None = None, limit: int = 5, county: str | None = None
) -> str:
    """Documents already in the store for the place (or its county or state), so a person does not fetch
    them again: "<doc_id[:12]> <type> <title or url>; ..." (empty when none or no store)."""
    if docs is None:
        return ""
    hits = docs.find(geoid=geoid, county=county, category=category) or docs.find(geoid=geoid, county=county)
    return "; ".join(
        f"{h.doc.doc_id[:12]} {h.doc.doc_type} {(h.doc.title or h.doc.first_url)[:80]}" for h in hits[:limit]
    )


def write_csv(rows: list[dict], path: Path, columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


def read_answers(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def to_markdown(rows: list[dict], title: str) -> str:
    """A checklist a person can work top to bottom; the CSV is where the answers go."""
    buf = io.StringIO()
    buf.write(f"# {title}\n\nFill answers in the CSV with the same task_id. Priority 1 first.\n\n")
    for r in rows:
        opt = " · optional" if r.get("optional") == "yes" else ""
        buf.write(
            f"- [ ] **{r['task_id']}** · {r['place']} · priority {r['priority']}{opt} · `{r['blocker']}`\n"
        )
        buf.write(f"  - Open: {r['start_url']}\n  - Tip: {r['browser_tip']}\n")
        buf.write(f"  - Look for: {r['look_for']}\n  - Fill: `{r['fields_to_fill']}`\n")
        if r.get("held_docs"):
            buf.write(f"  - Already held (no need to download): {r['held_docs']}\n")
    return buf.getvalue()


def base_problems(row: dict, date_columns: tuple[str, ...] = ()) -> list[str]:
    """Checks every answered row must pass (empty: usable, or not answered yet). By hand: result 'found'
    with no quote -> 'found needs a quote'; result 'maybe' -> not one of the three answers; a 400-character
    quote -> too long; checked_on '11/17/26' -> not YYYY-MM-DD."""
    res = (row.get("result") or "").strip()
    if not res:
        return []
    out = []
    if res not in RESULTS:
        out.append(f"result {res!r} is not one of {RESULTS}")
    if res == "found":
        if not (row.get("quote") or "").strip():
            out.append("found needs a quote")
        if not (row.get("source_url") or row.get("start_url") or "").startswith("http"):
            out.append("found needs a source_url")
    for c in (*date_columns, "checked_on"):
        v = (row.get(c) or "").strip()
        if v:
            try:
                date.fromisoformat(v)
            except ValueError:
                out.append(f"{c} {v!r} is not YYYY-MM-DD")
    if len(row.get("quote") or "") > QUOTE_MAX:
        out.append(f"quote longer than {QUOTE_MAX} characters")
    return out


def take_saved_file(docs, row: dict, *, geoid: str, category: str, state: str) -> str | None:
    """A 'found' answer with a `saved_file` in the inbox: register it in the store (manifest + blob +
    text) as a person's document and return its doc_id, so evidence cites the exact bytes."""
    name = (row.get("saved_file") or "").strip()
    if not name or docs is None:
        return None
    f = docs.inbox / Path(name).name
    if not f.is_file():
        raise FileNotFoundError(f"saved_file {name!r} is not in {docs.inbox}")
    who = (row.get("checked_by") or "ben").strip().lower().replace(" ", "-")
    rec = docs.add(
        f,
        url=row.get("source_url") or row.get("start_url") or "",
        added_by=f"human:{who}",
        retrieved=(row.get("checked_on") or None),
        category=category,
        jurisdictions=[geoid],
        states=[state],
    )
    return rec.doc_id
