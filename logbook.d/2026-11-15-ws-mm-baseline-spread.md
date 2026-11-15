### LB-NNN · 2026-11-15 · Method: missing middle's baseline gets its own uncertainty (D-092 deviation; code only)
- **Question:**
  - Runs 4–5 found that no missing-middle model passes §7. The main cause is a no-reform baseline treated as
    known.
  - How do we give the baseline honest uncertainty without making each fit slower?
- **Decisions:**
  - Ben: "Yes, start step 1" (2026-11-15).
  - Ben, the same day: place types are a planned step whatever this run shows.
  - The deviation is pre-registered in `docs/analysis_plan.md` under D-092, before any refit or count.
  - The κ run and the refit each need Ben's go-ahead (§9).
- **What Claude did:**
  - **Model:** y_t ~ Poisson(w (B_t + θ u k_t)), with one w ~ Gamma(mean 1, variance κ) per place.
    - w multiplies the whole rate, so it integrates out in closed form, as a negative binomial on the place's
      total. A fit therefore costs the same as before.
    - A multiplier on B alone would have needed a 2-D integral, about 100× slower than run 4's 2 h 39 min.
  - **Code in `calibrate_mm`:** `kappa` on `Place` and `Stack`; `_w_mixed`; `fit_kappa`; `with_kappa`; and w draws
    in `predict_places` and `benchmark_places` from their own stream. κ = 0 leaves every likelihood and draw
    unchanged.
  - **New script:** `scripts/dev/mm_kappa_d092.py` estimates κ.
    - It uses 483 uncoded MN, NC, OH and TX places, from which every fit, test, level, excluded and holdout
      place is removed.
    - Each place is scored at two origins, 2016 and 2021. That gives 473 and 468 places; the dry run counted
      places only.
  - **Run scripts:** `--kappa` added to `calibrate_mm_d092.py` and `mm_tests_d092.py`. With κ > 0, only M and C4
    are refit and scored.
- **Outputs:**
  - `src/lotline/model/calibrate_mm.py`
  - `scripts/dev/mm_kappa_d092.py`, `scripts/dev/calibrate_mm_d092.py`, `scripts/dev/mm_tests_d092.py`
  - `tests/model/test_mm_baseline_spread.py` (17 tests)
  - the D-092 deviation entry in `docs/analysis_plan.md`
- **How it was checked:**
  - The closed form matches brute-force quadrature (to 1e-6), and so does the nested u × w integral (to 1e-3).
  - The stacked log-likelihood equals the sum over places.
  - `fit_kappa` gives 0 on data with no extra spread, and recovers κ = 0.5 from simulated places.
  - Draws at κ = 0 are bit-identical to the previous code.
  - The draws' variance matches the law of total variance.
  - The existing calibration tests pass (60), as do the full suite and `compliance_check.py`.
- **Not done:** no κ estimate, no refit and no test run. Those need Ben's go-ahead.
- **AI:** Claude (Opus 5.5) designed and wrote the code, the tests and the pre-registration. Ben approved
  starting the step.
- **Run 7, the κ estimate:** Ben asked for it once the tests passed. It took 90 s, offline.
  - **Result:** κ̂ = 7.65 (7.02–8.35). By state, MN 4.4, NC 5.0, OH 4.8 and TX 11.0.
  - **What that means:** the median place would get a multiplier of 0.02. That is not usable as it stands, so the
    refit was not started.
  - **Cause:** 2–4 unit buildings come in projects. 47% of the five-year pseudo-forecasts saw none, and only 28%
    landed within ×2 of their baseline. A one-project burst in the three pre-years sets the baseline: Forney
    has a baseline of 178 and built 0.
  - **Proposal for Ben:** choose a steadier baseline on the same uncoded places before refitting.
  - **Outputs:** `reports/mm-d092/run7-kappa/` (README, summary.json, places.csv, run-log.txt, results.html) and
    `scripts/dev/mm_kappa_page.py`. Page: https://claude.ai/artifact/7PUN5YyVXbsDUSsg3e6SWD
- **Deviation (b): the baseline choice, pre-registered and coded (no run).** Ben: "Yes, pre-register them".
  - **Pre-registration:** pushed first, in commit 5890ce71, before any scoring code.
  - **Candidates:** four constructions × two noise forms.
    - Constructions: C0 (3 pre-years, own growth), C1 (6 pre-years, own growth), C2 (6 pre-years, state
      growth) and C3 (6 pre-years, no growth).
    - Noise forms: Nw (place multiplier) and Ny (per-year negative binomial).
  - **Code:**
    - `calibrate_mm.nb_year_terms`, `baseline_scores` and `fit_noise`;
    - `scripts/dev/mm_baseline_choice_d092.py`, which fits on the 2016 origin, scores on 2021, and applies the
      2-SE preference rule and the coverage stop rule.
  - **Tests:** 7 more, 24 in all. They cover the NB by hand and against the gamma mixture, φ recovery, and the
    selection rule on hand-built scores.
  - **Dry run:** 473 and 468 pseudo-forecasts, present under all four constructions. The full suite passes (2,169).
- **CI failures Ben asked about (2026-11-15):**
  - `ruff check .` failed on every ADU branch from 14 Nov. The cause was `scripts/dev/adu_trend_page.py:49`, low
    in the stack. Local checks had linted only changed files.
  - The ADU session's rebase has fixed it. Its four rebased branches now fail `params_table.py --check`; that
    session has been told.
  - #395, #397, #398 and #401 had failed since 11 Nov on a Cincinnati test then broken on `main`. They are now
    merged with `main` and pushed.
- **Run 8, the baseline choice:** Ben said "Yes, run it". It took about 2 minutes, offline.
  - **The rule picks C0-year:** the current three-year baseline plus a per-year negative binomial, φ = 9.13.
  - **Margin:** C2-year (six years, state growth) scores best by 197, against a paired SE of 103. That is within
    2 SE, so the simpler candidate is kept. It is close.
  - **Noise form:** per-year noise beats a place multiplier by about 1,500 log points under every construction.
    The longer window doesn't help.
  - **Coverage:** 0.79 in 2021 (nominal 0.80), so the stop rule doesn't trigger.
  - **Next, pre-registered:** the NB likelihood in the fit, φ on both origins, then the refit and §7. All of it
    needs Ben's go-ahead.
  - **Outputs:** `reports/mm-d092/run8-baseline/` and `scripts/dev/mm_baseline_choice_page.py`. Page:
    https://claude.ai/artifact/BUNjwor6A2oD2WpUyEZLg8
- **Runs 9–11, the per-year NB in the fit, the refit and §7:** Ben said "Yes, code and refit".
  - **Code:**
    - φ is in `calibrate_mm`'s likelihood, held-out and no-effect scores, and draws. At φ = 0, draws are
      bit-identical.
    - 9 more tests, 33 in this file. The full suite passes (2,178).
  - **Run 9:** φ = 13.63 (12.85–14.48) on both origins.
  - **Run 10, the refit** (44 min):
    - M's θ is 1.68 per 1,000 (0.12–21.9). r5 is 0.00027, with a half-life of 4.5 years and α about 0.
    - Without Oregon, θ is 1.08, against 0.034 in run 4.
    - M beats no-effect by only 5.0 (SE 3.4).
  - **Run 11, the §7 tests:**
    - Test B, leave one state out and coverage (0.84) now pass.
    - Test C misses only on MN's three-place total: 79% of places are inside.
    - Test A has one place. The placebo still fails.
    - §5's rule picks C4.
  - **Plain reading:** the ranges are honest now, but too wide to show the reform's effect.
  - **Next, for Ben:** place types (already decided), and counting projects rather than buildings.
  - **Outputs:** `reports/mm-d092/run9-phi/`, `run10-refit-phi/` and `run11-tests-phi/` (README and page script).
    Page: https://claude.ai/artifact/Nc9Y2HZMAgmZbdb4sHPEEf
- **Deviation (c), place types: pre-registered and coded, not run.** Ben said "Yes, place types".
  - **Types:** ADU D-088's rule, in a new shared module, `src/lotline/model/place_types.py`, with 12 hand-worked
    tests. The ADU copy (PR #432) is to be merged into one later.
  - **Inputs count** (`scripts/dev/mm_types_d092.py --dry`): housing units and areas only, no permit count.
    - The 93 fit places are 86 Oregon places plus 7 elsewhere. Core cities and towns each come from 2 states, so
      D-088's size rule merges both. No type term on the reform rate.
    - The 483 unused places have every type in all 4 states, so φ by type can be tested there.
  - **Pre-registered:**
    - One φ against φ by type, trained on 2016 and scored on 2021, with a 2-SE rule.
    - If φ by type wins, refit and rerun §7, with the added criterion that ranges get narrower.
  - **Code:** a `Stack` can carry one φ per place (`with_phi_by`); 4 more tests. The `--phi-by-type` option is in
    the refit and test scripts.
  - **How it was checked:** the full CI set (ruff on the whole repo, params table, compliance, full pytest).
- **Run 12, φ by place type:** Ben said "Yes, run it".
  - **Result:** φ by type beat one φ by +24.8 held-out (paired SE 32.9), below the 2-SE bar, so it is **not
    adopted**. The refit and §7 rerun were not done, and run 11 stands. Coverage is 0.79 against 0.78.
  - **Reported only:**
    - φ on both origins: town 5.9, core city 15.8, suburb 16.3.
    - Within each state, suburbs are lumpier than towns. The state differs more than the type: Texas core
      cities and suburbs hit the search's edge.
    - The pre-run guess was that towns are lumpiest. It was wrong.
  - **Plain reading:** for missing middle, place types are coded but not used. The next lever is counting
    projects.
  - **Outputs:** `reports/mm-d092/run12-types/` (README, run log, type table) and
    `scripts/dev/mm_types_page.py`. Page: https://claude.ai/artifact/G5ceVA6aHXtUBP9UUMJEDf
- **What missing middle counts:** Ben asked to confirm the definition, then chose "Keep 2–4, disclose gaps".
  - The Handbook allows 2–6 homes per lot, up to three stories, and names townhouses. The model counts BPS
    2-unit and 3–4 unit buildings only; BPS files townhouses as 1-unit and puts 5–6 unit buildings in 5+. The
    reform strength (`units_grade`) stops at 4 homes.
  - Written up in `docs/model_and_assumptions.md` ("What missing middle counts", and the BPS limitation): the
    missing-middle result is a floor for the Handbook's scenario. The `units_grade` docstring no longer calls
    4 homes "the Handbook's fourplex". Proposed HANDOFF decision in the PR description.
  - Claude read the Handbook (via a fetch agent) and the code; the comparison was checked against
    `estimate_mm.py` and `calibrate_mm.py`.
- **Deviation (d), buildings per project: pre-registered and coded, not run.** Ben said "Do the size check first".
  - **Code:** `src/lotline/model/project_size.py` (same-lot and same-day groupings, inflation E[S²]/E[S]) with 7
    hand-worked tests; `scripts/dev/mm_project_size_d092.py` with `--dry`.
  - **Dry run:** field coverage per source only. 15 sources can group by lot, 20 by day.
  - **Rule:** same-day inflation under 1.5 → stop; same-lot 1.5 or more → raise the compound model.
- **Run 13, buildings per project:** Ben said "Yes, run it".
  - **Result:** pooled inflation E[S²]/E[S] is 12.8 grouped by lot and 5.3 by day. 34–42% of 2–4 unit
    buildings come in projects of 3 or more. By the pre-registered rule, the project model goes back to Ben.
  - Cities differ: Minneapolis 1.13, Cleveland 1.36, Cincinnati 1.41 (by lot); Austin 23.8, College Station
    22.0, Wilmington 16.6, Columbus 11.3. The pre-run guess (mostly single buildings) was wrong.
  - Same lot came out higher than same day, so it wasn't the lower bound the plan called it; both are over the
    bar. A check after the run, reported only: trimming each city's top 1% of projects leaves it well over 1.5.
  - **Outputs:** `reports/mm-d092/run13-projects/` (README, summary, coverage, run log, page) and
    `scripts/dev/mm_projects_page.py`. Page: https://claude.ai/artifact/BvoadqpTCF3itcSBYUYdgq
  - **How it was checked:** the grouping code has 7 hand-worked tests; the largest projects were looked at by
    hand (no `n_buildings` > 1 in any file, so the clusters are many permits on one parcel).
- **After run 13: recorded, not built.** Ben chose "Record it, choose config".
  - **Check after the run (reported only):** some permit files record one permit per home or duplex side
    (Austin's 202-permit parcel is about 100–130 duplexes; Durham 43% one-home duplex permits; Minneapolis's
    "3–4 unit" permits mostly carry no new homes). Recounted as homes ÷ homes per building, pooled inflation is
    11.8 by lot and 5.6 by day, 39–44% in projects of 3+: the finding holds. `check_building_equivalents.json`.
  - **Recorded:** a limitation in `docs/model_and_assumptions.md` (clustering is why the ranges are wide; a
    project model is a next step). README and page updated (same link).
  - **Aside for the data owner:** Minneapolis's `mpls_ccs_permits` types about 950 permits as 3–4 unit with 0
    new homes; worth a look in the adapter.
- **C4 to config:** Ben chose "C4 (θ 1.04)".
  - `config/params/mm_hazard.yaml`: θ 1.04 per 1,000 (0.13–19.4), half-way point 4.0 years (1.0–6.0), α at
    the search's floor, new `mm_year_spread_phi` 13.63 (run 9). Parameter table regenerated.
  - `scenarios/mm.py` draws each place-year's added buildings with the fit's lumpiness (Poisson × Gamma, mean 1,
    variance 1/φ); 2 hand-worked tests (mean kept, NB variance; no φ unchanged). V5 and V9 code left as frozen.
  - **Effect on the scenario** (`reports/mm-d092/config-c4/`, `scripts/dev/mm_config_compare.py`): statewide
    median net homes over five years rise about 2.5× (MN 696 → 1,758; TX 4,747 → 12,066), P90s about 4×;
    year 5 carries 57% of the total. Page: https://claude.ai/artifact/1BzpK5S9isRk9eptDaBKDR
  - Decision recorded in `docs/analysis_plan.md`; proposed for HANDOFF in the PR description.
  - **How it was checked:** the 57 config-dependent tests (scenario, V5, V9, results) and the full CI set.
- **Accuracy report:** Ben asked how accurate the missing-middle model is at three jobs: a place's count, a
  statewide total, and a new state.
  - Built from results already on file; nothing rerun, no permits read: run 11's §7 tests for C4, run 12's
    held-out baseline coverage, V5 Charlotte (blind, D-055 values) and V9 Oregon (frozen D-038).
  - **Findings:** 78% of 136 places inside their P10–P90 (target 60–95%); the baseline alone 79% of 468 held-out
    places. Single places miss by up to 3–6× at the median (Franklin County, Minneapolis), still inside. State
    totals inside for TX and OH, missed for MN (small numbers). New state: Oregon held out, 703 built against a
    median of 915 (457–4,789). The reform effect itself isn't clearly detected (+5.0, SE 3.4; placebo fails).
  - **Outputs:** `scripts/dev/mm_accuracy_page.py`, `reports/mm-d092/accuracy/results.html`. Page:
    https://claude.ai/artifact/72uydyJJNJduLuErr9uQXw
  - **How it was checked:** every number read from the result files by the script; the page was viewed in the
    browser.
