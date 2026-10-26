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
- `tx-fee-lookups-todo.csv` (2026-10-26, Texas thread 12, S6): water/sewer and impact fees per home for the four
  Texas cities with permit data and Houston, plus Austin's parkland and meter fees. Austin's water/wastewater
  impact fees and street impact fee are coded in `config/fees/tx.csv`.
- `nc-fee-lookups-todo.csv` (same day): water/sewer and impact fees per single-family home for the 10 largest
  places other than Raleigh (Raleigh FY2022-FY2027 is coded in `config/fees/nc.csv`).
