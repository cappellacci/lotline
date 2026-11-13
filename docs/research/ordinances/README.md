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
- `tx-second-coder-lubbock-2026-11-07.csv` and `.md`: the second coder for `TX-4845000-missing_middle-2023`,
  flagged by D-059 (`docs/analysis_plan.md`). Verdict partly: the 2023 use-matrix cells hold, but old R-2
  (two-family) already allowed duplexes and became MDR, and the SF-2 gain is limited by the block-face rule
  (§39.02.018.c.1.A). Not applied to `config/reforms/tx.csv` (Texas coding closed); a recode needs Ben.
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

<!-- ws-adu-rules:start -->
## WS-ADU-RULES: ADU rule details for the fit places (2026-11-12)

Brief: `docs/build/workstreams/WS-ADU-RULES.md`. Research only: nothing in `config/` changed, no model was run, and
no ADU permit counts, refit results or `reports/` were opened while coding. St. Paul (holdout) was coded for its
rules only.

**Files.**
- `adu-fit-rules-todo-2026-11-12.csv`: the worklist, filled. `found_*` hold the value per rule version
  (`date: value; date: value` when it changed). `source_*` hold every cited source and quote.
  `second_coder` / `agrees` hold the second coder's tally per place.
- `adu-fit-rules-proposed-2026-11.csv`: 153 proposed `reforms` rows, one per rule version 2016-2025, in
  the schema's columns. Four review columns follow them: `tags`, `field_status` (`agree` / `inherited` /
  `adjudicated` / `flag` per field), `second_coder_agreed_fields` and `second_coder_flags`. Rows that reuse an
  existing `reform_id` propose changes to that row; the others are new. Nothing is applied until Ben accepts
  rows and a dated script in `scripts/dev/` applies them.
- PDFs saved during the work are in `~/lotline-data/manual/adu-rules-2026-11/<state>/`, outside the repo. Each
  download is logged with URL, sha256 and time in `downloads.jsonl` there.

**How it was coded.**
1. One first-coder agent per group of places read the existing rows and earlier research records. It then
   opened the code, the adopted ordinances and Wayback copies of past versions, and wrote each rule version
   with verbatim quotes of at most 25 words.
2. A fresh second-coder agent re-opened every cited page and judged each (version, field) value: yes / partly /
   no / unverifiable. A value resting on a third-party mirror (Zoneomics), a draft, a city guide or a news
   report was rated at most "partly".
3. One browser agent then re-checked values whose official page refuses scripts against the official code
   (Municode, American Legal, city PDFs). It opened one page at a time and stopped on any challenge.
   Browser results: {'confirmed': 74, 'manual_needed': 9, 'partly': 5, 'contradicted': 2}.

**Status.** Places: {'partly coded': 33, 'coded': 32}. Proposed rows by `coder_agreement`: {'agree': 88, 'adjudicated': 11, 'single_coder': 54}. Tags: {'[detached-conditional]': 18, '[moratorium]': 1}.

Core fields across all 65 places:

| core field | agreed by both coders or decided by Ben (every version) | one coder only (some version flagged) | blank |
|---|---|---|---|
| by right | 44 | 21 | 0 |
| owner occupancy | 46 | 15 | 4 |
| extra parking | 43 | 18 | 4 |
| detached allowed | 46 | 19 | 0 |

Priority 1 only (46 places):

| core field | agreed by both coders or decided by Ben (every version) | one coder only (some version flagged) | blank |
|---|---|---|---|
| by right | 34 | 12 | 0 |
| owner occupancy | 36 | 6 | 4 |
| extra parking | 33 | 9 | 4 |
| detached allowed | 37 | 9 | 0 |

Blank `found_*` fields by priority (blank = not found, never "no restriction"):

| priority | places | by_right | owner_occ | parking_spaces | detached | adus_per_lot | max_sqft | min_lot_sqft |
|---|---|---|---|---|---|---|---|---|
| 1 | 46 | 0 | 4 | 4 | 0 | 4 | 14 | 10 |
| 2 | 18 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

**Coding decisions made without Ben** (agreed with the coordinating session on 2026-11-12, provisional; each can be
reversed):
1. `by_right` is true when any ADU type that meets the code is approved by staff alone. Where attached ADUs
   are by right but detached ADUs need a conditional, special or interim use permit, `coding_notes` carries the
   tag `[detached-conditional]`, so a sensitivity can treat those places as not by right. Every tag was
   reviewed by hand.
2. Blaine's 2025 moratorium on all ADU applications (Ord. 25-2577) is a row with `status = suspended`,
   `by_right = False` and the tag `[moratorium]`. Its end date is not confirmed.
3. Values that rest only on a third-party mirror count as agreed only if the browser check confirmed them on
   the official code. Otherwise they stay flagged (`single_coder`).
4. A field carried unchanged into a later version, with no evidence of its own, counts as agreed
   (`inherited`) when the earlier version's value was agreed and the second coder checked the later version.
5. Clear-cut second-coder corrections are applied as `adjudicated` and listed in the rows' notes:
   - College Station 2018 and 2023 `adu_max_sqft`: blank, because 400 sq ft is a floor.
   - Austin HOME 2024 `adu_max_sqft`: blank, because 2,300 sq ft is a floor.
   - St. Paul 2023 `adu_max_sqft`: blank, because 800 sq ft is a floor.
   - Charlotte 2024 `adu_max_sqft`: kept at 1,000, the cap for detached ADUs.
   - Bend 2021 effective date: 2021-11-05, from the notice of decision.
   Judgment calls are not adjudicated by the coders; they go to Ben (below).
6. A rule version in force at the start of the window whose first date is unknown is dated 2016-01-01 and
   tagged `[predates]` in its date basis.

**Judgment calls decided by Ben, 2026-11-13** (applied; field status `decided`, and the row's `coding_notes` say
"decided by Ben, 2026-11-13"):
1. Raleigh 2020-2022: 0 extra parking spaces for an ADU.
2. Bloomington: owner occupancy left blank in every version, because the city handout is not code.
3. Cincinnati 2023: owner occupancy not required, because the owner or a named responsible person may live on site.
4. Bend before 2016-02-17: by right.
5. Orono before 2022: the household-only guest apartment is not an ADU, so there were no ADUs (`adus_per_lot = 0`).
6. New Brighton before 2024: no ADUs (`adus_per_lot = 0`).
7. Durham from 2024: one ADU per lot; the accessory duplex counts as one.

**Still open for Ben:**
- Wayzata before 2022: one guest, carriage or caretaker's house was allowed by conditional use permit and could
  not be rented. It is coded as no ADU, the same way as Orono; the alternative is detached by CUP. The row stays flagged.
- Two values contradicted by the browser check, left flagged:
  - Ramsey 2023 `min_lot_sqft = 43,560`: the one-acre minimum is for detached ADUs only. Attached ADUs need an
    80-ft lot width (§106-425(1)i), so the field would be "none". Attached ADUs are not permitted in R-1B and R-1C.
  - Austin HOME effective date: Municode dates Ord. 20231207-001 to 12-18-23, but it is coded 2024-02-05. The
    `adu_max_sqft` contradiction was already corrected to blank.
- The conflicts with existing rows below, notably the Raleigh date and transit rule, the Fridley date, Cornelius
  2021/2023, Wilmington before 2021, Chanhassen 2025 and Baytown by right. None is resolved here.

**Process incidents** (reported plainly; the rule was reinforced with every agent afterwards):
- Medford OR (first coder, Oregon group): getpdf.py refused ('Access Denied') for medfordoregon.gov mmc_ch10_sec10-821.pdf; the agent re-fetched it with plain curl (different user agent) and got the PDF. Copy deleted by the coordinator; the values now rest on a Wayback copy of the same PDF (2025-03-15) checked by the second coder; the live URL is listed manual_needed.
- Scott County MN (first coder, Scott/St. Paul group): after getpdf.py was refused for scottcountymn.gov DocumentCenter/View/1428, the agent sent one plain-curl request with a browser user agent; it was also refused (Cloudflare 403) and nothing was saved. All Scott County values rest on Wayback copies saved through getpdf.py.
- Holdout-adjacent download: the east-metro coder (Stillwater) saved a St. Paul staff report to the Comprehensive and Neighborhood Planning Committee about ADUs (`~/lotline-data/manual/adu-rules-2026-11/MN/StPaul_StaffToCNPC_ADU_survey.pdf`, logged in downloads.jsonl) as a comparison memo of other cities' rules. It is cited for no value. The St. Paul coders and the coordinator did not open it. It may describe St. Paul ADU activity, so it is flagged for Ben, who may want to delete it.

**Rule changes found, 2016-2025** (132 entries across 56 places; each is a candidate
before-and-after event; format `date: field old → new (ordinance)`):

- **TX San Antonio city**: 2023-01-01: max_sqft 800 → 1600 (greater of 800 or 50% of house, cap 1,600) (Ord. 2022-11-03-0831); 2023-01-01: parking_spaces null (pre-2023 requirement applied to all ADUs, count unconfirmed) → depends (0 up to 800 sq ft, 1 above) (Ord. 2022-11-03-0831); 2023-01-01: one-bedroom and 3-occupant limits removed; separate utilities allowed; detached height 2 stories/25 ft (Ord. 2022-11-03-0831) — not coded fields
- **NC Charlotte city**: 2023-06-01: parking_spaces 1 → 0 (UDO replaces Zoning Ordinance; parking by principal use only); 2023-06-01: max_sqft 800 → null (no absolute cap; internal <=40%, detached <=50% of house) (UDO Sec. 15.6.F); 2024-06-17: max_sqft null → 1000 (detached ADU capped at 1,000 heated sq ft; internal 40% limit deleted) (UDO amendment, version 'Amended June 17, 2024')
- **OR Portland city**: 2021-08-01: adus_per_lot 1 → 2 (R7/R5/R2.5 on lots meeting Table 205-1, one must be detached; Ord. 190093, RIP); 2021-08-01: max_sqft cap 800 unchanged, but basement conversions of 5+ year-old houses exempted (Ord. 190093); 2022-06-30: two-ADU coverage extended to R20 and R10, and 2-ADU lot minimums cut (Table 205-2) (Ord. 190851, RIP2); 2018-07-01 / 2020-01-01: SB 1051 and HB 2001 changed nothing locally (Portland already allowed detached ADUs by right with no owner occupancy and no ADU parking)
- **TX Austin city**: 2015-11-30 (just before window): min_lot_sqft 7000 → 5750; max_sqft 850 → 1100 (smaller of 1,100 or FAR 0.15); parking_spaces 2+ → depends (1, or 0 near transit corridor) (Ord. 20151119-080); 2023-11-13: parking_spaces depends → 0 (Ord. 20231102-028); 2024-02-05: adus_per_lot 1 → 2; max_sqft 1100 → 2300 (greater of FAR 0.4 or 2,300, Subchapter F area only); coverage SF-3+ → SF-1, SF-2, SF-3 (Ord. 20231207-001, HOME phase 1)
- **NC Raleigh city**: 2019-05-20: by_right false (no ADUs) → false (ADUs only inside a rezoned -ADUOD overlay; none known) (Ord. 2019-917 TC 412, TC-3-17); 2019-05-20: detached n/a → true; adus_per_lot 0 → 1 inside overlay (TC-3-17); 2020-07-22: by_right false → true; overlay repealed; parking null → 0; max_sqft null → 800 (1,000 on lots >40,000); two-adult occupancy cap dropped (Ord. (2020) 117 TC 432, TC-16-19); 2022-05-14: citywide vehicle parking minimums eliminated (Ord. (2022) 352 TC 464, TC-11-21); ADU parking already 0; 2022-08-08: adus_per_lot 1 → 2 in Frequent Transit Areas (only one attached); ADUs allowed on townhouse and tiny-house lots; barred on flag lots (Ord. (2022) 362 TC 466, TC-20-21)
- **NC Durham city**: 2018-03-01: parking_spaces required (number not found) → 0 (TC17-05 Omnibus 11 / TC1700005); 2019-10-01: max_sqft 30% of primary → 800; min_lot_sqft district minimum → none (nonconforming lots allowed); ADU allowed with duplexes and in nonconforming accessory structures; detached may sit beside rear 25% of house (TC18-07 / TC1800007 EHC); 2024-01-01: max_sqft 800 → 1,200 total (1,000 on one story); adus_per_lot 1 → 2 (duplex accessory structure with a single-family house) (TC22-01 / TC2200001 SCAD)
- **OH Cincinnati city**: 2023-10-02: by_right false → true; adus_per_lot 0 → 1; detached false → true; owner_occ (n/a) → true (owner or responsible person); parking (n/a) → 0 (Ord. 266-2023)
- **OR Salem city**: 2017-07-10: by_right false → true; adus_per_lot 0 → 1; detached false → true; owner_occ (n/a) → false; parking (n/a) → 0 (Ord. Bill 10-17; adoption date, effective date not found); 2018-07-01 / 2020-01-01: SB 1051 and HB 2001 changed nothing in Salem's fields (local code already allowed detached ADUs as a special use with no owner occupancy and no parking); 2024-09-23: ADUs also allowed on townhouse lots >= 2,500 sq ft (Ord. Bill 8-24); no change in coded fields
- **OR Bend city**: 2016-02-17: by_right false → true (CUP for pre-1998 lots in SR 2 1/2/RL/RS deleted; Type I review) (NS-2260); 2016-02-17: max_sqft 600 → 800 (600 kept for properties <= 6,000 sq ft) (NS-2260); 2019-11-06: parking_spaces 1 → 0 (NS-2353, 'Consistent with HB 2001'; adoption date, effective likely ~2019-12-06); 2021-10-06: max_sqft small-lot 600 tier removed, flat 800 (NS-2423; effective 2021-11-05 per city); 2025-07-18: adus_per_lot 1 → 2 (second ADU <= 500 sq ft) (NS-2532)
- **NC Wilmington city**: 2021-12-01: parking_spaces 2+ → 0 (new LDC, adopted 2021-08-17); 2021-12-01: max_sqft 1200 (detached; attached 800) → 900 (attached/detached; internal 30%) (new LDC §18-200); 2021-12-01: min_lot_sqft 20000 (R-15: district minimum + lesser of 50%/5,000 sq ft, detached only) → 15000 (district minimum, all ADUs) (new LDC §18-200(A)(2)); 2022-11-01 (earliest-known; O-2022-41 of 2022-06-07 or O-2022-88 of 2022-11-01): max_sqft 900 → 1200 (lesser of 50% of principal GFA); internal 30% → 50%; lot-area minimum limited to detached ADUs; 2024-05-21: min_lot_sqft 15000 (detached) → none (LDC-7-424)
- **MN Blaine city**: 2021-12-20: ADUs first allowed: attached by administrative permit, detached by CUP, in single-family districts (Ord. 21-2489); complaint ¶43 says the 2025 application was the first since the code was amended in 2021 to allow ADUs; 2025-05-19: by_right true → false (one-year moratorium on all ADU applications, Ord. 25-2577)
- **OR Medford city**: 2018-12-20: parking_spaces depends (2 total for house+ADU) → 0 (Ord. 2018-132); 2018-12-20: max_sqft share 50% → 75% of primary (900 sq ft cap unchanged); ADUs extended to duplex/townhouse lots and multi-family/commercial zones (Ord. 2018-132); 2022-06-16: no coded-field change; four-unit cap per lot in SF zones incl. ADUs, cottage clusters excluded (Ord. 2022-60); 2018-07-01 / 2020-01-01: SB 1051 and HB 2001 imposed nothing Medford did not already allow (no owner occupancy before; parking removed locally in Dec. 2018)
- **TX College Station city**: 2018-11-29: owner_occ false → true; rental of quarters allowed (was family/servants only); parking_spaces null → 1; adus_per_lot null → 1; max_sqft 25% of house → greater of 25% or 400 sq ft (Ord. 2018-4059); 2023-08-20: parking_spaces 1 → depends (1 per bedroom) (Ord. 2023-4454)
- **MN Bloomington city**: 2016-04-18: approval wording changed from Planning Manager approval to administrative final site and building plan approval (by_right stays true) (Ord. 2016-6); 2019-03-25: min_lot_sqft 11000 → none; 33% size ratio base widened to combined ADU+house area (Ord. 2019-18); 2022-08-08: detached false → true; parking text no longer states four spaces (still single-family minimum) (Ord. 2022-39); 2025-05-19: max_sqft 959 → 1000 and 33% cap removed; owner_occ true → false (one-rental-license-per-site limit deleted) (Ord. 2025-09)
- **NC Huntersville town**: 2024-09-17: coverage_note GR 'for use by related person(s)' only → unrestricted ADU in GR (Ord. T24-07 / TA 24-07); 2025-08-19: coverage_note same-ownership requirement removed; principal may be a detached house or townhouse (Ord. TA25-08 Part 1 / TA25-01)
- **MN Plymouth city**: 2023-09-12: coverage new-plat (2001+, 10+ lots) garage-top units on new homes only → all detached single-family lots in FRD/RSF-1/2/3/PUD; internal, attached, garage-top and standalone detached (Ord. 2023-12); 2023-09-12: parking_spaces 2+ → 1 (Ord. 2023-12); 2023-09-12: max_sqft min(principal GFA, 1,000) → attached 30% of home up to 1,000 / detached 30% of rear yard up to 700 (Ord. 2023-12)
- **NC Durham County Unincorporated Area**: 2018-03-01: parking_spaces required (number not found) → 0 (TC17-05 Omnibus 11 / TC1700005); 2019-10-28: max_sqft 30% of primary → 800; min_lot_sqft district minimum → none (nonconforming lots allowed); ADU allowed with duplexes and in nonconforming accessory structures; detached may sit beside rear 25% of house (TC18-07 / TC1800007 EHC); 2024-01-01: max_sqft 800 → 1,200 total (1,000 on one story); adus_per_lot 1 → 2 (duplex accessory structure with a single-family house) (TC22-01 / TC2200001 SCAD)
- **MN Cottage Grove city**: 2023-01-01: accessory apartments (internal only) listed as permitted accessory use in R-1 to R-4 under the revised zoning code; whether this is new or carried over from the 1971 code is unknown
- **MN Andover city**: 2016-06-21: ADUs first allowed (conditional use, R-1 only) by Ord. 463; no earlier ADU provision (an earlier 'guest house' rule is a different use)
- **MN Burnsville city**: 2018-05-22: ADUs first allowed (R-1/R-1A; attached/internal on >=10,000 sq ft lots, detached on >=1 acre; owner-occupied; 1 extra stall; max 960 sq ft or 33%) (Ord. 1456); 2020-10-06: min_lot_sqft 10000 → none (detached no longer needs 1 acre); max_sqft 960/33% → 50% of primary dwelling, no absolute cap (Ord. 1528)
- **MN Ramsey city**: 2022-03-14: ADUs first allowed (permitted use in R-1, attached and detached) by Ord. 22-04; 2023-11-14: coverage changed in the Chapter 106 rewrite (Ord. 23-14): attached ADUs permitted in all residential districts (MR, RR, R-1A/B/C, R-2, R-3); detached ADUs limited to MR, RR, R-1A; core fields unchanged (adoption date; effective date not found); 2024-07-23 and 2025-09-23: Ord. 24-10 and Ord. 25-08 amended 106-425/106-422; content of each not read (likely added Shoreland Overlay limits: detached 700 sq ft, 15 ft height)
- **NC Chapel Hill town**: 2023-06-21: max_sqft 750 (or 75% of principal) → 1,000 (75% if principal ≤1,300 sq ft); detached height 29 ft; Director exceptions inside existing structures; 'single-family with cottage' use added (Ord. 2023-06-21/O-6)
- **MN Chanhassen city**: 2025-05-12: by_right false (variance only) → true for attached/internal ADUs by building permit; owner_occ → true; parking → 0; max <960 sq ft (Ord. 744); 2025-06-09: detached false → true, by conditional use permit only in A2/RR/RSF; RSF needs 1.0-acre lot; detached owner-occupied, no rental (Ord. 747)
- **NC Cornelius town**: 2021-06-21: ADU (rental cottage) allowed → not allowed; by_right true → false, detached true → false (TA 02-21, removal of Rental Cottage use); 2023-01-17: ADU not allowed → allowed; by_right false → true, detached false → true (internal also allowed), adus_per_lot 1, parking one space per bedroom (TA 01-22); 2023-01-17: owner_occ true (pre-2021 rental cottage) → false (TA 01-22)
- **MN Roseville city**: 2021-11-08: coverage LDR-1 only → LDR and LMDR (former LDR-2) (Ord. 1606)
- **MN Fridley city**: 2022-04-30: ADUs first allowed (attached as permitted accessory use with staff ADU permit; detached by Special Use Permit) in R-1, R-2, R-3, S-1 (Ord. 1400, adopted 2022-04-11); 2025-06-18: zoning code replaced by new title (Ord. 1431; reported effective 2025-07-01); ADU standards carried into 621.01 with the same owner-occupancy, one-per-lot, 50% size and parking rules; permit path under the new use tables not confirmed
- **MN Inver Grove Heights city**: 2018-10-08: ADU standards re-enacted as § 10-18-1 (Ord. 1358); specific changes from the 2015 text not identified (parking 2 extra spaces, one per lot and registration confirmed only for the 2018 text)
- **MN Rosemount city**: 2024-06-04: ADUs first allowed (internal/attached, PS in A-2/RR/R-1/R-2, max lesser of 75% or 800 sq ft, 1 extra stall) (Ord. 2024-04)
- **MN Crystal city**: 2018-02-10: by_right false (no ADUs) → true (P with zoning certificate in R-1/R-2); detached false → true; adus_per_lot 0 → 1; parking → 1 extra space; owner_occ none (rental allowed) (Ord. 2017-07); date unknown (after 2020-10): ADUs added as conditional use in NC district (no detached there); detached separation 10 ft → 5 ft (ordinance not identified; not a core-field change)
- **MN Forest Lake city**: 2023-01-23: detached false → true (A district, 5+ acre lots, 800 sq ft footprint, 1 space) (Ord. 719)
- **MN New Brighton city**: 2024-09-28: adus_per_lot 0 → 1 (general ADUs first allowed; servants'-quarters clause replaced) (Ord. 900); 2024-09-28: by_right null → true; owner_occ → true; parking → 1; detached → true; max_sqft → 1064 (Ord. 900)
- **MN Rogers city**: 2020-05-26: ADUs listed as an accessory use in AG and R1 in the new Land Development Regulations (earliest-known date; whether the repealed 1980 zoning chapter allowed ADUs is unknown)
- **MN Dayton city**: 2019-12-10: ADU rules adopted (attached/internal by administrative building permit; detached by IUP on 2+ acres) by Ord. 2019-22; whether ADUs were allowed in any form before is not known
- **MN Mounds View city**: 2025-06-29: owner_occ null → true (recorded covenant) (Ord. 1042); 2025-09-13: detached false → true (by CUP; 300 sq ft min, 50% of house max; 1 space) (Ord. 1045)
- **MN Vadnais Heights city**: 2024-07-16: ADUs allowed (attached by right, detached by CUP; owner occupancy; 1 per lot; max lesser of 1,200 sq ft or 35% of house) (Ord. 774); prior state not confirmed from code text
- **MN Orono city**: 2022-11-14: nonrental internal guest apartments (permitted) and detached guest houses (CUP, lot ≥2x district minimum) → ADUs attached or detached as permitted accessory use with building permit on lots ≥1 acre in R-1A/R-1B/LR-1A/1B/1C/1C-1/RR-1A/1B (Ord. 279, Third Series); 2022-11-14: detached by CUP → detached by right (Ord. 279); 2022-11-14: parking depends → 2+ (Ord. 279)
- **MN Hopkins city**: 2022-07-28: by_right false (no ADUs) → true (secondary suites by right; backyard cottages allowed) (Ord. 2022-1180); 2022-07-28: detached false → true; adus_per_lot 0 → 1; owner_occ → true in N1/N2 only; parking → 0 (Ord. 2022-1180)
- **MN Medina city**: 2024-08-20: max_sqft lesser of 750 (1-BR)/1,000 (2-BR)/40% → lesser of 40% and 1,400 (<5 ac)/1,600 (5+ ac) (Ord. 731); 2024-08-20: added rental limits (only one unit rented, 30-day minimum); removed § 826.98 attached-only clause for SR/UR/R1/R2 (district lists for SR/UR still say within principal structure) (Ord. 731)
- **MN Minneapolis city**: 2016-09-02: detached max 1,000 sq ft → greater of 1,300 sq ft or 16% of lot, max lesser of 1,600 or the house (Ord. 2016-060); coded max_sqft (internal/attached 800) unchanged; 2021-03-06: owner_occ true → false for attached/detached ADUs; kept for internal ADUs that are not separate dwelling units (Ord. 2021-009); 2021-05-22: citywide parking minimums repealed (file 2020-00704); ADU parking already 0, no change; 2023-07-01: ADU rules moved to Ch. 550 Art. IX; districts renamed (UN1-UN3, RM, CM); coded fields unchanged (Land Use Rezoning Study, file 2023-00172); 2025-05-23: detached footprint/separation edits (Ord. 2025-023); coded fields unchanged
- **NC Greensboro city**: 2024-04-16: owner_occ true → false (LDO text amendment, ord. no. not found); 2024-04-16: parking_spaces 1 → 0 (same); 2024-04-16: max size 30% of house with 400 sq ft minimum → 50% of house, no minimum (same; max_sqft stays null, relative cap); 2024-04-16: min_lot_sqft district minimum (R-5 7,000) → none (same); 2024-04-16: detached ADUs move from principal-structure setbacks/dimensions to accessory-structure standards (same)
- **NC Cary town**: 2025-06-02: detached false → true in all single-unit detached districts (ACT 32, Ord. 2025-CODE-01, adopted 2025-04-10); 2025-06-02: parking_spaces depends (1 per ADU bedroom; UDU 2 extra) → 1 (Ord. 2025-CODE-01); 2025-06-02: max size lesser of 33% or 800 sq ft → lesser of 50% or 800 sq ft (1,000 on 40,000+ sq ft lots) (Ord. 2025-CODE-01); max_sqft 800 → 800; 2025-06-02: detached-ADU minimum lot effectively 20,000 sq ft → none (Ord. 2025-CODE-01); min_lot_sqft for internal units none → none
- **MN Rochester city**: 2019-10-20 (earliest-known; approved Jul-Oct 2019): new R-2x district allows ADUs incl. detached, 600 sq ft, owner-occupied, no parking minimum, in the Residential Reinvestment area (R2018-003TA); detached false → true and parking 1 → 0 there only; 2023-01-01: UDC makes ADUs an accessory use in all residential and mixed-use districts incl. R-1; max_sqft 600 → 1000; detached allowed citywide; parking → set by Director (unlisted use); owner occupancy only in single-dwelling districts
- **MN Minnetonka city**: 2021-10-04: detached false → true in R-1/R-1A (CUP still required); current standards (owner 185 days, 1,000 sq ft/35%, adequate parking, one per lot) in force from this date; whether they changed from the pre-2021 text is unknown (Ord. 2021-20)
- **MN Edina city**: 2024-04-16: ADUs first allowed in R-1 (internal, attached, detached; 1,000 sq ft; one per lot; no owner-occupancy rule; no ADU parking) (Ord. 2024-02)
- **MN St. Louis Park city**: 2020-10-19: ADUs first allowed on single-family lots in R-1/R-2/R-3 (by right, one per lot, attached or detached, owner at initial construction, no added parking) (Ord. 2596-20; secondary source dates it 2020-11-13); 2021-01-04: §36-162(e) amended (Ord. 2602-21); content not identified, coded fields unchanged in the 2023 text; 2025-03-28: ADU rules moved to §36-169(a) for N-1/N-2; detached rear setback 15 → 5 ft; coded fields unchanged (Ord. 2690-25)
- **MN Apple Valley city**: 2023-06-08: no coded field change; Am. Ord. 1121 amended §155.382 (short-term rental ban under 30 days in (D)(22))
- **MN Maplewood city**: 2023-12-11: ADU standards adopted (Ord. No. 1044): by_right unknown → true; detached unknown → true; adus_per_lot unknown → 1; owner_occ unknown → false; parking_spaces → 1; max_sqft → 900 (whether ADUs were allowed before is not settled)
- **MN Golden Valley city**: 2022-11-11: ADUs first allowed (Ord. No. 745): by_right false → true; detached false → true; adus_per_lot 0 → 1; owner_occ → true; parking_spaces → 1; max_sqft → 950; 2025-12-16: parking_spaces 1 → 0 (Ord. No. 812, adoption date; effective date not found, may be early 2026)
- **MN Mound city**: 2024-11-03: ADUs first allowed (Ord. No. 07-2024): by_right false → true; detached false → true; adus_per_lot 0 → 1; owner_occ → true; parking_spaces → 1; max_sqft → 800
- **MN Cedar Lake township**: 2020-08-18 (earliest-known; Comprehensive Revision #2 or a 2015-2020 amendment): ADU occupancy family-only -> family or single caregiver; size basis 'total' -> 'habitable' sq ft; IUP exception to detached-ADU separation for existing structures; design standards simplified. Core fields unchanged.; 2025-05-06: max_sqft 800 (and 40% of house, 300 min) -> 1,000 attached / 1,200 detached; room-count limits and side-or-rear-yard rule removed; IUP exception to size for existing structures (Ch. 7 amendment, ordinance no. not found)
- **MN Wayzata city**: 2022-06-30: ADUs first allowed (Ord. 811): by_right false → true; detached false → true; adus_per_lot 0 → 1; owner_occ → true; parking_spaces → 1; max_sqft → 960 (R-2A to R-3; 33% of house elsewhere); 2025-01-16: Ord. 845 amended §937.02/§937.03; the current ADU text (Zoneomics mirror) matches Ord. 811, so no ADU field change identified
- **MN Helena township**: 2020-08-18 (earliest-known; Comprehensive Revision #2 or a 2015-2020 amendment): ADU occupancy family-only -> family or single caregiver; size basis 'total' -> 'habitable' sq ft; IUP exception to detached-ADU separation for existing structures; design standards simplified. Core fields unchanged.; 2025-05-06: max_sqft 800 (and 40% of house, 300 min) -> 1,000 attached / 1,200 detached; room-count limits and side-or-rear-yard rule removed; IUP exception to size for existing structures (Ch. 7 amendment, ordinance no. not found)
- **MN Jackson township**: 2020-08-18 (earliest-known; Comprehensive Revision #2 or a 2015-2020 amendment): ADU occupancy family-only -> family or single caregiver; size basis 'total' -> 'habitable' sq ft; IUP exception to detached-ADU separation for existing structures; design standards simplified. Core fields unchanged.; 2025-05-06: max_sqft 800 (and 40% of house, 300 min) -> 1,000 attached / 1,200 detached; room-count limits and side-or-rear-yard rule removed; IUP exception to size for existing structures (Ch. 7 amendment, ordinance no. not found)
- **MN St. Lawrence township**: 2020-08-18 (earliest-known; Comprehensive Revision #2 or a 2015-2020 amendment): ADU occupancy family-only -> family or single caregiver; size basis 'total' -> 'habitable' sq ft; IUP exception to detached-ADU separation for existing structures; design standards simplified. Core fields unchanged.; 2025-05-06: max_sqft 800 (and 40% of house, 300 min) -> 1,000 attached / 1,200 detached; room-count limits and side-or-rear-yard rule removed; IUP exception to size for existing structures (Ch. 7 amendment, ordinance no. not found)
- **MN St. Paul city (holdout: rules only)**: 2016-11-16: ADUs first allowed (permitted use) in R1-RM2/T1-T3 within 1/2 mile of University Ave, Emerald St-Lexington Pkwy; owner_occ true, 1/lot, 800 sq ft, 5,000 sq ft lot min, parking 0 extra (Ord. 16-13); 2018-12-01: coverage corridor -> citywide RL-RM2/T1-T3; min_lot_sqft 5000 -> none for internal/attached (5,000 kept for detached) (Ord. 18-28); 2022-03-05: owner_occ true -> false; detached lot minimum 5000 -> none; max_sqft 800 -> 75% of principal (no fixed cap); ADU parking clause deleted (Ord. 22-1); 2023-11-26: adus_per_lot 1 -> 2; max_sqft 75% -> greater of 800 or 75%; districts recast (H1/H2) (Ord. 23-43)
- **MN Richfield city**: 2021 (date not found): garage size rule — first 400 sq ft of ADU space exempt from 1,000 sq ft detached-garage cap, likely added by Bill No. 2021-4 (code history lists 2021-4 on §514.05 Subd. 3; content not confirmed); 2023-01-24: ADU principal dwelling may be single-family or two-family (was single-family only); R and MR-1 merged into one R district; R lot width/depth apparently 50x100 -> 47x100 (min lot area 6,700 -> 6,000, order inferred from text without strike-through) (Bill No. 2023-2). Core fields unchanged.

**Conflicts with existing `config/reforms` rows** (not applied; for Ben):

- **TX San Antonio city**: TX-4865000-adu-2023: adu_max_sqft coded 800 (floor convention); the absolute cap is 1,600 sq ft. Convention difference.
- **NC Charlotte city**: NC-3712000-adu-2023: coded from the current (amended) permit form; the UDO as effective 2023-06-01 had internal <=40% and detached <=50% with no absolute cap, but from the June 17, 2024 version the internal limit is gone and detached ADUs are capped at 1,000 heated sq ft. A 2024-06-17 row is missing. by_right, owner_occ, parking (blank in row) coded true/false/'0' here.
- **OR Portland city**: OR-4159000-adu-2022: row's Table 205-2 minimums (12,000/6,000/4,200/3,000/1,500) agree with the 6/30/22 text; row says a 10/1/24 chapter version exists — the city's current 33.205 PDF is still dated 6/30/22, so I found no 2024 amendment to 33.205 (the 10/1/24 item may be another chapter).
- **TX Austin city**: TX-4805000-adu-2023: effective_date coded 2023-11-02 (vote date); the city staff review sheet says Ord. 20231102-028 took effect 2023-11-13.
- **TX Austin city**: TX-4805000-adu-2015: adu_max_sqft coded 862 (floor at a 5,750 lot); I coded the absolute cap 1,100 with the FAR rule in the note. Convention difference, not a factual disagreement.
- **TX Austin city**: TX-4805000-adu-2010: parking_min_per_unit=2 and 'separate driveway' agree; the pre-2015 driveway rule was a paved-driveway width rule unless alley access, not strictly a separate driveway.
- **NC Raleigh city**: NC-3755000-adu-2020: effective_date coded 2020-07-07; ordinance signature block says Effective July 22, 2020 (15 days after adoption).
- **NC Raleigh city**: NC-3755000-adu-2020: component says 'owner-occupancy requirement struck'; IndyWeek's wording is 'striking rules limiting occupancy', and TC-3-17 had a two-adult occupancy cap, not an owner-occupancy rule found in Art. 5.7. owner_occ=False is right for 2020, but the 'struck' framing is not supported.
- **NC Raleigh city**: NC-3755000-adu-2022: adus_per_lot coded 2; that applies only in Frequent Transit Areas; elsewhere (most single-family lots) still 1.
- **NC Raleigh city**: NC-3755000-adu-2019: effective_date 2019-02-19 in one row vs the ordinance's EFFECTIVE: MAY 20, 2019 (the adjudication already accepted 2019-05-20).
- **NC Durham city**: NC-3719000-adu-2019: effective_date coded 2019-09-03 (vote); UDO text-amendment table gives City effective 10/1/2019.
- **NC Durham city**: NC-3719000-adu-2023: effective_date coded 2023-11-20 (vote); table gives effective 1/1/2024. adu_max_sqft blank: adopted code reads 1,000 sq ft single story / 1,200 total.
- **NC Durham city**: NC-3719000-adu-2023: no adus_per_lot; SCAD §5.4.2B.1.d allows a duplex accessory structure (2 units) with a single-family house.
- **OH Cincinnati city**: OH-3915000-adu-2023: coded adu_max_sqft=800, but § 1421-06(g) caps ADU size at the principal dwelling's square footage with no absolute cap; 800 sq ft appears only in § 1421-06(d) as the minimum footprint allowance ('15% of the total lot area or 800 square feet, whichever is greater'). Suggest max_sqft blank with the relative rule in the note.
- **OH Cincinnati city**: OH-3915000-adu-2023: effective date 2023-10-02 now confirmed by the ordinance itself (Section 17), not only secondary sources; parking 0 confirmed (§ 1421-06(j)).
- **OR Salem city**: OR-4164900-adu-2018 / -2020: no value conflict, but the rows imply the state law was the first ADU allowance; Salem's local code allowed ADUs (detached, by right, no owner occupancy, no parking) from 2017-07-10 (Ord. Bill 10-17). Suggest a local row OR-4164900-adu-2017 and a 'none' row before it.
- **OR Bend city**: OR-4105800-adu-2016: owner_occ blank — the 2016 text (old and new 3.6.200(B)) has no owner-occupancy clause; suggest owner_occ False. Its effective date 2016-03-18 is computed; the ordinance states only adoption 2016-02-17.
- **OR Bend city**: OR-4105800-adu-2016: row's notes say the 2019 parking deletion was 'found only as a proposal' — it was adopted in Ord. NS-2353 on 2019-11-06, so ADU parking went to 0 locally about two months before HB 2001's 2020-01-01 date (suggest a local row OR-4105800-adu-2019).
- **OR Bend city**: No local row captures NS-2423 (2021) dropping the 600 sq ft small-lot cap; adu_max_sqft=800 in existing rows is right for the field but the small-lot tier ended 2021.
- **NC Wilmington city**: NC-3774440-adu-pre2021: coded adu_max_sqft=900; old §18-248(b) caps detached at the lesser of 35% or 1,200 sq ft (attached §18-247(h): lesser of 35% or 800). Lot rule is 'exceed district minimum by the lesser of 50% or 5,000 sq ft', not a flat 1.5x. by_right (blank) = true (accessory use with city-manager site plan); owner_occ (blank) = false. effective_date 2010-01-01 placeholder: code history shows O-2008-25 (2008-04-08) and O-2012-53 (2012-08-21).
- **NC Wilmington city**: NC-3774440-adu-2021: coded 'lot-and-a-half minimum dropped' but the 2021 LDC §18-200(A)(2) still required the lot to meet the district minimum lot area for every ADU (that was dropped for internal/attached in 2022 and for all in 2024). 900 cap confirmed for attached/detached (internal 30%). Parking 0 confirmed. by_right (blank) = true ('C' = permitted with conditions). end_date 2024-05-20 conflicts with Municode Supp. 4, which already shows the 50%/1,200 cap under 2022 ordinance history notes.
- **NC Wilmington city**: NC-3774440-adu-2024: values confirmed from the certified ordinance (Wayback copy): 1/lot, 50%/1,200 cap, detached allowed, effective on adoption 2024-05-21. But the 900→1,200 increase appears in Supp. 4 with 2022 history notes; WHQR (2024-04-30) says the prior limit was 900. Needs the O-2022-41 / O-2022-88 ordinance text to settle. owner_occ (blank) = false; parking (blank) = 0.
- **MN Blaine city**: MN-2706382-adu-2021: coded by_right=False (CUP). Attached ADUs were an accessory use with an administrative permit (staff) in R-1 and other SF districts; only detached ADUs needed a CUP. Under the by_right definition (staff-only path exists) this should be True, with detached noted as CUP.
- **MN Blaine city**: MN-2706382-adu-2021: the 2025-05-19 moratorium (Ord. 25-2577) is not coded; existing notes call its date unknown.
- **MN Blaine city**: MN-2706382-adu-2026: out of window; second coder reports a May 4, 2026 second reading vs coded 2026-03-16; the 2026-03-16 council agenda (trms.northmetrotv.com packet) lists 'ORD 26-2601 Second Reading', supporting 2026-03-16.
- **OR Medford city**: OR-4147000-adu-2018 / -2020: no value conflict; but Medford allowed ADUs (detached, permitted, no owner occupancy) locally since at least 2004, and dropped ADU parking by Ord. 2018-132 (2018-12-20), a year before HB 2001's 2020-01-01 date. Suggest local rows for the 2004-2018 and 2018 versions.
- **TX College Station city**: TX-4815976-adu-2023: effective_date coded 2023-08-10 (adoption); Part 4 makes it effective ten days after passage, i.e. 2023-08-20.
- **TX College Station city**: TX-4815976-adu-2018: by_right and adu_detached_allowed left blank; the 2018 ordinance text supports by_right=true and detached=true.
- **TX College Station city**: No existing row for the pre-2018 rule: before 2018-11-29 accessory quarters could not be rented outside the family/servants, which the current rows do not record.
- **MN Bloomington city**: MN-2706616-adu-2009: coded min_lot_sqft=11000 for the whole pre-2022 period; Ord. 2019-18 (2019-03-25) deleted the 11,000 sq ft minimum, so 2019-03-25 to 2022-08-07 has no lot minimum.
- **MN Bloomington city**: MN-2706616-adu-2022: owner_occ left null; one-rental-license-per-site rule (and city handout) imply owner_occ=true until Ord. 2025-09.
- **MN Bloomington city**: MN-2706616-adu-2025: ordinance number not given in row; it is Ord. 2025-09 (passed 2025-05-19). Row does not record that 2025-09 deleted the one-rental-license limit (owner_occ → false).
- **NC Asheville city**: NC-3702140-adu-2015 second-coder note says 'later rules amended these standards': no amendment to UDO 7-14-1 between 2015 and the 2025 S-3 codification (history note ends at Ord. 4431); first later changes are Ord. 5175 (eff. 2026-01-27) and Ord. 5256 (2026-08-25), both after the window.
- **NC Huntersville town**: NC-3733120-adu-2024: the row starts in 2024, but ADUs were permitted accessory uses (by right) in R, TR, NR, NC and TC, and in GR for related persons, from at least 2016; a pre-2024 row is missing. Ordinance number: town code history tag reads 'Ord. T24-07' (case TA 24-07); second coder's 'T24-09' not seen. owner_occ (blank in row) coded false; parking coded 'depends' (1 / 1.5 per dwelling unit by bedrooms).
- **MN Lakeville city**: MN-2735180-adu-2013: adus_per_lot=1 is not stated in the code text read (only 'one postal address'); left null here.
- **MN Lakeville city**: MN-2735180-adu-2013: owner_occ blank; code has no owner-occupancy condition (Dakota County guide: 'None specified') → false.
- **MN Plymouth city**: MN-2751730-adu-2002: owner_occ, parking and size blank; pre-2023 text shows owner_occ=true, 2 extra spaces, max min(principal GFA, 1,000 sq ft). Coverage also required the ADU permit to be filed with the building permit for the principal structure (new construction only).
- **MN Plymouth city**: MN-2751730-adu-2002: coverage omits zones RSF-R, RSF-1, RSF-2, PUD named in the struck pre-2023 text.
- **NC Durham County Unincorporated Area**: NC-37063-adu-2019: effective_date coded 2019-10-28 = vote date; the UDO text-amendment table also lists County effective 10/28/2019 (agrees). Missing fields now filled: by_right true, owner_occ false, parking 0 (since 2018-03-01), detached true, adus_per_lot 1, min_lot none.
- **NC Durham County Unincorporated Area**: No county row exists for SCAD (TC22-01, effective 2024-01-01: max 1,200 sq ft, duplex accessory structure); the county's SCAD vote approved 'most of' the package — whether every ADU item passed in the county was not verified beyond the UDO table listing §5.4.2B for both jurisdictions.
- **MN Cottage Grove city**: MN-2713456-adu-2023: coded adus_per_lot=1, but the code states no per-lot limit for accessory apartments (left null here). Otherwise agrees.
- **MN Burnsville city**: MN-2708794-adu-2018: coded min_lot_sqft=43560 (1 acre) for all ADUs; the 2018 text set 10,000 sq ft for attached/internal and 1 acre only for detached. owner_occ (true, 185 days) and parking (1 extra) were blank; max 960 sq ft/33% not coded.
- **MN Burnsville city**: MN-2708794-adu-2020 (second-coder/decision row): adoption was unconfirmed and the row was at risk of deletion; Ord. 1528 was ADOPTED 2020-10-06 (signed ordinance), so the 2020 change is real. Date should be 2020-10-06, not 2020-10-01.
- **MN Ramsey city**: MN-2753026-adu-2022: coverage 'R-1' is right for 2022-2023 only; after Ord. 23-14 (2023-11-14) detached ADUs are not permitted in R-1B/R-1C/R-2/R-3 (attached still allowed everywhere residential). Not a field conflict, a missing later version.
- **NC Chapel Hill town**: NC-3711800-adu-2023: parking left blank; the 2023 ordinance's 5.9.7 row reads as a MINIMUM of 1 per accessory-apartment bedroom (maximum N/A), resolving the town page's 'maximum' vs FAQ 'minimum' conflict in favour of minimum.
- **NC Chapel Hill town**: NC-3711800-adu-2003: parking blank; same minimum applied from November 23, 2015 (date as printed in the 5.9.7 row).
- **NC Mint Hill town**: NC-3743480-adu-2011: adu_max_sqft=900 is the general accessory-building cap and binds only detached suites; an attached/internal suite has no cap found. Otherwise agrees. Parking (blank in the row) coded 'depends' here.
- **MN Chanhassen city**: MN-2710918-adu-2025 (2025-06-09): coded by_right=False; attached/internal ADUs became by-right (building permit) under Ord. 744 on 2025-05-12, a separate earlier event not in the reform rows; only detached needs a CUP.
- **MN Chanhassen city**: MN-2710918-adu-2025: owner_occ, parking blank; adopted text has owner occupancy (both types) and no additional parking.
- **MN Chanhassen city**: MN-2710918-adu-none: effective 1986-01-01; Ord. 80 (zoning code) date is 1986-12-15.
- **NC Matthews town**: NC-3741960-adu-2016: owner_occ left blank; this coding sets owner_occ=false for R-20/R-15/R-12/R-9/R-VS (requirement only in CrC). Other fields agree (by_right, 900 sq ft, detached, 1 parking space). Adds adus_per_lot=1 and min_lot_sqft=none.
- **NC Cornelius town**: NC-3714700-adu-2023: coding_notes say whether ADUs were allowed before 2023 is not shown; in fact a 'Rental Cottage (In Outbuildings)' accessory use (AC in RP/GR/NR/NMX, owner-occupied principal, min 480 sq ft) was in force from at least 2016 until TA 02-21 (2021-06-21) removed it. A pre-2021 row and a 2021-2023 'not allowed' gap are missing.
- **NC Cornelius town**: NC-3714700-adu-2023: parking_min_per_unit=1 is the 1-bedroom minimum; coded 'depends' (1 per bedroom) here. owner_occ (blank in row) coded false. Second coder doubted by_right; Sec. 5.2.1.A says uses permitted with conditions are allowed 'as a matter of right', so by_right=true kept.
- **MN Roseville city**: MN-2755852-adu-2011: coded adu_max_sqft=600 (Ben 2026-11-02: '650 came with Ord. 1606'). The Ord. 1418 text as passed 2011-10-10 sets 300-650 sq ft with the 600 cap struck, and the 2021 Ord. 1606 redline shows no change to this clause. Suggest 650 from 2011.
- **MN Roseville city**: MN-2755852-adu-2021: component says '300-650 sq ft' is new in 2021; the only ADU change found in the Ord. 1606 redline is LMDR (former LDR-2) moving from NP to P. Size, parking, owner occupancy and detached are unchanged.
- **MN Roseville city**: MN-2755852-adu-2010: before Ord. 1418, ADUs were conditional uses under the rewritten code (effective on publication 2010-12-21, per RCA 4/18/2011 §1.1), not 2010-01-01; the 600 sq ft cap belongs to this pre-2011 CUP version. Ord. 1418's table redline also appears to drop ADUs from LDR-2 and MDR (struck C / P), so the 2010 coverage 'LDR-1, LDR-2, CMU, MDR' did not carry into the window.
- **MN Fridley city**: MN-2722814-adu-2022: effective_date coded 2022-09-01 (earliest-known); the city's own ADU page (2022 Wayback copy) gives second reading 2022-04-11, publication 2022-04-15, effective 2022-04-30, Ord. No. 1400.
- **MN Fridley city**: MN-2722814-adu-2022: coded by_right=False. Attached ADUs were a permitted accessory use with a no-fee staff ADU permit; only detached needed a Special Use Permit. Under the by_right definition this is True (staff-only path), with detached noted as SUP.
- **MN Fridley city**: MN-2722814-adu-2022: decisions file tagged it [predates]; the ordinance and city page show ADUs were first allowed in 2022 (an event inside the window, not predating).
- **MN Inver Grove Heights city**: MN-2731076-adu-2018: coded min_lot_sqft=43560 for all ADUs; the one-acre minimum applies only to detached ADUs (attached/internal have no ADU lot minimum).
- **MN Inver Grove Heights city**: MN-2731076-adu-2015: all fields blank; minutes support by_right=true, owner_occ=true, detached=true (>=1 acre), max 1,000 sq ft from 2015-11-02.
- **MN Rosemount city**: MN-2755726-adu-2024: owner_occ left blank; no owner-occupancy standard in § 11-6-7(A) → false. Otherwise agrees.
- **MN Crystal city**: MN-2714158-adu-2018: parking blank / second coder said 'no ADU-specific parking-space count'; Table 11 requires 1 space per ADU beyond the principal's spaces.
- **MN Crystal city**: MN-2714158-adu-2018: second coder's 10 ft separation is the 2020 text; current code says 5 ft.
- **MN Stillwater city**: MN-2762824-adu-2017: component and coverage omit that RA, the city's main one-family district, did not allow ADUs before 2021; the row's 2017 date is a short-term-rental ordinance (agrees with Ben's note).
- **MN Forest Lake city**: MN-2721770-adu-2023: section cited as 153.092(B); Ord. 719 inserts the standards as §153.096(B) (later renumbering possible). Coverage should note that ADUs are confined to rural A (detached, 5+ acres) and A/RR (internal) lots, not the urban single-family districts.
- **MN New Brighton city**: MN-2745430-adu-2024: effective_date coded 2024-09-24 (adoption); the affidavit of publication bound with the signed ordinance gives publication 2024-09-28, and the ordinance takes effect on publication.
- **MN Hugo city**: MN-2730392-adu-2011: Ord. 2011-459 (2011-10-03) is the source of §90-277 per the code history note, confirming the second coder (not Ord. 2011-460, 2011-11-07). Also, 2011-459 created garage-only, non-rental 'accessory dwelling units' in rural districts; the CUP/owner-occupancy rules belong to the older §90-203 accessory-apartment section, so the row mixes two provisions. Rule predates 2016: not an in-window event.
- **MN Rogers city**: MN-2755186-adu-2020: adu_detached_allowed is blank; the AG and R1 district tables say accessory buildings shall not contain dwelling units, and 125-89 bars dwellings in accessory buildings, so detached ADUs appear not allowed (detached=false).
- **MN Mounds View city**: MN-2744530-adu-2025a: treated as a first ADU adoption, but the city's 2025 staff report says internal ADUs were already a permitted accessory use (and additions a conditional use) before Ord. 1042; Ord. 1042 only rewrote (I)(1) and added the owner-occupancy covenant. ADUs predate 2025 (first date unknown).
- **MN Mounds View city**: MN-2744530-adu-2025b: coded by_right=False for the whole place; internal ADUs stayed permitted after Ord. 1045, only detached ADUs need a CUP.
- **MN Orono city**: No reform row for the pre-2022 guest apartment (permitted, internal, nonrental) / guest house (CUP) regime; it was in force 2016-2022.
- **MN Orono city**: MN-2748580-adu-2022: owner_occ, parking, size, adus_per_lot blank; ordinance gives no owner-occupancy clause (separate rental banned), 2 parking spaces, 50% of primary floor area, 1 per lot, 1-acre minimum lot.
- **MN Hopkins city**: MN-2730140-adu-2022: owner_occ=True is right only for N1/N2 zones; worth a coverage note.
- **MN Hopkins city**: No row records the pre-2022 'no ADU' rule; the former Section 530 confirms none was allowed.
- **MN Medina city**: MN-2741480-adu-2011: second coder's 1,400/1,600 sq ft caps and 30-day rental term are the post-2024 (Ord. 731) text; 2011-2024 cap was the lesser of 750/1,000 sq ft (by bedrooms) or 40%.
- **MN Medina city**: MN-2741480-adu-2024 (second-coder sheet): said no 2024 ADU amendment confirmed; the code history lists Ord. 731 (2024-08-20) amending § 826.98 on ADUs, and the text changed as above. It is a real (minor) ADU amendment.
- **MN Baytown township**: MN-2716304132-adu-2018: coded by_right=False, but the Certificate of Compliance is issued by the Zoning Administrator when the use complies (Ch. 1 §8.3), with no hearing: by right under the coding definition. Also the 2018-06-05 date is the county overlay code's; the township rule predates 2018-05-07.
- **MN Denmark township**: MN-2716315688-adu-2022: effective_date 2022-12-08 is only the compiled code's date; the rule predates it (second coder already says so). by_right=True agrees (administrative Certificate of Compliance).
- **MN Minneapolis city**: MN-2743000-adu-2014: effective_date coded 2014-12-05 (adoption); proceedings show publication 2014-12-13, which is the effective date under the charter's publish-to-take-effect practice.
- **MN Minneapolis city**: MN-2743000-adu-2014: max_sqft 800 is right for internal/attached, but detached cap was 1,000 sq ft incl. parking (confirmed in 2014-Or-120 §537.110(9)b, primary).
- **MN Minneapolis city**: MN-2743000-adu-2016: ordinance number is 2016-060 (second coder); effective date still unknown.
- **NC Greensboro city**: NC-3728000-adu-2024: coding_notes say 'ADUs per lot not stated' — §30-8-11.2(C) says only one per lot (adus_per_lot=1).
- **NC Greensboro city**: NC-3728000-adu-2024: component says '(400 sq ft minimum removed)' — correct, but the pre-2024 cap was 30% of the house (not stated in row); no pre-2024 row exists: owner_occ=True and 1 parking space applied 2016-2024.
- **NC Cary town**: NC-3710740-adu-pre2019: parking coded parking_min_per_unit=1; in the most common single-family zones only the UDU was allowed, which needed 4 spaces total (2 beyond the house), so 'depends'/2 for those zones.
- **MN Rochester city**: MN-2754880-adu-2023 (only row): misses the pre-2023 rules. The 2016 LDM already allowed internal 'accessory apartments' (owner-occupied, 600 sq ft, 1 parking space) in R-2 and higher (not R-1), detached ones in CN-NR, and R-2x ADUs from 2019. The 2023 row is a coverage/size expansion, not a first ADU rule.
- **MN St. Louis Park city**: MN-2757220-adu-2020: ordinance is Ord. No. 2596-20 with code-history date 10-19-20 (primary, Wayback code supplement); coded 2020-11-13 rests on an architect's release. 10-19-20 may be adoption, 11-13 publication/effect - unresolved.
- **MN St. Louis Park city**: MN-2757220-adu-2020: owner_occ=True is only an initial-construction requirement (§36-162(e)(4)), not continuing.
- **MN St. Louis Park city**: MN-2757220-adu-2020: coverage was R-1, R-2 and R-3 single-family lots; from 2025 N-1/N-2.
- **MN Golden Valley city**: MN-2724308-adu-2022: min_lot_sqft coded 10000, but that minimum applies only to detached ADUs; internal/attached ADUs have no lot minimum found (coded 'none' here with the detached rule in the note).
- **MN Golden Valley city**: MN-2724308-adu-2022: row has no later version; Ord. 812 (2025-12-16) removed the extra parking space (parking 1 → 0).
- **MN Golden Valley city**: Ordinance number: 2022-11-01 council agenda names the ADU ordinance No. 745 (No. 746 was the 2023 fee schedule), supporting 745 over the code history's 746.
- **MN Mound city**: MN-2744476-adu-2024: coverage lists R-1, R-1A, R-2 'accessory use' plus MU-D/MU-C; agrees. min_lot_sqft blank in the row: the code sets no ADU-specific minimum ('none'). No conflicts on core fields.
- **MN Cedar Lake township**: MN-2713910450-adu-2010 and -2025: by_right coded False. Attached ADUs are an Administrative Use decided by the Planning Department with no hearing (§2-8-4), which meets the by_right definition; only detached ADUs need an IUP. Suggest by_right=True with a note (detached not by right).
- **MN Cedar Lake township**: MN-2713910450-adu-2010 and -2025: min_lot_sqft=217800 codes the detached-only 5-acre rule; attached ADUs have no ADU lot minimum. Suggest 'none' with the 5-acre detached rule in the note (or keep 217800 if the panel codes the stricter type).
- **MN Cedar Lake township**: MN-2713910450-adu-2010: missing intermediate version — caregiver occupancy added by 2020-08-18 (Rev. #2); no core-field change, so no new row strictly needed.
- **MN Helena township**: MN-2713928322-adu-2010 and -2025: by_right coded False. Attached ADUs are an Administrative Use decided by the Planning Department with no hearing (§2-8-4), which meets the by_right definition; only detached ADUs need an IUP. Suggest by_right=True with a note (detached not by right).
- **MN Helena township**: MN-2713928322-adu-2010 and -2025: min_lot_sqft=217800 codes the detached-only 5-acre rule; attached ADUs have no ADU lot minimum. Suggest 'none' with the 5-acre detached rule in the note (or keep 217800 if the panel codes the stricter type).
- **MN Helena township**: MN-2713928322-adu-2010: missing intermediate version — caregiver occupancy added by 2020-08-18 (Rev. #2); no core-field change, so no new row strictly needed.
- **MN Jackson township**: MN-2713931580-adu-2010 and -2025: by_right coded False. Attached ADUs are an Administrative Use decided by the Planning Department with no hearing (§2-8-4), which meets the by_right definition; only detached ADUs need an IUP. Suggest by_right=True with a note (detached not by right).
- **MN Jackson township**: MN-2713931580-adu-2010 and -2025: min_lot_sqft=217800 codes the detached-only 5-acre rule; attached ADUs have no ADU lot minimum. Suggest 'none' with the 5-acre detached rule in the note (or keep 217800 if the panel codes the stricter type).
- **MN Jackson township**: MN-2713931580-adu-2010: missing intermediate version — caregiver occupancy added by 2020-08-18 (Rev. #2); no core-field change, so no new row strictly needed.
- **MN St. Lawrence township**: MN-2713957184-adu-2010 and -2025: by_right coded False. Attached ADUs are an Administrative Use decided by the Planning Department with no hearing (§2-8-4), which meets the by_right definition; only detached ADUs need an IUP. Suggest by_right=True with a note (detached not by right).
- **MN St. Lawrence township**: MN-2713957184-adu-2010 and -2025: min_lot_sqft=217800 codes the detached-only 5-acre rule; attached ADUs have no ADU lot minimum. Suggest 'none' with the 5-acre detached rule in the note (or keep 217800 if the panel codes the stricter type).
- **MN St. Lawrence township**: MN-2713957184-adu-2010: missing intermediate version — caregiver occupancy added by 2020-08-18 (Rev. #2); no core-field change, so no new row strictly needed.
- **MN St. Paul city (holdout: rules only)**: MN-2758000-adu-2018: coded min_lot_sqft=5000; under 18-28 the 5,000 sq ft minimum applies only to detached ADUs (internal/attached: none). The row's coverage note says this; just flag that min_lot_sqft codes the detached rule.
- **MN St. Paul city (holdout: rules only)**: MN-2758000-adu-2016: second coder left 2016-11-16 unresolved; the city's own ADU page (Wayback 2017-01-26) states 'effective as of November 16, 2016', confirming the coded date.
- **MN Richfield city**: MN-2754214-adu-2015: adu_detached_allowed coded False (adjudicated from handout 'standalone units are not allowed'), but code §514.05 Subd. 8 allows 'Internal, attached, and detached' ADUs and (l) permits detached ADUs as part of an approved accessory garage structure (a detached garage apartment). Under the field definition (false = attached/internal only) this is detached=true with a garage-only limit.
- **MN Richfield city**: MN-2754214-adu-2015: min_lot_sqft=6000 — the ADU rule requires only current minimum lot width and depth, not area; and 6,000 sq ft appears to be the post-Bill 2023-2 R lot area (pre-2023 appears 6,700). Recommend min_lot_sqft blank with a width/depth note.
- **MN Richfield city**: MN-2754214-adu-2015: handout cited as 7/2015 in coding notes; the copy I could open (Wayback 2026) is dated 05/2021.
<!-- ws-adu-rules:end -->
