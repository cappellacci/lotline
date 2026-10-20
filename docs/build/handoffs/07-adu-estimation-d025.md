# Thread 7: ADU estimation, D-025 (WS-ENGINE)

**Precondition:** Ben has approved D-025 as described below, and PRs #181 (separation fix) and #182 (rerun log) are merged. Until then, stop.

**Context:** D-023's fixed-effects PPML was underpowered on the Twin Cities panel: 53 of 76 places had zero ADU permits every year; only 143 of 760 place-years remained; no modifier was identified; the bootstrap tripped the coefficient guard. See D-023's dated notes and `reports/adu-d023/`.

**Goal:** write **D-025** in `docs/analysis_plan.md` before running anything, then run it once.
- **Main model:** the statistical protocol's pooled model (§5.7): a negative binomial with place random effects (partial pooling), year fixed effects, the log(eligible parcels) offset, and the effect pooled over event time (k = 0–1, 2–3, 4+). Pre-adoption modifiers stay in (z-scores) and are reported as weakly identified if their intervals are wide; never silently dropped. Same dose, sample, holdout and exclusions as D-023 (St. Paul out; Hastings out; early adopters don't inform modifiers).
- **Robustness:** D-023's fixed-effects PPML (if it estimates), the Borusyak imputation estimator, and a binary by-right dose.
- **Checks and transport test:** as in D-023, with the same pass rules.
- **Estimation:** maximum likelihood with a Laplace or adaptive-quadrature integral over the random effects, in numpy (no new dependencies without Ben's OK); or a Gibbs or Hamiltonian sampler if justified in the PR.
- **Tests first:** synthetic panels with 70% all-zero places recover the pooled effects; the common-shock test; the separation tests carry over.

**Run once** after tests pass, and report whatever it shows, with chart-ready numbers.

**Done when:** D-025 PR (pre-registration and code) and a results PR are open with green CI.
