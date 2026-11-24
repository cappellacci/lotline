### LB-NNN · 2026-11-17 · Build: WS-SCALE task 5 rule 6, county remainders get their 2020 population (D-102)
- **Question:** What 2020 population does a county's unincorporated remainder have, and what moves when it is
  no longer read as 0?
- **What I did:**
  - `jurisdictions.remainder_population`: the county minus its listed places and townships, the same
    subtraction as `eligible.allocate_homes`, fed 2020 populations; hand-worked test.
  - Before/after bundles for all five states, offline and in memory.
- **Findings:**
  - NC adds up to its 2020 state population.
  - Oregon missing middle −40%, NC ADU −8%, OH ADU −4%; baselines and fees are unchanged.
  - The cause: remainders now borrow mid- or large-band priors, which are pooled from cities.
- **Outputs:** `src/lotline/build/jurisdictions.py`, `src/lotline/build/place_inputs.py`, tests,
  `docs/analysis_plan.md` D-102.
- **Decisions:** D-102 (Ben approved the rule). Open for Ben: should remainders borrow from cities' bands?
- **AI:** Claude wrote the rule, test and runs.
- **Open / next:** rebuild the stored jurisdictions tables (Ben's OK).
