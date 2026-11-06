## LB-xxx · 2026-11-06 · WS-ENGINE · D-055: does the ACS fallback stand in for real eligible-parcel counts?

**Question answered:** (Drafted as D-053 in the 2026-11-06 docs; renumbered D-055 at merge because D-053 and D-054 were taken.) Can a state with no parcel data use ACS one-unit detached homes as its eligible-parcel denominator, i.e. does the pre-registered D-055 test (leave one state out, every held-out ratio in [0.7, 1.4]) pass on the five states that have both?

**Outputs**
- `src/lotline/model/eligible_proxy.py`: `proxy_test` (r_s, k, leave-one-out k_(−s) and q_s, σ, verdict) and the per-draw step `multipliers` / `proxy_states`.
- `scripts/dev/eligible_proxy_test.py` → `reports/eligible-proxy/` (`ratios_adu.csv`, `ratios_missing_middle.csv`, `by_jurisdiction.csv`, `summary.json`).
- `docs/analysis_plan.md` D-055: **Result** appended, status set to run/passed.
- `config/params/eligible_proxy.yaml`: `eligible_proxy_scale` 0.998 (0.939–1.059) and `eligible_proxy_sd` 0.060, source D-055.
- `model/scenarios/adu.run(..., eligible_proxy=True)`: multiplies a tier-3 state's eligible parcels per draw by k·exp(σz), one z per state per draw, own random stream; off by default, so V9's frozen Oregon run (ACS fallback) and every existing run are unchanged.
- `tests/model/test_eligible_proxy.py`: hand-worked three-state examples (one failing, one passing), level-invariance, the multiplier step, and a run-level test that a parcel-based state is bit-identical with the step on.

**Result:** pass. ADU held-out ratios MN 1.052, NC 0.927, TX 1.071, OH 0.916, OR 1.045; k = 0.998, σ = 0.060. Missing middle (check) also inside the band, k = 1.136, σ = 0.044. The proxy is near-unbiased for ADU because the ADU rule needs an existing single-family house but no single-family-only zoning; missing-middle eligible counts run ~14% above it (vacant lots, unknown zoning counted as SF-only).

**Decisions proposed for HANDOFF**
- D-055 passed: the national-data-only tier is built; every state in `config/states/` gets a bundle with the overlap flag and the "zoning not observed" caveat.
- Open: one k (ADU's) is applied to every theme, per the rule as written; a missing-middle-specific scale (1.136) would need its own analysis-plan entry.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-ENGINE instance) wrote the module, script and tests, fixed the implementation choices (newest roll per jurisdiction; ACS end year paired by `eligible._nearest_acs_year`, as `scale_history` anchors a roll) before the run, ran it once, and recorded the numbers by the rule already written. Checked by the hand-worked unit tests, the full test suite, ruff and `compliance_check.py` (0 FAIL). Data read only through `DataStore` processed tables (holdouts removed by the adapters); no outcome read.
