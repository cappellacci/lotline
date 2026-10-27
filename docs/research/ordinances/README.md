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
