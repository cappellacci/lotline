### LB-NNN · 2026-11-15 · ADU · m_x drawn from a refitted grid (D-097), and a gut-check page

- **Question:** carry m_x's uncertainty into the ranges (D-097, accepted); then show how well the model
  predicts ADUs within a state and what it predicts for 2027–31. Ben: "Once we've made this update, I'd like
  to see a visual breakdown … My goal here is to gut check the results."
- **Outputs:**
  - D-097's status and result in `docs/analysis_plan.md`;
  - `config/params/adu_partial_share_grid.csv`, plus `adu_partial_share_draws` (off) in `adu.yaml`;
  - `scenarios.adu.apply_partial_share_grid` and its tests;
  - scripts: `adu_mx_grid.py`, `adu_mx_engine.py`, `adu_gut_check_data.py`, `adu_gut_check_places.py`,
    `adu_gut_check_page.py`;
  - `reports/adu-mx-grid/`, `reports/adu-mx-engine/`, `reports/adu-gut-check/`;
  - gut-check page https://claude.ai/artifact/GTSTVZFmMr7gdwJsV52KXq.
- **Result:**
  - Drawing m_x keeps the medians and widens the ranges somewhat.
  - The gut check shows good within-state forward forecasts (state totals inside their ranges) and wide but
    honest ranges for an unseen state.
  - It flags the large predicted gains in core cities that allow no ADUs today (Dallas, Fort Worth,
    Cleveland) and a no-reform mean above recent counts.
- **What Claude did:** implemented and tested the grid draws, ran the fits and five engine variants, built
  the page, and checked it in the browser.
- **How it was checked:**
  - the grid's 0.7 row equals D-096's fit, and a test checks it against config;
  - mode 3 at 0.7 reproduces the fixed run exactly (test);
  - current-rules ADUs stay within 2%.
  - The held-out mixture score was not computed (disclosed in D-097).
