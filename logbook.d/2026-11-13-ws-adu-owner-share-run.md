### LB-NNN · 2026-11-13 · ADU model · Does owner-occupied share improve the ADU model on D-079's tests? (D-084 built and run)

- **Question:** Ben accepted D-084 ("Accept D-084"). Built and run once: does Form A′ (Form A × exp(β_o z),
  with z the ACS 2011–15 owner-occupied share) beat Form A on D-079's tests, under D-084's rule?
- **Outputs:**
  - `src/lotline/model/adu_owner.py` (the term, the fit-3 fitter, the decision rule);
  - `joint_refit.GlobalsA` β_o draws;
  - `config/params/adu_owner.yaml` (center, scale, fit vintage only);
  - `tests/model/test_adu_owner.py` (10 hand-worked tests);
  - `scripts/dev/adu_owner_refit.py` and `scripts/dev/adu_owner_page.py`;
  - `reports/adu-owner-share/` (README, CSVs, `results.html`);
  - D-084 status, Built note and Result in `docs/analysis_plan.md`.
- **Result:**
  - **The rule picks A′.** Neither form passes any tier: A′ has 1 useful state per tier, A has 0. A′'s
    held-out log score is +5.0, against a 2-SE bar of 4.1. Tests A–B are 1 vs 1.
  - **Fit:** β_o −0.55 (−0.88 to −0.22), and α falls 19%.
  - **States:** every state moves the right way, but TX and OR stay about ×2.5 under.
  - **Nothing is in config;** adoption is Ben's call.
- **What Claude did and how it was checked:**
  - Wrote the code and tests. The new fitter reproduces `calibrate_adu.fit3` on synthetic data, and its
    Form A matches D-079's refit to four figures on the real fit set.
  - Committed the code and the Built note before any fit (`7760ee5e`).
  - A first start stopped before scoring because the worktree had no `CENSUS_API_KEY`. It reran with the main
    `.env`, offline.
  - After the run, a descriptive check found that the six MN townships explain why β_o is smaller than the
    screen's value.
  - St. Paul stayed out, and ACS rows went through `holdout.apply_acs`.
