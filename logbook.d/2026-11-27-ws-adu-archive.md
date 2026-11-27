### LB-NNN · 2026-11-27 · Build: research-only ADU code moves to the script archive
- **Question:** the code review of main @98b3f113 found library modules that nothing in the library calls.
  Their only callers are archived scripts, one dev script and their own tests. Can they leave `src/`?
- **What I did:**
  - Rechecked callers in `src/`, `tests/`, `scripts/` and the config, docs and app text. None in the library.
  - Moved to `scripts/archive/`, each with its tests (to `scripts/archive/tests/`):
    - From `validation/`: `adu_reform_check`, `sensitivity`, `adu_trend`, `adu_profiles`.
    - From `calibrate/`: `runs`, `runs_dashboard` and its HTML.
    - From `scripts/dev/`: `results_dashboard.py`, the dashboard's only caller.
  - Archived scripts now import these as neighbours. The archived tests still pass from that folder (44).
  - One live test (`test_adu_types`, D-089's town prior) used `adu_profiles.town_sd`. It now computes
    |β_core| / z_90 inline, as the calibration runner does.
  - The app's trust panel names the dashboard command; its path now points to `scripts/archive/`.
  - Added rows to the archive README.
- **Decision:** Ben (2026-11-27): "yes, we don't need those to prove our results."
- **Outputs:** the moves above, `scripts/archive/README.md`, `tests/slow_tests.txt`, one line of
  `src/lotline/app/template.html`. PR (branch `ws/adu-archive`).
- **AI:** Claude Opus 5.5 did the moves. Checked by the caller grep, the archived tests run from the
  archive, the non-slow tests, `lotline calibrate --check` and the compliance check.
