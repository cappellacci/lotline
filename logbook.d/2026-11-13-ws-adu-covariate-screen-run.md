### LB-NNN · 2026-11-13 · Analysis: D-083 run, the ADU place-effect covariate screen
- **Question:** which place factors that the ADU model doesn't use explain the spread between places (α) in
  the D-079 Form A fit?
- **Decisions:**
  - Ben accepted D-083 on 2026-11-13 ("Accept D-083"), and the screen ran as written.
  - Its thresholds are in `config/params/adu_screen.yaml`. These are test bars, not model values.
- **What Claude did:**
  - Wrote `src/lotline/model/adu_screen.py`, which vectorizes `calibrate_adu.frailty_loglik` with a
    per-place exp(βz) scale, and provides the profile fits, Holm, the posterior means and the verdict.
  - Added 8 tests: hand-worked values, a match to `calibrate_adu`, and planted-effect recovery.
  - Wrote the run script `scripts/dev/adu_covariate_screen.py` and the page builder
    `scripts/dev/adu_screen_page.py`.
  - Ran the screen offline in 11 minutes. ACS, BPS and parcel rolls went through the holdout filters, and
    St. Paul stayed out.
- **Outputs:**
  - `reports/adu-covariate-screen/`: README, screen.csv, factors.csv, summary.json and results.html.
  - The results page is published as an Artifact.
- **Findings:**
  - **Two candidates pass all three bars, both narrowly:**
    - owner-occupied share: β −0.71 per SD, Holm p 0.083, α falls 16% (26% pooled);
    - pre-1960 housing share: β +0.59, Holm p 0.095, α falls 11% (within states only).
  - **Not measurable:** new-house rate, lot size, detached share, place size and home value.
  - **Not screened:** HOA share (no data) and homestead share (Minnesota only).
- **How it was checked:**
  - The unit tests pass.
  - At β = 0 the vectorized likelihood equals `calibrate_adu.frailty_loglik_place`.
  - The factor SDs used in the README were recomputed from `factors.csv`.
  - The page was viewed once in the browser.
  - `params_table.py --check` and `compliance_check.py` were run.
- **AI disclosure:** Claude Code wrote the code, ran the screen and wrote the report and page. Ben decides the
  next step.
- **Leave-one-place-out check:** Ben asked for it ("Run the check"), and it was pre-registered as a dated
  addition to D-083 before it ran.
  - Each of the 57 places was dropped and β refitted. Both candidates are robust: β kept its sign and p stayed
    below 0.10 in all 57 drops.
  - Owner share ranges from −0.83 to −0.55. Housing age ranges from +0.43 to +0.70, weakest with Asheville
    out (p 0.075).
  - Outputs are `influence.csv` and `influence.json`; the page gained Finding 4.
  - The code is `adu_screen.drop_one` and `influence_reading`, with 2 new tests.
