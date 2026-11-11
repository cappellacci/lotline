### LB-NNN · 2026-11-11 · DATA: NC parser hand checks after the second parser round (Mecklenburg, Greensboro, Asheville)
- **Question:** after #389 and the offline rebuild (#391), what are precision, recall and k = precision ÷ recall
  (D-081 item 1) for `meck_permits`, `greensboro_permits` and `asheville_permits` (before 2022 and 2022 on,
  separately), the NC sources whose counts moved?
- **What I did:** wrote the judging rule, strata, seeds and estimator into the report and committed them
  (`f90a2efb`) before reading any sampled permit. Drew seeded samples (new seeds 20261121–20261124) from the #391
  tables: 30 flagged permits (Greensboro: all 41), every unflagged permit that names an ADU outright, 100 near-miss
  permits (30 for Asheville 2022 on) and 30 broad-word permits per stratum. Joined descriptions in memory from the
  cached raw files, only for ids in the holdout-filtered tables. Judged 802 permits blind to their flag. Scored k by
  simulation (100,000 independent beta draws of precision and near-miss rate) and ran the no-kitchen sensitivity.
  One change after reading: 5 Mecklenburg permits with run-together text ("ADUNew.", "Acc Dwell Unit") were added
  to the strong stratum; both results are reported.
- **Inputs:** `LOTLINE_DATA_DIR` processed NC permits (rebuilt offline 2026-11-11, #391) and the raw snapshots that
  rebuild read. No download; no data committed.
- **Outputs:** `reports/nc/parser-handcheck-2026-11-11b.md`. Scripts and labels (no description text) are in the
  session notes folder, `nc-parser-handcheck-2026-11-11b/`.
- **Findings:** k = p ÷ r (90%): Mecklenburg 0.98 (0.86–1.13), or 1.02 (0.88–1.19) as pre-registered; Asheville
  before 2022 1.47 (1.33–1.61); Asheville 2022 on 1.00 (0.87–1.16); Greensboro 1.39 (1.10–2.33). The kitchen rule
  fixed Greensboro's precision (40/41); its recall is now the limit. Asheville before 2022 still misses ADU records
  that cite the house (parser conflict, 25 of 55 named misses). Both #391 issues are confirmed: one code-437
  apartment "basement unit upfit" among the Mecklenburg flags, and two real ADUs vetoed by "upgrade". The
  no-kitchen setting barely moves k.
- **Decisions:** proposed in the PR: the four undercount-table rows; whether `adu_flag_undercount` accepts k < 1
  (Mecklenburg 0.98); keeping Asheville 2022 on as a field-prior row.
- **AI:** Claude Code wrote the rule, the sampling and scoring scripts and the report, and judged every permit.
  One reader, no second coder.
- **Open / next:** the parser fixes in report §3 (Mecklenburg run-together text, the alteration veto, the
  Asheville conflict, new names); the PR that writes all k values into `adu_flag_undercount`.
