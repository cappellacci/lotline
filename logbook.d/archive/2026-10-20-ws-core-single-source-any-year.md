### LB-NNN · 2026-10-20 · Build: One parcels source per jurisdiction across roll years
- **Question:** Why did the one-source guard (#154) miss Durham's 5 eligible parcels?
- **What I did:** The guard compared sources within a roll year only; Durham had a 2023 Wake roll (363 Wake County parcels) and a 2026 OneMap roll, so every origin before 2026 used the sliver (found by WS-NC, fixed for NC in #163). `eligible.single_source` now raises when a jurisdiction has rolls from two sources in any years and no `parcel_sources` choice. Test added.
- **Inputs:** WS-NC's diagnosis (#163).
- **Outputs:** `src/lotline/build/eligible.py`, `tests/core/test_eligible.py`.
- **Findings:** On local data MN, OH and TX pass; NC stops (18 jurisdictions) until #163's `parcel_sources` lands, so this merges after #163.
- **Decisions:** none.
- **AI:** Claude Code (WS-CORE) made the change; all tests pass.
- **Open / next:** none.
