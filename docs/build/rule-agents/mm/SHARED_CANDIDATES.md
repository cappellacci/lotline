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

## 10. Primary-document store (Ben's added requirement, 2026-11-17)

"The swarm should also have an intelligent way of storing and referencing primary documents and other
necessary data." Proposed as **one shared store for all three categories**; MM keeps only the category bits.

### What exists today

- `lotline.io.http.fetch` writes raw files under `LOTLINE_DATA_DIR/raw/<source>/<vintage>/` and appends a
  `ManifestEntry` (url, path, accessed_at, **sha256**, bytes, source, license, adapter) to `manifest.jsonl`;
  `DataStore.register()` does the same for a file downloaded by hand (hard-links it into `raw/`).
  `lotline provenance` renders the manifest into `docs/data_provenance.md`.
- Rule documents are scattered: `~/lotline-data/manual/{mn,nc,ohio,texas,adu-rules-2026-11,...}/` (Ben's and
  agents' PDFs, logged in ad-hoc `downloads.jsonl`), two MN registers in the repo
  (`mn-downloaded-pdf-inventory-2026-11-02.csv`: place, filename, source_url, title, official, status;
  `mn-source-evidence-register-2026-11-02.csv`: place, source_url, source_type (≈150 free-text variants),
  section, excerpt, dates_status, pdf_downloaded). Coded rows cite only a URL, so the exact bytes a value came
  from cannot be found again.
- **Three Sunfish Lake PDFs are committed in the repo** (`docs/research/ordinances/source-pdfs/`), against the
  no-committed-data rule. They should move into the store below and leave git (Ben's call; not done here).

### Proposed design (`src/lotline/rule_agents/common/docs.py`, used by all three swarms)

1. **Content-addressed identity.** `doc_id` = the sha256 of the bytes (already in every manifest entry). The
   same bytes fetched from two URLs, for two places or by two categories are one document. A URL whose bytes
   change is a new `doc_id`; both versions stay (the manifest's supersession log already handles this).
2. **Storage stays in the IO layer.** Fetches keep going through `lotline.io.http.fetch` into
   `raw/rule_docs/<host>/<sha256[:2]>/<sha256><ext>` (one shared source name `rule_docs`, not one per run or
   category, so dedupe is automatic and the manifest has one provenance entry per document). Files a person
   supplies go through `DataStore.register(file, source="rule_docs_manual", url=<page it came from>,
   vintage=<date>)`. Nothing under the repo.
3. **Sidecars beside each blob:** `<sha>.txt` — extracted text with `=== page N ===` markers (HTML → text;
   PDF → text layer, or the text a coder read from the page image, marked `image_read`); `<sha>.meta.json` —
   `doc_id, urls[], first_seen, title, publisher, doc_kind` (controlled: `code`, `ordinance`, `minutes`,
   `staff_report`, `fee_schedule`, `city_page`, `state_law`, `archive`, `mirror`, `news`, `manual`),
   `jurisdictions[]` (GEOIDs it covers: a county code covers its unincorporated area and any town that adopts
   it), `pages, text_method, draft_markers, signed (yes/no/unknown), effective_dates_seen[]`,
   `cited_by[]` (category, run, reform_id or fee key, field).
4. **One index:** `LOTLINE_DATA_DIR/rule_docs/index.jsonl`, append-only, one line per (doc_id, event):
   `seen` (fetch or register), `cited`, `verified` (quote re-found), `superseded`. A small reader builds the
   current view (pandas) and answers: docs for a GEOID (any category), docs for a URL, citations of a
   doc_id, docs with no text layer, docs cited by unverified rows. `grep`-style text search runs over the
   `.txt` sidecars.
5. **Citations.** Every coded field cites `doc_id + url + retrieved + page/section + quote` (MM's `Evidence`
   now carries `doc_id`; fees' `sha256` is the same thing). `rows.py` can write `doc_id` into
   `coding_notes` ("Sources: …") until the schema has a column.
6. **Who uses it.** Scouts query the index by GEOID **before** searching, so a county code fetched for ADUs is
   reused for MM and fees (no second fetch, no second robots check). The verifier re-finds quotes in the
   sidecar by `doc_id` (no network). The hand-off packager lists the docs already held for the place so a
   person does not re-download them, and turns a person's answer + file into a `register()` call and a
   `cited` event. Ben's existing folders and the two MN registers are imported once by a migration script
   (register each file, map `source_type` to `doc_kind`).
7. **Holdout safety.** The index stores rule documents only; staff reports with permit counts are flagged
   `contains_outcomes: true` in meta and never shown to coders of a held-out place.

### MM-specific today

`fetch.FetchResult.doc_id` and `Evidence.doc_id` (sha256) are in place; snapshots still sit under
`raw/rules_mm/<run>/`, and `.txt` sidecars are written by the coder for PDFs. Moving to the shared store
changes only `fetch.get`'s destination and adds index writes.
