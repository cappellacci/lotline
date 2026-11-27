### LB-NNN · 2026-10-21 · Study design: D-031, additive imputation as robustness to D-025, and review fixes ported to the D-025 path
- **Question:** after a 2026-10-20 review found design defects in D-023's estimator, what still applies now
  that D-025 (pooled hierarchical NB) is the main model, and what robustness and sensitivity runs should be
  declared before D-025's remaining stages run?
- **What I did:**
  - First drafted a replacement main estimator (additive imputation). Ben kept D-025 as the main model
    (2026-10-21), so the entry became **D-031** in `docs/analysis_plan.md`: robustness, written after
    D-025's main estimate (overall 2.26, 90% 0.22–4.21) and its checks and robustness results were seen, and
    unable to change the main result.
  - Ported the fixes that apply to D-025: randomization inference now moves each dose path with its permuted
    adoption year (`estimate_adu.permute_adoption`, used by `pooled_adu.randomization_inference`); household
    growth is never measured after adoption (`estimate_adu.household_growth`); the panel gains `T_announce`,
    `parking` and `process`.
  - Declared three D-025 sensitivity runs (`pooled_adu.sensitivity_runs`): pre-panel adopters excluded, T at
    the announcement year, and parking/process controls (`build_pooled_design(controls=...)`). These were
    wired into `scripts/dev/estimate_pooled_adu.py` with the D-031 additive imputation. **Not run.**
  - Stacked the branch on #192 by merging `ws/engine-17-d025-results`.
- **Inputs:** D-023 and D-025 entries and logs; protocol §5.6–5.7; confounder register (C08, C21, C26, C29);
  `config/reforms/mn.csv` (theme counts only).
- **Outputs:** `docs/analysis_plan.md` (D-031), `src/lotline/model/estimate_adu.py`,
  `src/lotline/model/pooled_adu.py`, `scripts/dev/estimate_pooled_adu.py`, `tests/model/test_estimate_adu.py`,
  `tests/model/test_pooled_adu.py`.
- **Findings (synthetic panels only):** D-023 fails each review regime: zero pre-periods (2.5–3.2 against log
  50), a 2016 cohort (≈ −0.1 against ~0.9), pre-panel adopters growing past k = 5 (≈ 0 against ~0.45), and
  singleton cohorts (θ collinear, interval coverage 37%). D-031's additive imputation recovers each. Its
  bootstrap still covers only 77% with six singleton cohorts.
- **Decisions:** for Ben: approve D-031 (a)–(c); choose whether to re-estimate the D-025 main model on the
  corrected household-growth panel (the `--remaining` match check will stop otherwise).
- **AI:** Claude Code wrote the entry, code and tests. Each regime test asserts D-023 fails and D-031 passes on
  the same panel; the RI test records every permuted panel and checks the dose path; the sensitivity test
  records each refit's panel and keywords. No real-data estimate was computed.
- **Open / next:** Ben's approval; the remaining D-025 stages; the TIGER adjacency dataset for a spillover
  run.
