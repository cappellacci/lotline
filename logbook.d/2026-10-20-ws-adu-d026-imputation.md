### LB-NNN · 2026-10-20 · Study design: D-026 imputation estimator for the ADU effect (pre-registered, not run)
- **Question:** what replaces D-023's primary ADU estimator, given that a 2026-10-20 review found design
  defects (not just thin data), and can the replacement be shown to fix each failing regime before any
  real-data estimate?
- **What I did:**
  - Wrote D-026 in `docs/analysis_plan.md` before any code or estimate (its own commit). It sets out an
    imputation estimator (Borusyak et al.) on the additive scale: a place + year Poisson model fitted on
    untreated rows only, with ATT per 1,000 eligible parcels by k ∈ {0–1, 2–3, 4+}. It also covers explicit
    exclusions, parking/process/replaced-rule controls, θ and δ declared not identified (heterogeneity
    described; hierarchical NB priors stated in advance), randomization inference as primary, a stratified
    place bootstrap for the range, and seven checks including anticipation (C29) and first ring excluded (C26).
  - Implemented it in `src/lotline/model/estimate_adu.py` (`impute`, `randomization_inference` that moves
    each dose path with T, `place_bootstrap`, `summarize_att`, `check_*`, `transport_predict`). Fixed D-023
    defects 6 (dose path in RI), 7 (2025 year effect after the panel; `year_effect`) and 8 (household
    growth never after adoption; `household_growth`). Added `T_announce`, `parking` and `process` to the
    panel. Kept D-023's estimator as the robustness run.
  - Rewrote `scripts/dev/estimate_adu.py --full` for D-026. **Not run.**
- **Inputs:** D-023 and its run logs; protocol §5.6–5.7; causal diagram and confounder register (C08, C21,
  C26, C29); `config/reforms/mn.csv` (theme counts only).
- **Outputs:** `docs/analysis_plan.md` (D-026), `src/lotline/model/estimate_adu.py`,
  `tests/model/test_estimate_adu.py`, `scripts/dev/estimate_adu.py`.
- **Findings (synthetic panels only):** D-023 gets each regime wrong: zero pre-periods (log effect ~2.6 vs
  log 50 = 3.9), a 2016 cohort and pre-panel adopters with growth past k = 5 (both ≈ 0 vs ~0.9 and ~0.45).
  With singleton cohorts its interval covers 37%. D-026 recovers the additive truth in all four. Its
  bootstrap interval still covers only 77% with six singleton cohorts, so RI carries the inference and the
  range is labelled "probably too narrow" below 10 contributing places.
- **Decisions:** D-026 proposed; awaiting Ben's approval before the one real run.
- **AI:** Claude Code wrote D-026, the code and the tests. Each regime test asserts D-023 fails and D-026
  passes on the same simulated panel; hand-worked examples cover `impute`, `replaced_rule_dose`,
  `shift_dose_path` and `household_growth`. No real-data estimate was computed.
- **Open / next:** Ben approves (or amends) D-026; the TIGER adjacency dataset for the first-ring check; the
  Minnesota rules file codes no `process` reforms and 2 parking rows, so those controls may drop.
