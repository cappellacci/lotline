### LB-NNN · 2026-11-10 · WS-ENGINE: permit-level county remainders in the ADU fit panels (D-074 step 2; no fit)
- **Question:** #375 added `eligible.permit_level`, the county-remainder lot count that leaves out places counted
  from their own permits. How does it reach the ADU fit without counting the same lots twice?
- **What I did:**
  - Added `estimate_adu.adu_panel_eligible` (with `permit_level_eligible`, `needs_permit_level` and
    `permit_acs_rows`). It swaps in permit-level lots only for rows that meet all three conditions: a county
    remainder, an ACS-fallback count, and ADU counts in the panel (which come only from record-level permit
    sources, never BPS).
  - Places, parcel-roll remainders and every BPS-outcome path keep the stored, BPS-kind lots.
  - Wired the swap into the `estimate_adu` panel (D-023 / D-048) and `calibrate_adu.place_years`. The default is
    `remainder="permits"`, and `"bps"` turns it off.
  - The D-070 floor (`places_from_store`) is left alone. Its lots already go through `adu.non_overlapping`, and
    applying both would subtract the local-only places twice. A test checks the two never stack.
- **Outputs:** `src/lotline/model/estimate_adu.py`, `src/lotline/model/calibrate_adu.py`,
  `tests/model/test_adu_permit_remainder.py`.
- **Decisions:** none added to HANDOFF. Proposed in the PR, as #375 proposed: ADU rates from record-level
  permits use permit-level remainders, and BPS outcomes keep the BPS kind.
- **AI:** Claude Code wrote the helpers and tests overnight, with Ben asleep. Checks:
  - 4 hand-worked synthetic tests: 37119 1,000 → 300, an uncounted remainder kept, a parcel-roll remainder
    kept, the lots adding back up, no Census shares built when nothing needs them, the switch, and the floor
    not stacking;
  - full `pytest` and `compliance_check.py`.
  - No data was read and nothing was fitted or run.
- **Open / next:** the rebuild and the joint refit. That is where the permit-level 37119 (about 20,000 lots
  instead of 275,000 in 2024) first changes a fitted number.
