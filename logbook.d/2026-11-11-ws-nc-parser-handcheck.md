### LB-NNN · 2026-11-11 · DATA: NC parser hand checks after the shared parser fix (Mecklenburg, Asheville, Greensboro)
- **Question:** after #376 and #380, what are parser recall and k_parser = 1 / recall for `meck_permits`,
  `asheville_permits` (before 2022 and 2022 on, separately) and `greensboro_permits`, per source as D-078 §2 says?
- **What I did:** wrote the judging rule, pools and estimator into the report and committed them before reading any
  sampled permit (two dated amendments, each committed before the draws they changed). Drew seeded samples from the
  rebuilt processed tables: 30 flagged permits (Greensboro: all 44), every unflagged permit that names an ADU
  outright, 30 or 100 near-miss permits and 30 broad-word permits per stratum. Joined descriptions in memory from
  the raw files only for ids in the holdout-filtered tables. Judged every permit blind to its flag, then scored with
  90% Wilson intervals. Re-ran Asheville's city-flag benchmark.
- **Inputs:** `LOTLINE_DATA_DIR` processed NC permits (rebuilt 2026-11-11) and the raw files the rebuild used; no
  download, no data committed.
- **Outputs:** `reports/nc/parser-handcheck-2026-11-11.md`.
- **Findings:** k (90%): Mecklenburg 1.07 (1.02–1.31), was 1.04; Asheville before 2022 1.71 (1.52–2.10), was 1.59,
  and the city-flag benchmark is unchanged at 82/130 (1.59); Asheville 2022 on 1.02 (1.02–1.16); Greensboro 1.12
  (1.11–2.46), its first measured k. Asheville's misses come from two shared-parser behaviours the fix did not touch
  (a cited house permit reads as a conflict; amendment text reads as an alteration). Greensboro's precision is 0.75
  because #376 now flags mother-in-law suites with no kitchen named. 4 legalizations, all in Asheville before 2022,
  all unflagged.
- **Decisions:** proposed in the PR: the four undercount-table rows; whether k should be 1 / recall (D-074) or
  precision / recall; whether in-law suites without a kitchen count as ADUs.
- **AI:** Claude Code wrote the rule, the sampling and scoring scripts (kept outside the repo with the labels) and
  the report, and judged every permit. One reader, no second coder.
- **Open / next:** shared-parser fix for the two Asheville behaviours (would change every state's counts); code 437
  in `meck_permits.classify`; `asheville_permits.NEW_HOUSE` wording.
