### LB-NNN · 2026-10-30 · Policy analysis: Texas rule rows from Ben's own lookups
- **Question:** what do Ben's answers to the open Texas items settle? There were seven ADU and code-history
  questions and a missing-middle table for eight places, follow-ups for Plano, Lubbock
  and Laredo, and two Austin fee answers.
- **What I did:**
  - Coded Ben's answers with `scripts/dev/tx_ben_lookups_2026_10_30.py` (rerun-safe): 13 new rows and 5 rows
    coded earlier updated with dated notes.
  - Updated the lookup trackers and added `test_ben_lookups_2026_10_30`.
  - Read Killeen's overlay terms from `Killeen_North-Killeen-Overlay_2026-10-20.pdf` (OCR text layer).
  - Checked that the Killeen row's coverage text triggers the D-021 limited-area share.
  - Opened Ben's McKinney Legistar link: a 2024-01-16 council work session, with no ordinance attached. One web
    search for a later McKinney amendment found none.
- **Inputs:** Ben's answers in chat (2026-10-30), with links: Killeen Daily Herald post, citizenportal.ai
  (Lewisville), McKinney Legistar, College Station Ord. 2023-4454, League City Ch. 125 Art. 3. Also the local
  Killeen overlay PDF and Ben's research workbook (2026-10-29).
- **Outputs:** `config/reforms/tx.csv` (102 rows), `config/fees/tx.csv` (13 Austin rows annotated), `docs/research/ordinances/tx-{adu,mm}-lookups-todo.csv`,
  `scripts/dev/tx_ben_lookups_2026_10_30.py`, `tests/states/tx/test_reforms.py`, ordinances README.
- **Findings / changes:**
  - **ADU:**
    - Killeen overlay: by right, overlay only. It does not supersede the citywide "none" row.
    - Lewisville cottages are now in force (adopted 2026-09-21).
    - Denton DCA25-0001a: by right, 800 sq ft or more, from 2026-01-13. It supersedes the 2023 row with the
      unsupported date.
    - College Station Ord. 2023-4454: one space per bedroom.
    - Pearland: CUP only since 2006-02-27, so a "none" row.
    - McKinney stays rentable from 2022, with Ben's caveat noted.
  - **Missing middle:**
    - Duplex by right in some single-family districts: El Paso (R-4, R-5) and Amarillo (R-3).
    - Duplex by SUP or CUP: Denton (R4) and Pearland (R-4, 2006).
    - One home per lot: Corpus Christi, Killeen (narrow board exception noted), Carrollton, College Station and
      Plano (the 2024-25 amendments did not open the single-family districts to duplexes).
    - Lubbock: the 'limited use' duplex approval is administrative (Director, Use Verification Form) with
      design standards, which confirms by right. No ADU on a duplex lot.
    - Laredo: Ord. 2025-O-004 (2025-01-28) sets duplex lot area and defines a vertical duplex. The row is
      unchanged.
    - League City RSF-5 has no duplexes. This withdraws the 2026-10-30 reading of #32, which came from a
      misaligned PDF text layer.
  - **Austin fees:**
    - ADUs and duplex units on existing lots pay the parkland fee unless an affordable-housing program exempts
      them, so the three parkland rows now carry a per-unit amount.
    - Service units follow meter size (5/8-inch 1.0, 3/4-inch 1.5, 1-inch 2.5; a secondary source, flagged),
      noted on the 10 impact-fee rows.
  - **Trackers:** ADU 8 coded / 5 partial / 2 open; missing middle 30 / 1 / 1 (Laredo partial, Pasadena
    pending); fees 0 / 5 / 0. 80 of 102 rule rows carry a second-coder FLAG.
- **Decisions:**
  - Killeen's 6,000 sq ft lot minimum goes in the notes, not `min_lot_sqft`, so coverage reads as overlay only.
  - Missing-middle rows whose start date wasn't researched are dated 2010-01-01 and flagged.
  - The College Station id `TX-4815976-adu-2023` is reused for the parking amendment.
  - The Amarillo R-3 duplex is read as by right.
  - Proposed for HANDOFF: none.
- **AI:** Claude coded Ben's answers, read the Killeen PDF text, and ran the Texas and panel tests (132 pass)
  and the full suite. Ben's secondary sources (a news post, citizenportal.ai) are flagged for checking against
  the official record.
- **Open / next:**
  - Killeen's signed ordinance number and dates.
  - Lewisville ordinance number.
  - Denton's DCA25-0001a ordinance number and effective date, and when the R4 duplex SUP started.
  - McKinney's lot minimum before 2026.
  - Pasadena.
  - Fees.
  - Second-coder pass.
