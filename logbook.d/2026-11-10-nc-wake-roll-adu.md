### LB-NNN · 2026-11-10 · Data feasibility: Wake roll diff, ADUs built 2019–2023 and Raleigh's flag undercount
- **Question:** how many second homes were actually added to Wake County single-family lots between the Nov 2019
  and Dec 2023 rolls, by jurisdiction, independent of permit flags; and how much do Raleigh's ADU-flagged permits
  undercount real ADUs?
- **What I did:**
  - Wrote the detection rule first and committed it before any count (56330e7, `reports/nc/wake-roll-adu-diff.md`
    §1): a new dwelling card or a unit/use change on a REID present in both rolls, sorted into groups (new card
    built ≥2019, older building, unit change, rebuild with two homes; acreage-growth merges set aside).
  - Implemented it as tested functions (`wake_roll_diff.py`, 11 hand-worked tests on a synthetic fixture) and a
    read-only runner that reads the registered rolls through `DataStore` (non-personal columns only).
  - Matched Raleigh's roll finds to its ADU-flagged permits by 10-digit PIN; after the first count, added a
    documented ADU-only adjustment (drop 4 duplex rebuilds, add 5 flags issued outside 2019–2022) and reported
    both versions.
- **Inputs:** Wake rolls `Real_Est_Data_Final_Nov2019.xlsx`, `Real_Est_Data_Final_Dec2023.xlsx` (registered, not
  re-downloaded); `processed/nc/permits/raleigh_permits.parquet` through `holdout.apply`.
- **Outputs:** `reports/nc/wake-roll-adu-diff.md`, `reports/nc/wake-roll-adu-diff.json` (aggregates only),
  `src/lotline/adapters/states/nc/wake_roll_diff.py`, `tests/states/nc/test_wake_roll_diff.py`,
  `scripts/dev/nc_wake_roll_adu_diff.py`. No processed table written.
- **Findings:**
  - Wake County: 88 of 256,532 single-family lots gained a second home (0.08 per 1,000 a year, 95% 0.07–0.10;
    strict 47). Raleigh 48 (0.14) and unincorporated Wake 32 (0.13); the eleven other towns 8 between them.
  - Raleigh: 73% (58–84%) of roll-detected ADUs carry an ADU flag, so about 1.4 (1.2–1.7) real detached ADUs per
    flagged one; Chapman 1.37 (1.20–1.54); 1.78 without the duplex adjustment. A lower bound (dependent sources;
    attached/internal ADUs invisible to the roll).
  - D-072 (PR #358) k, P = flags issued 2019-01-01 to 2023-06-30: |P∩R| 30, |a| 6, |b| 12, |P\R| 75; k = 1.20
    (90% 1.10-1.41). 4 of the 6 in (a) are duplex permits; without them k = 1.07 (1.02-1.21). Chapman 1.46-1.59x.
  - The roll undercounts more than the flags: 31 of 63 flagged permits (2019–2022) show no second home by Dec 2023.
    The roll is a correction check on the flags, not a second outcome series.
- **Decisions:** none added to HANDOFF. For D-072: use the duplex-removed k = 1.07 (1.02-1.21) as the field-flag
  undercount, with 1.4 (all roll-only ADUs) as the upper sensitivity.
- **AI:** Claude Code wrote the rule, functions, tests, runner and report. Checked by the hand-worked tests,
  by tracing 26 known flagged ADUs through both rolls before writing the rule, and by inspecting every roll-only
  Raleigh parcel's permits; the 2022 permit cohort was not looked at before the rule was committed.
- **Open / next:** Cary/Apex permit files (sibling sessions) could test whether the near-zero town counts are real;
  Wake has a separate outbuilding file that might show attached ADUs (not checked).
