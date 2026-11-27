### LB-NNN · 2026-11-10 · WS-CORE: the D-078 ADU undercount table, wired (no fit or run)
- **Question:** How does each permit source's flag undercount k (D-074, D-075 step 2, D-078) enter the model,
  so that the joint refit can use it?
- **What I did:**
  - Made `adu_flag_undercount` in `config/params/adu.yaml` a table of 28 permit sources. Every row cites its
    report or adapter. It holds measured field rows (Raleigh, Austin, Portland), prior field rows (Durham,
    Asheville from 2022, Bend, Medford, MWVCOG, College Station, San Antonio), measured parser rows
    (Minneapolis, Charlotte and the Mecklenburg towns, Cleveland, Asheville before 2022, Austin's inferred
    rule), parser rows with no hand check yet (k = 1), the Met Council floor and the Columbus no-k rows.
  - The table loads through `lotline.config.load_undercount` (pydantic rows, validated). `load_params` skips
    entries marked `table: true`.
  - Wrote `lotline.model.undercount`. Each row's draw is a split lognormal, with the median at the row's value
    and its ends at the interval's quantiles. The prior is exp(mean ln k) over measured field rows, with a range
    from 1.0 to the largest measured field high (1.086, 1.0–1.21). Field rows share one z per draw; each parser
    row has its own.
  - k scales counted ADU permits only. It is applied in `observed_adu_counts` and `calibrate_adu.adu_counts`
    (each source scaled, then the larger kept), and so in the `estimate_adu` panel, `calibrate_adu.place_years`
    and `historical_floor`, all at the central k. `places_from_store` and the D-070 floor are scaled the same
    way. `run` redraws the floor's k in every draw (`observed_rate_draws`, seed + 6). Eligible lots are never
    scaled.
  - `scripts/dev/params_table.py` now renders the table into `docs/model_and_assumptions.md`.
  - Added a "Wired" note to D-078 in `docs/analysis_plan.md` listing the wiring choices.
- **Outputs:** `config/params/adu.yaml`, `src/lotline/config/__init__.py`, `src/lotline/model/undercount.py`,
  `src/lotline/model/scenarios/adu.py`, `src/lotline/model/calibrate_adu.py`, `src/lotline/model/estimate_adu.py`,
  `src/lotline/model/results.py`, `scripts/dev/params_table.py`, `docs/model_and_assumptions.md`,
  `docs/analysis_plan.md` (D-078 note), `tests/model/test_undercount.py`.
- **Decisions:** none added to HANDOFF. The wiring choices are listed in the PR under "Choices for Ben".
- **AI:** Claude Code wrote the table, loader, module and tests overnight, with Ben asleep. Checks:
  - 20 hand-worked synthetic tests: the prior's centre and range, quantiles, shared and independent draws,
    floor, no-k and pending rows, year-split rows, scaled counts, per-draw floor rates, and a scan that every
    ADU-flagging adapter has a row;
  - full `pytest` and `compliance_check.py`.
  - No data was read and no engine, fit or scenario was run.
- **Open / next:** rebuild the processed tables, then the joint refit (D-075 step 3) with the model form from
  its own entry (D-079 proposal).
