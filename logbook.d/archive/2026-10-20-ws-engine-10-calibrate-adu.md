### LB-NNN · 2026-10-20 · Calibration: ADU anchor estimated from Lotline's own post-reform places (D-019); non-overlapping scenario units (D-020)
- **Question:** What mature ADU hazard do our own post-reform places support, tested on a place held out in
  advance, and does the scenario count any parcel twice?
- **What I did:**
  - Pre-registered the fit (fit Minneapolis + Twin Cities suburbs + Austin when coded; test Raleigh, Durham
    when fixed; NB likelihood; profile interval) in D-019 and pushed it (commit fd21217) before any fit ran.
  - `src/lotline/model/calibrate_adu.py`: NB likelihood, profile-likelihood fit with α and the partial share
    profiled, predictive bootstrap, place-year assembly from the processed tables (`place_years`).
    `scripts/dev/calibrate_adu.py` runs the pre-registered fit and an exploratory Austin variant.
  - Wrote the estimate into `config/params/hazard.yaml`; re-ran the development run and current-rules check.
  - `scenarios/adu.non_overlapping`: local-only places no longer double-counted in ACS-fallback county
    remainders (D-020). D-021 proposes rule coverage (zones, lot sizes).
- **Inputs:** permits flagging ADUs (Met Council, Minneapolis, Raleigh, Austin); config/reforms; ACS; FRED.
- **Outputs:** the files above; `tests/model/test_calibrate_adu.py`; tests in `test_scenario_adu.py`;
  `docs/analysis_plan.md` (D-019 results, D-020, D-021); `docs/model_and_assumptions.md`.
- **Findings:** θ = 0.000467 per parcel a year (90% 0.000275–0.000868), 0.12 of Portland's band; α = 6.6;
  partial share not identified (kept at 0.3). Raleigh test: 230 observed vs mean 112 (90% 2–445): inside but
  wide. With the new anchor the model gives 0.3x observed in Minneapolis, Raleigh and Austin (2016–22).
  Development run, five-year added ADU permits: MN 1,362, NC 2,088, OH 1,584, TX 7,859. D-020 removes NC
  344,992 and MN 10,459 double-counted eligible parcels.
- **Decisions:** D-019 results (estimate replaces the anchor per the pre-registered rule); D-020 and D-021
  proposed.
- **AI:** Claude wrote the estimator, tests (hand-worked likelihood, recovery and coverage on simulated data)
  and scripts, ran the fit once per the pre-registration, and reported the misfit without refitting.
- **Open / next:** re-run the fit after Austin's rules are coded and Durham's parcels rebuilt (no code
  change); pre-register the next specification (graded partial share, coverage, place effects).
