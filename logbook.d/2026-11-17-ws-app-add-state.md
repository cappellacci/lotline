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
- **What I did:** Built Ben's sketch. The page now opens with a large headline, "[State] can add [X] homes over the next 5 years". X is the largest of the three reforms' midpoints (ADUs, missing middle, fee reduction), and the note under it names that reform. Each reform is passed on its own; they are never added together. Ben first had the median and switched to the largest after seeing it. Below it are three range boxes, one per reform. Each box shows the P10–P90 range, the midpoint and a small bar on a shared scale, plus one line on what the reform is (the Handbook definitions). The fee box switches between the Handbook benchmark and real local fees, and the headline follows the switch. The "Count homes" toggle further down moves the headline and boxes too. The old "Results" heading and lead line were folded into the headline and its note. The rest of the page is unchanged.
- **Inputs:** Ben's sketch, described in chat (2026-11-17).
- **Outputs:** `src/lotline/app/template.html`; a test in `tests/app/test_build.py`.
- **AI:** Claude Code wrote the change and test. Checked with `tests/app` (48 passed), ruff and `compliance_check.py`, and in the browser pane for MN and OR (fee switch and the count toggle move the headline).
- **Open / next:** the detail card below still repeats the ranges.

### LB-NNN · 2026-11-17 · Deliverables: a range chart, a model selector and the ADU evidence card on the Results page
- **Question:** How should a state's Results page lay out the three reforms and the evidence behind the ADU estimate?
- **What I did:** Built Ben's next sketches.
  - The three range boxes became one chart: a row per reform on a shared log axis, with a P10–P90 band and the midpoint, as in the "Results for 2027–2031" page's first chart.
  - Below it sits a segmented selector (ADUs | Missing middle | Fee reduction), outside and above an evidence card that changes with it. The scenario tabs further down were dropped; the selector drives the cards below.
  - The ADU card has four parts:
    1. The year-by-year chart.
    2. The first forecast year, with no reform and added.
    3. Core cities, suburbs and towns (D-088's place types), drawn like the ADU gut check's "By place type" chart, with the method in plain words.
    4. "How we get these numbers" in five steps, each with the bundle's own values.
  - Missing middle and fees keep their existing content until their cards are designed.
- **Inputs:** Ben's sketches (2026-11-17); the "Results for 2027–2031" and "ADU Gut Check" artifacts as visual references.
- **Outputs:** `src/lotline/app/template.html`; tests in `tests/app/test_build.py`.
- **AI:** Claude Code wrote the change and tests. Checked with `tests/app`, ruff and `compliance_check.py`, and in the browser pane. The preview fed the place-type chart from `reports/adu-gut-check/places.csv` with a "preview only" note; nothing from that run is in the app's data.
- **Open / next:** the results bundle does not yet carry the ADU split by place type, the statewide estimate of ADUs built each year, or the no-reform forecast. Until the engine exports them, the card says so in place of those numbers.
