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
