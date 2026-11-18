"""Structured human lookup tasks: what the agents could not read, packaged so a person can finish it fast.

One task = one place + one question (an era's date, or a set of fields from one document). Each task says
where to go, what to look for, which exact cells to fill with which allowed values, and what counts as done
(acceptance). Tasks are written largest place first, because lessons L-H2/L-H3 showed ranked, one-row-per-
place return tables were the ones that got filled.

Priority: 1 = the rule's existence or timing (`adus_per_lot`, dates), 2 = other fields, 3 = **optional**: a
source only a public-records request reaches. The user may file that request themselves or mark the task
`no_usable_source`; agents never file requests, email or call anyone.
Filled tasks are read back as `human_lookup` evidence (`quote_status` human); a `found` answer with no URL
and quote is rejected (lesson L-H4: search-summary answers without links could not be used). A file the
person saved goes in the document store's inbox and is registered with `common.handoff.take_saved_file`,
so the evidence cites its exact bytes (`doc_id`).

Shared pieces come from `common.handoff`: the browser tip for each blocker kind, the `result` answers, the
answer columns, the base answer checks, and the documents already held for a place.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from lotline.rule_agents.adu.coding import RUBRIC_FIELDS, Evidence
from lotline.rule_agents.common import handoff as CH
from lotline.rule_agents.common.evidence import BLOCKER_KINDS

CATEGORY = "adu"
# blocker kind -> plain-language "why the agent stopped" (what to do: `common.handoff.browser_tip`).
WHY = {
    "robots_disallow": "The site's robots.txt tells automated agents not to read this page.",
    "robots_unavailable": "The site's robots.txt did not answer, so the agent did not read the site.",
    "http_403_waf": "The site refuses automated requests (HTTP 403 or a bot check).",
    "code_host_wall": "This code publisher blocks automated agents (Municode, American Legal, eCode360).",
    "login_required": "The page needs a login.",
    "js_only": "The code viewer only works with JavaScript in a browser.",
    "scanned_pdf": "The PDF is a scan with no text layer.",
    "not_found": "The page no longer exists, or the agent searched and found no online source.",
    "unreachable": "The site did not answer.",
    "records_request_only": "This record is only available by public-records request.",
    "ambiguous_source": "The page is readable but does not settle the value (or only minutes mention it).",
    "conflicting_sources": "The two coders read different values and the verifier could not settle it.",
    "budget_spent": "The agents ran out of search budget for this place.",
    "judgment_call": "The text is clear but how to code it is a policy choice.",
}
REASONS = WHY  # the blocker kinds a coding may use
_TODO = {
    "ambiguous_source": "Read the section and say which value the text supports.",
    "conflicting_sources": "Read the section and pick the value the code supports.",
    "judgment_call": "Decide, and say why in notes.",
}
assert set(BLOCKER_KINDS) <= set(WHY)


def what_to_do(url: str, kind: str) -> str:
    return _TODO.get(kind) or CH.browser_tip(url, kind)


# Sources only a public-records request reaches: an optional, priority-3 task (also recognised as a note
# prefix on a `not_found` block).
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
    "Done when result is filled. 'found': fill every listed field in answers (field=value; field=not found "
    "if absent), with the URL you read it on and a verbatim sentence (under 25 words) that shows it. Dates "
    "need the ordinance number if the page shows one. " + CH.ACCEPTANCE[CH.ACCEPTANCE.index("If you saved") :]
)
TASK_COLUMNS = [
    "task_id",
    "priority",
    "optional",
    "state",
    "geoid",
    "place",
    "pop_2020",
    "era_id",
    "question",
    "blocker",
    "why_agent_stopped",
    "url",
    "alt_urls",
    "what_to_do",
    "what_to_look_for",
    "held_docs",
    "fields_to_fill",
    "allowed_values",
    "acceptance",
    "est_minutes",
]
ANSWER_COLUMNS = ["answers", "section", *CH.COMMON_ANSWER_COLUMNS]
COLUMNS = TASK_COLUMNS + ANSWER_COLUMNS


@dataclass
class HumanTask:
    state: str
    geoid: str
    place: str
    question: str
    blocker: str
    url: str
    what_to_look_for: str
    fields_to_fill: list[str]
    era_id: str = ""
    pop_2020: int = 0
    alt_urls: list[str] = field(default_factory=list)
    est_minutes: int = 10
    held_docs: str = ""  # documents the store already holds for the place (`common.handoff.held_docs`)
    notes: str = ""
    priority: int = 0  # 1 rule existence/timing, 2 other fields, 3 optional (records request only)
    optional: bool = False
    task_id: str = ""

    def __post_init__(self):
        if "all" in self.fields_to_fill:  # shorthand: the whole rubric and both dates
            self.fields_to_fill = list(ALLOWED)
        if self.blocker not in REASONS:
            raise ValueError(f"unknown blocker {self.blocker!r}; expected one of {sorted(REASONS)}")
        bad = set(self.fields_to_fill) - set(ALLOWED)
        if bad:
            raise ValueError(f"unknown fields {sorted(bad)}")
        if not self.task_id:
            key = (
                f"{self.state}|{self.geoid}|{self.era_id}|{','.join(sorted(self.fields_to_fill))}|{self.url}"
            )
            self.task_id = f"ADU-{self.state}-{self.geoid}-" + hashlib.sha1(key.encode()).hexdigest()[:6]

    def row(self) -> dict:
        d = asdict(self)
        d.update(
            why_agent_stopped=WHY[self.blocker],
            what_to_do=what_to_do(self.url, self.blocker),
            alt_urls="; ".join(self.alt_urls),
            fields_to_fill="; ".join(self.fields_to_fill),
            allowed_values=" | ".join(f"{f}: {ALLOWED[f]}" for f in self.fields_to_fill),
            acceptance=ACCEPT,
            optional="yes" if self.optional else "",
        )
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
        t.optional = t.blocker == RECORDS_REQUEST_ONLY or t.notes.startswith(RECORDS_REQUEST_ONLY)
        if t.optional:
            t.priority = 3
        else:
            t.priority = 1 if PRIORITY_1_FIELDS & set(t.fields_to_fill) else 2
        queue.append(t)
    queue.sort(key=lambda t: (t.priority, -t.pop_2020, t.place, t.era_id))
    return queue, []


def write_csv(tasks: list[HumanTask], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    CH.write_csv([t.row() for t in tasks], Path(path), COLUMNS)


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
            *([f"- **Already held (no need to download):** {t.held_docs}"] if t.held_docs else []),
            f"- **Fill:** {r['allowed_values']}",
            f"- **Done when:** result filled; for 'found', URL + verbatim sentence + section; about "
            f"{t.est_minutes} min. "
            f"Task `{t.task_id}`.",
            "",
        ]
    Path(path).write_text("\n".join(lines))


def read_csv(path: str | Path) -> list[dict]:
    return CH.read_answers(Path(path))


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


def answered(row: dict, docs=None) -> tuple[dict[str, str], Evidence | None, list[str]]:
    """(answers, evidence, problems) for one filled CSV row. Only `result` = found is read back: it needs
    answers for every listed field, an https source_url and a verbatim quote (`common.handoff.base_problems`).
    A `saved_file` in the inbox is registered in the document store and cited by doc_id."""
    problems = CH.base_problems(row)
    if (row.get("result") or "").strip() != "found":
        return {}, None, problems
    try:
        ans = parse_answers(row.get("answers", ""))
    except ValueError as exc:
        return {}, None, [*problems, str(exc)]
    want = {f.strip() for f in row.get("fields_to_fill", "").split(";") if f.strip()}
    missing = want - set(ans)
    if missing:
        problems.append(f"fields not answered: {sorted(missing)} (write field=not found if absent)")
    url = (row.get("source_url") or "").strip()
    if not url.startswith("https://"):
        problems.append("source_url must be an https link to the page read")
    if problems:
        return ans, None, problems
    doc_id = CH.take_saved_file(
        docs, row, geoid=row.get("geoid", ""), category=CATEGORY, state=row.get("state", "")
    )
    when = row.get("checked_on") or dt.date.today().isoformat()
    ev = Evidence(
        url=url,
        retrieved=dt.date.fromisoformat(when),
        quote=row["quote"].strip(),
        section=row.get("section") or None,
        source_kind="human_lookup",
        quote_status="human",
        doc_id=doc_id,
    )
    return ans, ev, problems


def field_names() -> list[str]:
    return [f.name for f in fields(HumanTask)]


assert set(RUBRIC_FIELDS) <= set(ALLOWED)
