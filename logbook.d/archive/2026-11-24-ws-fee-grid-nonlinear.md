### LB-NNN · 2026-11-24 · APP · Why did Minnesota and Oregon's results stop at the fee-slider check, and what is the fix?

- **Question:** the build-time check from #510 stopped the MN and OR bundles: houses there take the
  lot-feasibility route (places with a parcel roll), and its homes are not linear in the fee change. Can the
  slider still be exact there?
- **Outputs:**
  - `results.fee_types_with_stops` and `FEE_STOPS` in `src/lotline/model/results.py`: a size that is not
    linear gets the engine's value at every slider stop;
  - `results_fee_types` schema 1.22 in `src/lotline/schemas.py`;
  - `feePolicyDraws` and `fee_policy_draws` use a stored stop where one exists and scale the half cut
    otherwise;
  - tests in `tests/model/test_results.py` and `tests/app/test_aggregate_parity.py`.
- **What Claude did and how it was checked:**
  - Tests with a hand-made non-linear grid, parity with a stored curve, and 806 core, app, results and fee
    tests.
  - The MN bundle builds. Houses abolished: 583 vs 2 × 293 at the half cut; a 50% rise: −320. The MN bundle
    grows to 5.5 MB.
  - The check had worked as intended: it stopped a wrong slider before anything was published.
