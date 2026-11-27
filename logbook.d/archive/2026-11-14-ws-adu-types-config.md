### LB-NNN · 2026-11-14 · ADU model · Put Form A + place types and the town prior in config

- **Question:** Ben chose Form A + place types (D-088) and accepted D-089's town prior. He then approved writing
  the fitted values to config ("Open the config PR").
- **Outputs:**
  - `config/params/adu_place_types.yaml`: the typing rules, the A + P fit and the town prior sd;
  - the parameter table in `docs/model_and_assumptions.md`, regenerated;
  - two tests in `tests/model/test_adu_types.py`, which check that the config matches the module's typing
    defaults and that the town sd equals |β_core| / 1.645;
  - a config note under D-089 in `docs/analysis_plan.md`.
- **Result:**
  - The values are in config, but the engine doesn't read them yet. It still runs D-053's Form A.
  - The file's θ is a suburb's rate, so switching the engine before the core term is wired would understate core
    cities about 3.3-fold. The switch waits for the wiring PR.
  - α's 90% interval is 1.05–2.30, from observed information.
  - The rule shares' profile intervals are 1.0–1.0 for m_o and 0.4–0.4 for m_x.
- **What Claude did:**
  - wrote the config file and the tests;
  - reran the central A + P fit offline once, to read the intervals the D-088 run didn't save (α and the rule
    shares).
- **How it was checked:**
  - the rerun reproduced D-088's θ, α, core term and rule shares exactly;
  - the new tests and the D-088/D-089 module tests;
  - `params_table.py`;
  - the full test suite and `compliance_check.py`.
