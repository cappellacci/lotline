# City-ordinance pipeline records

Raw records from the city-ordinance pipeline (one research agent per city, then an independent checker that
re-opens every cited page). Each record lists, for one city: ordinances since 2010 on ADUs, 2-4 unit homes in
single-family zones, parking and fees (with the direct document link, PDF where one exists); fee schedules by
fiscal year; ADU programs with dates; when 2-4 units became legal; and every document that must be fetched by
hand (`manual_needed`, and links with `manual_pdf_needed: true`). Quotes are verbatim and at most 25 words.

Links marked `robots_allowed: false` were never fetched. Nothing here is coded into `config/reforms` or
`config/fees` until it has a quote the checker confirmed or Ben's manual lookup confirms it.

- `batch1-2026-10-20.json`: 20 Minnesota cities, Austin, Raleigh, Durham. Manual list:
  `docs/build/manual-ordinance-pdfs-batch1.md`.
- `metro-adu-adoption-2026-10-20.json`: ADU rule history for 162 Twin Cities metro places (the D-023 comparison set; St. Paul excluded). Priority manual list: `docs/build/manual-adu-adoption-dates.md`.

## Fill-in tables for Ben (manual lookups)

- `nc-adu-lookups-todo.csv` and `nc-mm-lookups-todo.csv` (2026-10-21, NC thread 10): the 40 largest North
  Carolina places (Census 2020), largest first, minus places already coded. Most city sites answer scripts with
  HTTP 403, so these need a browser. Fill the blank columns with a source link; confirmed rows are then coded
  into `config/reforms/nc.csv`.
- `tx-adu-lookups-todo.csv` and `tx-mm-lookups-todo.csv` (2026-10-23, Texas thread 12, S4/S5): places among
  Texas's 40 largest (Census 2020) whose ADU or missing-middle rules one read of the zoneomics code mirror did not
  settle, largest first, plus a line for the second-coder check of every flagged row in `config/reforms/tx.csv`.
  Rows that were settled are coded by `scripts/dev/tx_rules_21_40.py`.
- `tx-fee-lookups-todo.csv` (2026-10-26, Texas thread 12, S6): water/sewer and impact fees per home for the four
  Texas cities with permit data and Houston, plus Austin's parkland and meter fees. Austin's water/wastewater
  impact fees and street impact fee are coded in `config/fees/tx.csv`.
- **Status of the three Texas tables** (column `status`: open / partial / coded), updated 2026-10-27 from Ben's
  research workbook (`~/lotline-data/manual/texas/`, an agentic research run, kept out of the repo): Corpus
  Christi's ADU rule and Austin HOME's dates are coded (`scripts/dev/tx_research_2026_10_27.py`), Carrollton
  and San Antonio are partial, everything else is still open.
- `tx-workbook-2026-10-29.json` (Ben's second workbook run, with official PDFs in
  `~/lotline-data/manual/texas/Official-PDFs/`): 35 rule rows, 38 fee rows, notes on 34 earlier rows and tracker
  updates, applied by `scripts/dev/tx_research_2026_10_29.py` (append only). After it: ADU 5 coded / 8 partial /
  2 open, missing middle 20 / 4 / 8, fees 0 / 5 / 0. Changes it proposes to earlier rows are **not applied**: they
  are in `tx-corrections-2026-10-29.csv` (35 rows) for Ben to decide.
  - **Decided 2026-10-30** (`decision` column): 32 accepted, Denton's date kept with a note, College Station's
    parking left as a note, Abilene kept at one home per lot. Applied by `scripts/dev/tx_corrections_2026_10_30.py`
    (run after the 10-29 script), which also renames four rows whose effective year moved: San Antonio
    `TX-4865000-adu-2001` → `-2010`, Frisco `TX-4827684-adu-2021` → `-2019`, Laredo `TX-4841464-adu-1992` →
    `-2010`, College Station `TX-4815976-adu-2023` → `-2018`.
- **Ben's own lookups (2026-10-30)**, applied by `scripts/dev/tx_ben_lookups_2026_10_30.py` (run after the
  corrections script):
  - Killeen overlay ADUs (passed 4-1, overlay only).
  - Lewisville cottages: adopted, now in force.
  - Denton DCA25-0001a (2026-01-13).
  - College Station 2023 parking. Reuses the id `TX-4815976-adu-2023`.
  - Pearland's 2006 UDC rules.
  - Missing middle for El Paso, Corpus Christi, Amarillo, Killeen, Denton, Carrollton, College Station and Plano;
    Lubbock's limited-use terms; Laredo's Ord. 2025-O-004; Austin parkland and service units, SAWS middle and
    high elevation, Houston 2021 (`config/fees/tx.csv`); official sources from the updated workbook.
  - League City RSF-5 has no duplexes.
  - Pasadena stays pending.
- `tx-second-coder-2026-10-30.csv`: **the second-coder worksheet**, one line per Texas rule row flagged
  "FLAG for second coder" (80 on 2026-10-30).
  - Priority 1: dated reforms inside the window, which become D-024/D-025 events.
  - Priority 2: dated "none" or one-home rows.
  - Priority 3: rules in force since 2010 or earlier.
  - Each line has what was coded, what to check (from the row's own flags) and the sources. Four columns are
    blank for the second coder: `second_coder`, `agrees (yes/no/partly)`, `correct_value`,
    `second_coder_note`.
  - Rows the second coder agrees with get `coder_2` and `coder_agreement = agree` in `config/reforms/tx.csv`;
    disagreements are adjudicated.
  - **Reviewed 2026-10-30** (Ben's review pass, `second_coder = ben-review`; applied by
    `scripts/dev/tx_second_coder_2026_10_30.py`):
    - 2 rows agreed (Abilene ADU 2010, College Station ADU 2023).
    - 4 "partly" rows have their finding added to the notes.
    - 74 rows carry the reviewer's "could not independently confirm" note. They stay single-coder and flagged,
      because a check that could not read the source is not agreement.
- **Ben's second batch (2026-10-30)**, applied by `scripts/dev/tx_ben_lookups_2026_10_30b.py` (run after the
  second-coder script):
  - League City's 2026 ADU row is back in force and by right.
  - Tyler's garage-apartment row is renamed `TX-4874144-adu-2010`.
  - Laredo's one-home row now covers R-1A, R-1B and R-1-MH.
  - Notes for Denton, McKinney, Killeen, Lewisville and Edinburg.
  - SAWS 2015-2019 water totals noted on the 2014-schedule rows; Houston's pre-2021 water rate as a new row.
  - Replay order of the Texas scripts: `tx_research_2026_10_29`, `tx_corrections_2026_10_30`,
    `tx_ben_lookups_2026_10_30`, `tx_second_coder_2026_10_30`, `tx_ben_lookups_2026_10_30b`, then
    `tx_fee_rule_2026_10_30` (Ben's rule for fees that vary by area or plat date, `config/fees/README.md`).
    Rerunning them all leaves the files unchanged (checked 2026-10-30).
- `nc-fee-lookups-todo.csv` (same day): water/sewer and impact fees per single-family home for the 10 largest
  places other than Raleigh (Raleigh FY2022-FY2027 is coded in `config/fees/nc.csv`).
