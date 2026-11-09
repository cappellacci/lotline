### LB-NNN · 2026-11-09 · `engine` · ADUs in two steps, by zone: D-072 proposed (method only)
- **Question:** how should the ADU model first estimate the state's ADUs today from the places we can count,
  then forecast them, inferring only from collected evidence?
- **Decided by:** Ben, 2026-11-09 (two steps; three zones; "if we're inferring anything it has to be based on
  collected evidence"). D-072 is proposed; no code or run yet.
- **Outputs:** D-072 in `docs/analysis_plan.md`:
  - zones (places of 100k+, other places, unincorporated) × metro/micro/none, from `jurisdictions`;
  - step 1: cell levels from sampled places pooled across states, with a place bootstrap; unmeasured cells
    bounded, never in the headline;
  - step 2: forecast with new single-family lots from the baseline, and rents at the origin with an
    ACS-evidence sensitivity;
  - pre-registered tests (leave one place out, leave one state out, time split) and data tasks.
- **Evidence gathered first (central values, holdout-filtered store):**
  - NC sample: model 66 vs observed 126 ADUs a year. Statewide scale-ups disagree: 330–770 a year.
  - Unincorporated or township rates per 10,000 lots a year: Durham County 0.22, Bexar 0.14 (coverage
    unverified), 42 Twin Cities metro townships 0.75. The model gives NC's county areas 0.84.
  - No sampled place in any state lies outside a metro area.
- **What Claude did and how it was checked:**
  - Computed the rates above from the store with ad hoc scripts, not committed.
  - Checked that `jurisdictions` has `pop_2020`, `kind` and `cbsa_type` in all five states (blank
    `cbsa_type` to be confirmed as "outside any CBSA").
  - Wrote the entry before any code.
- **Open:**
  - Ben reviews D-072.
  - Then the data tasks: Bexar coverage, non-metro permit sources, Charlotte after V5.
  - Then code, tests and the pre-registered checks.
