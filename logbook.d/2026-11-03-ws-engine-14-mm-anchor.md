### LB-NNN · 2026-11-03 · Build: missing-middle uptake calibrated on the four states (D-038)
- **Question:** what mature uptake hazard, ramp and homes per building does the missing-middle scenario get
  when they are calibrated on our own post-reform places (D-037 amendment)? How well does that predict
  reformed places it did not see?
- **What I did:**
  - First draft (same day): compiled outside evidence (Portland, Houston, Auckland, SB 9, Oregon, Spokane,
    Arlington) into `docs/research/mm-uptake-evidence.md` and register rows E105–E113. After Ben's change of
    direction this became the plausibility check.
  - Pre-registered the fit in D-038 and pushed it before running anything:
    - a Poisson-gamma model on BPS 2–4 unit buildings;
    - each place's pre-reform baseline × its growth in other homes, plus θ × eligible parcels × dose × feasibility
      × ramp;
    - a profile-likelihood interval, checks 1–7, a V4 leave-one-place-out backtest and the D-037 test places.
  - Wrote `src/lotline/model/calibrate_mm.py`, with 17 tests against hand-worked and closed-form cases, and
    `scripts/dev/calibrate_mm.py`. Ran it once.
- **Inputs:** the D-024 four-state panel (`estimate_mm.build_panel`, holdout-filtered); D-014, D-019, D-030,
  D-037 and its amendment.
- **Outputs:**
  - `config/params/mm_hazard.yaml`;
  - `reports/mm-d038/`;
  - D-038 in `docs/analysis_plan.md`;
  - `docs/research/mm-uptake-evidence.md`;
  - register rows E105–E113;
  - the parameter table in `docs/model_and_assumptions.md`.
- **Findings:**
  - θ = 1.08 per 1,000 eligible parcels a year (0.36–5.35), ramp half-way at 2 years, α = 7.3.
  - The estimate rests on Houston: 0.57 without it, 0.24 without Houston and Austin (exploratory).
  - The placebo date gives 0.32, so the check is not passed.
  - Backtest coverage is 67%, but the error is no better than assuming no effect.
  - The out-of-sample tests are covered 4 of 4.
  - The local permit files can't count buildings, so BPS gives homes per building: 2.08.
- **Decisions:** D-038 for Ben to confirm. It deviates from the pre-registration in two places:
  - homes per building comes from BPS, not the local permit files;
  - the eligible-lot check was not done (parcel numbers don't match).
  - Choices left for Ben: accept the fit, widen the ramp range, or change the growth control (a new entry).
- **AI:** Claude Code (Opus 5.5) wrote the method, code, tests and reading. Research subagents compiled the
  outside table. The checks were the unit tests, the full suite and `compliance_check.py`. The likelihood was
  checked against the closed-form negative binomial and frailty cases.
- **Open / next:**
  - fix the permit-to-parcel join for check 6;
  - decide on the placebo shortfall;
  - build the missing-middle scenario on these parameters.
