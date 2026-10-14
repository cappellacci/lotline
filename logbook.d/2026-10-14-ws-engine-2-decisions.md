### LB-NNN · 2026-10-14 · Validation: V1 decisions D-002 to D-006 and a pre-declared demand specification
- **Question:** How should V1 be judged, and what's the next baseline specification, fixed before running it?
- **What I did:** Applied Ben's five decisions on PR #93: randomized coverage (D-003), bias on the mean (D-004), spec B kept with A reported (D-002), a 20-parcel scoring floor (D-005, new parameter `v1_min_eligible_parcels` and test). Wrote spec C (county household growth and house-price change, coefficients fitted on fit years only) into `docs/analysis_plan.md` as D-006 **before** any run. Reran V1 with the floor.
- **Inputs:** WS-ENGINE V1 report (PR #93).
- **Outputs:** `docs/analysis_plan.md` (D-002 to D-006), `src/lotline/model/backtest.py`, `config/params/baseline.yaml`, `tests/model/test_backtest.py`.
- **Findings:** With the floor, still 17 of 48 cells pass. The model beats both benchmarks for 2+ unit buildings (5+: 2.82 vs 3.29 and 3.94 MAE per 1,000 parcels) but is now slightly worse than the 3-year mean for single-family (10.08 vs 9.66): the demand signal is needed there.
- **Decisions:** D-002 to D-006 (Ben, 2026-10-14).
- **AI:** Claude Code (coordinating session) implemented the floor and test, reran the backtest, and drafted the plan entries Ben approved.
- **Open / next:** implement and run spec C once (D-006); Ben chooses B or C (D-007).
