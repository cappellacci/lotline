### LB-XXX · 2026-11-17 · WS-APP · Every state's range per reform, in the Model tab

**Question:** Where does the "every state at once" picture live now that #466 owns the Results page?

**Output:** `src/lotline/app/template.html` (Model tab chart `#allstates`), `src/lotline/app/build.py` (`headline`: each scenario's five-year net homes and need share, embedded per state), `src/lotline/model/results.py` (`SINGLE_SCENARIOS`: combined scenarios no longer listed as pending), `tests/app/test_build.py`.

**What happened:** Ben asked (2026-11-17) for the five-state chart from the results page to go into the Model section, to show model effectiveness, and dropped combined scenarios. PR #460's home-screen redesign was superseded by #466; this PR keeps only #460's chart, the embed it needs and the pending-list change. The embedded numbers are per scenario and feed only this chart; the Results headline stays #466's per-draw sum.

**Claude's part and checks:** Claude (ADU session) rebuilt the pieces on main after #466; app and results tests pass, ruff clean.
