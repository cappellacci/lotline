# Archived development scripts

One-off analyses, superseded fits and report-page renderers, moved here from `scripts/dev/` on 2026-11-26
(calibration phase 6). Nothing in the library, tests, CI or the how-to docs runs them. They stay in the repo
as the record of how each decision in `docs/analysis_plan.md` was reached; the reports they wrote are under
`reports/`. Every fitted value in `config/params/` is now reproduced by `uv run lotline calibrate --run`
(see the README, "Reproduce the fitted parameters"), not by these scripts.

- **Old paths.** `LOGBOOK.md`, `HANDOFF.md` and older logbook fragments still say `scripts/dev/<name>`; the
  file is now `scripts/archive/<name>`. Every other reference in the repo was updated, except the source
  column of `config/params/adu_partial_share_grid.csv`, which its calibration step writes.
- **Rerunning one.** Run from the repo root with `uv run python scripts/archive/<name>`. A script that loads a
  neighbour by file path may need that path pointed at `scripts/dev/` (for the scripts still there) first.

Summaries are each script's own first docstring line; decision ids are those named near its top.

## ADU

| Script | What it answered | Decisions |
|---|---|---|
| `adu_age_page.py` | Build the D-087 results page from reports/adu-age-term (tiers.csv, test_a.csv, fits.csv, summary.json). | D-087 |
| `adu_age_refit.py` | D-087: Forms A, A′ (owner share) and A″ (owner share + housing age), refitted on the checked rule rows and scored on D-084's tests. | D-075, D-083, D-084, D-087 |
| `adu_baseline_share.py` | Recompute `baseline_adu_share_of_one_unit` in config/params/aggregate.yaml from permits that flag ADUs. |  |
| `adu_config_fit.py` | The A + place types fit the ADU config holds, on the rule rows in `config/reforms/` (D-096 inputs). | D-096 |
| `adu_config_fixed_rows_page.py` | Build the D-096 config page: the ADU engine's statewide results before and after the config change. | D-096 |
| `adu_coverage_audit.py` | Audit of how ADU rule rows are coded for coverage and for "no ADUs" (follow-up to D-095). | D-095 |
| `adu_current_rules_check.py` | V2-style check of the ADU hazard against places that already allow ADUs (D-019, D-022). | D-019, D-021, D-022 |
| `adu_drift.py` | D-091: D-090's forecasts with a per-place drift d = exp(σ z), σ learned leaving one state out. | D-090, D-091 |
| `adu_drift_page.py` | Build the D-091 results page from reports/adu-drift (totals.csv, place_scores.csv, summary.json). | D-091 |
| `adu_engine_drift_check.py` | Statewide ADU scenario totals with D-091's own-counts-with-drift path off and on (development check). | D-091 |
| `adu_engine_drift_page.py` | Results page for D-093, the engine wiring of D-091's adopted outcome: reports/adu-engine-drift/. | D-089, D-091, D-093 |
| `adu_fixed_rows_page.py` | Build the D-096 results page: A + place types on the coverage-fixed rule rows, against the checked rows. | D-096 |
| `adu_gut_check_data.py` | The counted ADUs per place and year behind the fit (for the gut-check page), from the D-096 inputs. | D-096 |
| `adu_gut_check_page.py` | The ADU gut-check page: how well the model predicts ADUs within a state, and what it predicts for 2027-31. | D-091, D-096, D-097 |
| `adu_gut_check_places.py` | Per-place ADU engine results for the gut-check page: where each state's predicted ADUs come from. | D-097 |
| `adu_mx_engine.py` | D-097's engine report: statewide ADU totals with m_x fixed, drawn from the grid, and fixed at 0.4 and 1.0. | D-093, D-096, D-097 |
| `adu_mx_grid.py` | D-097: A + place types fitted at each partial-rule share m_x on the 0.1 grid, and weights to draw it. | D-096, D-097 |
| `adu_new_rule.py` | D-099: profile of the first-years share ν, and its held-out check, on the D-096 rows. | D-088, D-096, D-099 |
| `adu_new_rule_page.py` | Build the D-099 results page from reports/adu-new-rule. | D-099 |
| `adu_owner_page.py` | Build the D-084 results page from reports/adu-owner-share (tiers.csv, test_a.csv, fits.csv, summary.json). | D-084 |
| `adu_owner_refit.py` | D-084: Form A′ (Form A with owner-occupied share as a place term) against Form A, on D-079's tests. | D-074, D-075, D-079, D-083 |
| `adu_profiles_page.py` | Build the D-089 results page from reports/adu-state-profiles (profiles.csv, evidence.csv, summary.json). | D-089 |
| `adu_range_coverage.py` | Are the ADU ranges the right width? Coverage of the held-out predictive ranges, place by place. | D-075, D-088, D-091 |
| `adu_range_coverage_page.py` | Build the ADU range-coverage results page from reports/adu-range-coverage. |  |
| `adu_refit_fixed_rows.py` | D-096: run a dev ADU script with `UNKNOWN-PLACEHOLDER` place-years left out of its inputs. | D-079, D-084, D-095, D-096 |
| `adu_reform_ratio.py` | D-095: does the engine's ADU reform ratio match what happened where coded rules changed? | D-079, D-095 |
| `adu_reform_ratio_page.py` | Build the D-095 results page from reports/adu-reform-ratio. | D-095 |
| `adu_screen_page.py` | Build the D-083 results page from reports/adu-covariate-screen (screen.csv, summary.json). | D-083 |
| `adu_state_profiles.py` | D-089: a profile of each state's places by type, the share of each state outside the fit's evidence, and statewide 5-year ADU totals under Form A + place types with and without … | D-084, D-088, D-089 |
| `adu_time_split.py` | D-090: the within-state ADU forecast test. | D-087, D-090 |
| `adu_time_split_page.py` | Build the D-090 results page from reports/adu-time-split (totals.csv, place_scores.csv, fits.csv, summary.json). | D-090 |
| `adu_trend_page.py` | Build the D-085 results page from reports/adu-time-trend (fits.csv, test_d_states.csv, tiers.csv, summary.json). | D-085 |
| `adu_trend_refit.py` | D-085: Form T (a calendar-year trend) against its base, Form A and Form A′, and test D. | D-075, D-084, D-085 |
| `adu_type_spread.py` | D-094: a place-effect variance per place type (Form S), against A + P, on the checked rule rows. | D-074, D-075, D-088, D-094 |
| `adu_type_spread_page.py` | Build the D-094 results page from reports/adu-type-spread. | D-094 |
| `adu_types_checked_page.py` | Build the results page for D-088 rescored on the checked rule rows: reports/adu-place-types (old rows) against reports/adu-place-types-checked (#419's rows). | D-088 |
| `adu_types_engine_check.py` | Statewide ADU scenario totals from the engine as it stands (development check, not a published result). | D-088, D-089 |
| `adu_types_engine_page.py` | Results page for the engine switch to Form A + place types (D-088, D-089): reports/adu-types-engine/. | D-053, D-088, D-089 |
| `adu_types_page.py` | Build the D-088 results page from reports/adu-place-types (fits.csv, tiers.csv, summary.json, ...). | D-088 |
| `adu_types_refit.py` | D-088: where the ADU place effects' differences sit (Part 1), and Form P, place types shared across states (Part 2), against its base, Form A and Form A′. | D-049, D-075, D-083, D-084 |
| `adu_types_slopes.py` | The anchor's draw terms for Form A + place types (D-088): config/params/adu_anchor.yaml. | D-030, D-048, D-079, D-088 |
| `adu_types_slopes_page.py` | Results page for the anchor draw terms recomputed for Form A + place types: reports/adu-types-slopes/. | D-053, D-089 |
| `austin_permit_class_check.py` | Do Austin's post-HOME 2-unit counts hold ADUs? (causal diagram v0.2, §6.6) |  |
| `calibrate_shape.py` | D-047: approach 2 (shape terms on the mechanism) and approach 3 (empirical benchmark), each with the leave-one-state-out backtest, next to D-041. | D-041, D-047, D-048 |
| `d053_or_insample.py` | D-053: Portland's and Bend's yearly ADU counts against each fit's predictive (θ and the place effect drawn, as for any place), five-state fit next to the four-state D-048 fit. | D-048, D-053 |
| `estimate_pooled_adu.py` | The D-025 ADU estimation (pooled hierarchical negative binomial): smoke test, or the one real run. | D-023, D-025, D-031 |
| `observed_permits.py` | Observed ADU and missing-middle (2-4 unit) permits per state and year, for results pages (not a model run). |  |
| `plot_d025_followups.py` | Charts for the D-025 follow-ups (D-031 dated notes): as-run vs corrected main, the event study, and the HonestDiD sensitivity. | D-025, D-031 |
| `score_models.py` | D-049: held-out log score per place for D-041, D-046, D-047 (approaches 2 and 3) and D-048. | D-041, D-046, D-047, D-048 |

## Missing middle

| Script | What it answered | Decisions |
|---|---|---|
| `calibrate_mm_d058.py` | Missing middle: D-054's statewide backtest, with a baseline rule for unstable pre-reform pace (D-058). | D-038, D-054, D-058 |
| `calibrate_mm_d059.py` | Missing middle: D-054's statewide backtest with Lubbock out of the fit and targets (D-059, run once). | D-038, D-054, D-055, D-058 |
| `calibrate_mm_d062.py` | Missing middle: the five-year rate r5 = θ × m(half) by profile likelihood (D-062, run once). | D-054, D-055, D-059, D-062 |
| `d054_posthoc.py` | D-054 POST-HOC diagnostics (not pre-registered; | D-042, D-054 |
| `d055_v9_rescore.py` | D-055: re-score V9 Oregon's missing-middle targets with D-054's refit (not blind; written before the run). | D-038, D-051, D-054, D-055 |
| `estimate_mm.py` | D-024's missing-middle panel run (`--smoke`, `--full`); archived with the D-092 checks (MM step 2). | D-024 |
| `mm_accuracy_page.py` | Missing-middle accuracy report: reports/mm-d092/accuracy/results.html. | D-038, D-055 |
| `mm_baseline_choice_page.py` | Results page for D-092 run 8 (choosing the no-reform baseline): reports/mm-d092/run8-baseline/results.html. | D-092 |
| `mm_config_compare.py` | Statewide five-year added homes, D-055 values against C4 (same places, seed, draws). | D-055 |
| `mm_config_page.py` | Results page for C4 to config: reports/mm-d092/config-c4/results.html. | D-055 |
| `mm_counts.py` | D-092 §2-§3 counting rules (building collapse, roll diffs); was `lotline.validation.mm_counts` (MM step 2). | D-092 |
| `mm_counts_d092.py` | Inputs and runs for the D-092 missing-middle counts (`mm_counts.py`). | D-092 |
| `mm_fast_ramp_page.py` | Results page for D-100's fast-ramp sensitivity: reports/mm-d100/fast-ramp/results.html. | D-092 |
| `mm_fast_ramp_run.py` | Fast-ramp sensitivity for the Handbook missing-middle scenario (D-100, pre-registered 2026-11-17). |  |
| `mm_gut_check_data.py` | Missing-middle gut check, numbers: reports/mm-gut-check/summary.json. |  |
| `mm_gut_check_page.py` | Results page for the missing-middle gut check: reports/mm-gut-check/results.html. | D-092 |
| `mm_kappa_page.py` | Results page for D-092 run 7 (κ, the baseline's own spread): reports/mm-d092/run7-kappa/results.html. | D-092 |
| `mm_project_size_d092.py` | Missing middle: buildings per project in city permit files (D-092 deviation 2026-11-15 (d)). | D-092 |
| `mm_projects_page.py` | Results page for D-092 run 13 (buildings per project): reports/mm-d092/run13-projects/results.html. | D-092 |
| `mm_ramp_d100.py` | Missing middle's ramp after St. | D-092, D-098 |
| `mm_ramp_d100_summary.py` | Write D-100 run 1's summary.json from the files the run saved (the run stopped at the summary step on a JSON key bug, fixed since in `mm_ramp_d100.py`; | D-092 |
| `mm_ramp_page.py` | Results page for D-100 run 1 (missing middle's ramp): reports/mm-d100/run1/results.html. | D-092 |
| `mm_results_page_d092.py` | Build the D-092 run-6 results page from the run-4 and run-5 report files (to scale, log axes). | D-092 |
| `mm_scenario_run.py` | First run of the Handbook missing-middle scenario (D-063), five states, approved by Ben 2026-11-08. | D-055, D-063 |
| `mm_tests.py` | D-092 §7 accuracy-test pass rules, fixed before any test ran; was `lotline.validation.mm_tests` (MM step 2). | D-092 |
| `mm_tests_d092.py` | D-092 §7 accuracy tests, scored with `mm_tests.py`. | D-092 |
| `mm_tests_phi_page.py` | Results page for D-092 runs 9-11 (lumpy years, refit and §7): reports/mm-d092/run11-tests-phi/results.html. | D-092 |
| `mm_types_d092.py` | Missing middle: place types, φ by type (D-092 deviation 2026-11-15 (c)). | D-088, D-092 |
| `mm_types_page.py` | Results page for D-092 run 12 (φ by place type): reports/mm-d092/run12-types/results.html. | D-092 |
| `project_size.py` | Buildings per project (same lot, same day); was `lotline.validation.project_size` (MM step 2). | D-092 |

## Fees

| Script | What it answered | Decisions |
|---|---|---|
| `coverage_fees_mn_2026_11_09.py` | Fee coverage for the six largest uncoded Minnesota places (manual-fee-lookups.md, priority 4) -> config/fees/mn.csv. |  |
| `coverage_fees_mn_2026_11_09_rows.json` | Data file read by its script |  |
| `coverage_fees_nc_2026_11_09.py` | Fee coverage for the largest uncoded NC places (manual-fee-lookups.md, priority 4) -> config/fees/nc.csv. |  |
| `coverage_fees_nc_2026_11_09_rows.json` | Data file read by its script |  |
| `coverage_fees_oh_2026_11_09.py` | Fee coverage for Ohio's six largest uncoded places (manual-fee-lookups.md, priority 4) -> config/fees/oh.csv. | D-069 |
| `coverage_fees_oh_2026_11_09_rows.json` | Data file read by its script |  |
| `coverage_fees_tx_2026_11_09.py` | Fee coverage for the six largest uncoded Texas places (manual-fee-lookups.md, priority 4) -> config/fees/tx.csv. |  |
| `coverage_fees_tx_2026_11_09_rows.json` | Data file read by its script |  |
| `eugene_fees_2026_11_09.py` | Eugene, OR: price the known SDCs per house (D-066, Ben's option (a), 2026-11-09) -> config/fees/or.csv. | D-066 |
| `fee_knobs_export.py` | Export the fee slider's grid for the results page (D-077): statewide five-year units added for each fee change and home type, in every draw, plus the central path (development r… | D-076, D-077 |
| `fee_pencil_out_table.py` | Pencil-out table: house, duplex and fourplex pro formas per coded place, at today's fees and after a cut (fee plan Phase 2, D-073; office hours 2026-11-03, A5). | D-066, D-073 |
| `plex_utility_fees_2026_11_09.py` | Duplex and fourplex water/sewer rows (manual fee lookups, priority 1) -> config/fees/<st>.csv. |  |
| `v6b_fee_threshold.py` | V6b, the pro forma threshold test (validation plan §V6; |  |

## Rule coding and state checks

| Script | What it answered | Decisions |
|---|---|---|
| `apply_adu_rules_proposed_2026_11.py` | Apply PR #417's proposed ADU rule rows to config/reforms/*.csv. |  |
| `mn_lookups_2026_11_02.py` | Apply Ben's decisions on the MN second-coder lookups (2026-11-02) to config/reforms/mn.csv. |  |
| `mn_mm_batch1_2026_11_02.py` | Minnesota missing-middle rules from the batch-1 ordinance records -> config/reforms/mn.csv (thread 13, M4). | D-022 |
| `mn_readiness_counts.py` | Counts behind `docs/build/mn-readiness.md` (thread 13, M5). | D-024, D-025 |
| `mn_second_coder_2026_11_02.py` | Apply the MN second-coder review of 2026-11-02 to config/reforms/mn.csv (append-only notes). |  |
| `mn_second_coder_decisions_2026_11_02.py` | Apply Ben's decisions on the MN second-coder review (2026-11-02) to config/reforms/mn.csv. |  |
| `mn_second_coder_sheet.py` | Write the Minnesota second-coder worksheet from config/reforms/mn.csv (thread 13, M5). | D-024, D-025 |
| `nc_readiness_counts.py` | Counts behind `docs/build/nc-readiness.md` (thread 13). | D-024, D-025 |
| `nc_second_coder_2026_11_01.py` | Apply the NC second-coder review of 2026-11-01 to config/reforms/nc.csv (append-only notes). |  |
| `nc_second_coder_decisions_2026_11_01.py` | Apply Ben's decisions on the NC second-coder review (2026-11-01) to config/reforms/nc.csv. |  |
| `or_adu_new_places.py` | Counts behind §3 of `reports/or/adu-coverage-and-undercount.md`: ADU permits in Oregon's new places. |  |
| `tx_adu_rows.py` | ADU rules for the 20 largest Texas places (2020 population) -> config/reforms/tx.csv. |  |
| `tx_ben_lookups_2026_10_30.py` | Texas rule rows from Ben's own lookups (2026-10-30) -> config/reforms/tx.csv and the lookup trackers. | D-021 |
| `tx_ben_lookups_2026_10_30b.py` | Ben's second batch of lookups (2026-10-30, evening) -> config/reforms/tx.csv and the lookup trackers. |  |
| `tx_ben_lookups_2026_11_01.py` | Carrollton ADU rule and Dallas utility fees from Ben's lookups (2026-11-01) -> config/ and the trackers. |  |
| `tx_corrections_2026_10_30.py` | Ben's decisions on the proposed Texas corrections (2026-10-30) -> config/reforms/tx.csv. |  |
| `tx_research_2026_10_27.py` | Texas rule rows from Ben's research workbook (2026-10-27) -> config/reforms/tx.csv. |  |
| `tx_research_2026_10_29.py` | Texas rule and fee rows from Ben's second research workbook (2026-10-29) -> config/. |  |
| `tx_rules_21_40.py` | ADU and missing-middle rules for Texas places 21-40 by 2020 population -> config/reforms/tx.csv. | D-022, D-024, D-025 |
| `tx_second_coder_2026_10_30.py` | Ben's second-coder review (2026-10-30) -> config/reforms/tx.csv. | D-025 |

## Results pages and other checks

| Script | What it answered | Decisions |
|---|---|---|
| `eligible_proxy_test.py` | Run analysis plan D-056: does the ACS fallback stand in for real eligible-parcel counts? | D-056 |
| `gutcheck_diagnostics.py` | Gut-check diagnostics for a state's ADU forecast (WS-NC-GUTCHECK tasks 1-3; |  |
| `range_drivers.py` | What drives each result's range: first-order sensitivity shares from the runs in the results bundles (#54). | D-097 |
| `results_run_summary.py` | Summarize a set of results bundles for a run's results page (not part of the app). |  |
