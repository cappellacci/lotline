### LB-NNN · 2026-11-17 · Deliverables: "Add a state" button and placeholder page in the app
- **Question:** Where does a reader find how to add their own state to Lotline?
- **What I did:** Added an "Add a state" button to the right of the app's toolbar, next to the state picker. It opens a new page (`#add`) with five placeholder steps: what you already have, parcels, permits, local rules and fees, run and check. A draft note links to the README's "bring your own state" guide, because Ben is still revising the workflow. The map's grey tiles and its "bring your own state" and "sharpen it with your state's own data" links now open this page instead of the README in a new tab.
- **Inputs:** Ben's request (2026-11-17).
- **Outputs:** `src/lotline/app/template.html`; a test in `tests/app/test_build.py`.
- **AI:** Claude Code wrote the change and test. Checked with `tests/app` (46 passed), ruff and `compliance_check.py`, and by building the page from local bundles and clicking through it in the browser pane.
- **Open / next:** Ben to write the real step-by-step content.

### LB-NNN · 2026-11-17 · Deliverables: the app opens on a card with the state map
- **Question:** What should someone see first when they open Lotline?
- **What I did:** Built Ben's notebook sketch. The app now opens on a two-column card (`#home`). On the left: "Lotline" in display type, what it measures, and two buttons, "Pick a state →" (brings the map into view and focuses its first state) and "Add a state". On the right: the state map, moved off the Results page. Clicking a state opens that state's Results page, now titled with the state's name. There is no all-states results page. The old intro line above every page became the card's description. The wordmark and mark go back to the card.
- **Inputs:** Ben's sketch, described in chat (2026-11-17).
- **Outputs:** `src/lotline/app/template.html`; tests in `tests/app/test_build.py`.
- **AI:** Claude Code wrote the change and tests. Checked with `tests/app` (47 passed), ruff and `compliance_check.py`, and by clicking through the built page in the browser pane at desktop and phone widths.
- **Open / next:** Ben's further sketches for the add-a-state workflow.

### LB-NNN · 2026-11-17 · Deliverables: Results open with "[State] can add [X] homes" and a range box per reform
- **Question:** What should a policymaker read first on a state's Results page?
- **What I did:** Built Ben's sketch. The page now opens with a large headline, "[State] can add [X] homes over the next 5 years". X is the median of the three reforms' midpoints (ADUs, missing middle, fee reduction), with each reform passed on its own; they are never added together. Below it are three range boxes, one per reform. Each box shows the P10–P90 range, the midpoint and a small bar on a shared scale, plus one line on what the reform is (the Handbook definitions). The fee box switches between the Handbook benchmark and real local fees, and the headline follows the switch. The "Count homes" toggle further down moves the headline and boxes too. The old "Results" heading and lead line were folded into the headline and its note. The rest of the page is unchanged.
- **Inputs:** Ben's sketch, described in chat (2026-11-17).
- **Outputs:** `src/lotline/app/template.html`; a test in `tests/app/test_build.py`.
- **AI:** Claude Code wrote the change and test. Checked with `tests/app` (48 passed), ruff and `compliance_check.py`, and in the browser pane for MN and OR (fee switch and the count toggle move the headline).
- **Open / next:** Ben to confirm "median of the three" is the headline he wants; the detail card below still repeats the ranges.
