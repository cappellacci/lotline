### LB-NNN · 2026-10-20 · Build: Parcel rolls with mostly unknown land use fall back to ACS (D-017)
- **Question:** Do counties that send no land use get sensible eligible-parcel denominators?
- **What I did:** Checked Akron and Toledo on Ohio's statewide parcels (#150): Akron counted 0 eligible parcels rated `high`. Added `eligible.usable_rolls`: a jurisdiction-roll counts as a parcel denominator only if land use is known for ≥90% of parcels (the D-016 tier 2 threshold); otherwise the ACS fallback is used. Test added; logged D-017 (pending Ben).
- **Inputs:** processed `oh_parcels` (from #150), OH jurisdictions.
- **Outputs:** `src/lotline/build/eligible.py`, `tests/core/test_eligible.py`, `docs/analysis_plan.md` (D-017).
- **Findings:** 81.6% of Ohio parcels are in usable rolls; Akron and Toledo now use ACS; Columbus still counts from parcels (174,404 ADU-eligible, `low` quality because zoning is unknown).
- **Decisions:** D-017 (pending Ben).
- **AI:** Claude Code (WS-CORE) found and fixed it; all tests pass.
- **Open / next:** a county land-use source for Summit and Lucas would bring Akron and Toledo onto parcels.
