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
