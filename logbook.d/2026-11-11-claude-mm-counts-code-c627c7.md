### LB-NNN · 2026-11-11 · Build: D-082 missing-middle counting code (no counts run)
- **Question:** Can the counting rules D-082 (proposed) §2–§3 pre-registers be committed in code, with
  hand-worked tests, before Ben approves the protocol and before any count is seen?
- **What I did:**
  - New `src/lotline/model/mm_counts.py`. It holds five pieces:
    - building collapse (parcel × issue year × address, U2/U3_4, units summed, 2–4 check);
    - the coverage screen, with k_src and a conditional-binomial Wilson 90% interval;
    - the strong-source tests;
    - the uplift ratios r56, rTH, rCV and s_td, with building-weighted pooling and a min–max range over
      sources with at least 50 buildings;
    - a generic 2–4 roll-diff rule (single or vacant lot → one 2–4 unit building; merges and splits reported
      and left out).
  - Every table goes through `mm_counts.blind`: St. Paul and Ramsey County rows are dropped, then
    `holdout.apply` runs. The counting functions raise `NeverReadError` if a St. Paul or Ramsey row reaches
    them.
  - The thresholds (0.85, 3 years, 0.8 and 1.25, 2–4 units, 50 buildings, ±2 years, +20%, z) are in
    `config/params/mm.yaml` with source "D-082 (proposed)".
  - `scripts/dev/mm_counts_d082.py --dry` prints input structure only. Without `--dry` it stops, because
    counts need Ben's go-ahead. I ran `--dry` once.
- **Inputs:**
  - D-082 and the methodology review §1–§3 (branch `ws/mm-review`, PR #392);
  - the roll-diff pattern in `wake_roll_diff.py`, `franklin_roll_diff.py` and `mpls_roll_diff.py`;
  - for the one dry run, the processed `permits`, `parcels` and `bps_place_year` tables. Structure only.
- **Outputs:** `src/lotline/model/mm_counts.py`, `tests/model/test_mm_counts.py` (22 tests),
  `scripts/dev/mm_counts_d082.py`, `config/params/mm.yaml` (10 new `mm_*` keys).
- **Findings (structure only, from the dry run):**
  - No processed permit table has a street address. The schema filter drops it, and Raleigh doesn't request
    it. So the collapse falls back to parcel × issue year, and two buildings on one parcel in one year merge.
  - No parcel roll has `sf_only_zoned`, so rTH and r56 need a zoning join before they can be measured.
  - Franklin's `oh_parcels` has no `units`, so test B there must use the dwelling-card summary
    (`franklin_roll_diff.summarize`), not `roll_from_parcels`.
  - Parcel-ID fill is at least 0.918 in every candidate source; Raleigh is the lowest.
  - The Minneapolis permits file is `mpls_permits.parquet`. The first dry run looked for `mpls_ccs_permits`
    (the `source` value) and reported it "not built". The script is fixed, but the fix has not been re-run.
- **Decisions:** none recorded. The PR lists every choice made without Ben.
- **AI:** Claude wrote the module, tests and script. Each test is a hand-worked synthetic example whose expected
  numbers are worked out in comments. `compliance_check.py` gives 0 FAIL. No count, ratio or 2–4 building
  number was computed or printed from real data.
- **Open / next:**
  - Ben approves D-082 or amends it;
  - decide whether to carry an address key (contract-change issue);
  - add a zoning join for `sf_only_zoned`;
  - write adapters from the Wake, Franklin and Minneapolis card/building summaries to the roll interface;
  - the counting run, once Ben gives the go-ahead.
