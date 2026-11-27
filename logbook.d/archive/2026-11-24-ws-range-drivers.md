### LB-NNN · 2026-11-24 · Uncertainty · Which assumptions drive each reform's range? (issue #54)

- **Question:** The Handbook asks which assumptions matter most, and the "Critical assumptions" section of
  the Policy Scenario Comparison was empty. Ben chose a cheap version over full Sobol (2026-11-24, "Let's do
  the cheap review").
- **Outputs:**
  - `src/lotline/model/sensitivity.py` and `tests/model/test_sensitivity.py`.
  - `scripts/dev/range_drivers.py`.
  - `reports/range-drivers/`: `drivers.csv`, `README.md`, and `results.html`
    (https://claude.ai/artifact/AWq8ivW6dLV82AaLhpSERk).
  - The "Critical assumptions" section of `docs/policy_scenario_comparison.md`.
- **Result:**
  - Missing middle: its fitted uptake rate explains 96% of a ×40 range in every state.
  - Fee cuts: the fee-to-permits elasticity explains 42–93%.
  - ADUs: the fitted uptake rate and the partial-rule share together explain most of a ×4.5–7 range.
  - Wisconsin's ADU range comes mostly from its unseen-state adjustment.
- **What Claude did and how it was checked:**
  - Claude Code first tried splitting the bundle's per-run product. That was uninformative, because θ
    there is back-solved and soaks up everything.
  - It then regenerated each run's parameter draws from the scenarios' seeds and estimated first-order
    shares from the existing runs.
  - The estimator has hand-worked and analytic tests. The draw regeneration is checked exactly against
    the bundles.
  - No model code, config or results changed.
