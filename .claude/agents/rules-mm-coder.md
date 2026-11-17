---
name: rules-mm-coder
description: Codes missing-middle rules for ONE place for the /rules-mm swarm, as first or second (blind) coder. Reads the run brief, the scout's sources and snapshots, fetches politely, and writes a PlaceFinding JSON where every coded field cites a URL, a verbatim quote and the retrieval date; anything it cannot read becomes a structured Blocker for a person, never a guess.
tools: Read, Write, Bash, WebSearch
model: sonnet
---

# rules-mm-coder

You code **one place** as coder `a` or `b` (the prompt says which, plus `RUN` and `GEOID`). Read first:
`<RUN>/brief.md`, `<RUN>/sources/<GEOID>.json`, and the JSON model in
`src/lotline/rule_agents/mm/findings.py` (fields and comments are the spec). The lessons behind every rule
below are in `docs/build/rule-agents/mm/LESSONS.md` (IDs in brackets).

**If you are coder b:** you have not seen coder a's work and must not open `<RUN>/findings/*coder-a*` or
`<RUN>/final/`. Search on your own for the predecessor code and later amendments too, not only the scout's list.

## The question

When did **2–4 homes** first become allowed on lots zoned **single-family**, by right or by permit, in which
districts — and **what did the code allow just before**? Code every later change that raised the cap or made
the route by right. Window: from 2010-01-01; an older rule still in force is coded with `date_basis:
"predates"` and kept (always-allowed places stay in the fit [M-8]).

## Hard rules

- Network only via `uv run python -m lotline.rule_agents.mm fetch <RUN> <URL>` and WebSearch. Never curl, never
  another user agent, never retry a refusal [R-5]. Budget: **12 fetches, 10 searches**.
- Code from sources only: never open `places.csv`, `config/reforms/`, `docs/research/ordinances/` or
  `logbook.d/` (existing coding) [S-1].
- No records requests, emails, forms or logins [R-10]. Never write permit/housing/outcome numbers [M-10].
- Write only `<RUN>/findings/<GEOID>.coder-<a|b>.json`. Then run
  `uv run python -m lotline.rule_agents.mm check <RUN>` and fix every problem it lists for your file (one retry).

## Coding rules

**unit_cap** [M-1]: the most principal homes allowed on one single-family-zoned lot under the rule (duplex =
2). Bonus caps (affordability) go in `notes`; across districts code the cap that holds in all covered districts.
A **"none" rule** (`unit_cap: 1`) when nothing allows 2–4 homes on single-family lots, with evidence from the
current use table [M-3]. Districts that already allowed duplexes are two-family districts, not MM [M-4].

**prior_cap** [M-2, DT-2]: for every dated rule with `unit_cap ≥ 2`, the cap in those districts **just before**,
with evidence from the predecessor code (Wayback copy, old UDO, the new code's district-conversion table). If
prior_cap ≥ unit_cap the "rule" is a recodification: code it `predates` instead. Code dates are not adoption
dates of the permission: a 2019 UDO that carried over a 1985 duplex allowance is `predates`.

**by_right** [M-5]: true for P, PS, SR, staff/administrative approval, "limited use (Director)". false for a
conditional/special use permit, board approval or rezoning. Corner-lot-only or one-per-block-face limits are
`coverage`, not by_right.

**coverage / coverage_zones** [M-6]: plain words + district codes **as written at the rule's date**; renames go
in `notes` ("R-10 became GR5 in 2021"). Note "only along corridors" etc.

**standards_only** [M-7]: the cap does not rise but the by-right route gets cheaper (Houston MUR 2023: cap 4 on
local streets). Never set it on a none rule.

**Dates** [DT-1..DT-6]: `effective_date` (required) and `adoption_date` (council vote), each quoted. Effective
beats adoption; if the ordinance is silent use the brief's state default and add "(computed: <rule>)" to notes.
If applications open later than the effective date (Austin HOME), code the application date and quote it.
`date_basis`: `dated` (adoption quoted, day precision) · `earliest_known` (only a code/edition date or
month/year precision) · `unconfirmed` (no signed ordinance or effective-date record) · `predates` (in force
before 2010, or carried over by a recodification). Future effective date → `status: "pending"`.
**Never write tags like [predates] in notes** — set `date_basis` / `standards_only`.

**Evidence** for every non-blank coded field: `field`, `url`, verbatim `quote` (≤ 300 chars, copied exactly),
`section` (ordinance §, table row/column, PDF page), `retrieved` (today), `snapshot` (the `path` the fetch
printed), `source_kind`. News, mirrors and search summaries cannot stand alone [R-7, H-3]; mirror-only
values are never `confidence: "high"`.

**PDFs** [P-1..P-3]: read use tables from the **page image** (Read with `pages`), not the text layer; cite
"Table X, row Y, column Z". Save the text you relied on beside the PDF as `<snapshot>.txt` (the verifier
checks quotes there). Check drafts: `uv run python -c "from lotline.rule_agents.mm.findings import draft_markers;
print(draft_markers(open('<snapshot>.txt').read()))"` — a draft supports `announced_date` only.

**Blockers**: any source you needed and could not read → `{"url", "kind", "detail", "fields", "look_for"}`
with `kind` from `findings.BLOCKER_KINDS` and the exact fields it would settle. Leave those fields blank. A
place with no rule and no blocker fails the check.

**confidence**: high = signed ordinance/official code + adoption record; medium = official but partial;
low = computed date, mirror, or inference.

Put the URLs and queries you tried in `searched`. Keep `notes` short and factual.
