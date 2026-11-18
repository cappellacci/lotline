### LB-NNN · 2026-11-17 · Build: WS-SCALE task 5 rule 5, one county for a place in two counties (D-101)
- **Question:** Which county does a place that spans counties belong to, and does it have to be the same one
  in the jurisdictions table and in the baseline?
- **What I did:**
  - The county holding most of the place's 2020 homes (`geoparts.main_county`) now sets the place's county in
    `jurisdictions`, in the baseline panel and in `place_inputs`.
  - Ben's rule says population; housing units are used because they are already downloaded (D-101 states
    the deviation).
  - Ran before/after bundles for all five states, offline and in memory, with nothing written to the data
    directory.
- **Findings:**
  - 18 places move (NC 10, OH 2, TX 6).
  - Scenario medians move by 0.06% or less.
  - Baseline: OH −0.14%, TX −0.16%; the largest class move is OH 2-4 units, −1.2%.
- **Outputs:** `src/lotline/adapters/national/geoparts.py`, `src/lotline/build/{jurisdictions,panels,place_inputs}.py`,
  tests, `docs/analysis_plan.md` D-101.
- **Decisions:** D-101 (Ben approved the rule 2026-11-17). Propose a HANDOFF row.
- **AI:** Claude wrote the rule, tests and runs.
- **Open / next:** population instead of housing units, if Ben approves the download; rebuild the stored
  `jurisdictions` tables (Ben's OK).
