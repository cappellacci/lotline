### LB-NNN · 2026-11-17 · Missing middle: fast-ramp sensitivity (D-100), what if builders took it up as fast as cities that chose it?

- **Question:** D-100 found that places adopting missing middle on their own reach half pace in about half a
  year, against 4 years for Oregon's state-required places. Ben asked for that fast ramp as a sensitivity next
  to the main (C4) result.
- **Outputs:** `mm_ramp_half_years_fast` in `config/params/mm_hazard.yaml` (0.5, high 1.0, cited to D-100 run
  1); `scenarios/mm.py` (`RAMPS`, `ramp_half`, `run(..., ramp="fast", places=...)`); two hand-worked tests in
  `tests/model/test_scenario_mm.py`; `scripts/dev/mm_fast_ramp_run.py`, `scripts/dev/mm_fast_ramp_page.py`;
  `reports/mm-d100/fast-ramp/`; results page https://claude.ai/artifact/CjkLoS18nmRupLFcyskYR6. D-100 gained
  a pre-registration bullet (written before the run) and a run bullet.
- **Result:** five-year totals 3.30× C4's at half-way 1.0 and 3.61× at 0.5, in every state, exactly as
  predicted by hand; Texas median 12,066 → 43,589 net homes. Main values in config unchanged.
- **What Claude did and how it was checked:** wrote the pre-registration, config entry, code, tests, run and
  page. The main variant reproduces config C4's published numbers to the home (same draws and seed); the ratios
  match the ramp sums computed before the run. Page checked in the browser. The first run attempt stopped
  because `CENSUS_API_KEY` was not loaded (the county-share step needs it even from cache); rerun with `.env`.
- **Open:** showing it in the app needs a new results-bundle part (shared contract, WS-CORE).
