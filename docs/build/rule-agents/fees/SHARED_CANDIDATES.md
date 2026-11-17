# Components the fees, ADU and missing-middle swarms should share

*For the parent session to merge. The fees swarm built its own copy of each (in `src/lotline/rule_agents/fees/`)
so it could be tested now; none of it is fees-specific except where noted.*

| # | Component | Fees version | What is shared | What stays per category |
|---|---|---|---|---|
| 1 | **Polite fetch + robots layer** | `access.py` (`robots_allows`, `access_reason`), `cli.py fetch/robots` | robots.txt check before the first request to a host; block detection (403/401/429, challenge and login pages, with a length guard so a long page naming a CDN is not a block); "a block ends automated access to that host for the run"; per-host spacing; downloads only through `lotline.io.http.fetch` into `LOTLINE_DATA_DIR/raw/<source>/` with manifest entries | the raw source name |
| 2 | **Quote check** | `access.normalise`, `access.quote_found`, `cli.py quotecheck` | word-for-word match after NFKC, quote/dash and whitespace normalising; `...` splits a quote into ordered parts; `quote_status` = verbatim / image_read / summariser / none | nothing |
| 3 | **Evidence fields** | `records.FeeItem` evidence block | `url`, `local_path`, `sha256`, `retrieved_at`, `page_or_section`, `quote` (≤300 chars, the schema limit), `quote_status`, `source_kind` (official / wayback / mirror / draft / guide), `coder`, `verified_by`, `verified_date`, `confidence` | the value fields (fees: amount, basis; rules: by_right, max_sqft, …) |
| 4 | **Confidence rule** | `build.confidence` | high = verbatim/image_read + official + blind second coder agrees; medium = read evidence, single coder; low = summariser / mirror / draft / guide / unresolved disagreement, held back from the proposed rows | nothing |
| 5 | **Human task format** | `handoff.py`, `HANDOFF_FORMAT.md` | one task per (place, body or document, field group); reason codes; `start_url`, `look_for`, `fields_to_fill`, `done_when`, `priority`, `est_minutes`, `status`; `answer_*` columns; CSV + markdown; `ingest` turns answers into items coded `human:<initials>`; **no records-request / email / phone reason** (Ben's rule) | the `answer_*` columns, which mirror each category's value fields |
| 6 | **Blind second-coder protocol** | `rules-fees-second-coder.md`, `reconcile.py` | second coder gets only place + source list; never sees coder 1; pairing → agree / partly / differ / only_coder1 / only_coder2; only `agree` fills `verified_by`; reconciler fixes slips with a quote and sends judgment calls to Ben (no majority vote) | the pairing key and the "same value" test (fees: amount within 0.5% or $1; rules: field equality) |
| 7 | **Run folder layout** | `/rules-fees` command | `$LOTLINE_DATA_DIR/rule-agents/<category>/<ST>/<date-time>/`: plan.json, places.jsonl, sources.jsonl, items.coder1/2.*.jsonl, pairs.jsonl, items.final.jsonl, decisions.md, tasks.*.jsonl, human_tasks.csv/md, report.md; never committed; merge into `config/` only through a dated, reviewed script | file names of the category's rows |
| 8 | **Date basis** | `build.schedule_year` | adopted vs effective kept apart; `date_basis` token (effective_date / fiscal_year_start / fy_label_range / fy_label_end_year_assumed / schedule_label / read_date); Wayback is evidence of its capture date only | fiscal-year handling is fees-specific |
| 9 | **Agent rules file** | `AGENT_RULES.md` | hard stop conditions (no UA change, no curl retry, no summariser numbers, no records requests, no model runs, budgets per place), the report-back length limit | the "what an item is" section |
| 10 | **Notes tokens** | `build.py` | until the schema has columns for them, write `body= ; conf= ; quote_status= ; date_basis= ; coder= ; item=` at the start of `notes` so they can be moved into columns mechanically | — |

## Proposed schema change (one `contract-change` issue for all three)

Additive, optional columns on `fees` and `reforms`: `quote_status`, `confidence`, `retrieved_date`,
`source_kind`; on `fees` also `levying_body`. Today these live in free-text `notes`.

## Where shared code would live

`src/lotline/rule_agents/common/` (fetch/robots, quote check, evidence model, human tasks, reconcile skeleton),
with `src/lotline/rule_agents/__init__.py` added at merge time. The fees package currently relies on an implicit
namespace package for `lotline.rule_agents` so it does not create a file the sibling sessions also create.

## Proposed dependency (for Ben)

`pypdf` (BSD-3-Clause) to extract PDF text so `quotecheck` can mark PDF quotes `verbatim` instead of
`image_read`. Most fee schedules are PDFs; today only HTML and text sources can be checked word for word.

## 11. Primary-document store (Ben's requirement, relayed 2026-11-17)

*Shared by all three swarms; designed here, not built as shared code. The fees package has only the thin
pieces it needs now (marked "fees now").*

**What exists today.** `lotline.io.http.fetch` downloads into `LOTLINE_DATA_DIR/raw/<source>/<vintage>/` and
appends a `manifest.jsonl` entry (url, path, accessed_at, sha256, bytes, source, license, etag). `DataStore.register`
records a file saved by hand the same way (hard link, no second copy). `provenance.py` renders the manifest into
`docs/data_provenance.md`. Ordinance work kept its own side lists instead: `manual/adu-rules-2026-11/<ST>/`
with a `downloads.jsonl`, `mn-source-evidence-register-2026-11-02.csv` (place, url, type, section, excerpt,
`pdf_downloaded`), and three PDFs committed under `docs/research/ordinances/source-pdfs/` (see the note at the
end). Nothing links a coded value to the exact bytes it came from, and nothing links one schedule to the next.

**Design.**

| Piece | Where | What it holds |
|---|---|---|
| Bytes | `raw/rule-agents/<st>/<file>` via `fetch`; hand-supplied files via `register` (source `rule-agents-manual`) | the document exactly as retrieved; manifest entry with sha256. **fees now:** `fetch` and `register` commands |
| Doc ID | the file's **sha256** | every coded value cites `doc_id` + url + retrieved date + page/table + quote. Same bytes from two URLs or two places = one doc (dedupe across places and categories for free). **fees now:** `FeeItem.sha256` is the doc ID; `fetch` prints it |
| Text sidecar | `interim/docs/<sha256>.txt` (and `.pages.jsonl`: one line per PDF page once a PDF reader is approved) | plain text for search, quote checks and re-checking without re-downloading. **fees now:** written for HTML/text on `fetch`; `quotecheck` uses it |
| Doc index | `interim/docs/index.jsonl`, one line per doc_id | `doc_id, urls[], first_seen, last_seen, title, doc_kind` (fee schedule, rate ordinance, utility rules, budget book, ordinance, code section, council minutes), `issuer` (levying body / city), `jurisdictions[]` (GEOIDs it covers: a utility schedule covers many places), `categories[]` (fees / adu / mm), `label` ("FY2027"), `adopted_date`, `effective_date`, `supersedes` / `superseded_by` (doc_ids), `supplied_by` (`agent` or `human:<initials>`), `access` (ok / reason code) |
| History | `supersedes` links in the index | successive schedules of one issuer and doc_kind form a chain, so "what was in force in 2019" is a walk back along the chain; Wayback captures join the chain with their capture date |
| Human slot | `register <file> --url --issuer ...` | a person who opens a blocked page saves the PDF and registers it; it gets a doc_id, a sidecar and an index line marked `supplied_by=human:<initials>`, and answers to human tasks cite that doc_id |
| Queries | a small `docs` module: `find(issuer=, jurisdiction=, kind=, category=)`, `history(doc_id)`, `text(doc_id)`, `cited_by(doc_id)` | used by the scout (do we already have it?), the second coder (read the same bytes), the reconciler and the human-task packager (attach the doc already on disk) |

**Rules.** Index lines are append-only; corrections are new lines (latest wins), as the manifest does. Nothing
under `LOTLINE_DATA_DIR` is committed; the repo holds only rows that cite doc_ids and URLs. A doc is never
re-downloaded when its URL's manifest entry is current, so two swarms reading the same county code share one
copy.

**Schema proposal (adds to the one above):** optional `source_doc_id` (sha256) on `fees` and `reforms`.

**Note for Ben:** `docs/research/ordinances/source-pdfs/` holds three Sunfish Lake PDFs committed on
2026-11 (commit 0cf58b81). They are public records, but CLAUDE.md says downloaded documents stay in
`LOTLINE_DATA_DIR`; with a doc store they could move there and be cited by doc_id.
