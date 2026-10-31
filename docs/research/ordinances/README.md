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
- `nc-fee-lookups-todo.csv` (same day): water/sewer and impact fees per single-family home for the 10 largest
  places other than Raleigh (Raleigh FY2022-FY2027 is coded in `config/fees/nc.csv`).
- `oh-adu-lookups-todo.csv` and `oh-mm-lookups-todo.csv` (2026-10-26, Ohio thread 11, S2/S4): Ohio's 40 largest
  places and the Franklin County places of 5,000+ people (the ones `franklin_permits` covers), largest first. A
  place appears if a rule is uncoded or a coded row has an open question (named in `need`). The ADU table also
  says what ADU permit data Lotline has (`adu_permit_data_now`) and asks where yearly ADU permit counts could
  come from: the big markets (Cleveland, Toledo, Akron, Dayton …) have none. Places on American Legal answer
  scripts with HTTP 403, so they need a browser. Confirmed rows are then coded into `config/reforms/oh.csv`.
- `oh-rules-tracker.csv` (2026-10-27): Ben's working list for the two Ohio tables above, one row per place,
  ranked by what a found rule adds. **Priority 1**: Columbus's yearly ADU counts, Euclid (likely Ohio's second
  missing-middle event) and the Franklin County places whose ADU permits are already flagged (a dated ADU rule
  puts each straight into the ADU panel). **Priority 2**: the largest cities: Cleveland and Toledo (dates of
  recent reforms), Dayton (missing middle) and the five with no ADU rule coded (Akron, Parma, Canton, Lorain,
  Cuyahoga Falls). **Priority 3**: everyone else, largest first. `what_to_check` says what to look for;
  `udo_name`, `udo_url`, `adu_first_allowed`, `mm_first_allowed`, `status` and `ben_notes` are for Ben. The
  detailed fields stay in the two tables above. Built once from those tables, `config/reforms/oh.csv` and the
  processed `jurisdictions` table.
  **2026-10-28:** merged Ben's agentic research workbook (`lotline-data/manual/ohio/`, kept outside the repo
  with the PDFs it saved): `status` is now `researched: lead to confirm`, `researched: nothing found` or
  `not researched`; `research_*` columns hold its findings, dated ordinances, open questions and evidence
  URLs (`research_sources`, IDs from its evidence register); `next_step` says what would close each lead;
  `udo_url` was filled from its code links where empty. The workbook marks most first-permission dates
  unresolved, so nothing was coded from it yet.
  **Later on 2026-10-28:** Ben's Columbus/Euclid pilot workbook (Desktop) was merged too. Euclid's Ord. 120-2024
  (two-family by right in the former single-family U1 district, effective 2024-11-06) is coded as
  `OH-3925704-missing_middle-2024`, Ohio's second missing-middle event; Columbus's ADU effective date was
  corrected to the city's 2025-12-24. Dublin's §153.059 was checked (Bridge Street District only: no
  conflict) and Hamilton's coded row kept (Ben: the 2023 amendment did not pass).
