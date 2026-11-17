# Parts the MM, ADU and fee rule swarms could share

Written by the MM swarm session (2026-11-17) for the parent session to merge with the ADU and fee sessions'
lists. Nothing here is built as a shared core yet: each item lives in `src/lotline/rule_agents/mm/` today,
named so it can move to `src/lotline/rule_agents/common/` with little change. The MM tests in
`tests/rule_agents/mm/` would move with them.

| # | Component | MM file today | Why every category needs it | What would change on moving |
|---|---|---|---|---|
| 1 | **Polite fetch layer**: robots check for our token *and* Claude's (`lotline`, `Claude-User`, `ClaudeBot`, `anthropic-ai`), a robots.txt 403 closes the host, per-host spacing across processes (3 s), one attempt, snapshot under `LOTLINE_DATA_DIR/raw/rules_<cat>/<run>/` via `lotline.io.http.fetch` (so it is in `manifest.jsonl`), never another user agent | `fetch.py` | The Medford/Scott County/Charlotte incidents (LESSONS R-5) happened in ADU and fee work too | `source=f"rules_{category}:{host}"`; the raw folder name takes the category |
| 2 | **Blocker classifier + code-host table** (Municode, American Legal, eCode360, Code Publishing, Legistar, Granicus, CivicPlus, Laserfiche) with browser tips | `access.py` | Fee schedules sit on the same hosts | None |
| 3 | **Evidence model** (`field, url, quote ≤ 300, retrieved, section, snapshot, source_kind`) + `verify_quote` (normalised, ellipsis-aware) + `draft_markers` + `LEAD_ONLY` kinds (news, search summaries) and the mirror rule | `findings.Evidence`, `verify_quote`, `draft_markers` | The schema's citation columns (1.7) are the same for `reforms` and `fees` | `EVIDENCED_FIELDS` becomes per category |
| 4 | **Blocker model and human lookup sheet**: one task per blocked source, priority, start URL, browser tip, look-for, fields to fill, acceptance rule, closed `result` (found / not_found / no_usable_source), quote required, records-request-only never written; Markdown checklist; `ingest` with answer checks | `handoff.py` | Wide per-place sheets sat empty in every category (H-1) | Answer columns per category (MM: max homes, by right, dates, districts; ADU: allowed, size, owner-occupancy, parking; fees: amount, basis, building type, year); `_FIELD_COLUMN` and `_LOOK_FOR` become category tables |
| 5 | **Two-blind-coder protocol**: coder B never sees A's file or existing coding; different model tier; field diffs paired by effective date; minor/major severity; `agree / adjudicated / single_coder`; "could not read" is not agreement | `reconcile.py`, agent files | S-1, S-2, S-4 apply to every category | `KEY_FIELDS` per category; fee rows pair by (component, building type, year) instead of effective date |
| 6 | **Date-basis vocabulary and tag writer** (`dated / predates / earliest_known / unconfirmed` ↔ `[predates]`, `[earliest-known]`, `DATE UNCONFIRMED`) | `dates.py` | `rule_tags.py` reads the same tags for ADU and MM | None (fees use `year` / `in_force_through`, so only `parse_date` is shared there) |
| 7 | **Run folder, brief and CLI shape** (`init / places / fetch / quote / check / reconcile / handoff / ingest / build / compare`), holdouts and state-law rows in the brief, blind brief (no existing coded IDs) | `__main__.py`, `brief.py`, `places.py` | Same orchestration for all three | Category argument; `build` calls the category's row builder and `schemas.validate(df, "reforms" | "fees")` |
| 8 | **Verifier agent** (re-find quotes, right place and state, not a draft, quote supports value; never fetches) | `.claude/agents/rules-mm-verifier.md` | Category-independent | Step 4's "quote supports the value" examples per category |
| 9 | **Optional browser stage** run by the orchestrator in the main session, one page at a time, stop on any challenge | DESIGN §4.5 | Code hosts block every category | None |

## Not shared (MM-specific)

- `prior_cap` and the cap-rise check (M-2), none rows (`unit_cap` 1), `standards_only`, the coverage rules and
  the coder's MM question.
- `compare.py` (cap path and event year through `rule_tags`); ADU could reuse it with `adus_per_lot`.

## Proposed schema additions (all three would use them; WS-CORE decides)

`date_basis`, `confidence`, `source_kind` (controlled vocabulary) on `reforms` and `fees`; `prior_cap` and
`standards_only` on `reforms` (DESIGN §9).

## To settle at merge (after reading the ADU and fee sessions' notes, 2026-11-17)

- All three found the same four core pieces (fetch/robots, human task, evidence, blind second coder); ADU also
  has a date resolver that matches `dates.py` here.
- **Run folder:** MM and ADU use `$LOTLINE_DATA_DIR/rule_agents/<cat>/`, fees `rule-agents/<cat>/`. Pick one.
- **Evidence:** fees adds `sha256` and `quote_status` (verbatim / image_read / summariser / none). MM would take
  both: `image_read` is exactly the P-1 case (use tables read from the page image).
- **Reconcile labels:** fees uses agree / partly / differ / only_coder1 / only_coder2; MM uses minor/major diffs
  plus the schema's `agree / adjudicated / single_coder`. Keep the schema values as the output.
- **Package files:** none of the three creates `src/lotline/rule_agents/__init__.py`; the parent adds it.
  MM tests are `tests/rule_agents/mm/test_mm_agent_helpers.py` (with `tests/rule_agents/mm/__init__.py`).
- **Leak all three hit:** never show coders existing `reform_id`s (their years give the dates away). MM's brief
  omits them; the orchestrator keeps them in `places.csv`.
- **pypdf (BSD-3)** is proposed by fees too; MM would use it for `.txt` sidecars and scan detection.
