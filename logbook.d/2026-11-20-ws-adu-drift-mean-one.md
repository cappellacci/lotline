### LB-NNN · 2026-11-20 · ADU · Re-centre the per-place ADU drift so a state's forecast sits on its permit pace

- **Question:** with D-091's median-1 drift, NC's no-reform forecast sat far above its permit history. Does a
  mean-1 drift fix that, and what does it do in the other states?
- **Outputs:** `own_rate_draws(mean_one=...)` in `src/lotline/model/scenarios/adu.py`; switch
  `adu_drift_mean_one` in `config/params/adu.yaml` (parameter table regenerated); test in
  `tests/model/test_adu_own_rate.py`; dated deviation in `docs/analysis_plan.md` (proposed D-entry).
- **What Claude did and how it was checked:** wrote the switch and a hand-worked test (each mean-1 draw is the
  median-1 draw × exp(−σ²/2) = ×0.5914; drift mean 1). Ran both settings for every state, one state at a
  time (Ben's machine had frozen under parallel runs); table in the deviation entry. Ben asked for the fix in
  chat; the "ADU reform level discrepancy in North Carolina" session had started it and handed it back.
