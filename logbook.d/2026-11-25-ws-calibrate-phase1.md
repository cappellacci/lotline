### LB-NNN · 2026-11-25 · Calibration · Phase 1: every fitted value traced to one step; `lotline calibrate --check`

- **Question:** Can a judge see, in one command, where every fitted number in config comes from?
- **Outputs:**
  - `src/lotline/calibrate/__init__.py` (`order`, `produced`, `check`, `write_lock`) and
    `src/lotline/calibrate/steps.py` (22 steps);
  - `config/calibration.lock.json`;
  - `lotline calibrate --list | --check | --write-lock` in `src/lotline/cli.py`;
  - `tests/calibrate/test_registry.py`;
  - `docs/calibration.md`;
  - the design page https://claude.ai/artifact/8XR3iNs2knPpTUFNPPu1Y3.
- **Decision:** Ben, 2026-11-25: "start phase 1". Deviation from the design: the step registry, not a new
  `fitted_by` field in each YAML entry, records which step produces a value. Four scripts rewrite their YAML files
  whole and would drop such a field.
- **What Claude did and how it was checked:**
  - A read-only subagent mapped every fitted parameter to its script, inputs, decision, seed and how it reached
    config. Claude Code turned the map into the registry.
  - `--check` passes on the repository: 22 steps account for 130 values, and every parameter whose source says
    "Estimated" is covered.
  - Synthetic tests show it catches a value edited without its step, an uncovered estimated value, a missing key,
    a cycle, an unknown step and a value produced twice.
  - No fit was run and no number changed.
