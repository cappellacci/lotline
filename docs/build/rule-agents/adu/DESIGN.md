# ADU rule agent swarm: design

**Goal.** Given one state, produce `reforms` rows (schema `Reforms`, `src/lotline/schemas.py`, theme `adu`)
for every place worth coding: whether and since when ADUs are allowed, by right or not, attached/detached,
owner occupancy, parking, size cap, ADUs per lot, lot minimum, coverage, and adoption/effective dates. Every
value cites a URL, a verbatim quote and a retrieval date. Anything the agents cannot read becomes a structured
human lookup task. Lesson IDs (`L-xx`) refer to [`LESSONS.md`](LESSONS.md).

Run it with `/rules-adu <ST> [--places N | --geoids a,b] [--run-id id] [--second-coder targeted|full|off]` (`.claude/commands/rules-adu.md`).

## 1. Shape

```
/rules-adu (main session = orchestrator; owns budgets, stop rules, never codes)
 ├─ 0. worklist ............ helper `worklist`        places.csv (largest first, existing rows, holdouts)
 ├─ 1. rules-adu-state-law . agent (1 per state)       state_law.json (+ per-place coverage)
 ├─ 2. rules-adu-scout ..... agent (1 per ~5 places)   sources/<geoid>.json (candidate URLs, fetch results)
 ├─ 3. rules-adu-coder ..... agent (1 per ~5 places)   coding_a/<geoid>.json
 ├─ 4. check + score ....... helpers `check`, `score`  refuse malformed codings; score/<geoid>.json: weak values
 ├─ 4b rules-adu-second-coder agent, blind, targeted   coding_b/<geoid>.json (weak fields only; full on audit)
 ├─ 5. rules-adu-verifier .. agent (1 per ~5 places)   decisions/<geoid>.json -> helper `merge` -> final/
 ├─ 6. rows ................ helper `rows`             rows.csv (schema-validated `reforms` rows)
 ├─ 7. rules-adu-handoff ... agent + helper `tasks`    tasks.csv / tasks.md (human lookups)
 └─ 8. report .............. orchestrator              report.md; compare.md on dry runs
```

Agents (judgment) and helpers (`python -m lotline.rule_agents.adu …`, deterministic, tested) are split on
purpose: anything a test can check — robots, block classification, date rules, comparisons, ids, schema — is
code, so a run is reproducible and a judge can read why a value was chosen.

**Run folder** (outside the repo, never committed): `$LOTLINE_DATA_DIR/rule_agents/adu/<ST>/<run_id>/`.
Downloaded copies go to `$LOTLINE_DATA_DIR/raw/rule_agents/adu/<ST>/<host>/` and `manifest.jsonl` (L-H6).
`rows.csv` is a proposal: the user reviews it and imports what they accept; the agents never write `config/` (L-O3).

## 2. Steps, inputs, outputs, stop rules

| Step | Input | Output | Stop rule |
|---|---|---|---|
| 0 worklist | state; `--places N` / `--geoids`; jurisdictions table | `places.csv` (for agents), `existing_rows.csv` (orchestrator only: reform ids reveal rule years), blind holdouts printed | places with `pop_2020 < 2,500` skipped unless named (L-O5) |
| 1 state law | state | `state_law.json`: each enacted ADU statute, citation, adopted/effective dates, coverage rule (threshold, strictness, population source), fields it sets | statute text read (official or Wayback); a bill that did not pass is never law (MN SF 3964) |
| 2 scout | places batch, `state_law.json` | `sources/<geoid>.json`: official code URL + publisher, ADU section, adopting ordinance(s), Legistar/Wayback leads, fetch result per URL | ≤ 8 web searches and ≤ 10 fetches per place, incl. an amendment sweep; stop on a host after its first block (L-R1, L-R9) |
| 3 coder | `sources/<geoid>.json`, `state_law.json` | `coding_a/<geoid>.json` (`coding.PlaceCoding`) | ≤ 4 extra searches and ≤ 10 fetches per place; every era 2016–2025 plus the prior state (L-S5) |
| 4 check + score | `coding_a`, `sources` | pass / problems; `score/<geoid>.json` (§5a) | a coding that fails twice is kept as `partial` with the failing fields blanked |
| 4b second coder | `sources/<geoid>.json`, the field list only | `coding_b/<geoid>.json` | same budget; codes only the listed fields (all on audit places) and resolves uncoded amendments |
| 5 verifier | both codings + `diff-coders` output | `decisions/<geoid>.json`, `final/<geoid>.json(.meta)` | re-opens only the diffs' sources; anything not settled from a primary source is `human` (L-S7) |
| 6 rows | `final/*.json` | `rows.csv` validated by `schemas.validate(df, "reforms")` | any schema error stops the run |
| 7 hand-off | blocked sources, unresolved diffs | `tasks.csv` + `tasks.md` | records-request-only questions closed as `no_usable_source` (L-H1) |

## 3. Evidence requirements

- **Every coded value** (`FieldValue`) has ≥ 1 `Evidence`: https URL actually opened (Wayback https for
  http-only pages), retrieval date, verbatim quote ≤ 300 characters (aim ≤ 25 words), section, source kind,
  `cache_path` of the copy read, and `doc_id` (sha256 of those bytes), `page` and `quote_status`. The
  document store these ids point into is shared across the three swarms: `SHARED_CANDIDATES.md` §0. `check` refuses a value without evidence (L-O6, L-F3).
- **Source kinds** split into primary (official code, ordinance, staff report, minutes, state law,
  human-primary) and secondary (city page, mirror, news, draft, human-secondary). Only primary evidence can be
  `high` confidence; agreement on secondary evidence alone never counts as agreement (L-R4, L-S3).
- **Dates** are `DateEvidence` with a type (`effective`, `adopted`, `vote`, `codified`, `first_seen`,
  `in_force_by`, `announced`) and precision. The coder records what the source says; `dates.resolve` decides
  (§4). Coders never compute a date (L-D2).
- **Quotes are checked mechanically**: `verify-quotes` finds each quote in the cached text copy (whitespace,
  quote marks, dashes and case normalised; `...` splits). PDFs are listed for the verifier to check by eye.
- The row's `source_quote`/`source_section` is the evidence for the most decisive field (adus_per_lot, then
  by_right, …); `coding_notes` lists every field's sources and confidence, so nothing is lost.

## 4. Coding rules the helpers enforce

| Rule | Where | Lesson |
|---|---|---|
| Effective beats adoption; adoption-only → effective = adoption + `DATE UNCONFIRMED`; a bound before 2016-01-01 → `[predates]` at 2016-01-01; a bound inside the window → `[earliest-known]` + a human task for the first-allowed date | `dates.resolve` | L-D1–D4 |
| "No ADUs" era: `adus_per_lot = 0`, `by_right = False`, `NO ADU RULE` prefix; cannot be by right or allow detached | `coding.check`, `rows.build` | L-F1 |
| Moratorium: in-force no-ADU era tagged `[moratorium]` (no `suspended` status exists) | `coding.Era`, `check` | L-F4 |
| Tags only from the fixed list; never a tag string in prose | `coding.TAGS` | L-F14 |
| Eras chained by `supersedes`; earlier era ends on the successor's effective date; ids `<ST>-<geoid>-adu-<year>[b…]` | `rows.build` | L-D10 |
| Blank = unknown; unresolved coder disagreements are blanked, never guessed | `reconcile.merge` | L-F3, L-S7 |
| `coder_agreement`: `agree` only if every value agreed on primary evidence; `adjudicated` after the verifier; else `single_coder` | `reconcile.coder_agreement` | L-S3 |

Rules the agents apply (in their prompts, checked by the verifier): absolute size caps only (L-F5); by-right
and `[detached-conditional]` (L-F6); parking increment (L-F7); detached-only lot minimums (L-F8); coverage
lists vs citywide (L-F9, L-F10); what is not an ADU (L-F11); state and GEOID on every source (L-F12); county
remainders only where one code governs (L-F13); state law per covered place and local-first check (L-D7, L-D8).

## 5. Confidence flags

Per value: `high` (primary source, unambiguous text), `medium` (secondary source, or primary but needs a
reading), `low` (inferred from context; the verifier must confirm or blank it). Per place, `outcome`:
`coded`, `partial` (some eras or fields blocked) or `no_usable_source`. Per row, `coder_agreement` and tags.
The report counts values by confidence and agreement so the user sees at a glance what rests on what.

## 5a. First-pass score: second look only where evidence is weak

The NC dry run second-coded everything: the blind coder took about 40% of the tokens, mostly re-deriving
values already quoted verbatim from an official source. Now `score` (`score.py`) rates each value of the
first coding:

- **strong**: `high` confidence, a primary source, and the quote found by machine in the cached text copy
  (HTML, or a text PDF on the page the coder named; pypdf). Dates: as above, and not `DATE UNCONFIRMED` or
  `[earliest-known]`.
- **weak**: anything else, with the reasons listed; also a core field the coder left out with no blocked
  source to explain it.
- **uncoded amendment**: an ordinance the scout listed (2016 or later) whose year matches no coded era. This
  catches the NC dry run's main miss (Raleigh 2022, Wilmington 2022), which no value-level score could.

A place with nothing weak skips the second coder; otherwise the second coder, still blind, recodes only the
weak fields (dates always, so eras can be matched) and resolves the amendments. `diff-coders` and `merge`
then compare only those fields (`--score`), and the rows say which fields had the second look. A fixed ~10%
sample of places (chosen by a hash of the GEOID, so reruns pick the same ones) is second-coded in full: the
report counts how many strong values it contradicted, which is the check that the score can be trusted.
On the NC dry run's first codings (rescored after the PDF text fix), all 71 quotes were found by machine;
1 place would skip the second coder (Matthews: nothing coded) and 4 get targeted looks, because most first
values there were `medium` (mirrors, news, a Cloudflare-walled code).

## 6. Retrieval policy (L-R1–R9)

Agents fetch only through `python -m lotline.rule_agents.adu fetch --state ST <url>` — no WebFetch, curl or
browser user agents on official hosts. The helper reads robots.txt first and honours rules for `lotline`,
`ClaudeBot`, `Claude-User` and `anthropic-ai` (a disallow for any of them stops the request; 5xx robots =
assume disallowed, RFC 9309); waits 3 s per host across processes; never retries a block and stops using a
host for the run after a 403, challenge, 429 or login wall; refuses http-only URLs; caps size at 15 MB;
caches the copy and its text under `LOTLINE_DATA_DIR` with a manifest line; flags scanned PDFs. WebSearch is
allowed for discovery (it reads a search engine, not the site). Known script-friendly alternatives (Legistar
API, Municode PDF blob, `files.amlegal.com`, Wayback) are tried before handing off; mirrors only as secondary.

## 7. Human hand-off format

`tasks.csv` (one row per place + question, largest place first; columns in `handoff.COLUMNS`) and `tasks.md`
(a checklist with the same content). Each task says: the URL to open (plus alternatives), why the agent
stopped in plain words, what to look for, exactly which fields to fill with their allowed values, an estimate
in minutes, and **done when**: every field filled (or "not found") with the URL read and a verbatim sentence;
dates with the ordinance number where shown. `ingest` accepts only rows marked `done` with an https URL and a
quote; accepted answers become `human_primary` evidence and re-enter at step 5. Questions only a records
request or staff could answer are closed at once as `no_usable_source` (L-H1).

## 8. Holdouts and other guards

The service's shared principles are in `docs/build/rule-agents/PRINCIPLES.md` (the table is a proposal the
user imports; rules, not rates; GEOIDs and existing headers; no workarounds; no outcome data for held-back
places; coders blind to existing rows). The shared core will live in `src/lotline/rule_agents/common/`; ADU
moves onto it after that lands.

- `worklist` prints the state's still-blind holdouts (`lotline.validation.holdout`). Their rules may be coded;
  agents open no permit data, ADU dashboards, staff reports with activity counts, refits or `reports/`, and
  drop any search snippet quoting permit numbers (L-O1). The check lives in every agent prompt.
- No engine, scenario, calibration or dev-run script is ever run (L-O2).
- Nothing in `config/` is edited by the swarm (L-O3).

## 9. Cost

Per place, a scout pass (≤ 8 searches, ≤ 10 fetches), one coder (≤ 4 searches, ≤ 10 fetches), a targeted
second look on weak values only (§5a) and a verifier pass on diffs only. Batches of about five places per
agent keep the shared prompt cost low. Blocked hosts are dropped after one refusal, so a fully blocked place
costs one scout pass plus tasks. `--second-coder off` skips the
second look entirely and marks every row `single_coder`; `--second-coder full` is the dry run's setup.

## 10. Reuse by the other categories

The fetch layer, evidence model, human-task format and second-coder protocol are not ADU-specific; see
[`SHARED_CANDIDATES.md`](SHARED_CANDIDATES.md). The ADU-specific parts are the rubric fields, the eras logic,
the date rules' window, and the agents' coding rules.
