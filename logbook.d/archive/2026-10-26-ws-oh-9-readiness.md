### LB-NNN · 2026-10-26 · Data feasibility: Ohio data readiness report (thread 11, step 3, draft)
- **Question:** How ready is Ohio's data for an end-to-end run, and how many places does it add to the ADU and missing-middle estimation panels?
- **What I did:**
  - Counted every model input across Ohio's 952 jurisdictions from the processed tables after the #232 rebuilds (real, fallback, unknown), with population shares.
  - Applied D-025's and D-024's inclusion rules to count panel places, without running any estimator.
  - Listed the remaining gaps with what closes each and who owns it.
- **Inputs:** processed `jurisdictions`, `eligible_parcels`, `permits`, `bps_place_year`; `config/reforms/oh.csv` (#226); PRs #224, #226, #232.
- **Outputs:** `docs/build/oh-readiness.md`.
- **Findings:**
  - 93% of Ohio's population now has an eligible-lot count from real parcels; tier 1 covers 28.5% (72 places, Columbus among them).
  - Ohio adds 4 places to the ADU panel (Cincinnati, Columbus, Dublin, Gahanna; 1 before this thread) and 1 treated place to missing middle.
  - The cheapest way to add ADU-panel places is rule rows for the 15 Franklin places whose ADU counts already exist.
- **Decisions:** none.
- **AI:** Claude Code (WS-OH) computed the counts and wrote the report; no model or scenario was run.
- **Open / next:** finalize after #224, #226, #232 merge and Ben's lookups; S7 Cleveland permits, S8 fees.

**Addendum 2026-11-01.** Ben asked for the report to be rewritten now that #226 and #246 are merged. Claude merged
`main` (6a70f9d) into the branch and rebuilt `oh_parcels`, `jurisdictions` and `eligible` from the cached
2026-10-19 snapshot.

- **What went wrong first:** a run without `OH_PARCELS_VINTAGE` started a fresh statewide download dated
  2026-11-01. It hung on the ArcGIS server and was stopped. It left a partial `raw/oh_parcels/2026-11-01/` folder
  and 529 manifest entries that nothing uses.
- **What was counted:** a read-only script counted the tables and `config/reforms/oh.csv`. No model runs.
- **Headline changes:**
  - real-parcel share up from 92.5% to 95.5%;
  - tier 1 up from 72 to 85 places;
  - the ADU panel up from 4 to 15 places;
  - missing-middle treated places in the window up from 1 to 2.
- **Flagged:** township `pop_2020` totals look partial.
