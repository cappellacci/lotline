### LB-NNN · 2026-11-27 · review · Shared permit-adapter helpers

**Question:** Can the helpers copied across permit adapters be written once, without changing any table?

**Outputs:**
- `src/lotline/adapters/common.py` (new): `multi_type`, `size_class` and `units_fit`.
- They replace identical copies:
  - `multi_type` in Dallas, Fort Worth and Greensboro;
  - `size_class` in Portland, Bend and MWVCOG;
  - the `_fits` body in Dallas, Fort Worth, Greensboro and Cary.
- Variants that behave differently are left alone: Minneapolis U5_6/U7P, Durham, Cincinnati, College
  Station's missing count, and the other `_fits` signatures.

**What Claude did:** Worked modularity-review finding 9 (2026-11-27), limited to copies that are exactly the
same.

**Checked:**
- All seven touched adapters were rebuilt offline in memory and their tables hashed. They are identical to
  main's code (Dallas 134,124 rows, Fort Worth 297,818, Greensboro 111,866, Portland 36,436; Cary, Bend and
  MWVCOG equal to their stored tables).
- States tests 900 passed; fast tier passed; ruff clean; compliance 0 FAIL.
- Noticed: the stored Portland and Greensboro permit tables are older than the code (Portland 9 rows fewer;
  Greensboro `units_confidence` differs on 0.5% of rows). An offline refetch refreshes them; not done here.
