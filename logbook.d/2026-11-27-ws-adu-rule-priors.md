### LB-NNN · 2026-11-27 · Build: what a new state borrows for ADU rules is saved in config
- **Question:** the code review of main @98b3f113 found a gap. A state outside `REFORM_STATES` built its
  borrowed ADU priors from the other five states' parcels and jurisdictions at run time, and missing parcels
  quietly fell back to the judgment share. So its results depended on what was in `LOTLINE_DATA_DIR`. Can
  the borrowed pools live in config instead, with the same results?
- **What I did:**
  - New calibration step `adu_rule_priors` (`calibrate/data_steps.py`, runner
    `adu_rule_inputs.borrowed_pools`). It writes two tables to `config/params/`, recorded in the lock:
    - `adu_rule_priors.csv`: the `rule_priors` rows, plus the borrowed rows as state `*`.
    - `adu_field_counts.csv`: the pooled field-restriction counts.
  - Both are saved once per origin year 2016-2025, as of 31 December.
  - `rule_inputs` for a state outside `REFORM_STATES` reads them (`saved_priors`) and reads only its own
    reforms and parcels. An origin that isn't saved is an error naming the step.
  - The listed states keep pooling live. Their code moved, unchanged, into `_pools` and `_every`.
  - The new-state guide no longer tells users to fetch every state's jurisdictions.
- **Decisions:**
  - Ben (2026-11-27): save the pools to config ("It's part of our model after all").
  - Ben (2026-11-27): save every origin year 2016-2025.
  - Mine: the tables sit in `config/params/` beside the D-097 grid, the framework's existing home for
    whole tables. The review had suggested `config/priors/`.
- **Outputs:** the step, both tables, the lock, `adu_rule_inputs.py`, tests in
  `tests/model/test_new_state_runs.py`, and docs (`adding_a_state.md`, `calibration.md`, README). PR (branch
  `ws/adu-rule-priors`).
- **AI:** Claude Opus 5.5 built it. Checked by:
  - `lotline calibrate --run --step adu_rule_priors`: the step reproduces both tables exactly.
  - Bundle hashes for MN, NC, OH, TX, OR and WI on main and on the branch.
  - A test that the new state reads no other state's table.
  - A hand-worked test of the relabelling.
  - The non-slow tests, the slow new-state tests and the compliance check.
- **Open / next:** the missing-middle session adds its borrowed dose pool to the same step.
