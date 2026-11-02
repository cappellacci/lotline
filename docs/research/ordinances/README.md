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
    Then `tx_ben_lookups_2026_11_01` (Carrollton ADU and Dallas utility fees, 2026-11-01).
    Rerunning them all leaves the files unchanged (checked 2026-10-30).
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

- `nc-second-coder-2026-11-01.csv` (North Carolina thread 10): **the second-coder worksheet** for the 66 local rule
  rows in `config/reforms/nc.csv` (every row except the S.L. 2026-59 state-law rows), same columns as the Texas sheet.
  - **Review first: the 24 lines with `panel_event` set** (sorted to the top, 2026-11-01, thread 13). They are the
    rows that would serve as dated events: 11 D-025 rows (places with ADU-flagged permits: Raleigh, Durham city and
    county, Greensboro, Cornelius, Huntersville, Matthews, Mint Hill) and 13 D-024 rows (BPS places of 10,000+
    with a missing-middle change in 2010-2025, plus unincorporated Durham County). 11 of the 24 are priority 2:
    their date is the ordinance's adoption date, so the event may be earlier than coded.
  - Priority 1 (28): dated reforms from 2010 on, which become D-024/D-025 events.
  - Priority 2 (31): rows dated 2010 or later by the ordinance's adoption date (`[earliest-known]`): the event date
    itself needs confirming.
  - Priority 3 (7): rules in force before 2010.
  - Copies of the ordinances Ben downloaded are in `~/lotline-data/manual/nc_udos/`; `source_url` names the file.
  - Four columns are blank for the second coder: `second_coder`, `agrees (yes/no/partly)`, `correct_value`,
    `second_coder_note`. Agreed rows get `coder_2` and `coder_agreement = agree`; disagreements are adjudicated.
  - **Reviewed 2026-11-01** by Ben's second agent (Codex; `second_coder = codex-2026-11-01`; its working files,
    evidence register and PDFs are in `~/lotline-data/manual/nc/second_coder_2026-11-01/`): 8 yes, 44 partly,
    14 no, plus 5 supplemental rows (Goldsboro, New Bern, Concord missing middle). Applied by
    `scripts/dev/nc_second_coder_2026_11_01.py`: the 8 agreed rows get `coder_2` and `coder_agreement = agree`;
    every reviewed row gets the finding in its notes; no coded value changes.
  - `nc-second-coder-decisions-2026-11-01.csv`: the 14 disagreements, one value-changing "partly" (Rocky Mount)
    and the 5 supplemental rows, each with a recommended action, for Ben to decide. Proposed tag `[predates]` in
    `coding_notes`: the rule was in force before the coded date and the first date is unknown, so the row is not
    an in-window event.
  - **Decided 2026-11-01** (Ben: accept the recommendations; keep Mint Hill's duplexes by right). Applied by
    `scripts/dev/nc_second_coder_decisions_2026_11_01.py` (run after the review script): 15 rows adjudicated,
    of which 8 tagged `[predates]`; renamed `NC-3702080-adu-2021` → `-2014`, `NC-3741960-adu-2014` → `-2016`,
    `NC-3757500-adu-2005` → `-2004`; added Goldsboro ADU and duplex, New Bern 'no ADUs' and duplex, Concord
    duplex/triplex. The reviewer's Thomasville (Georgia) source was rejected; a Newbern, Tennessee PDF in its
    folder was moved to `wrong_place/`.

- `mn-mm-lookups-todo.csv` (2026-11-02, thread 13, M4): **Minnesota missing-middle fill-in table**, the 33 of the
  40 largest MN places with no coded missing-middle row, largest first, in the NC format. `notes` carries what
  the batch-1 record found, and `start_url` its link where there was one. Five rows were coded from the batch-1
  records by `scripts/dev/mn_mm_batch1_2026_11_02.py`:
  - St. Louis Park 2025, an in-window event (N-1 up to 3 homes; effective date from a search snippet, to confirm);
  - Duluth 2026, after the window (R-1 up to 4);
  - "one home" rows (`unit_cap = 1`) for Rochester (R-1, 2023 code), Brooklyn Park and Coon Rapids (2010
    placeholder, `[earliest-known]`).
