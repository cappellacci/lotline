### LB-NNN · 2026-11-17 · Deliverables: "Add a state" button and placeholder page in the app
- **Question:** Where does a reader find how to add their own state to Lotline?
- **What I did:** Added an "Add a state" button to the right of the app's toolbar, next to the state picker. It opens a new page (`#add`) with five placeholder steps: what you already have, parcels, permits, local rules and fees, run and check. A draft note links to the README's "bring your own state" guide, because Ben is still revising the workflow.
- **Inputs:** Ben's request (2026-11-17).
- **Outputs:** `src/lotline/app/template.html`; a test in `tests/app/test_build.py`.
- **AI:** Claude Code wrote the change and test. Checked with `tests/app` (46 passed), ruff and `compliance_check.py`, and by building the page from local bundles and clicking through it in the browser pane.
- **Open / next:** Ben to write the real step-by-step content.
