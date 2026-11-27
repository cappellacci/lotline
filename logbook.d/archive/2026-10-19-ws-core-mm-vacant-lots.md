### LB-NNN · 2026-10-19 · Build: Missing middle counts vacant single-family-zoned lots (D-014, rule 1.1)
- **Question:** Does the missing-middle denominator follow the Handbook's definition?
- **What I did:** Changed `build/eligible.classify` so missing middle counts an existing single-family house or a vacant residential lot on single-family-only zoning (ADU still needs an existing house); bumped `RULE_VERSION` to 1.1; updated the hand-worked test (p8 vacant SF-zoned: MM eligible; new p9 vacant, not SF-only: not eligible; MM count 2 → 3, quality low → medium) and added a lot-size-floor edge test for both themes (5,000 qualifies, 4,999 does not). Logged D-014.
- **Inputs:** judging run 2026-10-19-0518 (methodology MS-02; replicability RS-03).
- **Outputs:** `src/lotline/build/eligible.py`, `tests/core/test_eligible.py`, `docs/analysis_plan.md` (D-014).
- **Findings:** The ACS fallback has no vacant land, so ACS-based missing-middle denominators still exclude vacant lots (already `low` quality).
- **Decisions:** D-014 (Ben, 2026-10-19).
- **AI:** Claude Code (WS-CORE) wrote the change and tests; all tests pass.
- **Open / next:** rebuild `eligible_parcels` for states with parcels (`lotline fetch --source eligible`) after merge.
