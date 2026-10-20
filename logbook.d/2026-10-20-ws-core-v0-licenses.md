### LB-NNN · 2026-10-20 · Validation: V0 national reports regenerated for TX and OH; licenses limited to the state's sources
- **Question:** Do the V0 national reports reflect the parcels and eligibility rule now on main?
- **What I did:** Rebuilt `eligible_parcels` (rule 1.1, D-014) for TX and OH and regenerated `reports/tx/V0-national.md` and `reports/oh/V0-national.md` (both last generated 2026-10-14, before the TCAD and Ohio parcel loads). Found that the licenses section listed every source in the shared manifest, including other states' and unmerged branches' sources; it now lists only national adapters and the sources registered for that state (`v0.state_sources`), with a test.
- **Inputs:** processed BPS, ACS, FHFA, parcels and eligible tables in `LOTLINE_DATA_DIR`.
- **Outputs:** `src/lotline/validation/v0.py`, `tests/core/test_v0.py`, `reports/tx/V0-national.md`, `reports/oh/V0-national.md`.
- **Findings:** OH V0 still PASS; TX unchanged at "gaps to explain". Eligible parcels now come from parcel rolls for Austin and the Franklin and Hamilton jurisdictions. MN and NC reports wait for their parcel PRs.
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) regenerated and checked the reports; all tests pass.
- **Open / next:** regenerate MN and NC V0 national reports after their parcel PRs merge.
