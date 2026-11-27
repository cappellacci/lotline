### LB-NNN · 2026-10-20 · Build: Fix data tiers receiving the place-to-county map (#137 follow-up)
- **Question:** Why did `lotline fetch --source jurisdictions` fail validation after #137?
- **What I did:** #137 inserted `parcel_tiers` before `place_counties` in `build()`, and `load()` passed both by position, so county GEOIDs were read as tiers and validation failed for every state with a local permit source. Made the trailing arguments keyword-only, passed them by name, and added a regression test. Rebuilt TX and OH jurisdictions.
- **Inputs:** local rebuild after #137 merged.
- **Outputs:** `src/lotline/build/jurisdictions.py`, `tests/core/test_jurisdictions.py`.
- **Findings:** After the fix: TX has Austin at tier 1 (TCAD roll with year built); OH has 52 Franklin and Hamilton jurisdictions at tier 2 (land use, no year built); everything else is tier 3.
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) found the bug while rebuilding, fixed it and added the test; all tests pass.
- **Open / next:** rebuild NC and MN jurisdictions when their parcel PRs merge.
