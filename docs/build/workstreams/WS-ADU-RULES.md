# WS-ADU-RULES: code the ADU rule details for the places in the ADU fit

**Branch:** `ws/adu-rule-coding` · **Started from:** 2026-11-12 discussion after the D-079 refit and D-082
**Read first:** `CLAUDE.md`, `docs/research/ordinances/README.md`, `docs/schemas.md` (`reforms`), this brief.

## Why this workstream exists

The D-079 joint refit (`reports/adu-joint-refit-2026-11`, PR #411) failed D-075's claim rule. The model
under-predicts the active cities and over-predicts the suburbs. An exploratory look on 2026-11-12 (not
pre-registered) found that ADU uptake in the 64 fitted places differs sharply with the coded rule details:
whether an ADU is allowed by right, whether the owner must live on site, and how much parking is required.
The direction and size of those differences are left out of this brief on purpose (see "Code without
looking at outcomes").

The model folds all of this into one discount: owner occupancy gets no effect, and every other restriction
shares a factor of 0.4. Ben is considering a model version that fits a separate effect for each rule detail.
That can't be built while so many fields are blank: 20 to 40 of the 64 places have blank fields, depending on
the field, including Portland, Austin, Raleigh, Durham, Charlotte and San Antonio.

**Your job is research only.** Find and cite each place's ADU rule details and its rule changes from 2016 to
2025. You don't change the model, fit anything or score anything.

## The worklist

`docs/research/ordinances/adu-fit-rules-todo-2026-11-12.csv` has one line per place: the 64 places in the
D-079 fit set, plus St. Paul for its rules only (see Ground rules). Lines are sorted by priority, then by
eligible lots, largest first.

- **Priority 1 (46 places):** no local ADU row, or one or more of the four core fields is blank. The core
  fields are `by_right`, `owner_occ`, `parking` and `adu_detached_allowed`.
- **Priority 2 (18):** the core fields are coded, but a secondary field is blank: `adu_max_sqft`,
  `min_lot_sqft`, `adus_per_lot` or `parking_min_per_unit`.
- **Priority 3 (1):** complete. Check the dates only.

The pre-filled columns, built from `config/reforms/*.csv` on 2026-11-12:

| Column | What it holds |
|---|---|
| `local_rule_rows`, `rule_dates` | the place's coded ADU rows and their effective dates |
| `state_law_rows` | the state's ADU law rows (for example Oregon SB 1051 and HB 2001) |
| `core_fields_blank`, `other_fields_blank` | what is missing |
| `second_coded` | whether every local row already has `coder_agreement = agree` |

You fill the `found_*` columns, `source_url`, `source_section`, `source_quote`, `status` and `notes`.

## What to find, and how to code it

Code the rule **as it stood in each year from 2016 to 2025**. When a value changed in that span, record each
version with its effective date. Rule changes are as valuable as the details: the model needs before-and-after
events, and it has only 5 today.

| Column | Question | Values |
|---|---|---|
| `found_by_right` | Can an ADU that meets the code be approved by staff alone, with no hearing, conditional or special-use permit, or neighbour notice with a right to appeal? | `true` / `false`. A site-plan review by staff counts as by right. |
| `found_owner_occ` | Must the owner live in the house or the ADU? | `true` / `false`. Note it if the rule applies only to rentals or only for some years. |
| `found_parking_spaces` | Extra off-street spaces required **for the ADU**, beyond the house's own | `0`, `1`, `2+`, or `depends` with the rule in `notes` (for example "1 per bedroom", "waived near transit"). |
| `found_detached` | Is a detached ADU (backyard cottage, garage apartment) allowed? | `true` / `false` (`false` = attached or internal only) |
| `found_adus_per_lot` | Most ADUs allowed on one single-family lot | integer |
| `found_max_sqft` | Largest ADU allowed | square feet. If it is a share of the house, give the rule in `notes`. |
| `found_min_lot_sqft` | Smallest lot on which an ADU is allowed | square feet, or `none` |
| `found_rule_changes_2016_2025` | Each change to any field above | `YYYY-MM-DD: field old → new (ordinance no.)`, separated by `;` |

- **State law first.** Where a state law sets a field, record `set by state law (<reform_id>)` rather than
  searching the local code. Examples are Oregon's ADU laws (SB 1051 of 2017, and the later
  bills on owner occupancy and parking) and North Carolina's 2026 law. Check which bill set which field and
  when it took effect; don't assume. Then check whether the local code was
  stricter before the state law took effect, and record that as a rule change.
- **Coverage.** If ADUs are allowed in some single-family zones only, say which in `notes` and estimate the
  share of single-family lots covered, if the zoning map makes that easy.
- **A blank found value means not found**, never "no restriction". If you can't settle a field, leave it blank
  and say in `notes` what you looked at.

## Sources, in order

1. The records we already hold:
   - `docs/research/ordinances/batch1-2026-10-20.json` and `metro-adu-adoption-2026-10-20.json` (the Twin
     Cities metro);
   - the North Carolina, Texas and Ohio lookup tables and second-coder sheets in the same folder;
   - the `source_url`, `source_quote` and `coding_notes` of the existing rows in `config/reforms/*.csv`;
   - the downloaded ordinances in `~/lotline-data/manual/` (`nc_udos/`, `texas/Official-PDFs/`, `ohio/`).
2. The current code on Municode, American Legal, eCode360 or the city's own site.
3. Past versions of the code: the code host's version history, adopted ordinances in council minutes, and the
   Internet Archive (Wayback) for older pages.
4. A city's ADU guide or FAQ page counts only as a lead. Confirm it against the code or an ordinance.

## Ground rules

- **Don't edit `config/reforms/*.csv`.** Fill in the worklist. Proposed new or changed rule rows go in
  `docs/research/ordinances/adu-fit-rules-proposed-2026-11.csv`, using the `reforms` schema's columns. Ben
  accepts them, and a dated script in `scripts/dev/` then applies them, as with the Texas and North Carolina
  batches.
- **Code without looking at outcomes.** Don't open ADU permit counts, the refit's results, the
  over-predicted and under-predicted lists, or any `reports/` folder while coding. The details must not be
  shaped by which places the model misses.
- **Holdouts:** you may code St. Paul's *rules*. Never open St. Paul's permits or any other holdout outcome,
  never bypass the holdout filter, and never pass `--unblind`.
- **Quotes:** verbatim, at most 25 words, with the section number in `source_section`. One quote per field
  that the source settles.
- **Pages that refuse scripts:** many city and code-host pages return HTTP 403. Use the browser. Don't get
  around bot protection or CAPTCHAs; mark the line `status = manual_needed` and give the URL.
- **No contact with city staff, and no records requests.** Ben's standing rule. If only staff could answer,
  write `status = no public source` and move on.
- **No data in the repo.** Save any PDF you download to `~/lotline-data/manual/adu-rules-2026-11/<state>/` and
  name the file in `source_url`. Every download goes through a fetch that leaves a provenance trail.
- **Second coder.** When the first pass is done, run an independent check that re-opens every cited page and
  confirms each value. Use a fresh agent, not the one that coded. Record it in the worksheet's `second_coder`
  and `agrees` columns, in the same format as the Texas and North Carolina sheets. Only agreed values become
  proposed rows without a flag.
- **Status values:** `open`, `coded`, `partly coded`, `manual_needed`, `no public source`.

## Deliverables (one PR, `Closes` the issue Ben opens for it)

1. The completed `docs/research/ordinances/adu-fit-rules-todo-2026-11-12.csv`.
2. `docs/research/ordinances/adu-fit-rules-proposed-2026-11.csv`: the proposed `reforms` rows, one per rule
   version, with the source fields filled in and `coder` and `coder_2` set.
3. A short section in `docs/research/ordinances/README.md` covering:
   - what was coded;
   - how many fields are still blank, by priority;
   - every rule change found in 2016–2025, listed separately, since these are candidate events;
   - anything that conflicts with an existing row.
4. A logbook fragment: `logbook.d/<YYYY-MM-DD>-ws-adu-rules.md`.

**Paths you own:** the files named above. Everything else is read-only, including `config/`, `src/` and
`HANDOFF.md`.

## Done means

- Every priority-1 line has its four core fields found or marked `manual_needed` or `no public source`, with
  a reason.
- Priority-2 lines are attempted. Large places come first, and the work stops when the remaining lines are
  townships with no code online.
- Every rule change in 2016–2025 is listed with its effective date and ordinance.
- The second coder has checked every value that will be proposed.

## What happens after (not this workstream)

Ben decides which proposed rows to accept. A separate entry in `docs/analysis_plan.md` would then pre-register
a model version with separate rule-detail effects, before anything is fitted. The 2026-11-12 discussion leans
towards by-right plus parking, with Oregon's 2018 state law and the other rule changes added as before-and-after
events, and the policy effect reported as a range from "rules explain the gap" to "only what the events show".
Nothing in that design is decided yet.
