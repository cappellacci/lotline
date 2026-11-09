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
- **Data checks (same day, appended to D-072):**
  - Blank `cbsa_type` = outside any CBSA: 0 mismatches against OMB 2023, all five states.
  - Coverage against BPS, new units 2021–25:
    - Bexar unincorporated 0.30: fails, left out.
    - Durham County unincorporated 0.69: fails for now; probably current-limits geocoding of annexed areas.
    - MN metro townships (Met Council) 3.0x BPS: pass.
  - Added a coverage rule (at least 0.8 of BPS) before any run. The metro unincorporated cell now rests on
    the MN townships alone.
- **Durham County follow-up:**
  - City and county permits together are 1.20x BPS (2021–25); no permits look missing. The county's 0.69 is
    a city/county split question.
  - BPS's own Durham rows are broken or imputed in several years.
  - No independent count is possible yet: Durham parcels in the store have no year built.
  - Decision for Ben (combined-office test, or a new Durham parcel source) recorded in D-072.
