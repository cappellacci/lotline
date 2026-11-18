# ADU coding rules (read by every ADU rule agent)

Short, binding rules for coding one place's ADU history. Lesson IDs point to `LESSONS.md`. Output format is
`coding.PlaceCoding` (see `src/lotline/rule_agents/adu/coding.py`; example below).

## What to code

An **era** is one rule version. Code every era in force at any time from **2016-01-01 to today**, plus the
state just before the first one (often "no ADUs"), oldest first (L-S5, L-F2). A new era starts when any coded
field changes. Fields (blank = not found; never guess, never infer — L-F3):

| field | value | rule |
|---|---|---|
| `adus_per_lot` | int | 0 = no rentable ADU allowed (incl. guest/family/servants' quarters that may not be rented, units only by rezoning/SUP/board case) (L-F1). 1 only if the text says one (or "an ADU" per lot with an explicit limit). |
| `by_right` | bool | true if any qualifying ADU type is approved by staff alone ("permitted with standards", administrative permit). If detached needs CUP/SUP/IUP, still true and tag `[detached-conditional]` (L-F6). |
| `owner_occ` | bool | true only if the code (not a handout) requires the owner to live on site. "Owner or responsible person" = false. |
| `adu_detached_allowed` | bool | false if only attached/internal ADUs. A garage apartment is detached. |
| `adu_max_sqft` | number | absolute cap only. "% of house" only → blank + note. "Greater of X or Y%" → X is a floor → blank (L-F5). |
| `parking_min_per_unit` | number | extra spaces required **for the ADU**, not the lot total; 0 if "no additional parking"; blank if "1 per bedroom"/waivers (write `parking` = "depends; …") (L-F7). |
| `parking` | text | the parking rule in a few words, starting "No …" when none is required. |
| `min_lot_sqft` | number | lot area needed for any ADU; if it applies to detached only, blank + note (L-F8). |
| `coverage` | text | plain words: "all single-family districts", "R-1 and R-2 only", "Frequent Transit Areas only". |
| `coverage_zones` | text | `;`-separated district codes **only when the rule covers a subset** of single-family districts; leave blank for citywide (L-F9). Overlays go here or in notes, never as the citywide rule (L-F10). |

**Not ADUs** (don't code as ADU eras, L-F11): temporary family health-care dwellings, two-family principal
uses, accessory-structure footprint rules, farm manufactured homes, short-term-rental rules, a bill or draft
that did not pass (L-D9).

**Moratorium**: an era with `adus_per_lot = 0`, tag `[moratorium]`, in force (L-F4).

## Dates (record; don't decide)

For each era list every dated source as `DateEvidence` with `type`: `effective` (the ordinance's effective
clause or a dated notice), `adopted` (final passage), `vote` (a council vote reported elsewhere),
`codified` (a code edition, recodification or "current through" date), `first_seen` (earliest Wayback copy
or document showing the rule), `in_force_by` (a document saying it was in force on a date), `prior_to` (the era was the rule until a
dated reform, start unknown: use this for the "before" state), `announced`.
Never compute "+30 days" (L-D2). The helper resolves the dates (`dates.resolve`, DESIGN §4) and sets the date-quality tags (`[predates]`,
`[earliest-known]`, `DATE UNCONFIRMED`) itself: never put them in `tags` (only `[detached-conditional]` and
`[moratorium]` are yours). The quote for a
date must name the ADU ordinance or section — check it is the ADU ordinance and the right town (L-D9, L-F12).

## Evidence

- Fetch only with `uv run python -m lotline.rule_agents.adu fetch --state <ST> --run-id <ID> --geoid <G>
  <url>`: the shared core, **store first** (a document any swarm already holds is served with no request; a
  refusal any swarm met in the last 30 days is returned with no request). It prints JSON with `doc_id`,
  `blocker`, `cached`, `pages` and `text_path`. Before fetching, look in the store:
  `uv run python -m lotline.rule_agents docs find --geoid <G> --category adu`.
- Read with the shared tools, not whole files: `uv run python -m lotline.rule_agents outline <DOC>` (headings
  and pages), `… excerpts <DOC> adu` (short page-cited ADU passages), `… docs text <DOC> --page N`, and check a
  quote with `… docs quote <DOC> "<quote>"` (prints `verbatim p.N`). A `scanned_pdf` has no text layer: read
  its page images and mark the quote `image_read`. Never use WebFetch, curl, a browser user agent, or a
  different URL form to get round a block (L-R6). A block → add a `Blocker` with the helper's `kind` and move
  on.
- **Wayback**: ask for an exact capture (`https://web.archive.org/web/<14-digit timestamp>/<url>`, from the
  CDX list `https://web.archive.org/cdx/search/cdx?url=<url>`), so the capture served is the one you cite; a
  year-only `/web/2023/…` may redirect to a 2025 copy. Date the source by that timestamp, not by the year you
  asked for. A Wayback copy of an official page keeps its own kind (`code`, `ordinance`, `city_page`) with
  `archived_from` = the live URL, never `mirror`.
- Quote verbatim, ≤ 25 words, with the section number. Put the fetch result's `doc_id` (the document store's
  sha256 id of the bytes read) in `doc_id`, and the PDF page in `page`: the verifier and `score` check the
  quote against that stored document. A quote read off a scanned page image is `quote_status: image_read`. Use https (Wayback `https://web.archive.org/web/<ts>/<url>` for http-only pages).
- `source_kind` (the shared vocabulary, `common.evidence.SOURCE_KINDS`): `code` (the city's code or its
  official publisher, incl. Municode PDF blob, amlegal PDFs), `ordinance`, `staff_report`, `minutes`,
  `state_law`, `archive`, `city_page`, `mirror` (Zoneomics etc.), `news`, `other` (drafts), `human_lookup`.
- `confidence` follows the shared rule (`common.evidence.max_confidence`, enforced by `check`): `high` only on
  a primary source whose quote is verbatim (or a person's lookup) with unambiguous text; mirrors, city pages,
  drafts and image-read quotes are at most `medium` (L-R4); news alone is `low`; anything you had to infer is
  `low`.
- **The first pass is scored** (`score`): a value is strong only if `high`, primary, and its
  quote is found by machine in the stored document (on the PDF page given). Only weak values, uncoded amendments
  and a ~10% audit sample get the blind second coder. Under-marking confidence costs tokens; over-marking it
  skips the check, and the audit sample measures how often that happens.

## Hard rules

- Holdouts (the orchestrator lists them): code rules only; open no permit data, ADU counts, dashboards, staff
  reports with activity numbers, `reports/` or refits; drop search snippets with permit numbers (L-O1).
- Run no engine, scenario, calibration or dev-run script (L-O2). Edit nothing in the repo.
- Judgment calls (text is clear, coding is a policy choice): code blank, add a `Blocker` with kind
  `judgment_call` describing both readings. The user decides (L-S7).
- A source only a public-records request reaches: `Blocker` with kind `records_request_only` (it
  becomes an optional, priority-3 lookup; never file a request, email or call anyone yourself).

## Example (one era)

```json
{"era_id": "2020", "component": "Ord. 2020-12 (made-up example): ADUs by right in R-1 to R-3",
 "dates": [{"date": "2020-07-07", "type": "adopted", "evidence": [{"url": "https://…", "retrieved": "2026-11-17",
   "quote": "Adopted: July 7, 2020 … Effective: July 22, 2020", "section": "Ord. 2020-12",
   "source_kind": "ordinance", "doc_id": "<64 hex>", "page": 3}]},
   {"date": "2020-07-22", "type": "effective", "evidence": ["…same evidence…"]}],
 "fields": {"adu_max_sqft": {"value": 800, "confidence": "high", "evidence": [{"…": "…"}]}},
 "tags": []}
```
