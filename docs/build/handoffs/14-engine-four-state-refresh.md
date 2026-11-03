# Thread 14: refresh the engine on all four states' data (WS-ENGINE)

**Goal:** the data threads are closed. Ohio and Texas closed on 2026-11-01; North Carolina and Minnesota on
2026-11-02 (PRs #255–#262, all on `main` at 4e01c59). This thread takes the engine from the October runs to the
four-state data:
1. Make the engine read the rule tags the data threads now rely on.
2. Rebuild the D-025 (ADU) and D-024 (missing-middle) panels on the new data and report the counts.
3. Write dated amendment entries **before any fit**, get Ben's go-ahead, then run each once.
4. Freeze the two V5 blind-test predictions (Charlotte, St. Paul) **by Tue Nov 17**.

**Dates:**

| Date | What | Why it matters here |
|---|---|---|
| Tue Nov 10 | Benchmark state chosen (BUILD_PLAN phase 4); last day for Mecklenburg's archive (Charlotte V5 option a) | Ben's choice draws on the panel counts (task 2) and the four readiness reports |
| **Tue Nov 17** | V5 predictions frozen in `results/frozen/` (#45) | Hard deadline: the freeze must happen before any unblinding |
| Week of Nov 18 | Product phase: scenarios, statewide totals, app | Uses whatever D-024 and D-025 estimates are on `main` then |

## Read first
- `CLAUDE.md`, the shared rules in `docs/build/handoffs/README.md`, and `docs/build/workstreams/WS-ENGINE.md`.
  This is an engine thread, so **model runs are allowed**, but each fit needs a dated entry in
  `docs/analysis_plan.md` first and Ben's go-ahead (the D-023 to D-031 practice: write, push, then run once).
- **The four readiness reports, §0 first in NC and MN:** `docs/build/nc-readiness.md`, `docs/build/mn-readiness.md`,
  `docs/build/oh-readiness.md`, `docs/build/tx-readiness.md`. Also the closing sections "For the engine threads" in
  `11-ohio-data-complete.md` and `12-texas-data-complete.md`.
- `docs/analysis_plan.md`: D-022 (anything uncoded is unknown), **D-024** (missing middle, including its
  2026-10-20 run and the 2026-10-21 switch to D-025's estimator), **D-025** (ADU, pooled hierarchical NB), D-031
  (imputation robustness), D-035 (eligible history).
- The October results: `reports/mm-d024/`, `reports/mm-d024-nb/`, `reports/adu-d025/`. D-024's run gave "no
  credible estimate": Houston supplied about 91% of the added homes, two placebo checks failed and both
  out-of-sample tests failed. The new data roughly doubles the treated places outside Texas, which is the main
  reason to rerun.
- V5: `reports/nc/V5-charlotte-inputs.md` and `reports/mn/V5-stpaul-inputs.md` (both include an input check for
  the freeze).

## Holdouts (read twice)
- **Charlotte (3712000) and Mecklenburg County (37119):** no outcomes from 2023-06-01. The only Charlotte parcel
  information allowed is the pre-UDO layer dated 2023-05-31. Every place reporting under Mecklenburg in BPS is out
  of D-024.
- **St. Paul (2758000):** no outcomes from 2024-01-01, and no parcel roll exported on or after that day
  (`holdout.apply(..., snapshot=True)`). St. Paul is out of D-024 and D-025 entirely. Don't repeat or use the
  post-reform St. Paul figures (D-013).
- Go through the IO layer's holdout filter; never bypass it, never pass `--unblind`, and don't print held-out
  rows while debugging. Freeze first, unblind later (and only when Ben asks).

## The rule-tag contract (task 1 implements it)
All four `config/reforms/*.csv` files now use these tags in `coding_notes`. **No engine code reads them yet**:
`git grep -n predates -- src` finds nothing.

| Tag or convention | Meaning for the engine | Source |
|---|---|---|
| `[predates]` | Never a reform event. The rule counts as in force from before the window (always treated for D-024 and D-025) | HANDOFF decision, 2026-11-01 |
| `[earliest-known]`, or a blank `adoption_date` | The date may be later than the rule's first appearance. Main runs include these rows; a sensitivity drops them as events | Readiness reports; the counts scripts treat both forms alike |
| `DATE UNCONFIRMED` | The row counts as an event at its coded date; a sensitivity runs without it | Ben, 2026-11-02 (Minnesota thread; not yet folded into HANDOFF: propose it in your PR) |
| "None" rows: ADU `adus_per_lot = 0`, missing-middle `unit_cap = 1` | A control on evidence, never an event | Readiness reports (NC, MN) |

The tags are free text in the notes until WS-CORE adds a `date_basis` field. Read them with one small helper in
the model package, tested on synthetic rows. Don't edit `schemas.py` or the config loaders (WS-CORE owns
them); if a field would be cleaner, open a `contract-change` issue.

## Tasks (stop where marked)

**1. Tag handling (code and tests; one PR).**
- One helper (e.g. in `model/estimate_adu.py`, shared with `estimate_mm.py`, or a new small module) that returns,
  per rule row: is-event, always-treated (`[predates]`), earliest-known and unconfirmed flags.
- Use it in both panel builders (`estimate_adu.build_panel` with `pooled_adu`, and `estimate_mm.build_panel` and
  `adoption_year`). A `[predates]` row should put its rule in force before the panel's first year, not at its date.
- Add options for the two sensitivities: drop `[earliest-known]` events, drop `DATE UNCONFIRMED` events.
- Hand-worked synthetic tests for each tag. Tests use fixtures, never downloaded data.

**2. Panel counts on the four-state data (counts only, no fit).**
- First check that each state's `eligible_parcels` table is newer than #252 (the eligible-history fix). Rebuild
  any that isn't. Ohio's command is `OH_PARCELS_VINTAGE=2026-10-19 uv run lotline fetch --state OH --source
  eligible`; always set that variable, because without it a full statewide download starts. NC and MN were
  rebuilt after #252 (2026-11-01 and 2026-11-02).
- Run the panel builders' counts: `uv run python scripts/dev/estimate_mm.py --smoke` and
  `uv run python scripts/dev/estimate_pooled_adu.py --smoke`. Report places, adopters per year, never-treated comparisons, all-zero places, and the counts under each sensitivity.
- Compare with the readiness reports. Any difference beyond rounding is a bug in task 1 or a data problem: say
  which in the PR.

Expected, from the readiness reports (verify; don't copy):

| Panel | MN | NC | OH | TX |
|---|---|---|---|---|
| D-025 places with an in-window change | 43 (54 event rows; 4 DATE UNCONFIRMED; 10 `[earliest-known]`) | 8 (5 firm dates) | 7 | 2 treated (Austin, San Antonio) |
| D-025 "no ADUs" or comparison places | 28 | — | 8 | 2 (Fort Worth, Dallas) |
| D-024 BPS places of 10,000+ | 100 | 55 | 156 | 232 |
| D-024 in-window events | 3 (Minneapolis 2020, Richfield 2023, St. Louis Park 2025) | 10 (only Durham and Raleigh firm; 8 `[earliest-known]`) | 2 (Cincinnati 2024, Euclid) | 5 |

**3. Amendment entries, then one run each. STOP for Ben's go-ahead after writing them.**
- Write dated entries in `docs/analysis_plan.md`, one each for D-024 and D-025, **before any estimate on the new
  data**. Keep the specifications, checks and pass rules unchanged unless there is a reason, and if so say it.
  State:
  - what changed in the sample (new places by state, the tags, coverage lists for Ohio's ADU-only permit files);
  - the sensitivities (without `[earliest-known]` events, without `DATE UNCONFIRMED` events, firm dates only);
  - which out-of-sample tests apply now (more places now have post-reform years);
  - the open D-025 sample questions the data threads left: whether NC's places join the pooled panel (Ben pooled
    Texas in on 2026-10-30); Fort Worth's non-rental ADUs; Ohio's lower-bound counts.
- Push the entries as a PR. **Stop and ask Ben** to approve one run of each.
- After approval: run each once, write the results into the entries, and open a results PR with chart-ready CSVs
  in `reports/`. Report whatever comes out, failures included.

**4. V5 freezes (in parallel with 1–3; deadline Tue Nov 17).**
- **Charlotte:** follow `reports/nc/V5-charlotte-inputs.md`. Use option (b), the town prior with its range,
  unless Mecklenburg sends the archived roll by Nov 10 (Ben will say). Cap annual inputs at 2022.
- **St. Paul:** follow `reports/mn/V5-stpaul-inputs.md`: 55,269 eligible H1/H2 lots on the pre-window roll.
  Cap annual inputs at 2023, and disclose D-013's exposure in the freeze file.
- The missing-middle effect in each freeze is whatever D-024 estimate or prior is on `main` when you freeze; name
  it in the freeze file. Don't hold the freeze for task 3.
- Write `results/frozen/V5-NC-CHARLOTTE.json` and `results/frozen/V5-MN-STPAUL.json`, on `main`, before Nov 17.

## Caveats the data threads flagged
- **MN ADU:** Met Council's ADU flags start in 2014 and Minneapolis's in 2016, so the 8 Minnesota events from
  2010–2013 have no flagged pre-years. 12 events fall in 2025 with almost no post-period. Sunfish Lake
  (2025-12-09) may fall just outside the window. Drop Minneapolis 2026 (partial).
- **MN missing middle:** Richfield's effective date is coded as passage; the true date is about a month later.
  Its pre-2023 rule (conditional duplexes on arterial lots) is a partial dose. Minneapolis has the injunction
  windows (2022-06-15 to 07-26; 2023-11-04 to 2024-05-13) as a sensitivity.
- **NC:** the Mecklenburg towns' ADU counts are small and parser-based; treat 2025 as partial and drop 2026.
  Raleigh's ADU flags start in 2019.
- **OH:** the Franklin and Montgomery permit files flag only ADUs, so the panel caller must pass their covered
  places (`montgomery_permits.covered_places`). Ohio's ADU counts other than Cincinnati's are lower bounds.
- **TX:** Houston has no zoning and binding deed restrictions; in October it drove D-024. Leave-one-out must
  report Houston.

## Done when
- Task 1 PR merged (tags read, tests green).
- Task 2 counts in a PR, matching the readiness reports or with differences explained.
- Task 3 entries written and pushed, then approved, run once and reported (results PR with green CI).
- Task 4: both V5 predictions frozen on `main` by Nov 17.
- One logbook fragment per PR in `logbook.d/`. Propose the `DATE UNCONFIRMED` rule as a HANDOFF decision in the
  task 1 PR description.
