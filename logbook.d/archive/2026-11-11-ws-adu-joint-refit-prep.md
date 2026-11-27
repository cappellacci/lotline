### LB-NNN · 2026-11-11 · Build: ADU joint refit, pre-run code (D-079), no fit run
- **Question:** Does the code feed the five-state ADU refit exactly what D-074 to D-081 decided, and can it run
  D-079's comparison of Form A and Form B, with its tests, once and unattended?
- **What I did:**
  - Took Dallas out of the fit with `fit: false` on its undercount row; `place_years` drops such sources.
  - Fixed `place_years` storing `int(count)`. That rounded each k-scaled count down and undid k on small counts.
  - Built `lotline.model.joint_refit` with Form B's dose, the event list, the g identification rule, the D-075
    tiers (borrowed rules, ACS lots, the tier-2 update by reweighting draws), the scores, the claim rule, the
    pass bars of tests A to C and D-079's decision rule.
  - Built `scripts/dev/adu_joint_refit.py`, which does the whole run inside `offline_build`.
  - Added `config/validation/adu_roll_counts.csv` (test B's roll counts, copied from the Wake and Franklin reports).
- **Inputs:** D-074, D-075, D-078, D-079, D-080, D-081; #400's undercount table; the processed tables from #391;
  `reports/nc/wake-roll-adu-diff.md`; `reports/oh/franklin-roll-adu-diff.json`.
- **Outputs:**
  - Code: `src/lotline/model/joint_refit.py`, `scripts/dev/adu_joint_refit.py`.
  - Tests: `tests/model/test_joint_refit.py` (31 hand-worked tests).
  - Config: `config/validation/adu_roll_counts.csv`.
  - Pre-fit record: `reports/adu-joint-refit-2026-11/fit_set.csv` and `events.csv`.
  - Docs: the "Built" note under D-079 in `docs/analysis_plan.md`.
- **Findings:**
  - The fit set is 64 places with 395 place-years, 11 of them new since D-053.
  - There are only 5 in-window rule-change events, in 2 states. So under D-079's rule g is held at 0, and Form B
    is approach 3.
  - Ohio's one fit place is its tier-2 city, so Ohio cannot be scored in the data-tier test. The 4-of-5 claim rule
    then needs all four other states.
- **Decisions:** none. The building choices are listed under D-079 for Ben to confirm before the run.
- **AI:**
  - Claude Code wrote the code, tests and note.
  - The new functions have tests against hand-worked examples.
  - The full suite and `compliance_check.py` were run.
  - The run's code paths were smoke-tested on real inputs with placeholder (unfitted) parameters. Only shapes
    and finiteness were printed, never a score.
- **Open / next:** merge #400, then this PR. Then run the refit once (step 2) and open the results PR (step 3).
