### LB-NNN · 2026-11-17 · Build: WS-SCALE task 4 (part 1), place_inputs and a read cache
- **Question:** Can one table hold every shared per-place input the ADU, missing-middle and fee models and
  the baseline read, reproducing today's values exactly?
- **What I did:**
  - `src/lotline/build/place_inputs.py`: one row per (state, geoid, year), every jurisdiction x every BPS
    year; the row for year Y holds what a run with origin Y reads. Filled by calling the functions the models
    use today (nearest roll, `non_overlapping`, `acs_values`, `house_shares`, `fees.parcel_inputs`, observed
    ADU counts), once, instead of in each model. A `models` / `models_note` pair says which models read the
    row and why it is out of the others. No fills: each model keeps its own missing-value rule until task 5.
  - `DataStore.read` cache keyed on file path, size and modification time; returns copies.
  - Moved the synthetic national-only state "ZZ" into `tests/conftest.py` (fixture `zz`).
- **Inputs:** processed tables of the five states (read-only, offline).
- **Outputs:** `src/lotline/build/place_inputs.py`, `src/lotline/io/store.py`, `tests/build/test_place_inputs.py`,
  `tests/core/test_io.py`, `tests/conftest.py`.
- **Findings:** On the synthetic state and on the five states' real tables (origin 2025), every shared column
  equals what `adu.places_from_store` and `mm.places_from_store` compute (counts in the PR description).
- **Decisions:** none yet; the table is not yet wired into `lotline fetch` nor read by any model (owners'
  switch-over PRs).
- **AI:** Claude wrote the module, tests and comparison script; checked as above.
- **Open / next:** register as a build step; hand switch-over notes to the ADU and MM owners; fee dev run.
