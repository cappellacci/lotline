### LB-NNN · 2026-10-21 · Policy analysis: NC rules and fees from direct fetches, Ben's lookups and UDOs (NC thread 10, S4–S6)
- **Question:** which dated ADU and missing-middle rules, and fees by year, can be coded for the 40 largest NC
  places from official pages, Ben's lookups and the codes he downloaded?
- **What I did:**
  - One direct fetch of an official page per place for the largest uncoded places; checked all 40 city homepages
    for script access (25 answer HTTP 403, 2 not at all); wrote fill-in tables for Ben, largest first.
  - Raleigh fees FY2022–FY2026 from four Internet Archive copies of the fee guide (overwritten yearly at one URL),
    read with pypdf, each value from that year's own column.
  - Recorded Ben's 67 dated lookup claims (search summaries; two with links) in `manual-lookups.csv`; moved his
    11 downloaded PDFs out of the repo to `~/lotline-data/manual/nc_udos/` (checksums matched).
  - A sub-agent read the PDFs (read-only, verbatim quotes with pages); I re-checked the two oddest findings myself
    (Hickory's size rule, Garner's parking) and coded the rows below.
- **Inputs:** Asheville's UDO text-amendments page; Raleigh Development Fee Guide (archive.org copies); Ben's
  workbook `NC ADU + MM.xlsx`; UDOs/LDCs of Burlington, Concord, Garner, Hickory, Matthews, Rocky Mount,
  Thomasville, Asheboro, Jacksonville, Wake Forest; Holly Springs Ord. 26-07; Census 2020 place populations.
- **Outputs:** `config/reforms/nc.csv` (Asheville ADU and missing middle 2026; ADU rows for Burlington, Garner,
  Hickory, Matthews, Rocky Mount, Jacksonville, Wake Forest; missing middle for Burlington, Garner, Hickory, Wake
  Forest), `config/fees/nc.csv` (45 Raleigh rows), `docs/research/ordinances/` (three fill-in CSVs, 67 lookup rows,
  README).
- **Findings:**
  - Most lookups and codes show a code's adoption date or today's rule, not when ADUs or duplexes first became
    allowed; rows dated only that way carry `[earliest-known]` in `coding_notes`.
  - Jacksonville does not allow ADUs (coded 0 per lot); Matthews and Jacksonville do not allow duplexes in their
    single-family districts (recorded, not coded). The codes contradicted two lookups (Hickory's ADU section tags;
    Thomasville's §22-43 is the cable TV chapter); Rocky Mount's ADU section dates to 2005.
  - Raleigh's per-home impact fees rose about 3–7% a year; the sewer capital facility fee fell in FY2023.
- **Decisions:** proposed for WS-CORE (contract change): a `date_basis` field (adoption / earliest_known) on reform
  rows. Flag for thread 2: `scripts/dev/ordinance_records.py` rewrites `config/fees/nc.csv`.
- **AI:** Claude Code (Opus 5.5) and one sub-agent fetched, extracted and coded; quotes are verbatim; source URLs
  for the downloaded codes are city homepages until Ben supplies the download links.
- **Open / next:** download links; the 12 large and 12 under-50k places Ben is collecting; Concord, Asheboro,
  Thomasville and Holly Springs need fuller files.
