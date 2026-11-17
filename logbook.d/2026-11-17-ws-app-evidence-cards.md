### LB-NNN · 2026-11-17 · Deliverables: evidence cards for missing middle and fees; a missing middle deep dive on the Model page
- **Question:** How do the missing middle and fee reforms show their evidence on the Results page and the Model page, the way the ADU card does?
- **What I did:**
  - **Missing middle, Results page:** under its year chart, "How we get these numbers" in five steps, each with the state's own values: lots where 2–4 homes become legal, lots where building pays, homes per 10,000 lots over five years, permits to homes (finished share, houses torn down), net.
  - **Fee reduction, Results page:** from what the results files hold now (Ben's choice; the slider and targeted bills wait for the fee grid to move into the results files):
    - the two versions side by side (the Handbook benchmark and real local fees halved), each with its homes and its share of the homes expected with no change;
    - homes added each year for both;
    - "How we get these numbers": homes built anyway, how much cheaper each home gets, how strongly building responds, permits to homes, net.
    The response step names its studies (Baum-Snow and Han 2024 central; Mayer and Somerville 2000 and Campbell and Alm 2006 low; Saiz 2010 and Aastveit and others 2020 high), as in `config/params/fees.yaml`. The Model page's fee card names them too.
  - **Missing middle, Model page:** a range chart of its two out-of-sample tests (Oregon left out: 915, 457–4,789, against 703 built; St. Paul blind: 15, 9–28, against 55). A "State by state" deep dive like the ADU one: no reform against the reform a year, each state's record and forecast, and a lots-to-homes table.
- **Inputs:** Ben's requests (2026-11-17); `docs/build/handoffs/15-fee-section-for-app.md`; `config/params/fees.yaml`; `docs/model_and_assumptions.md` and `docs/analysis_plan.md` (D-092, V5) for the test numbers.
- **Outputs:** `src/lotline/app/template.html`; tests in `tests/app/test_build.py`.
- **AI:** Claude Code wrote the change and tests. Checked with `tests/app` (52 passed), ruff and `compliance_check.py`, and in the browser pane on all five states' real results (bundles at ef37f59a).
- **Open / next:** the fee slider and targeted-bill buttons need the fee grid in the results files (an engine step); the fee card's share is of all homes expected, not of household growth.

### LB-NNN · 2026-11-17 · Deliverables: the header tagline no longer blanks out the grid
- **Question:** Why did the "Housing Reform Model" tagline's box cover the header grid?
- **What I did:** The tagline has a page-coloured backing so it reads over the grid, but it stretched to fill the header row. It now hugs its text, and the grid shows around it.
- **Inputs:** Ben's screenshot (2026-11-17).
- **Outputs:** `src/lotline/app/template.html`.
- **AI:** Claude Code made the change. Checked with `tests/app`, `compliance_check.py`, and in the browser pane.
- **Open / next:** none.

### LB-NNN · 2026-11-17 · Deliverables: the header tagline has no backing box
- **Question:** Should the tagline keep a backing box at all?
- **What I did:** Ben asked for it to be transparent. The grid now runs behind "Housing Reform Model", and the text stays readable.
- **Inputs:** Ben's request (2026-11-17).
- **Outputs:** `src/lotline/app/template.html`.
- **AI:** Claude Code made the change. Checked with `tests/app`, `compliance_check.py`, and in the browser pane.
- **Open / next:** none.
