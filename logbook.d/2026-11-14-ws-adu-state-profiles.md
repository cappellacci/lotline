### LB-NNN · 2026-11-14 · ADU model · How can each state's mix of places be described, and turned into honest ranges, now that place type matters?

- **Question:** Ben chose Form A + place types (D-088) and asked whether each state's mix could be described
  ("proportion of suburb, city, population, price etc") to come up with a coefficient or modifier (2026-11-14).
- **Output:** D-089 (proposed) in `docs/analysis_plan.md`. It has four parts:
  1. a profile of each state by type: jurisdictions, population, eligible lots, value, rent and owner share;
  2. the share of each state's lots outside the fit's evidence: towns, or beyond the fit range for their type,
     with a 25% labeling rule;
  3. a town prior, N(0, 0.729²), set from D-088's core-city gap;
  4. one sensitivity run of statewide ranges with and without that prior.
- **What Claude did:**
  - recommended against a state-level coefficient: the model already sums place by place, so a state term would
    double count, and four scorable states can't support one;
  - drafted the entry before any profile was tabulated;
  - recorded Ben's choice of A + place types in D-088 (on #427).
- **How it was checked:** the numbers quoted were checked against D-083's and D-088's results; `compliance_check.py`.
