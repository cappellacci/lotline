### LB-NNN · 2026-11-15 · Data feasibility: ADU count sources in Texas, Oregon and Ohio
- **Question:** Are there public, record-level permit files that would let more TX, OR and OH places, especially
  core cities, enter the ADU fit (D-074 step 2, D-078 entry bar)?
- **What I did:**
  - Ran three parallel research subagents, one per state, against city, county and regional open-data portals and
    regional councils of government.
  - Texas and Ohio: count queries and samples of at most ~200 rows; nothing saved.
  - Oregon (V9 holdout): metadata only.
  - Checked each candidate against the registered sources and the coded ADU rules.
- **Inputs:** `docs/data_provenance.md`, `config/reforms/{tx,oh,or}.csv`, `docs/analysis_plan.md` (D-074, D-078),
  sibling session notes.
- **Outputs:** `docs/research/adu-count-sources-tx-or-oh-2026-11.md`
- **Findings:**
  - No new core city clears the bar cleanly. Houston has a 2015–2024 record-level layer of new single-family
    permits with ADUs in the project-name text only, so it is a lower bound (maybe).
  - Oregon: Deschutes County (public domain) and Jackson County (CC BY 4.0) look usable, from metadata only.
    Keizer, via MWVCOG, is the cheapest new place after unblinding.
  - Fort Worth's old Socrata table is gone, but `fw_permits` already uses the ArcGIS layer, so no repoint is
    needed. Its `Use_Type 'Accessory Dwelling'` field is mostly non-dwellings.
  - Cincinnati's short series comes from its permit text: ADUs are rarely named before 2023.
- **Decisions:** None made. Proposed for Ben:
  - which candidates, if any, to register;
  - whether the Corvallis and DLCD city-year ADU tables (holdout outcomes, not opened) should score the Oregon test
    after the freeze.
- **AI:** Claude Code (Opus 5.5) ran the search through subagents and wrote the report. The lead session re-ran the
  Fort Worth count and a 200-row sample, which downgraded the subagent's "usable" verdict to "not usable as it
  stands". Rule coverage was checked against `config/reforms`. No adapters, data or model runs.
- **Open / next:**
  - Ben picks candidates.
  - Houston would need an undercount factor k from an independent list (e.g. the HCAD roll) before entering the
    fit.
  - Summit County needs a parcel-join method and Akron rule coding.
