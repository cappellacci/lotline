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
