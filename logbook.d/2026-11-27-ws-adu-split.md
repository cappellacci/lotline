### LB-NNN · 2026-11-27 · Build: the ADU scenario split by method step (modularity step 3, ADU part)
- **Question:** can `scenarios/adu.py` (1,732 lines) become one module per method step, each under the
  620-line limit, without any result changing?
- **What I did:**
  - Moved the code unchanged into seven step modules in `src/lotline/model/scenarios/`:
    - `adu_rules.py`: legal lots, how close each place's coded rule is to the Handbook (`current_rules`).
    - `adu_rule_priors.py`: rule priors for places with no coded rule, and each place's rule share.
    - `adu_rule_inputs.py`: coded reforms, the states that feed shared pools, parcel coverage, `rule_inputs`.
    - `adu_params.py`: the parameters and their draws, and the partial-rule-share grid.
    - `adu_place_types.py`: the core-city term and the town prior.
    - `adu_paths.py`: uptake and pool depletion (`pool_paths`), the state effect and extrapolation noise.
    - `adu_own_rate.py`: observed ADUs and own-rate persistence with drift.
  - `adu.py` keeps the method docstring, the totals (`run`, `central_path`) and the store reader
    (`places_from_store`), and re-exports every moved name, so `scenarios.adu.<name>` still works for
    callers, scripts and docs.
  - Two tests now patch `REFORM_STATES`, `load_reforms` and `coverage_map` on `adu_rule_inputs`, where
    `rule_inputs` reads them. `scenarios.adu` left `OVERSIZE` in `tests/core/test_module_layout.py`, which is
    now empty.
- **Decision (mine, the brief left it to the owner):** legal lots is three modules, not one, so each stays
  well under the limit. No new tests: every step already has direct hand-worked tests (mostly in
  `tests/model/test_scenario_adu.py` and `test_adu_own_rate.py`).
- **Inputs:** none new (results runs read the shared data store).
- **Outputs:** the seven modules above; PR (see branch `ws/adu-split`).
- **AI:** Claude Opus 5.5 split the file with a script that moved each top-level definition whole. Checked by
  bundle hashes for MN, NC, OH, TX, OR and WI on main and on the branch (every part except run-time
  metadata), the guard test, `lotline calibrate --check`, the non-slow tests, ruff and the compliance check.
- **Open / next:** none for ADU modularity. Splitting `tests/model/test_scenario_adu.py` to match is
  optional.
