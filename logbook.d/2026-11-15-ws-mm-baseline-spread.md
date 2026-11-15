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
  - **Cause:** 2–4 unit buildings come in projects. 47% of the five-year pseudo-forecasts saw none, and only 33%
    landed within ×2 of their baseline. A one-project burst in the three pre-years sets the baseline: Forney
    has a baseline of 178 and built 0.
  - **Proposal for Ben:** choose a steadier baseline on the same uncoded places before refitting.
  - **Outputs:** `reports/mm-d092/run7-kappa/` (README, summary.json, places.csv, run-log.txt, results.html) and
    `scripts/dev/mm_kappa_page.py`. Page: https://claude.ai/artifact/7PUN5YyVXbsDUSsg3e6SWD
