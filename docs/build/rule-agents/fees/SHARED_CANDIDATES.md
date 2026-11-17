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
