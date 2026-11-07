### LB-NNN · 2026-11-06 · Engine: D-059 five-year window starts in 2027 (proposed)
- **Question:** The entry is read in 2027. Should the five-year projection still be 2026–2030, the five years
  right after the 2025 data origin?
- **What I did:** Checked the Handbook and the Rules: they fix a five-year horizon but no start year. Then I
  drafted D-059:
  - a new parameter `forecast_lead_years` = 1, so origin 2025 gives a 2027–2031 window;
  - the baseline simulates the lead year and drops it, and the scenarios start their reform clock at 2027;
  - the backtest keeps its registered lead through `v1_lead_years` = 0, and lead 1 is available as a
    supplementary check;
  - window labels in the ADU and fee scenarios, the results bundle and the dev runs.
  
  Listed four open items: which rules count as "current", the housing-need denominator's years, the bundle
  metadata, and earlier published results.
- **Outputs:** D-059 in `docs/analysis_plan.md`; `config/params/baseline.yaml` (`forecast_lead_years`,
  `v1_lead_years`); `src/lotline/model/baseline.py` (`window`, `window_label`); `src/lotline/model/backtest.py`;
  `src/lotline/model/scenarios/adu.py` (`pool_paths(lead=)`); `src/lotline/model/scenarios/fees.py`;
  `src/lotline/model/results.py`; `scripts/dev/adu_dev_run.py`; `tests/model/test_forecast_window.py`; one test in
  `tests/model/test_backtest.py`. Year labels updated in the scenario and results tests; the hand-worked baseline
  tests now pin lead 0. HANDOFF decision proposed in the PR description.
- **How Claude helped and how it was checked:** Claude (Claude Code) read the Handbook and Rules through a
  fetch agent, wrote the code, tests and entry, and ran the full test suite and `compliance_check.py`. Every
  new test is worked by hand. One test checks that the lead-1 draws are exactly years 2–6 of a lead-0, six-year
  run. No model or scenario runs on real data were made.
