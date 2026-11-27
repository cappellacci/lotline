### LB-NNN · 2026-11-17 · Deliverables: fee card's Oregon line corrected
- **Question:** the app's fee card said Oregon was "not in the fee run yet", but the rebuilt bundles (main at c6a06012) carry Oregon fee results. What should it say?
- **What I did:** read `config/fees/*.csv` through `fee_levels.coded_fees` (SFD) and `place_fees`' fill rule; replaced the Oregon line and corrected the coded-place count (50 → 58) in `src/lotline/app/template.html`.
- **Findings:** Oregon has 4 coded cities (Bend $42,800, Portland $41,800, Salem $27,100, Eugene $17,500 a home; system development charges are 81–100% of each). That is under the 5-place minimum for a state prior, so Oregon's other places take the pooled median of all 58 coded places (about $7,100), likely an understatement.
- **Decisions:** Ben: "Fix the Oregon line on the fee card" (2026-11-17).
- **AI:** Claude Code wrote the text from the fee config and code; app tests (45), ruff and `compliance_check.py` (0 FAIL) pass.
- **Open / next:** whether Oregon's uncoded places should draw from its 4 coded cities instead of the pooled median is a fee-model choice (D-065's 5-place minimum), not changed here.
