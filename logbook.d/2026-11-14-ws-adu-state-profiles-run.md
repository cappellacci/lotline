### LB-NNN · 2026-11-14 · ADU model · How much of each state's ADU forecast rests on places like the ones the model was fitted on?

- **Question:** D-089, accepted by Ben on 2026-11-14 ("Accept D-089"). It was built and run the same day.
- **Outputs:**
  - code: `src/lotline/model/adu_profiles.py`, `scripts/dev/adu_state_profiles.py`,
    `scripts/dev/adu_profiles_page.py`;
  - tests: `tests/model/test_adu_profiles.py`;
  - results: `reports/adu-state-profiles/`, and the page https://claude.ai/artifact/GoxSAAjVEv2szddSuRSJEb;
  - D-089's Built and run note in `docs/analysis_plan.md`.
- **Result:**
  - **All five states are labeled.** 63–93% of each state's lots are outside the evidence, mostly on price and
    size; towns are 9–30%.
  - **Towns yield only 1–5% of expected ADUs,** so the town prior barely moves the ranges.
  - **The share of expected ADUs from places outside the evidence** runs from 25% (NC) to 96% (TX).
  - **The fitted suburbs are all pricey Twin Cities and Triangle ones.** The most useful new data would be
    lower-priced suburbs.
- **What Claude did:**
  - wrote the module, tests and dev run;
  - fixed two run errors before any total was read: a county-remainder owner-share lookup, and the state-code
    case;
  - wrote the plan note, README and results page.
- **How it was checked:**
  - 6 hand-worked tests, including the totals matching `pool_paths` draw by draw;
  - a rerun reproduced every total exactly;
  - the claim that 79% of the fit set's lots are in core cities was checked against the profile table;
  - `compliance_check.py`.
