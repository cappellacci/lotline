### LB-NNN · 2026-11-09 · `missing-middle` · The missing-middle scenario in the app's results bundle

- **Question:** can the app show the Handbook missing-middle scenario next to ADUs?
- **Outputs:**
  - `src/lotline/model/results.py`: `mm_draws`, `mm_year_shares`; `build_bundle` runs `scenarios.mm` and adds
    its rows; `ENGINE_SCENARIOS` now ("adu", "missing_middle"). No schema change.
  - `src/lotline/model/scenarios/mm.py`: `Result.legal` (by data tier) and `Result.pencils` per draw;
    `f_share` (F(PCR)) kept beside `f_ratio`.
  - Tests: `tests/model/test_results.py` (+2: `mm_draws` by hand; the bundle's arithmetic reproduces
    the scenario's homes and teardowns).
  - `docs/analysis_plan.md` D-063: the bundle mapping.
- **What Claude did and how it was checked:** wrote the code and tests; built a real NC bundle
  (`lotline results --state nc`, gitignored) and the app page, and read the NC page in the in-app browser:
  missing middle shows 177–3,000 net homes (midpoint 791) beside ADUs 47–361. Spotted, not fixed (WS-APP):
  the page labels the window 2026–2030 from `origin_year + 1`, ignoring D-061's lead year.
