### LB-NNN · 2026-11-26 · Calibration · Phase 3: the missing-middle steps run from code; φ has drifted

- **Question:** Do the four missing-middle calibration steps re-derive config from today's tables with one
  command, no number changing?
- **Outputs:**
  - `src/lotline/calibrate/mm_steps.py`: runners for `mm_units_per_project`, `mm_year_spread`, `mm_c4` and
    `mm_fast_ramp`, wired in `steps.py`.
  - `src/lotline/model/mm_fitsets.py`: the fit sets moved out of `scripts/dev/calibrate_mm_d092.py`,
    `mm_kappa_d092.py`, `calibrate_mm_d054.py` and `calibrate_mm_d042.py`. The scripts now import them.
  - `mm_ramp_d100.py` reads φ from config instead of a hard-coded constant.
  - Tests: `tests/model/test_mm_fitsets.py` and `tests/calibrate/test_mm_steps.py`.
  - `docs/calibration.md`.
- **Decision:** Config is not changed. φ's drift is Ben's call (phase 5 refits are his).
- **What Claude did and how it was checked:**
  - A parity run on real data compared the old scripts with the library. Both give the same C4 fit set (93
    places), level set (15), prior and year-spread places.
  - Full runs reproduce 15 of 18 numbers exactly once rounded half up to config's precision:
    - units per project 2.08 (2.04-2.75);
    - mature rate 0.0010387 (0.0001316-0.01939);
    - place-effect variance 6.1e-06 (6.1e-06 to 1.92);
    - half-way point 4.0 (1.0-6.0);
    - fast half-way point 0.5 (0.5-1.0).
  - φ gives 13.03 (12.39-13.70) against 13.63 (12.85-14.48). The same rules now keep 713 places (1,379
    forecasts) where run 9 kept 483 (941), because the tables have grown since.
  - Hand-worked tests cover units per building, the event split, the year-spread exclusions and the
    significant-figure rounding.
