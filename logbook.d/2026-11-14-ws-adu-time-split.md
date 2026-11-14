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
