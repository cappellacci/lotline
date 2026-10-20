### LB-NNN · 2026-10-20 · Run: D-025 main model estimated; run stopped at randomization inference
- **Question:** What does the pre-registered pooled model estimate for the ADU reform effect in the Twin Cities?
- **What I did:** ran `scripts/dev/estimate_pooled_adu.py --full --out reports/adu-d025/` once.
- **Inputs:** main after #181/#182 plus D-025 (#191).
- **Outputs:** `reports/adu-d025/run-2026-10-20-log.txt`; dated note under D-025.
- **Findings:** main model converged (76 places, 760 place-years, 31 treated, 53 with no ADU; nothing
  dropped). Overall effect 2.26 on the log scale (90% 0.22–4.21; wide); bands 0–1: 2.32 (0.61–3.93),
  2–3: 1.88 (−0.52–4.15), 4+: 2.38 (−0.01–4.72); all modifiers weakly identified; ρ −0.18 (−0.50–0.16);
  δ −2.69 (−3.30 to −2.04; one place changes status, so weakly identified per D-023). A permutation refit in
  randomization inference did not converge and the guard stopped the run: checks, robustness and transport
  were not computed.
- **Decisions:** none; the handling of non-converging permutation refits needs a dated entry.
- **AI:** Claude ran the script once and transcribed the printed estimates.
- **Open / next:** decide the permutation-failure rule; run the remaining stages once.

### LB-NNN · 2026-10-20 · Build + run: D-025 convergence rule; remaining stages run once
- **Question:** With Ben's convergence rule for repeated refits, what do randomization inference, the checks,
  robustness and transport show for the D-025 main model?
- **What I did:** wrote the rule under D-025 and pushed it (e5185ed) before running; implemented it
  (`pooled_adu.refit`, `RefitLog`, tolerant score bootstrap, stage stop above 5%), with stub tests (fails
  once then succeeds on retry from the main estimates; fails twice and is excluded; > 5% stops a stage; a
  single-refit check reported as not computed); added `--remaining` to `scripts/dev/estimate_pooled_adu.py`,
  which reuses the main model (recomputed deterministically and checked against the first run's log) and runs
  the remaining stages once.
- **Outputs:** `src/lotline/model/pooled_adu.py`, `tests/model/test_pooled_adu.py`, the script,
  `reports/adu-d025/` (results), `docs/analysis_plan.md` (D-025 notes).
