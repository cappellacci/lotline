# What drives each result's range (issue #54)

First-order sensitivity shares for every state and scenario, from the 1,000 runs in each results bundle.
Nothing is rerun.

    uv run python scripts/dev/range_drivers.py --results reports/results --out reports/range-drivers

- **Method:** `src/lotline/model/sensitivity.py`. It gives each input's share of the variance of
  log(net homes + 1), Var(E[Y|X]) / Var(Y), estimated from the runs with 20 equal-count bins. The chance
  level is removed, so shares under about 3% are noise.
- **Inputs:** each run's parameter draws, regenerated from the scenario's seed, plus the bundle's
  completion, net-new and displacement draws.
- **Alignment check:** the script checks the regeneration exactly, against the ADU net-new share.
- **Inputs used:** the bundles of release `app-2026-11-24f` (commit 97e2436b).
- **Outputs:** `drivers.csv` (state, scenario, input, plain label, share, P90 ÷ P10) and `results.html`
  (https://claude.ai/artifact/AWq8ivW6dLV82AaLhpSERk).
- **Limits:**
  - Shares of correlated inputs overlap. The ADU uptake rate is refitted for each drawn partial-rule share,
    so those two overlap.
  - Total-order shares (interactions) would need new runs and are not estimated.
  - "Other" is place-to-place luck, rule draws and the unseen-state multiplier.
