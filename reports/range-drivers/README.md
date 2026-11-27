# What drives each result's range (issue #54)

First-order sensitivity shares for every state and scenario, from the 1,000 runs in each results bundle.
Nothing is rerun.

    PYTHONPATH=scripts/archive uv run python scripts/archive/range_drivers.py --results reports/results --out reports/range-drivers

- **Method:** `scripts/archive/sensitivity.py`. It gives each input's share of the variance of
  log(net homes + 1), Var(E[Y|X]) / Var(Y), estimated from the runs with 20 equal-count bins. The chance
  level is removed, so shares under about 3% are noise.
- **Inputs:** each run's parameter draws, regenerated from the scenario's seed, plus the bundle's
  completion, net-new and displacement draws.
- **Alignment check:** the script checks the regeneration exactly, against the ADU net-new share.
- **Inputs used:** the bundles of release `app-2026-11-27` (commit a42ba317), the published results. Rerun
  on 2026-11-27; the shares quoted in `docs/policy_scenario_comparison.md` come from this file.
- **Outputs:** `drivers.csv` (state, scenario, input, plain label, share, P90 ÷ P10). The 2026-11-24 results
  page was dropped because its numbers came from an older release.
- **Limits:**
  - Shares of correlated inputs overlap. The ADU uptake rate is refitted for each drawn partial-rule share,
    so those two overlap.
  - Total-order shares (interactions) would need new runs and are not estimated.
  - "Other" is place-to-place luck, rule draws and the unseen-state multiplier.
