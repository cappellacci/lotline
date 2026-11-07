## LB-xxx · 2026-11-06 · WS-APP · Slider shift rule marked provisional

**Question answered:** Is the sliders' per-draw P_q / P50 scaling (LB fragment `ws-app-results`) settled? Ben, 2026-11-06: no. Keep it for now, label it provisional, revisit after feedback, and invest no more in it.

**Outputs**
- Marked provisional in four places:
  - a comment in `src/lotline/app/aggregate.js`
  - a note in `src/lotline/app/knobs.yaml`
  - a "Provisional:" line above the sliders on the page
  - the docstring of `tests/app/test_aggregate_parity.py`
- `tests/app/test_build.py` checks the page says so.

**Decision proposed for HANDOFF (provisional):** sliders shift an assumption by scaling every draw by P_q / P50 of that factor, kept within [0, 1]. This keeps the engine's joint structure and is exact at the slider's centre. Revisit after feedback on the app.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) made the wording change. Checked by `tests/app` (27 passed) and `compliance_check.py`.
