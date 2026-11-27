## LB-xxx · 2026-11-06 · WS-APP · The data dashboard folded into the data tab

**Question answered:** Ben (2026-11-06): the data dashboard should be part of the data tab, not a button that opens it.

**Outputs**
- `src/lotline/app/build.py`: `fold_dashboard` restyles the dashboard's own page for section 2. It inlines the identity tokens, maps the dashboard's colour variables onto them, and hides the dashboard's header and state bar.
- `src/lotline/app/template.html`:
  - The dashboard loads into a frameless panel the first time the data tab opens. The panel grows to the dashboard's full height, so there is no inner scroll.
  - The app's state picker drives the dashboard: it presses the dashboard's own state chip, matched by the state's name.
  - For a state the summary doesn't cover, the panel says so instead of showing another state.
  - The "Open the data dashboard" button is gone.
- `tests/app/test_build.py`: the embedded page carries the tokens and fold styles; the panel is on the page.

**What Claude did and how it was checked:** Claude Code (Opus 5.5, WS-APP instance) made the change. Checked by `tests/app` (27 passed) and `compliance_check.py`. A browser check used the real data dashboard summary: the dashboard opened on the data tab scoped to the picked state with all 15 charts drawn; switching to a state not in the summary hid it with a note; switching back scoped it again. The first version kept showing the previous state for an uncovered one; that was caught and fixed.
