### LB-NNN · 2026-11-26 · Modularity · Step 3 for missing middle: the two big fitting files split by method step

- **Question:** Can `calibrate_mm.py` (1,535 lines) and `estimate_mm.py` (1,219) be split so a reader finds
  each method step in its own file, with no number and no caller changing?
- **Outputs:**
  - `calibrate_mm` is now eight modules in `src/lotline/calibrate/mm/`, each under 360 lines:
    - `places`: inputs, baselines, dispersion test;
    - `likelihood`: the place likelihood, with the κ and φ forms;
    - `year_spread`: `fit_noise`, `fit_kappa`;
    - `fit`: θ, α, the half-way point and the five-year ramp;
    - `capacity`: D-042;
    - `backtest`: V4;
    - `state_backtest`: D-054 and τ;
    - `challengers`: D-092's standards events, level prior C4, C1, C3 and model choice.
  - `estimate_mm` is now three modules: `panel`, `estimate` (PPML, NB, RE, bootstrap) and `checks`
    (randomization inference, the checks, `transport_predict`).
  - `calibrate_mm.py` and `estimate_mm.py` stay as short maps that re-export every name, including the
    names they imported. Scripts, validation and tests are unchanged, except one test, which now patches
    `fit_re` in `estimate`, where it is called.
- **Decision:** Ben, 2026-11-26: "yes, do steps 2 and 3 after #559 merges". `mm_counts.py` (820 lines, in
  `validation/`) is left whole for now. It is outside the engine size guard and lower priority.
- **What Claude did and how it was checked:**
  - A script cut each module at its existing section banners, unchanged. It worked out each part's imports
    from the names that part uses and refused any circular one. Two definitions were placed by hand:
    `_interval`, the shared profile-interval helper, went to `likelihood`, and `Fit` went to `fit`.
  - Every one of the original 109 top-level names in `calibrate_mm` is still reachable from it.
  - Results bundles for MN, NC, OH, TX, OR and WI built from this branch match `main` in every part, run
    metadata aside.
  - The non-slow tests pass, and `ruff` and `calibrate --check` pass. Each part keeps its existing
    hand-worked tests, which reach it through the re-exporting module.
