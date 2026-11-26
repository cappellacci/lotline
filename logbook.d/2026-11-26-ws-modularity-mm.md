### LB-NNN · 2026-11-26 · Modularity · Step 2 for missing middle: fitting code out of model/

- **Question:** Can the missing-middle fitting and check code leave `src/lotline/model/`, so the folder holds
  only what a forecast runs, with no number changing?
- **Outputs:**
  - `src/lotline/model/mm_rates.py`: the four helpers the forecast takes from the fit. These are
    `units_grade`, `blank_shares`, `rule_dose`, `plex_price_to_cost` and `_mm_coverage`. `scenarios/mm.py`
    and `estimate_mm` both import them from here.
  - `src/lotline/calibrate/mm/`: `estimate_mm`, `calibrate_mm`, `mm_fitsets`, `mm_routes`.
  - `src/lotline/calibrate/place_types.py`, shared with ADU's D-088.
  - `src/lotline/validation/`: `mm_tests`, `mm_counts`, `project_size`. These are the D-092 checks and
    counts, kept with their hand-worked tests rather than archived.
  - Tests moved with their modules to `tests/calibrate/` and `tests/validation/`. The engine helpers' tests
    are now in `tests/model/test_mm_rates.py`.
  - `tests/core/test_module_layout.py`: the MM lines were removed from `MOVING`, and `pooled_adu` was added
    for ADU. It was on the forecast path only through `estimate_mm`.
  - Runner notes in `calibrate/steps.py` and `config/calibration.lock.json`, comments in
    `config/params/mm.yaml`, and `docs/calibration.md`, `docs/adding_a_state.md` and `README.md` now name
    the new paths. Dated records in `docs/analysis_plan.md` and `docs/build/` keep the old ones.
- **Decision:** Ben, 2026-11-26: "yes, do steps 2 and 3 after #559 merges".
- **What Claude did and how it was checked:**
  - The modules were moved with `git mv` and the import paths rewritten. No function body changed.
  - Results bundles for MN, NC, OH, TX, OR and WI were built from `main` and from this branch. The sha256 of
    every part, run-time metadata dropped, matched. `config_hash` changes only because comments in `mm.yaml` and the lock's script notes changed.
  - `lotline calibrate --check` and `params_table.py --check` pass.
  - The non-slow tests pass (COUNT), and compliance shows 0 FAIL.
  - Every script in `scripts/dev/` still imports. The archived scripts that load a neighbour by file path
    fail as they already did on `main`.
