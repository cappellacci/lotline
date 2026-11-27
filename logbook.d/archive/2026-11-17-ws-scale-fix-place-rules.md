### LB-NNN · 2026-11-17 · Build: WS-SCALE task 5 rules 1, 2, 4 in place_inputs (D-103)
- **Question:** Can the place set, the missing-price rule and the parcel-roll rule be set once, in the shared
  input table, so every model inherits them?
- **What I did:**
  - In `place_inputs`: every jurisdiction feeds both scenarios; missing rent or value takes the state median,
    flagged; no roll later than origin + 1 for eligible lots and house shares (per origin).
  - Schemas 1.17; hand-worked tests.
  - Built the table before and after for five states, offline.
- **Findings (origin 2025):**
  - Places added to ADU: MN 56, OH 22, TX 11, NC 4.
  - 86 prices filled.
  - Eligible lots changed for 158 places (MN 153); house shares changed for 76 TX places.
  - Results unchanged until the owners switch over.
- **Outputs:** `src/lotline/build/place_inputs.py`, `src/lotline/schemas.py`, `docs/schemas.md`, tests,
  `docs/analysis_plan.md` D-103.
- **Decisions:** D-103 (Ben approved the rules). Interpretation for Ben: the baseline covers local-only places
  through their county row.
- **AI:** Claude wrote the rules, tests and comparison.
- **Open / next:** the ADU and MM owners' switch-over PRs; ADU drops the `results.py` filter; MM applies D-056.
