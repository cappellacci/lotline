### LB-NNN · 2026-11-25 · Calibration · Phase 2: the data-only steps run from code; the eligible proxy has drifted

- **Question:** Do the data-only calibration values re-derive from today's tables with one command?
- **Outputs:**
  - `src/lotline/calibrate/data_steps.py`: runners for `baseline_adu_share`, `eligible_proxy`,
    `adu_reference_values` and `mortgage_rate_forecast`, wired in `steps.py`;
  - the proxy's pairing logic moved out of `scripts/dev/eligible_proxy_test.py` into the library (the script now
    imports it);
  - `tests/calibrate/test_data_steps.py`;
  - `docs/calibration.md`.
- **Decision:** Ben, 2026-11-25: start the calibration phases (phase 1 authorised; phases 3–4 sent to the model
  sessions). Config is not changed: the eligible-proxy drift is Ben's call.
- **What Claude did and how it was checked:**
  - `lotline calibrate --run` reproduces three steps exactly: the baseline ADU share (0.033, range 0.0047–0.0765),
    the reference values (1,573; 519,222; 3.99) and the mortgage rate (6.60, 2.96–6.81).
  - The eligible proxy gives k 0.971 and σ 0.106 against config's 0.998 and 0.060 (2026-11-06). The original
    script gives the same result on today's tables, so the port is faithful and config is out of date. D-056
    still passes.
  - Values are rounded half up, as config writes them. Hand-worked tests cover two runners.
  - Completion factors stay recorded: config's 0.97 is a judgment informed by measured ratios near 1.03.
