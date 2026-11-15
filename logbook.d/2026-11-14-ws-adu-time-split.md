### LB-fragment · 2026-11-14 · ADU model · Can a state's own ADU history forecast its next five years?

- **Outputs:** D-090 (proposed) in `docs/analysis_plan.md`, branch `ws/adu-time-split` (built on
  `ws/adu-age-term`, #426).
- **Answer:** a method entry, written before any fit.
  - Fit on 2016–2019, with 2020 as the lead year, and forecast 2021–2025 in MN, NC, TX and OR.
  - Three forecasters: F0, persistence; F1, Form A with state θs and each place's own history; F2, F1 plus
    housing age within states.
  - Claim if F1 is useful in at least 3 of the 4 states. F1 must beat persistence by more than 2 SE in log
    score to claim value beyond pricing rule changes.
- **HANDOFF:** proposes D-090 (D-088 and D-089 taken by other threads). Ben to accept or amend, including the
  3-of-4 bar.
- **What Claude did:**
  - Asked by Ben ("Draft it D-90") after D-087 kept Form A.
  - Before writing, tallied observed and Form A expected ADU totals by state and year (descriptive only, the
    fit's own counts). They show no common trend, so the entry has no pooled trend term.
  - Cited D-048 and D-052 as the evidence against extrapolating a trend.

### LB-fragment · 2026-11-14 · ADU model · D-090 built and run: does own history forecast 2021–2025?

- **Outputs:**
  - Code: `src/lotline/model/adu_forecast.py`, `tests/model/test_adu_forecast.py` (16 hand-worked tests),
    `scripts/dev/adu_time_split.py`, `scripts/dev/adu_time_split_page.py`.
  - Results: `reports/adu-time-split/` (README, CSVs, `results.html`).
  - Results page: https://claude.ai/artifact/Bfz5915ng524v1tJu1mW1o
  - D-090's "Built" and "Result" notes in `docs/analysis_plan.md`.
- **Answer: no.**
  - F1 is useful in 1 of 4 states (bar 3).
  - F1 is no better than persistence: −5.5 against 2 SE = 204.
  - Housing age (F2) makes forecasts worse.
  - Persistence's medians are within ×2 in all four states. Every range is far too narrow (about ±9%), because
    nothing lets a place's rate drift between periods.
  - The mechanism priced NC's rule changes well (Wilmington, Charlotte) and over-priced Minneapolis and Bend.
- **HANDOFF:** D-090 accepted by Ben (2026-11-14, with the 3-of-4 bar). The result awaits his acceptance.
- **What Claude did:**
  - Recorded the acceptance.
  - Wrote the module and tests. They include a check that the log score and the draws agree on P(window = 0).
  - Listed places and rule changes by code before any fit, and committed them at 62669bd5.
  - Ran a smoke run (its per-state lines were seen) and parallelized the grid cells.
  - Ran the full run, then wrote the README and the page.
- **How it was checked:**
  - 57 tests pass (new, D-087's and the joint refit's).
  - Ruff is clean.
  - I checked the page's claims against the CSVs. One wrong note ("eight places carry nearly all of the
    difference") was corrected before publishing: they make up 90% of the absolute differences, but they
    cancel.
