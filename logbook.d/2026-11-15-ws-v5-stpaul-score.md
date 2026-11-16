### LB-NNN · 2026-11-15 · Validation: V5 St. Paul scoring step, ready but not run (D-098)
- **Question:** once Ben asks to unblind, can St. Paul's frozen C4 forecast be scored in one step, using exactly
  what was frozen?
- **Decisions:** none new. D-098 fixed the target, the pass rule and the no-reform benchmark before the freeze.
  Ben asked for #436 (C4 and the freeze) to be merged into `main`; it was merged as 4646aca9.
- **What Claude did:**
  - `scripts/dev/v5_stp_score.py`, after Charlotte's `v5_clt_score.py`:
    - it refuses unless V5-MN-STPAUL is released in `config/states/mn.yaml`;
    - it regenerates the frozen draws and stops unless they equal the freeze file;
    - it scores 2024–2025 (the pass rule) and each year BPS already has, with 2026 added once published;
    - the no-reform benchmark is the baseline part of the same draws (D-098).
  - `v5_stpaul.inputs` now drops BPS rows after 2023 instead of raising when it sees them. The baseline only
    ever read 2021–2023, so the inputs match before and after the release; the old guard would have stopped
    the scoring run.
  - `v5_stpaul.scorable_years`, with a hand-worked test.
- **How it was checked:** 8 hand-worked tests in `tests/core/test_v5_stpaul.py`; the changed code regenerates
  the frozen summaries exactly (holdout still in place, no outcome read); the full CI set.
- **Not done:** the release and the score. Both wait for Ben's "unblind".
- **Outputs:** `scripts/dev/v5_stp_score.py`, `src/lotline/validation/v5_stpaul.py`,
  `tests/core/test_v5_stpaul.py`.
- **2026-11-16, unblinded and scored:** Ben said "Yes, unblind".
  - The holdout was released in `config/states/mn.yaml` (`released_on: 2026-11-16`), after the freeze reached
    `main` in #436.
  - **Miss:** BPS St. Paul built 55 new 2–4 unit buildings in 2024–2025 (33, 22) against the frozen P10 9, P50
    15, P90 28 (98th percentile). It beats no reform on CRPS (32.8 vs 40.0). Homes 123 against 21–65.
  - As written in D-098 before the freeze, this says C4's slow ramp (half-way 4 years) is wrong for St. Paul.
  - **Post-hoc, reported only:** the same draws with C4's θ and a half-way point of 1.0 year give a median of
    55 (17–308); 0.5 year 66 (19–391); D-055's values 14 (9–36), also a miss. St. Paul implies θ 0.85–1.09 per
    1,000: C4's level, reached fast.
  - **Outputs:** `reports/v5-stpaul/` (README, score.json, posthoc_ramp.json, results.html),
    `scripts/dev/v5_stp_page.py`. Page: https://claude.ai/artifact/19Eyqzf78EtfjJtRqivixd. The accuracy
    report adds St. Paul (same link, https://claude.ai/artifact/72uydyJJNJduLuErr9uQXw). D-098 gains its
    "Scored" bullet.
  - **How it was checked:** the script regenerated the frozen draws exactly before scoring; the post-hoc rows
    reuse the frozen inputs, draws and seed; the page's chart labels were checked against each row's numbers
    (a label mix-up was caught and fixed before publishing).
  - **Not changed:** config. Any ramp change is a new dated entry; St. Paul would be in-sample for it.
