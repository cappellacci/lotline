### LB-NNN · 2026-11-13 · ADU model · Does a calendar-year trend help, and can the model forecast 2021–25 from 2016–20? (D-085 built and run)

- **Question:** Ben accepted D-085 ("Accept both"). Built and run once: does Form T (a shared yearly trend)
  beat its base on test D (new: fit 2016–20, forecast 2021–25) without losing ground elsewhere?
- **Outputs:**
  - `src/lotline/model/adu_trend.py`, `joint_refit.GlobalsA` γ draws, `config/params/adu_trend.yaml`;
  - `tests/model/test_adu_trend.py` (11 hand-worked tests);
  - `scripts/dev/adu_trend_refit.py`, `scripts/dev/adu_trend_page.py`;
  - `reports/adu-time-trend/` (README, CSVs, `results.html`); results page
    https://claude.ai/artifact/7XoGFvJ5UyHnyBvAV8Ypxb;
  - D-085 Built note and Result in `docs/analysis_plan.md`.
- **Result:** the rule keeps no trend (test D gains 4.2 and 0.7, bars 16.3 and 15.3). In sample γ is −0.128 a year,
  mostly Oregon (−0.044 without it). No form forecasts 2021–25 reliably; a carry-forward of each place's early
  rate does as well. Minneapolis's 2021 reform is forecast as a ~10× step that never came.
- **What Claude did and how it was checked:** wrote the code and tests; the trend fitter with γ held at 0
  reproduces D-084's fitter on synthetic data and recovers a planted γ; the base forms reproduce D-084's real
  fits to the digit. Code and Built note committed before any fit (`f7689e84`). Offline; St. Paul out.
