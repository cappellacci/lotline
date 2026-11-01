### LB-NNN · 2026-10-30 · Policy analysis: Texas rule and fee rows from Ben's second research workbook
- **Question:** which Texas ADU, missing-middle and fee lookups do Ben's second research run (2026-10-29) and the
  27 official PDFs he downloaded settle, and which rows coded earlier do they contradict?
- **What I did:**
  - Split the workbook's City Findings sheet into one text file per place. Five Claude subagents coded proposed
    rows, each with a shared brief that set out the WS-TX coding conventions (four city groups and one fee
    group). Each agent checked key facts against the local PDFs (text layer read with a local pypdf, not a
    project dependency) and flagged everything else for a second coder.
  - Merged and validated the results into `docs/research/ordinances/tx-workbook-2026-10-29.json`. Applied them
    with `scripts/dev/tx_research_2026_10_29.py` (append only, rerun-safe).
  - Proposed corrections to earlier rows are written to `tx-corrections-2026-10-29.csv` and not applied.
- **Inputs:** `~/lotline-data/manual/texas/Texas-Municipal-ADU-and-Missing-Middle-Research.xlsx` (2026-10-29)
  and `Official-PDFs/` (Ben's downloads, kept out of the repo); `config/reforms/tx.csv`, `config/fees/tx.csv`.
- **Outputs:** `config/reforms/tx.csv` (+35 rows: 89 in all), `config/fees/tx.csv` (+38 rows),
  `docs/research/ordinances/tx-{adu,mm,fee}-lookups-todo.csv`, `tx-workbook-2026-10-29.json`,
  `tx-corrections-2026-10-29.csv`, `scripts/dev/tx_research_2026_10_29.py`, ordinances README.
- **Findings:**
  - Missing middle: 21 new rows. 17 are one-home-per-lot "no" rows. Lubbock allows up to 4 units in SF-2
    (2023), Lewisville allows duplexes by right in R-7.5, R-6 and R-5, and Beaumont and Wichita Falls allow
    duplexes by permit.
  - ADU: 10 new rows.
    - Plano 2023: owner occupancy dropped.
    - League City 2026.
    - Lewisville 2026: pending.
    - Tyler, Edinburg and Abilene: rows coded.
    - Frisco 2011, Beaumont, Odessa and Allen: "none" rows.
  - Fees:
    - SAWS by elevation area and basin.
    - Fort Worth Ord. 27745-06-2025 steps.
    - Houston per service unit.
    - Austin meter, tap and parkland fees.
    - Dallas connection and inspection fees only.
    - Corpus Christi trust-fund lot fees.
  - Local PDFs contradict earlier rows. Proposed, not applied:
    - Dallas ADU effective 2018-06-30, not 06-27.
    - Austin ADU 2015 effective 11-30, not 11-19.
    - College Station ADU rule dates from Ord. 2018-4059, not 2023.
    - Denton's 2023 date belongs to an unrelated amendment.
    - El Paso 2011 has no ADU parking minimum.
    - McKinney's ADU is rentable.
    - Frisco's rental date is 2019-10-01.
    - San Antonio's 2001 row cites a Dallas report.
  - 70 of 89 rule rows now carry a second-coder FLAG.
- **Decisions:** none. The 35 proposed corrections await Ben (`decision` column).
- **AI:** Claude subagents coded the rows from the workbook and PDFs. Claude merged them, fixed two over-long
  quotes and the "none"-row convention (by_right False, `NO ADU RULE` prefix), and ran the Texas, fee, schema and
  panel tests (161 pass). Facts not checked against a local PDF are flagged; the workbook's own claims were not
  re-read at their web sources.
- **Open / next:**
  - Ben decides the corrections.
  - Missing-middle lookups still open: El Paso, Corpus Christi, Amarillo, Killeen, Pasadena, Denton, Carrollton
    and College Station.
  - Killeen overlay passage.
  - Pasadena stays PENDING.
  - Second-coder pass.
