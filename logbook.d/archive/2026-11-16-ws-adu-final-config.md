### LB-NNN · 2026-11-16 · ADU · Final ADU config before the results bundles

- **Question:** bring the ADU config to its final state for the app. Ben's decisions: merge #444, turn on
  the m_x draws, report medians, keep Dallas as no ADUs.
- **Outputs:**
  - the refreshed fit (`reports/adu-final-config/`);
  - `config/params/hazard.yaml`, `adu_place_types.yaml`, `adu.yaml` (`adu_partial_share_draws` 1),
    `adu_anchor.yaml` and `adu_partial_share_grid.csv`;
  - `scripts/dev/adu_config_fit.py`; tests; the parameter table; a config note in `docs/analysis_plan.md`.
- **Result:**
  - θ 0.000224, α 1.505, m_x 0.7, core +1.740, on 70 places and 498 place-years;
  - D-097 draws on;
  - the app already headlines medians.
- **What Claude did:** merged #444 on Ben's word; refit on main's rows; regenerated the grid and slopes;
  updated config and the pinned tests; ran the checks.
- **How it was checked:**
  - the slope script's central fit and the grid's 0.7 row both equal the config fit;
  - the ADU tests pass (70); the full suite and compliance run before the PR.
