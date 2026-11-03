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

### LB-NNN · 2026-11-03 · Research: missing-middle causal diagram v0.2, checked against the D-038 fit
- **Question:** which confounders and modifiers did D-038 leave out, and which can our own data measure, before
  D-039 picks any? Ben asked for land value, growth, and year-to-year interest rates to be covered.
- **What I did:**
  - Audited all register factors that bear on the fit: what D-038 did with each, which slot it belongs in
    (baseline, uptake or count), and what data we hold.
  - Added a v0.2 diagram and two register rows: C55, the national 2–4 unit cycle; C56, the growth index as a bad
    control.
  - Read the FRED national series and the D-038 per-place report. Ran no fit or model.
- **Outputs:**
  - §6 of `docs/research/lotline-causal-diagram-mm.md`;
  - rows C55–C56 in `docs/research/lotline-confounder-register.csv`.
- **Findings:**
  - Nationally, the 2–4 unit share of permits rose from 2.8% (2014) to 3.9% (2025), mostly in the 2022–25
    high-rate years. D-038's baseline assumes a flat share, so it is about 15% low in Houston's 2024–25.
  - Rate regime is confounded with place: every large place is exposed only at about 6.7% rates.
  - Only about 7 places carry information, so θ can take at most two place-level modifiers.
  - Pre-reform land values exist for TX (2019) and parts of NC and MN, not Ohio.
  - Houston's 2–4 count should be checked against its own permit records before any fit.
- **Decisions:** none. The D-039 proposal is in §6.4, for Ben.
- **AI:** Claude Code (Opus 5.5) wrote the audit and computed the FRED shares. The figures were checked against
  `reports/mm-d038/places.csv`, and `compliance_check.py` shows 0 FAIL.

### LB-NNN · 2026-11-03 · Data check: Houston's 2024–25 2–4 unit count against the city's own permits
- **Question:** is the Houston jump that carries D-038 a reporting change in Census BPS?
- **What I did:**
  - Pulled the City of Houston residential permit summary through the IO layer. A first ad hoc pull was
    superseded in the manifest, and the file was re-pulled by the new adapter `checks.houston_permits`.
    Registered it as a documented-only source, which needed a one-line change to `registry.documented_only`.
  - Compared it with BPS (`scripts/dev/houston_bps_check.py`).
  - Read the Houston and Austin reform rows. Fitted nothing.
- **Outputs:**
  - `src/lotline/adapters/checks/houston_permits.py`;
  - `tests/adapters/test_houston_permits.py`;
  - `reports/mm-d038/houston_check.csv`;
  - §6.5 of `docs/research/lotline-causal-diagram-mm.md`;
  - the regenerated `docs/data_provenance.md`.
- **Findings:**
  - BPS matches the city's own single-family permits within 7% in every year 2012–2025. There is no
    reporting break at the reform.
  - The 2025 fall in houses is real in the city's data, but whether some attached houses were filed as duplexes
    needs permit-level records.
  - Houston's duplexes were legal before Livable Places, and 3–4 unit buildings stayed near zero. The D-038
    Houston "effect" is a duplex trend the reform did not enable. D-039 should count only the types each reform
    newly allows.
- **AI:** Claude Code (Opus 5.5) wrote the adapter, script, test and write-up. The checks were the two tests,
  ruff and `lotline provenance --check`.
