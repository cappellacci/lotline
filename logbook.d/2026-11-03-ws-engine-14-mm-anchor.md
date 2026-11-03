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

### LB-NNN · 2026-11-03 · Data check: Austin's post-HOME two-family counts hold ADUs
- **Question:** does Austin's 2024–25 jump in 2-unit buildings come from ADUs being recorded as two-family
  buildings? Ben raised it.
- **What I did:** counted the city's new-building permits by Census class against BPS
  (`scripts/dev/austin_permit_class_check.py`). Read the HOME phase 1 ordinance copy in `manual/texas`. Fitted
  nothing.
- **Outputs:** `reports/mm-d038/austin_check.csv`; §6.6 of `docs/research/lotline-causal-diagram-mm.md`.
- **Findings:**
  - Yes. ADU permits fell from about 340 a year to 9 after HOME removed the secondary-apartment use, while
    two-family permits rose to 367. Their sum did not rise.
  - BPS 2-unit buildings follow the city's class, so D-038's Austin excess is mostly relabelled ADUs.
  - 3–4 unit permits, the type HOME newly allowed, stayed at 3–7 a year.
  - Austin's BPS 2-unit series also breaks in 2016–18.
  - Duplex and two-family uses existed before HOME; which districts allowed them is still to be read.
- **AI:** Claude Code (Opus 5.5) wrote the script and the write-up. The figures were checked against the
  stored permits and BPS tables.
- **Open / next:** Austin ADU counts from 2024 need the description flag, not the class (ADU side). Read the
  pre-HOME Austin code for SF-3 duplexes.

### LB-NNN · 2026-11-03 · Ordinance check: Austin's duplex and two-family rules before HOME
- **Question:** which Austin single-family zones allowed duplexes before HOME phase 1?
- **What I did:** read p. 2 of our HOME phase 1 copy as an image, and the 2015 ADU ordinance, both in
  `manual/texas`. Compared them with our Austin and Houston reform rows. Fitted nothing.
- **Outputs:**
  - §6.7 of `docs/research/lotline-causal-diagram-mm.md`;
  - `docs/research/ordinances/tx-corrections-2026-11-03.csv`, two proposed new rows for Ben.
- **Findings:**
  - Duplex and two-family residential were already permitted in SF-3, with up to 2 units per lot. HOME added
    them in SF-1 and SF-2, added three-unit everywhere, and raised the cap to 3.
  - Austin's old two-family use was a house plus a second unit in a separate structure, which is an ADU.
  - Our coding has no pre-HOME Austin row and no pre-2023 Houston duplex row.
- **Decisions:** none. The two rows wait for Ben, because they change the D-024 and D-025 panel.
- **AI:** Claude Code (Opus 5.5) read the ordinance page images and wrote the rows and the write-up.

### LB-NNN · 2026-11-03 · Coding: pre-reform missing-middle rows for Austin and Houston applied
- **Question:** apply the two proposed rows? Ben said "Apply both rows".
- **What I did:**
  - Added TX-4805000-missing_middle-2010 (SF-3 duplex and two-family, cap 2) and TX-4835000-missing_middle-2010
    (duplexes on single-family lots, cap 2) to `config/reforms/tx.csv`.
  - Tagged both `[predates]` and linked the 2024 and 2023 reforms to them with `supersedes`.
  - Marked the decision in `docs/research/ordinances/tx-corrections-2026-11-03.csv` and added a note to D-038.
  - Computed the D-022 blank shares before and after. Ran no fit.
- **Findings:**
  - Both places now have a rule in force before the window, so they leave the D-038 adopter set.
  - Blank shares barely move: P(by right) 0.842 → 0.846, units grade 0.298 → 0.299.
  - D-038's committed results predate the change.
- **Checks:** the Texas reform and schema tests (162 passed) and `compliance_check.py`.

### LB-NNN · 2026-11-03 · Method: D-039 drafted (second missing-middle fit, before any run)
- **Question:** how should the missing-middle fit change, given the confounder review and the Houston and
  Austin findings?
- **What I did:**
  - Drafted D-039 in `docs/analysis_plan.md`. It makes three changes:
    - the outcome counts only the building types each reform newly allows (prior cap from the reform rows);
    - the baseline comes from same-state comparison places;
    - there is one modifier, builder capacity.
  - Kept land share, a national 2–4 unit share baseline and dropping Houston and Austin as checks.
  - Fixed a reading rule for Ben's "do the confounders matter" question.
  - Before writing, looked only at structure: places by status, prior caps, and parcel-value vintages.
- **Findings that shaped it:**
  - Only Austin and Houston have an earlier rule followed by a later increase.
  - Only 5 of 14 fit places have a pre-reform value vintage.
  - Coded comparison places are 4 (MN), 2 (NC), 0 (OH) and 33 (TX), so uncoded places join the comparison set.
- **Decisions:** none. D-039 waits for Ben's approval before the code and the single run.
- **AI:** Claude Code (Opus 5.5) drafted the entry. It ran no fit.
