# Shared components: candidates for one core used by the ADU, missing-middle and fee swarms

Written by the ADU swarm session for the parent session that merges the three. Nothing here is a shared core
yet: each swarm keeps its own copy under `src/lotline/rule_agents/<category>/` until the parent merges them.
The fees session's list (`docs/build/rule-agents/fees/SHARED_CANDIDATES.md` on its branch) proposes the same
four components; the differences below are what the merge has to settle.

## 0. Primary-document store (Ben's added requirement, 2026-11-17)

"An intelligent way of storing and referencing primary documents and other necessary data." Proposed as one
store for all three swarms, because one county or city code routinely serves ADU, missing-middle and fee
coding. ADU's code already cites `doc_id` (sha256) in every `Evidence` and returns it from `fetch`; the
store below is what that id points into. Not built here (shared; for the parent).

**What exists today (and its gaps).**
- `manifest.jsonl` (`lotline.io.store`): url, path, accessed_at, sha256, bytes, source, license, adapter —
  every download, append-only. Good provenance, but keyed by path, not content; `lotline.io.http.fetch`
  raises `RawOverwriteError` if a second URL would write the same path, so it cannot be the content-addressed
  path itself.
- `DataStore.register` already records a hand-saved file into `raw/<source>/<vintage>/` with its sha256.
- Ad-hoc stores to fold in: `manual/adu-rules-2026-11/<ST>/` (PDF + `.txt` sidecars, `downloads.jsonl` with
  url, sha256, place), `manual/nc_udos/`, `manual/mn/`, `manual/ohio/`, `manual/texas/`, `manual/nc_fees/`;
  the MN inventory and evidence register CSVs (`docs/research/ordinances/mn-downloaded-pdf-inventory-…`,
  `mn-source-evidence-register-…`); and three Sunfish Lake PDFs **committed in the repo** under
  `docs/research/ordinances/source-pdfs/` (move them to the store; flag for Ben).
- No index answers "which documents do we hold for Raleigh / for this county code / that mention ADUs".

**Layout** (all under `LOTLINE_DATA_DIR`, never in the repo):

```
raw/rule_docs/by_url/<host>/<sha1(url)>/<YYYY-MM-DD>.<ext>   downloads via lotline.io.http.fetch (manifest line)
docs/blobs/<sha[:2]>/<sha256>.<ext>                         hard link to the bytes: one blob per content
docs/blobs/<sha[:2]>/<sha256>.txt                           extracted text, pages separated by \f
docs/blobs/<sha[:2]>/<sha256>.meta.json                     text_status, pages, extractor + version
docs/index.jsonl                                            append-only doc records (below); latest wins
docs/citations.jsonl                                        append-only: which coded value cites which doc
manual/rule_docs/inbox/                                     files a human saved by hand (picked up by `docs add`)
```

The download keeps going through the IO layer (manifest line, polite fetch); the blob is a hard link, so
dedupe costs nothing and two URLs serving the same bytes (a city PDF and its Municode copy, the same county
code fetched by the ADU and fee swarms) become one `doc_id`.

**Doc record** (`docs/index.jsonl`): `doc_id` (sha256), `urls[]` (every URL that served these bytes, with
retrieval dates), `wayback_of`, `mime`, `bytes`, `pages`, `text_status` (`text` / `scanned` / `image_read` /
`none`), `title`, `publisher` (city, municode, amlegal, ecode360, legistar, state, wayback, mirror),
`doc_type` (code_section, code_full, ordinance, minutes, agenda_packet, staff_report, fee_schedule,
state_law, city_page, mirror, news, draft), `jurisdictions[]` (GEOIDs it governs: a county code lists the
county and every township or town that adopted it), `states[]`, `categories[]` (grows as swarms cite it),
`dates_in_doc` (adopted / effective / codified dates the coders read in it), `supersedes` (the earlier
doc_id from the same URL), `added_by` (run id or `human:<initials>`), `may_contain_outcomes` (staff reports,
dashboards: a holdout guard), `notes`.

**Citation record** (`docs/citations.jsonl`, written by the row builders): `doc_id`, `page`, `section`,
`quote`, `quote_status` (verbatim / image_read / human), `category`, `reform_or_fee_id`, `field`, `run_id`.
This is the join that lets the verifier, a judge or Ben go from any coded cell to the exact bytes and page,
and from any document to every cell it supports (so a document found to be the wrong town or an unrelated
ordinance, lessons L-D9/L-F12, can be withdrawn everywhere at once).

**Commands** (one CLI for all swarms, e.g. `python -m lotline.rule_docs …`):
- `add <file> --url <where it came from> --geoid … --type ordinance` — human-supplied docs: wraps
  `DataStore.register`, links the blob, extracts text, indexes with `added_by = human:<initials>`. The human
  task's answer can cite the new `doc_id` instead of a URL when the document is not online.
- `find --geoid G [--category adu] [--type ordinance] [--text "accessory dwelling"]` — search the index and
  the text sidecars; the scout runs this **before** searching the web (saves budget; L-R9), the packager uses
  it to attach already-held alternatives to a task, the verifier to re-open a cited page.
- `show <doc_id>` (record + local path), `quote <doc_id> "<quote>"` (found? on which page?), `text <doc_id>
  [--page N]`.
- `backfill` — one-off import of the ad-hoc manual folders, `downloads.jsonl` files and the MN inventory.
- `catalog --write` — a committed, data-free catalogue `docs/research/rule_docs_catalog.csv` (doc_id,
  first URL, title, jurisdictions, categories, retrieved): judges can re-fetch each document and check it by
  hash, which serves Replicability without committing any document.

**Text sidecars.** HTML → text with the standard library (as ADU's `fetch.html_to_text`). Text PDFs →
`pypdf` (BSD-3, needs Ben's OK) with `\f` page breaks so quotes resolve to pages; without it, the Read tool
reads PDFs and the quote check for PDFs stays by eye. Scanned PDFs → `text_status = scanned`; a quote read
off the image is `quote_status = image_read`, never `verbatim` (L-R7). No OCR dependency proposed.

**Guards.** Docs flagged `may_contain_outcomes`, or tied to a blind holdout's GEOID, are listed with a
warning by `find`; agents must not open them while that holdout is blind (L-O1). The store never deletes:
withdrawing a document is an index record (`withdrawn: reason`), so earlier runs stay reproducible.

## 1. Polite fetch layer (`adu/fetch.py`; fees `access.py`)

What ADU's has: robots.txt checked for `lotline`, `ClaudeBot`, `Claude-User` and `anthropic-ai` together
(any disallow stops; 5xx or no answer = assume disallowed, RFC 9309; 4xx = no rules); 3 s per host across
processes (lock file in `LOTLINE_DATA_DIR/.ratelimit/`); no retry after a block, and the host is dropped for
the rest of the run after a 403, challenge, 429 or login wall; https only; 15 MB cap; block classifier
(`http_403`, `waf_challenge`, `login_required`, `rate_limited`, `js_only_viewer`, `not_found`, `http_error`,
`no_answer`, `too_large`, `scanned_pdf`, `robots_disallow`, `robots_unavailable`, `not_https`); copies cached
under `raw/rule_agents/<category>/<ST>/<host>/` with a `manifest.jsonl` line; HTML reduced to text with the
standard library; quote check that normalises whitespace, quote marks, dashes and case and splits on `...`;
`KNOWN_BLOCKERS` / `KNOWN_ALTERNATIVES` host tables.

To settle: one classifier vocabulary (fees and ADU use near-identical reason codes); the run-folder spelling
(`rule_agents` here vs `rule-agents` in fees); whether to fold the rate limit into `lotline.io.http.MIN_INTERVAL`
(a contract change for WS-CORE) or keep a rule-agent-only lock.

## 2. Human lookup format (`adu/handoff.py`; fees `handoff.py`)

Shared shape: one task per place + question; reason code with plain-language "why the agent stopped" and
"what to do"; URL + alternatives; what to look for; exact fields to fill with allowed values; estimate in
minutes; "done when" acceptance (URL + verbatim sentence + section); answer columns; ranked largest place
first; stable `task_id` (hash of place, era, fields, URL); CSV for answers, Markdown checklist for reading;
ingest accepts only rows with an https URL and a quote. Records-request-only questions are closed at once as
`no_usable_source` (Ben's rule). The category-specific part is only the `ALLOWED` field table.

## 3. Evidence model (`adu/coding.py` `Evidence`)

ADU fields: `url` (https), `retrieved`, `quote` (<= 300), `section`, `kind` (primary: official_code,
ordinance, staff_report, minutes, state_law, human_primary; secondary: city_page, mirror, news, draft,
human_secondary), `archived_from` (live URL of a Wayback copy), `cache_path`. Fees adds `sha256` and
`quote_status` (verbatim / image_read / summariser / none); ADU should adopt both (`image_read` matters for
scanned PDFs). Shared rule: only primary evidence can be `high` confidence; agreement on secondary evidence
alone is not agreement.

## 4. Second-coder protocol (`adu/reconcile.py`; fees `reconcile.py`)

Shared: a blind second coder sees only the scout's sources, never the first coding; field-by-field compare
with statuses agree / one-side-only / disagree (+ ADU's `agree_secondary` and era-level `era_a_only` /
`era_b_only`, needed wherever a category has versions over time); a verifier re-opens sources only for the
differences and rules a / b / blank / human, quoting the section; undecided differences are blanked and become
human tasks; `coder_agreement` = agree only when everything agreed on primary evidence. The category-specific
part is how records are matched (ADU: eras by effective date, then year; fees: schedule items).

## 5. Date resolver (`adu/dates.py`)

MM needs the same rules (effective beats adoption; adoption-only -> `DATE UNCONFIRMED`; recodification or
code-edition dates are bounds, never events; `[predates]` at the window start; `[earliest-known]` inside the
window). Candidate for the shared core with the window start as a parameter. Fees dates schedules differently
(fiscal year, "current"), so it may only share the date-evidence type.

## 6. Proposals that touch shared contracts (for WS-CORE / Ben, not done here)

- `schemas.Reforms`: no change needed for ADU. Optional additive columns all three could use:
  `confidence` (per row: lowest field confidence), `date_basis` (effective / adoption / earliest-known /
  predates — today this lives in tags inside `coding_notes`, which are fragile to match, lessons L-F14), and
  `evidence_ref` (a pointer to the run's evidence file for the row). Same as the fees proposal for
  `quote_status`, `confidence`, `retrieved_date`, `source_kind` if the parent prefers per-row provenance.
- Dependency `pypdf` (BSD-3-Clause) for PDF text: not added by ADU (the Read tool reads PDFs); fees proposes
  it. If added, `fetch.py` should write a `.txt` next to every text PDF so `verify-quotes` covers PDFs too.
- `src/lotline/rule_agents/__init__.py` is left to the parent (implicit namespace package meanwhile).
