"""Structured human lookup tasks: what the agents could not read, packaged so a person can finish it fast.

One task = one place + one question (an era's date, or a set of fields from one document). Each task says
where to go, what to look for, which exact cells to fill with which allowed values, and what counts as done
(acceptance). Tasks are written largest place first, because lessons L-H2/L-H3 showed ranked, one-row-per-
place return tables were the ones that got filled.

Priority: 1 = the rule's existence or timing (`adus_per_lot`, dates), 2 = other fields, 3 = **optional**: a
source only a public-records request reaches. The user may file that request themselves or mark the task
`no_usable_source`; agents never file requests, email or call anyone.
Filled tasks are read back as `human_primary` / `human_secondary` evidence; a filled value with no URL
and quote is rejected (lesson L-H4: search-summary answers without links could not be used).
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from lotline.rule_agents.adu.coding import RUBRIC_FIELDS, Evidence

# reason -> plain-language "why the agent stopped" and "what to do".
REASONS = {
    "robots_disallow": (
        "The site's robots.txt tells automated agents not to read this page.",
        "Open it in a browser.",
    ),
    "known_blocker": (
        "This publisher blocks automated agents (Municode, American Legal, eCode360): not tried.",
        "Open it in a browser.",
    ),
    "robots_unavailable": (
        "The site's robots.txt did not answer, so the agent did not read the site.",
        "Open it in a browser.",
    ),
    "http_403": ("The site refuses automated requests (HTTP 403).", "Open it in a browser."),
    "waf_challenge": (
        "The site shows a bot check (Cloudflare or similar).",
        "Open it in a browser; pass the check yourself.",
    ),
    "login_required": (
        "The page needs a login.",
        "Use it only if you already have access; otherwise mark no_usable_source.",
    ),
    "rate_limited": ("The site asked the agent to slow down (HTTP 429).", "Open it in a browser."),
    "js_only_viewer": ("The code viewer only works with JavaScript in a browser.", "Open it in a browser."),
    "scanned_pdf": (
        "The PDF is a scan with no text layer.",
        "Read the page in the PDF and copy the sentence.",
    ),
    "too_large": ("The file is too large to fetch automatically.", "Open it and find the section."),
    "no_answer": ("The site did not answer.", "Try it in a browser; if it is down, try the Wayback link."),
    "not_found": ("The page no longer exists.", "Try the Wayback link or search the city site."),
    "http_error": ("The site returned an error.", "Try it in a browser."),
    "not_https": ("Only an http page was found.", "Find the https page or a Wayback copy."),
    "minutes_only": (
        "The date is only in meeting minutes or agendas the agent could not open.",
        "Find the ordinance number and date in the minutes.",
    ),
    "not_found_online": (
        "The agent searched and found no online source.",
        "Search once more (city site, Wayback, Legistar); if nothing, mark no_usable_source.",
    ),
    "records_request_only": (
        "This record is only available by public-records request.",
        "Optional: this record is only available by public-records request. File one with the city clerk if "
        "you want it (it can take weeks); otherwise mark no_usable_source.",
    ),
    "conflicting_sources": (
        "The two coders read different values and the verifier could not settle it.",
        "Read the section and pick the value the code supports.",
    ),
    "judgment_call": (
        "The text is clear but how to code it is a policy choice.",
        "Decide, and say why in notes.",
    ),
}
# Sources only a public-records request reaches: an optional, priority-3 task (also recognised as a note
# prefix on a `not_found_online` block, the form the coders used before this reason existed).
RECORDS_REQUEST_ONLY = "records_request_only"
PRIORITY_1_FIELDS = {"adus_per_lot", "adoption_date", "effective_date"}

ALLOWED = {
    "adus_per_lot": "whole number (0 = no rentable ADU allowed)",
    "by_right": "True (staff approval only) / False (needs a hearing, CUP or SUP)",
    "owner_occ": "True (owner must live on site) / False",
    "adu_detached_allowed": "True / False",
    "adu_max_sqft": "number (absolute cap only; leave blank if only a % of the house, or if it is a minimum)",
    "parking_min_per_unit": "number of extra spaces for the ADU (0 if none)",
    "parking": "the parking rule as written (short)",
    "min_lot_sqft": "number (lot area needed for an ADU)",
    "coverage": "plain-language area (e.g. 'all single-family districts')",
    "coverage_zones": "district codes separated by ';'",
    "adoption_date": "YYYY-MM-DD (council vote / adoption)",
    "effective_date": "YYYY-MM-DD (date the rule took effect)",
}
ACCEPT = (
    "Done when every listed field is filled (or explicitly 'not found'), with the URL you read it on and a "
    "verbatim sentence (under 25 words) that shows it. Dates need the ordinance number if the page shows "
    "one. "
    "If no source exists online, set status = no_usable_source."
)
COLUMNS = [
    "task_id",
    "priority",
    "optional",
    "state",
    "geoid",
    "place",
    "pop_2020",
    "era_id",
    "question",
    "why_agent_stopped",
    "url",
    "alt_urls",
    "what_to_do",
    "what_to_look_for",
    "fields_to_fill",
    "allowed_values",
    "acceptance",
    "est_minutes",
    "status",
    "answers",
    "answer_url",
    "answer_quote",
    "answer_section",
    "answered_by",
    "answered_on",
    "notes",
]
STATUSES = ("open", "done", "no_usable_source")


@dataclass
class HumanTask:
    state: str
    geoid: str
    place: str
    question: str
    reason: str
    url: str
    what_to_look_for: str
    fields_to_fill: list[str]
    era_id: str = ""
    pop_2020: int = 0
    alt_urls: list[str] = field(default_factory=list)
    est_minutes: int = 10
    status: str = "open"
    answers: str = ""  # "field=value; field=value"
    answer_url: str = ""
    answer_quote: str = ""
    answer_section: str = ""
    answered_by: str = ""
    answered_on: str = ""
    notes: str = ""
    priority: int = 0  # 1 rule existence/timing, 2 other fields, 3 optional (records request only)
    optional: bool = False
    task_id: str = ""

    def __post_init__(self):
        if "all" in self.fields_to_fill:  # shorthand: the whole rubric and both dates
            self.fields_to_fill = list(ALLOWED)
        if self.reason not in REASONS:
            raise ValueError(f"unknown reason {self.reason!r}; expected one of {sorted(REASONS)}")
        bad = set(self.fields_to_fill) - set(ALLOWED)
        if bad:
            raise ValueError(f"unknown fields {sorted(bad)}")
        if not self.task_id:
            key = (
                f"{self.state}|{self.geoid}|{self.era_id}|{','.join(sorted(self.fields_to_fill))}|{self.url}"
            )
            self.task_id = f"ADU-{self.state}-{self.geoid}-" + hashlib.sha1(key.encode()).hexdigest()[:6]

    def row(self) -> dict:
        why, todo = REASONS[self.reason]
        d = {k: v for k, v in asdict(self).items()}
        d.update(
            why_agent_stopped=why,
            what_to_do=todo,
            alt_urls="; ".join(self.alt_urls),
            fields_to_fill="; ".join(self.fields_to_fill),
            allowed_values=" | ".join(f"{f}: {ALLOWED[f]}" for f in self.fields_to_fill),
            acceptance=ACCEPT,
            optional="yes" if self.optional else "",
        )
        d.pop("reason")
        return {c: d.get(c, "") for c in COLUMNS}


def triage(tasks: list[HumanTask]) -> tuple[list[HumanTask], list[HumanTask]]:
    """(tasks to queue, tasks closed now; nothing is closed any more). Duplicates (same place + page) are
    merged; tasks get priority 1/2/3 (3 = optional, records request only) and are sorted by priority, then
    largest place first."""
    seen: dict[tuple, HumanTask] = {}
    for t in tasks:  # one task per place + page: both coders and the merge often block on the same URL
        key = (t.state, t.geoid, t.url)
        if key not in seen:
            seen[key] = t
            continue
        k = seen[key]
        k.fields_to_fill = list(dict.fromkeys(k.fields_to_fill + t.fields_to_fill))
        eras = [e for e in dict.fromkeys(k.era_id.split("; ") + t.era_id.split("; ")) if e]
        k.era_id = "; ".join(eras)
        if t.what_to_look_for not in k.what_to_look_for:
            k.what_to_look_for += " " + t.what_to_look_for
        k.est_minutes = max(k.est_minutes, t.est_minutes)
        k.notes = "; ".join(n for n in (k.notes, t.notes) if n)
    queue: list[HumanTask] = []
    for t in seen.values():
        t.optional = t.reason == RECORDS_REQUEST_ONLY or t.notes.startswith(RECORDS_REQUEST_ONLY)
        if t.optional:
            t.priority = 3
        else:
            t.priority = 1 if PRIORITY_1_FIELDS & set(t.fields_to_fill) else 2
        queue.append(t)
    queue.sort(key=lambda t: (t.priority, -t.pop_2020, t.place, t.era_id))
    return queue, []


def write_csv(tasks: list[HumanTask], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for t in tasks:
            w.writerow(t.row())


def write_markdown(tasks: list[HumanTask], path: str | Path, title: str) -> None:
    """A checklist a person can work top to bottom; the CSV is where answers go."""
    lines = [
        f"# {title}",
        "",
        f"{len(tasks)} lookups, priority 1 first, then largest place. Fill answers in the CSV.",
        "",
    ]
    for n, t in enumerate(tasks, 1):
        r = t.row()
        opt = " · optional" if t.optional else ""
        lines += [
            f"## {n}. {t.place} ({t.geoid}) — {t.question} · priority {t.priority}{opt}",
            f"- [ ] **Open:** {t.url}" + (f" (or {r['alt_urls']})" if t.alt_urls else ""),
            f"- **Why the agent stopped:** {r['why_agent_stopped']} {r['what_to_do']}",
            f"- **Look for:** {t.what_to_look_for}",
            f"- **Fill:** {r['allowed_values']}",
            f"- **Done when:** URL + verbatim sentence + section; about {t.est_minutes} min. "
            f"Task `{t.task_id}`.",
            "",
        ]
    Path(path).write_text("\n".join(lines))


def read_csv(path: str | Path) -> list[dict]:
    with Path(path).open(newline="") as fh:
        return list(csv.DictReader(fh))


def parse_answers(text: str) -> dict[str, str]:
    out = {}
    for part in filter(None, (p.strip() for p in text.split(";"))):
        if "=" not in part:
            raise ValueError(f"answer {part!r} is not field=value")
        k, v = (s.strip() for s in part.split("=", 1))
        if k not in ALLOWED:
            raise ValueError(f"answer names unknown field {k!r}")
        out[k] = v
    return out


def answered(row: dict) -> tuple[dict[str, str], Evidence | None, list[str]]:
    """(answers, evidence, problems) for one filled CSV row. A 'done' row needs answers, an https URL and a
    quote; otherwise it is not accepted and stays open."""
    problems: list[str] = []
    if row.get("status") != "done":
        return {}, None, problems
    try:
        ans = parse_answers(row.get("answers", ""))
    except ValueError as exc:
        return {}, None, [str(exc)]
    want = {f.strip() for f in row.get("fields_to_fill", "").split(";") if f.strip()}
    missing = want - set(ans)
    if missing:
        problems.append(f"fields not answered: {sorted(missing)} (write field=not found if absent)")
    if not row.get("answer_url", "").startswith("https://"):
        problems.append("answer_url must be an https link to the page read")
    if not row.get("answer_quote", "").strip():
        problems.append("answer_quote is required (a verbatim sentence)")
    if problems:
        return ans, None, problems
    when = row.get("answered_on") or dt.date.today().isoformat()
    ev = Evidence(
        url=row["answer_url"],
        retrieved=dt.date.fromisoformat(when),
        quote=row["answer_quote"].strip()[:300],
        section=row.get("answer_section") or None,
        kind="human_primary",
    )
    return ans, ev, problems


def field_names() -> list[str]:
    return [f.name for f in fields(HumanTask)]


assert set(RUBRIC_FIELDS) <= set(ALLOWED)
