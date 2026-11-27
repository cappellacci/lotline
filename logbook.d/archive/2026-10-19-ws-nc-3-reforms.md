### LB-NNN · 2026-10-19 · Policy analysis: North Carolina reform rows (config/reforms/nc.csv)
- **Question:** Which NC reforms enter the model, with what dates and rubric values, and which cities does the
  2026 state ADU law (S.L. 2026-59) cover?
- **What I did:**
  - Coded 14 rows with the protocol §5.4 rubric against `schemas.Reforms`: Durham EHC (city and county, MM + ADU) and
    SCAD (parking, ADU); Raleigh TC-16-19, TC-5-20, TC-20-21 (MM and ADU); Charlotte UDO (MM, ADU); Greensboro ADU 2024;
    S.L. 2026-59 Sec. 44 (statewide row, GEOID "37").
  - Every row cites the URLs opened; facts not read in a source stay empty and are named in `coding_notes`.
  - Added `tests/states/nc/test_reforms.py` (schema, sources, supersedes order, hand-checked dates and values).
- **Inputs:** city ordinance PDFs and pages (Raleigh TC-05-20-ORD and TC-20-21-ORD, Durham EHC page, Greensboro LDO
  page), S.L. 2026-59 session-law text, G.S. 113A-103 (coastal counties), Census 2020 NC place file; news reports
  where city sites were unreachable (Strong Towns, IndyWeek, WFDD, Charlotte Regional Business Alliance).
- **Outputs:** `config/reforms/nc.csv`, `tests/states/nc/test_reforms.py`.
- **Findings:**
  - Durham SCAD passed late on 2023-11-20 (the brief's 2023-11-21 is the reporting date); Raleigh TC-5-20 took effect
    2021-08-05 and TC-20-21 on 2022-08-08 (both stated in the ordinances).
  - S.L. 2026-59 covers 19 non-coastal cities at or above 50,000 (2020 Census); Wake Forest and Holly Springs
    only on a post-2020 estimate; Wilmington and Jacksonville excluded as coastal. The law names no population source.
  - Unsourced: effective dates for Durham EHC/SCAD, Raleigh TC-16-19 and Greensboro (coded as vote dates); SCAD's
    adopted ADU size; Charlotte's original triplex conditions, N1 parking, TA 2024-067; Durham County SCAD rows.
- **Decisions:** proposed: S.L. 2026-59 enters the baseline for the 19 cities (plus a sensitivity with Wake Forest and
  Holly Springs).
- **AI:** Claude (WS-NC) researched sources with web search and fetch, coded every row, wrote the test; single coder
  (`coder_agreement = single_coder`), Ben to second-code a sample.
- **Open / next:** Durham ordinance PDFs (403 from this network) for EHC/SCAD effective dates; Charlotte TA 2024-067.
