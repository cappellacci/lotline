### LB-NNN · 2026-11-26 · Modularity · Step 2 for missing middle: fitting code out of model/

- **Question:** Can the missing-middle fitting and check code leave `src/lotline/model/`, so the folder holds
  only what a forecast runs, with no number changing?
- **Outputs:**
  - `src/lotline/model/mm_rates.py`: the four helpers the forecast takes from the fit. These are
    `units_grade`, `blank_shares`, `rule_dose`, `plex_price_to_cost` and `_mm_coverage`. `scenarios/mm.py`
    and `estimate_mm` both import them from here.
  - `src/lotline/calibrate/mm/`: `estimate_mm`, `calibrate_mm`, `mm_fitsets`, `mm_routes`.
  - `src/lotline/calibrate/place_types.py`, shared with ADU's D-088.
  - `scripts/archive/`: the D-092 checks and counts (`mm_tests.py`, `mm_counts.py`, `project_size.py`), with
    their drivers (`mm_tests_d092.py`, `mm_counts_d092.py`) and `scripts/dev/estimate_mm.py`. Nothing in the
    forecast or calibration uses them. Their three hand-worked test files were deleted (Ben, 2026-11-27:
    "Archive them"); git history keeps them.
  - Tests moved with their modules to `tests/calibrate/`. The engine helpers' tests are now in
    `tests/model/test_mm_rates.py`.
  - `tests/core/test_module_layout.py`: after main's ADU move (#565) was merged in, `MOVING` is empty.
  - Runner notes in `calibrate/steps.py` and `config/calibration.lock.json`, comments in
    `config/params/mm.yaml`, and `docs/calibration.md`, `docs/adding_a_state.md` and `README.md` now name
    the new paths. Dated records in `docs/analysis_plan.md` and `docs/build/` keep the old ones.
- **Decision:** Ben, 2026-11-26: "yes, do steps 2 and 3 after #559 merges". Ben, 2026-11-27, on the three
  D-092 check modules: "Archive them".
- **What Claude did and how it was checked:**
  - The modules were moved with `git mv` and the import paths rewritten. No function body changed.
  - Results bundles for MN, NC, OH, TX, OR and WI were built from `main` and from this branch. The sha256 of
    every part, run-time metadata dropped, matched. `config_hash` changes only because comments in `mm.yaml` and the lock's script notes changed.
  - `lotline calibrate --check` and `params_table.py --check` pass.
  - The non-slow tests pass (COUNT), and compliance shows 0 FAIL.
  - Every script in `scripts/dev/` still imports. The archived scripts that load a neighbour by file path
    fail as they already did on `main`.
