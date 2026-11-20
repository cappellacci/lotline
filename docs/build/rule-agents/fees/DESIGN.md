# Fees rule agent swarm: design

*2026-11-17, prototype. Built from the lessons in `LESSONS.md` (cited as R1, T2, … below).*

## What it does

Given **one state** (and optionally a list of places), the swarm produces rows for `config/fees/<st>.csv` that
pass the `fees` schema (`src/lotline/schemas.py`, v1.14) and carry evidence for every amount, plus a list of
**human lookup tasks** for every source it could not read. It never writes into `config/` itself: a person
reviews the run and merges the proposed rows in a PR, as with today's dated coverage scripts.

```
/rules-fees NC --places 3755000,3719000 --max 5        # one state, optional place list
```

## Shape: agents for judgment, Python for arithmetic

| Step | Who | Reads | Writes (in the run folder) |
|---|---|---|---|
| 0. Plan | command (main session) + `fees_tool init` | state, place list, `config/fees/<st>.csv` | `plan.json` |
| 1. Places and levying bodies | `rules-fees-enumerator` (1 agent) | plan, jurisdictions table, state law | `places.jsonl` |
| 2. Source discovery | `rules-fees-scout` (1 per ≤5 places) | `places.jsonl` | `sources.jsonl`, `tasks.scout.jsonl` |
| 3. Retrieval, extraction, labelling | `rules-fees-reader` (1 per place, ≤4 at once) | its place's sources | `items.coder1.<geoid>.jsonl`, `tasks.reader.<geoid>.jsonl` |
| 4. Blind second coding | `rules-fees-second-coder` (1 per place) | place, bodies, **source list only** | `items.coder2.<geoid>.jsonl` |
| 5. Pairing | `fees_tool reconcile` (Python) | both item files | `pairs.jsonl` |
| 6. Reconciling | `rules-fees-reconciler` (1, only on disagreements) | `pairs.jsonl`, the cited pages | `items.final.jsonl`, `decisions.md` |
| 7. Classify, price, group, validate | `fees_tool build` (Python) | `items.final.jsonl`, `proforma.yaml` | `rows.csv`, `rows_low.csv`, `build_report.md` |
| 8. Human tasks | `fees_tool handoffs` (Python) | all `tasks.*.jsonl` | `human_tasks.csv`, `human_tasks.md` |
| 9. Report | command | everything above | `report.md` |

Deterministic steps (component from the fee's purpose, prototype pricing, central-row rule, schema checks,
quote matching, robots checks, human task rendering) are Python in `src/lotline/rule_agents/fees/`, tested on
synthetic fixtures. Agents never do arithmetic for the table: they record what the source says (amount, basis,
bracket, share, units per dwelling) and the helper prices it. This removes the hand-arithmetic slips the
coverage passes had to recheck, and means every per-unit number can be reproduced from the items file.

**Run folder:** `$LOTLINE_DATA_DIR/rule-agents/fees/<ST>/<run-id>/` (outside the repo). **Shared core (since
2026-11-18):** documents live in the shared document store (`lotline.rule_agents.common.docstore`,
`$LOTLINE_DATA_DIR/rule_docs/`): `fees fetch` is `common.fetch.get(url, "fees", run)`, store-first (a schedule
any swarm already holds costs no request), with robots.txt, known refusals, one spaced request and a manifest
entry (R5, R6). The store keeps the blob, a text sidecar (PDF pages included) and the schedule's version chain;
the doc ID is the sha256 (`FeeItem.doc_id`), cited by every amount with the URL, retrieval date, page/table and
quote. Agents read with the shared `outline`, `excerpts` and `docs text`; hand-saved documents enter with
`docs add` or the inbox. Evidence vocabulary and the confidence cap are `common.evidence`; human tasks use the
shared tips and checklist (`common.handoff`); per-place spending is the shared ledger (`common.budget`);
`doctor` checks the set-up and `import` takes the proposed table into `config/fees/<st>.csv`. Nothing
downloaded is committed.

## The unit of work: a fee item

Agents write **items**, one per line of a fee schedule, in JSON lines (`records.FeeItem`). An item is close to
the source and holds no derived numbers:

| Field group | Fields | Notes |
|---|---|---|
| Where | `state`, `place_geoid`, `place_name`, `levying_body`, `body_kind` | `body_kind`: city, county, utility, regional, special_district, school_district, state (T2) |
| What | `fee_type` (source's own words), `pays_for`, `building_type` | `pays_for` drives the component (T1); building type SFD/U2/U3_4/ADU/OTHER (N5) |
| How much | `basis_kind`, `amount`, `bracket_base`, `bracket_start`, `bracket_end`, `rate_per_1000`, `pct`, `share_of`, `units_per_dwelling`, `quantity_per_unit`, `master_meter_amount` | `basis_kind` is one of 13 kinds (below) |
| Range group | `group_id`, `group_kind` (area, plat_date), `cohort_start` | Ben's 2026-10-30 rule (D4) |
| When | `schedule_label`, `adopted_date`, `effective_date`, `fiscal_year_start`, `in_force_through` | adopted ≠ effective (D2) |
| Evidence | `url`, `doc_id`, `retrieved_at`, `page_or_section`, `quote`, `quote_status`, `source_kind` (`local_path` only for files outside the store) | every amount needs all of these (below); `FeeItem.evidence()` gives the shared `Evidence` |
| Judgment | `applies_when`, `confidence`, `coder`, `notes` | |

`basis_kind` → how the helper prices one dwelling unit of the prototype (`prototype.price`):

| basis_kind | Per-unit amount | `basis` column |
|---|---|---|
| `per_unit` | amount | per_unit |
| `per_building` | amount ÷ units | flat |
| `per_sqft` | amount × sq ft per unit | per_sqft |
| `per_lue` | amount × `units_per_dwelling` (blank without it) | per_lue |
| `per_meter` | amount (one meter per unit, central; D-069); low = `master_meter_amount` ÷ units | per_lue |
| `valuation_table` | (`bracket_base` + `rate_per_1000` × ⌈(V − start)/1000⌉) ÷ units, blank if V is outside the bracket | other |
| `pct_of_value` | `pct` % × V ÷ units | pct_of_value |
| `share_of` | `pct` % × the priced parent item ÷ units | other |
| `per_bedroom` | amount × bedrooms per unit (`assumptions.yaml`) | other |
| `per_fixture`, `per_trip` | amount × `quantity_per_unit` (blank without it) | other |
| `per_acre`, `conditional`, `excluded` | blank (T4, P6) | other / flat |

V is the building's valuation: units × sq ft per unit × hard cost per sq ft, all from
`config/params/proforma.yaml` (N1). `OTHER` items are priced at the house.

## Component taxonomy (T1)

The component comes from `pays_for` (the agent states what the fee funds, with its quote), not from the
fee's name. `classify.component()` maps it, and `classify.name_hint()` reads the name as a cross-check; when the
two disagree the row is flagged for the reconciler.

| `pays_for` | Component | Examples from our coding |
|---|---|---|
| water, sewer, wastewater, reuse | `water_sewer` | TX "water impact fee", Austin capital recovery fees, OR water/sewer SDCs, Met Council SAC, taps and meters |
| parks, open_space, transportation, schools, fire, police, library, stormwater, general_capacity | `impact` | park dedication cash-in-lieu, street impact fee, OR parks/transportation/stormwater SDCs |
| building_permit, plan_review, trade_permit, inspection, state_surcharge, technology | `permit` | valuation tables, 65% plan review, MN 326B.148 surcharge |
| zoning, subdivision, site_plan, conditional_use, variance | `planning` | CUP application |
| anything else | `other` | |

Stormwater follows the Oregon rows (`impact`). A proposed change to the taxonomy goes to Ben, never into the
code silently.

## Evidence and confidence

Every item with an `amount` (or `pct`, or bracket numbers) must carry `url`, `retrieved_at`,
`page_or_section` and a `quote` of at most 300 characters taken from the document, plus a `quote_status`:

| `quote_status` | Meaning | Can be `agree`? |
|---|---|---|
| `verbatim` | `fees_tool quotecheck` found the quote in the saved text of the downloaded file | yes |
| `image_read` | read from a page image (scanned PDF) by the agent | yes, if the second coder reads the same number |
| `summariser` | read through a summarising web-fetch tool (R4) | no: it becomes a human `verify` task |
| `none` | no quote | no: the item is not written as a row |

**Confidence** (written into `notes` as `conf=`; the schema has no column for it, see *Proposed schema
change*):
- **high:** the shared cap allows high (`common.evidence.max_confidence`: a primary source, such as a
  `fee_schedule`, with a machine-found or person-read quote) **and** the second coder read the same amount
  (`verified_by` filled).
- **medium:** the cap allows high but a single coder, or the cap is medium (a mirror, city page or scan read by
  eye).
- **low:** no read quote, a `search_summary` or `news` source (S2), or coders disagree and the
  reconciler could not settle it from the page. Low rows go to `rows_low.csv` and a human task, not into
  `rows.csv`.

## Blind second coding (S1–S3)

The second coder gets the place, the levying bodies and the scout's source list, never coder 1's items. It
codes the same items its own way. `fees_tool reconcile` pairs items on (place, building type, component) and
then by amount and name similarity:

- `agree`: same priced basis and amount within 0.5% or $1, and the same effective year → `verified_by =
  rules-fees-second-coder`, `verified_date` = its run date.
- `partly`: same amount, different year → reconciler. A second pass pairs fees the coders labelled
  differently: within a place, compatible building types (equal, or either is `OTHER`, repriced at the other's
  prototype) and the same amount → `partly` with a `why`. If the only difference is per-type rows vs one
  `OTHER` row, it counts as verified; a component difference never does (dry run: the $125 connection permit).
- `differ` / `only_coder1` / `only_coder2` → reconciler.

The reconciler re-opens only the cited page, fixes transcription and column slips with a quote, and sends
every judgment call (which meter, which tier, whether an ADU pays, whether a fee is typical) to `decisions.md`
for Ben (S4). It may not pick a side by majority.

## Retrieval rules (R1–R9)

1. Look for a local copy under `$LOTLINE_DATA_DIR/manual/` first (R7).
2. `fees_tool robots <url>` before the first request to a host. Disallowed → human task `robots_disallow`.
3. Download with `fees_tool fetch` (wraps `lotline.io.http.fetch`: fixed honest user agent, manifest, cache,
   one request at a time, 2 s between requests to one host).
4. **Stop on the first 403, challenge page, CAPTCHA or login form for a host.** Record the host as blocked for
   the run; every remaining source on it becomes a human task. Never change the user agent, never use a
   different client, never use a proxy or a cached copy from a search engine (R2).
5. Wayback copies are evidence of a dated version only, never of "current" (R8).
6. Budgets per place: 12 requests, 6 searches, 3 documents read in full. Past the budget, write a human task
   for what is left.
7. A source available only on request closes as `no_usable_source`: no email, phone or records-request tasks
   (R9).

## Human lookup tasks

One task per (place, levying body, component), in `human_tasks.csv` and a readable `human_tasks.md`. The format
is in `HANDOFF_FORMAT.md`. Each task names the URL to open, why the swarm could not, what to look for in
plain words, the **exact columns to fill**, and when it counts as done. Answered tasks go back in with
`fees_tool ingest-tasks`, which turns each answer into an item with `coder = human:<initials>` and
`quote_status = verbatim` (a person read it), so the same build and checks apply.

## Stop rules for the run

- Stop a place when every expected (body, component) pair has an item or a task.
- Stop the run when every place is done, or when more than half of the places are blocked on the same host
  type (the report says so and lists the tasks).
- The swarm never runs engine, scenario or `scripts/dev/*run*` scripts (CLAUDE.md, memory note) and never opens
  outcome data. Fees are inputs, so holdout places (e.g. Charlotte, St. Paul) may be coded, as now.

## Dates (D1–D7)

`year` = the calendar year the schedule took effect. The helper derives it from `effective_date`, else
`fiscal_year_start`, else the schedule label, and writes the basis in notes (`date_basis=`). Step schedules are
one item per step. `in_force_through` is set only when the reader confirms an older schedule is still current
next to a newer row of the same component. Amounts stay in the schedule's dollars (`dollar_year` = `year`);
Lotline deflates later (D-066).

## What the build checks (`fees_tool build`)

1. `lotline.schemas.validate(df, "fees")` (types, enums, unique key, low ≤ central ≤ high).
2. Every row with `amount_per_unit_usd` has `source`, `source_section`, `source_quote` and a `quote_status` of
   verbatim or image_read in notes.
3. An explicit 0 needs a quote with an exemption/waiver/"no fee" word (T5).
4. A place mixing `OTHER` and type rows in one component gets a warning (N6).
5. Component from `pays_for` vs name hint: disagreements are listed.
6. Per place and component: which expected bodies are coded; `partial` when one is missing (T3).

## Proposed schema change (for WS-CORE, not made here; issue #472)

Rows today hide evidence status and confidence in free-text `notes`. Proposed additive columns for `fees`
(and `reforms`): `levying_body`, `quote_status` (verbatim / image_read / summariser), `confidence` (high /
medium / low) and `retrieved_date`. Until then the build writes them as `key=value` tokens at the start of
`notes`, so they can be moved into columns mechanically.

## Not in this prototype

- History before the current schedule (`--history`) is designed (the reader looks for prior budget books and
  Wayback captures, one item per vintage) but not tried in the dry run.
- Browser checks of blocked sites: tasks go to a person; a browser agent pass, as in the ADU work, is a
  possible later step if Ben wants it.
