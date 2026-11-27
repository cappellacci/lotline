### LB-NNN · 2026-10-20 · Build: D-023 staggered-adoption ADU estimator (built and tested; not yet run)
- **Question:** Can the pre-registered D-023 model recover known reform effects, and keep a common shock out
  of them, before it touches real data?
- **What I did:** `src/lotline/model/estimate_adu.py`: PPML with place and year fixed effects by IRLS
  (numpy), Wooldridge cohort × event-time cells scaled by dose, θ (pre-adoption modifiers × post), ρ (rate ×
  post), δ (missing middle); exposure-weighted aggregation to β_k and the overall effect; wild cluster score
  bootstrap (Webb weights, CR2 scores); randomization inference; the five D-023 checks; transport predictions
  and the pass rule; the panel builder from processed tables. `scripts/dev/estimate_adu.py` (`--smoke`,
  `--full`). Dose values in `adu.yaml` (flagged). Implementation notes under D-023.
- **Inputs:** D-023 (PR #175); Met Council permits; config/reforms; ACS; BPS; FRED.
- **Outputs:** the module, script and `tests/model/test_estimate_adu.py`; `docs/analysis_plan.md` (D-023
  implementation notes), `docs/model_and_assumptions.md` (status row), `config/params/adu.yaml`.
- **Findings:** on simulated panels the 90% intervals cover the true β_k, θ, ρ and δ (≥ 15 of 20 panels each);
  a −0.7 common shock after 2021 with no reform effect gives an overall effect near 0 with 0 in its interval;
  the lead test's size is 11–12% at the 10% level (150 panels); without CR2 the cluster SEs ran 10–15% low.
  Transport predictions for held-out simulated places cover at about nominal rates. Smoke test of the real
  panel (counts only): 21 places with dated rules, 164 left out, 12 ever treated (6 in 2016–2025).
- **Decisions:** none new; choices the spec leaves open are listed under D-023 for Ben.
- **AI:** Claude wrote the estimator, tests (hand-worked PPML, recovery, common shock, check behaviour,
  transport coverage) and script; no estimate was run on real data.
- **Open / next:** the real run, once, after the adoption dates for the 162 metro places are coded.
