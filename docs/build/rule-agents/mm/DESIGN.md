# Missing-middle rule agent swarm: design

Status: prototype, 2026-11-17 (branch `claude/rule-agent-mm-4aa182`). Lessons it builds on: `LESSONS.md` (IDs such
as R-5, M-2 below refer to it). Dry run: `DRY_RUN.md`. Parts the ADU and fee swarms could share:
`SHARED_CANDIDATES.md`.

## 1. What it does

`/rules-mm <STATE> [options]` researches **one rule category** (missing middle: rules that let 2–4 homes be
built on lots zoned for one house) for **one state**, place by place, and produces:

| Output (in the run folder) | What it is |
|---|---|
| `out/reforms_mm_<st>.csv` | Candidate `reforms` rows, theme `missing_middle`, validated against `lotline.schemas.Reforms`, in the same layout as `config/reforms/<st>.csv`. Ben merges what he accepts; agents never edit `config/`. |
| `out/human-lookups.csv` + `.md` | One task per source the swarm could not read: start URL, browser tip, what to look for, the exact columns to fill, acceptance rule. |
| `out/compare.csv` | Event year, final cap and date basis per place against the rows already in `config/reforms/<st>.csv` (when any). |
| `out/run-report.md` | Counts (places, rules, events, none rows, always-allowed, hand-offs, agreement), every major disagreement and how it was settled, places to check first. |

It does **not** code state preemption laws (a statute-driven generator does that, DT-7), confounders (parking,
moratoria: M-9) or anything outside MM, and it never runs the engine, scenarios or model scripts.

## 2. Pipeline

```
/rules-mm MN --limit 5                          (orchestrator = the command, in the main session)
  │
  ├─ 0 init + places          CLI: init, places      -> places.csv           (deterministic)
  │
  ├─ 1 scout      ×N places   rules-mm-scout         -> sources/<geoid>.json (URLs + routes, no values)
  │
  ├─ 2 coder A    ×N places   rules-mm-coder         -> findings/<geoid>.coder-a.json
  │    coder B    ×N places   rules-mm-coder (blind) -> findings/<geoid>.coder-b.json
  │       (both fetch only through the CLI `fetch`, robots first, one try; blocked -> Blocker)
  │
  ├─ 3 check                  CLI: check             -> problems list; coder re-run once per place
  ├─ 4 reconcile              CLI: reconcile         -> reconcile/<geoid>.json (field diffs)
  │    adjudicate ×places w/ diffs  rules-mm-reconciler -> final/<geoid>.json
  ├─ 5 verify     ×N places   rules-mm-verifier      -> verify/<geoid>.json; sets verified_by or demotes
  ├─ 6 [optional] browser check of hand-offs, orchestrator in the main session, Ben present (R-6)
  ├─ 7 build + handoff + compare   CLI               -> out/*.csv, out/human-lookups.*
  └─ 8 report                 orchestrator           -> out/run-report.md
         later: Ben answers lookups -> CLI ingest -> re-run steps 2–8 for those places only
```

Agents run as Claude Code subagents (`.claude/agents/rules-mm-*.md`). The orchestrator runs places in parallel
batches (default 4 at a time per stage) and moves a place to the next stage as soon as it is ready.

## 3. Run brief and folder

The orchestrator writes `brief.md` into the run folder before stage 1; every agent reads it first.

- `state`, `run_id`, run folder: `$LOTLINE_DATA_DIR/rule_agents/mm/<ST>/<run_id>/` (outside the repo; snapshots go
  under `$LOTLINE_DATA_DIR/raw/rules_mm/<run_id>/` and into `manifest.jsonl` through `lotline.io.http.fetch`).
- `window`: research rules in force from 2010-01-01 (the panel window) and anything earlier that is still in
  force (it is coded `predates`).
- `state_rules` (DT-1): the state's default effective-date rule for ordinances, e.g. Ohio R.C. 731.29 (30 days
  after passage unless emergency), Minn. Stat. §645.15 / city charter, NC: on adoption unless stated, TX: on
  passage unless stated, Oregon: 30 days unless emergency clause. The orchestrator fills it from this table
  or asks Ben for a new state.
- `state_law_rows`: state preemption rows already in `config/reforms/<st>.csv` (GEOID = 2-digit state, or
  per-place rows written by a generator). Coders code local rules only.
- `holdouts`: places whose outcomes are held out (from `config/states/<st>.yaml`). Their rules may be coded;
  no permit or housing counts may be written anywhere (M-10).
- `budgets` (§4) and `limit`.

Folder: `places.csv`, `brief.md`, `sources/`, `findings/`, `reconcile/`, `final/`, `verify/`, `answers/`,
`out/`. Every JSON file validates against the models in `src/lotline/rule_agents/mm/findings.py`.

## 4. Agents

| Agent | Model | Tools | Reads | Writes | Stop rule (per place) |
|---|---|---|---|---|---|
| orchestrator (`/rules-mm`) | session model | all | brief, CLI output | brief, run-report | ends after stage 8 or when Ben stops it |
| `rules-mm-scout` | haiku | WebSearch, Bash (CLI `fetch` only), Read, Write | brief, places row | `sources/<geoid>.json` | ≤ 8 searches, ≤ 6 fetches; stop once it has the current code's residential use table + one adoption record per candidate rule |
| `rules-mm-coder` (A, B) | sonnet (A), opus or a different tier (B) when available (S-4) | WebSearch, Bash (CLI only), Read, Write | brief, sources file, snapshots | `findings/<geoid>.coder-<x>.json` | ≤ 12 fetches, ≤ 10 searches; stop when every rule has dates + cap + prior cap with evidence, or every gap has a Blocker |
| `rules-mm-reconciler` | sonnet | Bash (CLI), Read, Write | both findings, diffs, snapshots | `final/<geoid>.json` | ≤ 4 new fetches; a diff it cannot settle from the cited text becomes a Blocker and the field is left blank |
| `rules-mm-verifier` | haiku | Bash (CLI `quote`), Read, Write | final, snapshots | `verify/<geoid>.json`, updates `final/` | no fetching; one pass |

The deterministic steps (place list, fetch, checks, diff, hand-off packaging, schema validation, comparison)
are Python in `src/lotline/rule_agents/mm/` with tests in `tests/rule_agents/mm/`, called through
`python -m lotline.rule_agents.mm <step>`. The "human-lookup packager" and "schema validator" of the brief are
these CLI steps, not agents: they must give the same answer every time.

### 4.1 Scout (source discovery)

Finds, does not code. Routes, in order (R-3): the city's Legistar Web API (`webapi.legistar.com/v1/<client>/
matters?$filter=...`) → the city's own code page / UDO PDF → council minutes and agenda packets (CivicPlus
AgendaCenter, Granicus) → county/BOCC agendas → Wayback copies of any of these (also for the predecessor
code, R-4) → mirrors (Zoneomics: lead only, R-7) → news (lead only). Output: a ranked list of
`{url, route, what_it_should_show, fetched: path|blocker}`, the place's code host (`access.host_label`) and
the search queries used. Same-name places in other states are rejected by checking state names in results
(R-8).

### 4.2 Coder (first and second)

Answers one question per place, the one the 2026-11-11 checks used: **"When did 2–4 homes first become
allowed on lots zoned single-family, by right or by permit, in which districts, and what did the code allow
just before?"** Writes one `PlaceFinding`: a `RuleFinding` per dated change (amendments are new rules with
`supersedes_effective`), a "none" rule (`unit_cap` 1) when nothing allows 2–4 homes (M-3), or Blockers. Field
rules are in the agent file (cap semantics M-1, approval codes M-5, coverage M-6, dates DT-1–DT-6, tags via
`date_basis`, never in notes). Every coded field needs an `Evidence` entry (URL, verbatim quote ≤ 300
characters, section, retrieval date, snapshot path, source kind); news, mirrors and search summaries cannot
stand alone (`findings.LEAD_ONLY`, R-7). PDFs: use tables are read from the page image (P-1); drafts are
checked with `draft_markers` (P-3).

**Blindness (S-1):** coder B gets the brief, the place row and the scout's source list, never coder A's file,
and is told to search for the predecessor code and for later amendments on its own. The orchestrator starts B
only after confirming A's file is not in B's prompt.

### 4.3 Reconciler

Runs `reconcile` (field-by-field diffs, rules paired by effective date, `reconcile.py`). For each diff it
re-reads both coders' cited passages and decides, writing one line per decision into `adjudication`
(becomes "Reconciled: …" in `coding_notes`). Major diffs it cannot settle → the field is blanked and a
`conflicting_sources` Blocker is added (H-5: unresolved stays unresolved). `coder_agreement` = `agree` (no diffs)
or `adjudicated`; a place only one coder could code stays `single_coder` (S-2).

### 4.4 Verifier

Independent of both coders. For every evidence entry: `python -m lotline.rule_agents.mm quote <snapshot>
"<quote>"` must print `found` (PDFs: the coder saved the page text beside the PDF); the place name and state
appear in the source (R-8); no draft markers for adoption/effective evidence (P-3); the quoted text actually
says what the field claims (e.g. the quote for `unit_cap` names the number of units). All pass →
`verified_by = rules-mm-verifier`, `verified_date` = today. Any fail → the evidence entry is dropped, the
field is blanked if nothing else supports it, confidence drops to `low`, and the reason goes in
`verify/<geoid>.json`.

### 4.5 Browser check (optional, R-6)

Code-host walls (Municode, American Legal, eCode360) are where most MM answers live. When Ben is present and
asks for it, the orchestrator opens each priority-1 hand-off in the built-in browser **one page at a time**,
reads it, and **stops on any challenge, CAPTCHA or login** (never solves or bypasses one). Results are
written as answered rows in `human-lookups.csv` with `checked_by = rules-mm-browser` and go through `ingest`
like a person's answers. Background subagents never drive the browser.

## 5. Evidence and confidence

- **Every coded field cites URL + verbatim quote + retrieval date** (and section and snapshot). `findings.check`
  enforces it; `rows.py` writes the main quote to `source_quote` and *every* entry into `coding_notes`
  ("Sources: …"), so nothing cited is lost.
- **Confidence** (per rule): `high` = signed ordinance or official code + adoption record, both coders agree,
  verifier passed; `medium` = official source but one coder, or minor diffs adjudicated; `low` = verifier
  failed something, mirror-only, or a computed date. Mirror-only can never be `high` (checked). Confidence
  goes into `coding_notes` today; see Proposed schema changes.
- **Date basis** maps one-to-one onto the engine's tags (`dates.py`, DT-5); only `rows.py` writes tags.
- **Prior cap (M-2):** every dated event carries `prior_cap` with evidence from the code just before (often a
  Wayback copy and the new code's district-conversion table). `prior_cap ≥ unit_cap` fails the check: it is a
  recodification (`predates`) or a standards route (`standards_only`).

## 6. Human hand-off

`python -m lotline.rule_agents.mm handoff RUN` writes one row per blocked source (deduplicated across coders,
priority 1 when it hides a date or cap, then by population). Columns:

`task_id, state, place, geoid, priority, blocker, start_url, browser_tip, look_for, fields_to_fill, acceptance`
then answers: `result (found / not_found / no_usable_source), max_homes_per_single_family_lot (1–4),
by_right (yes/no), adopted_date, effective_date (YYYY-MM-DD), districts (;-separated), ordinance, source_url,
quote (≤ 300), checked_by, checked_on, notes`.

The Markdown checklist lists the same tasks with the browser tip for the code host. Records-request-only
sources produce no task (R-10). `ingest` refuses answers without a quote or with malformed dates (H-3) and turns
good ones into `human_lookup` evidence; the orchestrator then re-runs the coder for just those places with
the answers attached. The format is built for Ben **or his own browser agent** (H-2).

## 7. Safety and project rules (in every agent file)

1. robots.txt first, for our token and Claude's (`fetch.AGENT_TOKENS`); disallowed → Blocker. One attempt per
   URL; never retry a refusal with curl, another user agent or browser headers (R-5). Network access only via
   `python -m lotline.rule_agents.mm fetch` or WebFetch/WebSearch after the robots check.
2. No records requests, no emails or forms to staff (R-10).
3. Never write permit, housing or outcome counts (holdouts, M-10). Never open permit or BPS data.
4. Never edit `config/`, `src/`, `docs/` or any repo file; everything goes in the run folder.
5. Never run engine, scenario, calibration or `lotline` model commands.
6. Downloaded files stay in `LOTLINE_DATA_DIR`; never in the repo.

## 8. Cost

Batch 1 spent ~107k tokens per city with one coder (R-9). Budget target here: scout (haiku) ~15k, two coders
~60k each, reconciler ~15k for places with diffs, verifier (haiku) ~10k → ~150k per place, ~0.75M for a
5-place dry run, ~15M for a 100-place state. `--single-coder` halves it for a first pass; `--only` re-runs
places.

## 9. Proposed schema changes (for WS-CORE; not made here)

1. `date_basis` column (`dated | predates | earliest_known | unconfirmed`) instead of free-text tags in
   `coding_notes` (proposed before in `lbd/2026-10-21-ws-nc-4-rules-research.md`); the tags stay readable.
2. `prior_cap` (Int64): the cap in force just before the rule; makes the D-092 cap-rise reading explicit
   instead of inferred from earlier rows.
3. `confidence` (`high | medium | low`) and `standards_only` (bool) columns, replacing `[standards]`.
4. `source_kind` for the main source (controlled vocabulary; the MN evidence register had ~150 free-text
   variants).
Until then `rows.py` writes all four into `coding_notes` in a fixed form.

## 10. Open choices (for Ben)

See the PR description: model tiers for coder B, whether to add `pypdf` (BSD-3) for PDF text checks, whether
the browser stage may run unattended, and where answered hand-off sheets live in the repo.
