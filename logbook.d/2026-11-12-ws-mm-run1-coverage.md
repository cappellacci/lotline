### LB-NNN · 2026-11-12 · Analysis: D-082 run 1, permit coverage screen and k_src
- **Question:** Which missing-middle permit sources see about as many new 2–4 unit buildings as Census BPS
  before each place's reform? Those sources are "strong" under D-082 §2 and feed runs 2–4.
- **Decisions:**
  - Ben approved D-082 on 2026-11-12 ("Approve D-082").
  - Ben gave the go-ahead for run 1 ("Yes, start run 1"). That answer also accepted PR #408's 13 counting
    choices.
- **What Claude did:**
  - Made branch `ws/mm-run1-coverage`. It stacks #408 (counting code) on #407, which brings in the model code
    and the #403 rule rows.
  - Added `mm_counts.area_coverage`: one k per source, with each place over its own pre-event years. It has a
    hand-worked test.
  - Added the `--coverage` run mode to `scripts/dev/mm_counts_d082.py`, then ran it once on cached tables. No
    download was made, and every table went through `mm_counts.blind`.
  - Added a split sensitivity for buildings merged by the address fallback. It is reported only and is not the
    entry rule.
- **Outputs:** `reports/mm-d082/run1-coverage/{README.md,coverage.csv,coverage_by_year.csv}`,
  `src/lotline/model/mm_counts.py`, `tests/model/test_mm_counts.py`, `scripts/dev/mm_counts_d082.py`.
- **Findings:**
  - As pre-registered, three sources are strong: Raleigh (k 0.81), Austin (0.92) and Bend (1.01).
  - Medford enters but has only 2 pre-years.
  - Minneapolis is too high (1.41, on 62 against 44 buildings).
  - Cincinnati, Portland, College Station, Durham and Columbus are too low.
  - Mecklenburg was not screened: BPS has no Charlotte or town rows.
  - With no street address (#406), merged buildings decide several verdicts. Splitting them moves Durham,
    Columbus and College Station into the band, and Austin above it. The address fix is recommended before
    run 2.
- **How it was checked:**
  - `pytest tests/model/test_mm_counts.py` passes (23 tests).
  - Aggregate diagnostics showed that the out-of-range buildings in Minneapolis, Columbus and Cincinnati are
    mostly permits with `units_new = 0`, which are alterations and not new buildings.
  - The 30-building hand check per source is not done yet.
- **AI disclosure:** Claude Code wrote the code, ran it and wrote the report. Ben approved the protocol and the
  run.
