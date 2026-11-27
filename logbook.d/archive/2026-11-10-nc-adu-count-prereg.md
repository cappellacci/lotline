### LB-NNN · 2026-11-10 · Study design: NC ADU counts, pre-registered before the counts arrive
- **Question:** if the goal is an accurate statewide ADU number, how do new counts of ADUs (Wake rolls, five
  more cities, Charlotte) enter the model, and how is accuracy judged, fixed before any count is read?
- **What I did:**
  - Worked through Ben's proposal for a stratified, in-state ADU rate with him. Showed with quick descriptive
    counts that NC's ADU-flagged places hold about 9% of eligible lots (Raleigh 0.47, Durham 0.73, Durham
    County remainder 0.20, Greensboro 0.03 ADU permits per 1,000 lots a year, 2021–24).
  - Started six data sessions on Ben's request: the Wake 2019→2023 roll comparison and permit sources for
    Asheville, Winston-Salem, Cary, Wilmington and Chapel Hill.
  - Wrote D-074 in `docs/analysis_plan.md`: the flag undercount k measured in Raleigh by matching the roll
    to the permits, the parser recall for parser sources, the entry rule for new places and Charlotte, and
    three accuracy tests with pass bars.
- **Inputs:** `~/lotline-data/processed/nc/{permits,eligible_parcels}`, D-048, D-070, D-071.
- **Outputs:** D-074 (`docs/analysis_plan.md`).
- **Findings:** (1) NC's rate rests on 11 places, about 9% of eligible lots. (2) A raw sum of `eligible_parcels`
  double-counts the local-only towns in county remainders that are on the ACS fallback (Mecklenburg's row is
  the whole county). `adu.non_overlapping` already removes this in the model, but ad hoc sums must not skip it.
  (3) The Charlotte holdout is released, but Charlotte's ADUs are not yet in the processed tables.
- **Decisions:** D-074 proposed (method only).
- **AI:** Claude Code wrote the analysis, the entry and the session briefs. The counts were checked against
  `docs/build/nc-readiness.md` (the same flagged totals). The double count was traced to
  `build/eligible.allocate_homes` and confirmed to be handled by `adu.non_overlapping`. No model was run.
- **Open / next:** Ben reviews D-074; the six sessions report; rebuild NC permits with Charlotte released.
