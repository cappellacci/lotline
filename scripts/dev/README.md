# Development scripts still in use

What stays in `scripts/dev/` after calibration phase 6 (2026-11-26), and why. One-off and superseded scripts
are in `scripts/archive/` (see its README). Fitted values are reproduced by `uv run lotline calibrate`, not by
running these by hand, except the steps marked "hand step" below.

| Script | Why it stays |
|---|---|
| `adu_covariate_screen.py` | hand step adu_covariate_centres |
| `adu_dev_run.py` | live tool: sensitivity runs cited in config/params |
| `adu_joint_refit.py` | imported by adu_covariate_screen.py |
| `adu_reference.py` | used by tests/model/test_hazard.py |
| `calibrate_adu.py` | hand step adu_survey_report_rate |
| `calibrate_mm.py` | named by the lock (mm_units_per_project) |
| `calibrate_mm_d042.py` | imported by calibrate_mm_d054.py |
| `calibrate_mm_d054.py` | imported by calibrate_mm_d092.py |
| `calibrate_mm_d092.py` | imported by mm_kappa_d092.py |
| `completion_factors.py` | hand step completion_factors |
| `create_issues.py` | used by pyproject.toml |
| `estimate_adu.py` | used by docs/model_and_assumptions.md |
| `fee_dev_run.py` | used by config/onboarding/steps.yaml |
| `fee_levels_table.py` | used by config/fees/README.md |
| `fee_ranges_2026_11_09.py` | used by config/fees/README.md |
| `fit_audit.py` | imported by fit_audit_zeros.py |
| `fit_audit_zeros.py` | imported by calibrate_adu.py |
| `housing_need.py` | used by tests/test_housing_need_window.py |
| `houston_bps_check.py` | live tool: check cited by adapters/checks/houston_permits |
| `merge_logbook.py` | used by tests/test_merge_logbook.py |
| `missing_input_matrix.py` | used by docs/adding_a_state.md |
| `mm_baseline_choice_d092.py` | used by tests/calibrate/test_mm_baseline_spread.py |
| `mm_kappa_d092.py` | imported by mm_baseline_choice_d092.py |
| `mn_adu_coverage.py` | hand step adu_undercount_k |
| `mn_mpls_roll_adu_diff.py` | live tool: roll check for mpls_roll_diff |
| `nc_onemap_crosswalks.py` | live tool: writes config/crosswalks/nc_land_use_*.csv (onemap_codes) |
| `nc_wake_roll_adu_diff.py` | hand step adu_undercount_k |
| `oh_adu_coverage.py` | hand step adu_undercount_k |
| `oh_franklin_history.py` | used by tests/states/oh/test_franklin_history.py |
| `oh_franklin_roll_adu_diff.py` | live tool: roll check for franklin_roll_diff |
| `or_adu_coverage.py` | hand step adu_undercount_k |
| `or_portland_adu_k.py` | hand step adu_undercount_k |
| `or_state_reform_rows.py` | used by docs/adding_a_state.md |
| `ordinance_records.py` | used by config/fees/README.md |
| `params_table.py` | used by .github/workflows/tests.yml |
| `parser_phrase_check.py` | hand step adu_undercount_k |
| `permit_fees_2026_11_09.py` | used by tests/states/tx/test_fee_rule.py |
| `permit_fees_2026_11_09_rows.json` | imported by permit_fees_2026_11_09.py |
| `results_dashboard.py` | used by src/lotline/app/template.html |
| `tx_adu_coverage.py` | hand step adu_undercount_k |
| `tx_austin_additions_fetch.py` | imported by tx_austin_adu_k.py |
| `tx_austin_adu_k.py` | hand step adu_undercount_k |
| `tx_fee_rule_2026_10_30.py` | used by config/fees/README.md |
| `v5_clt_predict.py` | frozen validation (V5/V8/V9) |
| `v5_clt_score.py` | frozen validation (V5/V8/V9) |
| `v5_stp_page.py` | frozen validation (V5/V8/V9) |
| `v5_stp_predict.py` | frozen validation (V5/V8/V9) |
| `v5_stp_score.py` | frozen validation (V5/V8/V9) |
| `v8_baseline_diagnosis.py` | frozen validation (V5/V8/V9) |
| `v8_freeze.py` | frozen validation (V5/V8/V9) |
| `v8_score.py` | frozen validation (V5/V8/V9) |
| `v9_or_predict.py` | frozen validation (V5/V8/V9) |
| `v9_or_score.py` | frozen validation (V5/V8/V9) |
