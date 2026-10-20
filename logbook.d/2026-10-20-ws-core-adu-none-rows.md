### LB-NNN · 2026-10-20 · Build: An explicit "no ADUs" reform row reads as no rule
- **Question:** Can a state workstream code "this city allows no ADUs" in `config/reforms/*.csv`?
- **What I did:** WS-TX found that `scenarios/adu.current_rules` classed every in-force ADU row as partial or Handbook-equivalent, so a row with `adus_per_lot = 0` would have counted as a partial rule (c = 0.3). Added `adus_per_lot` to the rubric; such a row now leaves the place at "none" (recording the row and a note), and a more permissive state law still wins. Test added; the test helper pads rows for the extra rubric field.
- **Inputs:** WS-TX's report (ADU-rules round).
- **Outputs:** `src/lotline/model/scenarios/adu.py`, `tests/model/test_scenario_adu.py`.
- **Findings:** Zone limits (e.g. Austin's SF-3-only rule) and minimum lot sizes are not classified: `coverage` is free text. Left for WS-ENGINE (needs a structured field or an eligible-share adjustment).
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) made the change; all tests pass.
- **Open / next:** WS-ENGINE: zone/lot-size limits in the rule classifier.
