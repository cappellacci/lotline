### LB-NNN · 2026-11-05 · validation · Does the V9 runner use the engine's adopted state-to-state spread?

- **Question:** after #279, #285 and #295 merged (D-044, D-048, D-050), does the V9 runner match the scenario?
  The ramp was already switched (40fe189). The state effect wasn't.
- **Finding:** `v9.adu_draws` read `adu_state_effect_sd`, which D-044/D-050 made a reference value (the
  maximum-likelihood τ, 0). So Oregon had no state multiplier. The scenario instead draws τ each draw from the
  grid in `adu_state_effect.yaml`.
- **Outputs:**
  - `src/lotline/validation/v9.py` now uses `scenarios.adu.state_effect` and `state_noise`: one exp(τ_d z_d) per
    draw, shared by Oregon's places.
  - `tests/core/test_v9.py`: existing tests pin τ = 0; a new test checks the multiplier's spread and that it
    is shared across places and absent for a fitted state.
  - `docs/analysis_plan.md`: D-051 amended, before any freeze.
- **Dry run (1,000 draws, not committed), 2018–2025 P10/P50/P90:**
  - Portland: transfer 3 / 150 / 1,418; own history 4,070 / 8,580 / 17,832.
  - Bend: 0 / 22 / 206.
  - Oregon 2–4 unit headline: 1,738 / 2,658 / 6,469 (62 places).
- **What Claude did and how it was checked:** read the scenario's implementation and matched it; tests use
  synthetic inputs; ran the full suite, ruff and `compliance_check.py`.
