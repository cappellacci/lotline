### LB-NNN · 2026-11-10 · Data feasibility: Charlotte and unincorporated Mecklenburg ADU permits (D-072)
- **Question:** now that V5 is released, how many ADU permits did Charlotte and unincorporated Mecklenburg
  issue each year in 2010–2025, how good is the flag, and are Charlotte's ADU rule rows right?
- **What I did:**
  - Found that `meck_permits` on `main` still filtered released holdouts. PR #357 already fixes it, so I dropped
    my duplicate change and rebuilt NC permits with `lotline fetch --state NC --source meck_permits` (482,249
    rows, the same as #357's rebuild).
  - Counted ADU-flagged permits by year against eligible lots.
  - Hand-checked 30 matches, 30 high-risk non-matches and all 79 unflagged permits that name an ADU.
  - Read the 2012 committee recommendation, the 1992–2023 amendment log and the city's UDO ADU declaration form.
- **Inputs:** registered `Winchester_BuildingPermits.zip` (2026-10-12); processed `eligible_parcels`;
  `onemap_parcels` (2026 roll); D-070, D-071, D-072 (PR #358).
- **Outputs:** `reports/nc/charlotte-adu-counts.md`.
- **Findings:**
  - Charlotte: 310 flagged ADU permits in 2010–2025 (58 in 2024; 0.20 per 1,000 eligible lots a year in
    2021–24). Unincorporated Mecklenburg: 15. 2025 is about half a year (Accela).
  - Precision 0.83 strict to 1.0. Recall 0.96 central (14 misses found: upfit/addition ADUs on code 434, and
    one code-437 permit), 0.79 at the 90% bound.
  - The 37119 `eligible_parcels` row keeps Charlotte's and the towns' homes (they are `in_bps: False`), so it
    would double-count lots for permit-level rates. OneMap has about 21,800 single-family lots instead of 275,566.
- **Decisions:** proposed in the PR: Charlotte's flags from 2016 behave like a field flag (D-072 k choice);
  the 37119 denominator fix (WS-CORE); a rule row for 37119 after an ETJ check.
- **AI:** Claude Code ran the counts and samples in memory (descriptions never written), judged the hand-check
  rows and read the ordinance PDFs. It checked counts against the rebuilt table and the legacy-file thinning by
  month. Rows to recheck: the 5 doubtful matches and the 4 ambiguous non-matches, listed in the report.
- **Open / next:** merge #357; parser fix for ADU upfits (shared `permit_text`); Accela download (steps in the
  report); read UDO amendment 2025-118.
