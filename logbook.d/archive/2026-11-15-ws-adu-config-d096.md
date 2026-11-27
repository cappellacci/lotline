### LB-NNN · 2026-11-15 · ADU · Engine config moved to the D-096 fit

- **Question:** move the ADU engine's fitted values to the refit on the coverage-fixed rule rows. Ben:
  "Yes, update config".
- **Outputs:**
  - `config/params/adu.yaml`, `hazard.yaml`, `adu_place_types.yaml` and `adu_anchor.yaml` (regenerated);
  - `docs/model_and_assumptions.md` (parameter table);
  - `tests/model/test_scenario_adu.py` (pinned values);
  - `scripts/dev/adu_refit_fixed_rows.py` (also cuts the D-079 fit set) and
    `scripts/dev/adu_config_fixed_rows_page.py`;
  - `reports/adu-config-fixed-rows/`; page https://claude.ai/artifact/N2MHdgvxHh3KL3rM2nLP7i;
  - the D-096 adoption note.
- **Result:**
  - m_x 0.4 → 0.7, θ 0.448 → 0.240 per 1,000, α 1.55 → 1.44, core +1.20 → +1.67.
  - The Handbook bill's additional homes fall by about half: the five states go from 6,819 to 3,948 at P50.
  - The row fixes alone change little; the new m_x drives it. m_x is fixed in a run, although its
    leave-one-state-out range is 0.4 to 1.0; that is flagged for Ben.
- **What Claude did:** reran the fit for the m_x interval; regenerated the slopes; updated the config and the
  tests; ran the engine three ways (today, fixed rows with the old values, fixed rows with the new values)
  from a scratch checkout of PR #440 that was never committed; built the page.
- **How it was checked:**
  - the slope script's central fit matches D-096 (63 places, 446 place-years, θ 0.2403, α 1.439, core +1.670);
  - ADU tests pass (72); the parameter table check passes; ruff passes.
