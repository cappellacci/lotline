### LB-NNN · 2026-10-21 · Policy analysis: NC rules and fees, first pass (NC thread 10, S4–S6)
- **Question:** which of the 40 largest NC places can have dated ADU and missing-middle rules, and fees by
  year, coded from official pages reachable without web searching?
- **What I did:**
  - Tried one direct fetch of an official page per place for the largest uncoded places (Winston-Salem,
    Cary, Fayetteville, Asheville, Chapel Hill, High Point, Concord, Greenville), within Ben's cap (about one
    fetch per place, no search sweeps).
  - Checked every one of the 40 city homepages for script access: 25 answer with HTTP 403, 2 not at all.
  - Coded what I could read, and wrote fill-in tables for the rest (largest first).
  - Raleigh fees FY2022–FY2026: the city overwrites its fee guide at one URL, so earlier years came from four
    Internet Archive copies (one index query), read with pypdf; each value from that year's own column.
- **Inputs:** Asheville's UDO text-amendments page; Census 2020 place populations (PL 94-171).
- **Outputs:** `config/reforms/nc.csv` (Asheville missing middle and ADU rows, effective 2026-08-25),
  `docs/research/ordinances/nc-adu-lookups-todo.csv` (37 places), `nc-mm-lookups-todo.csv` (36 places),
  ordinances README;
  `config/fees/nc.csv` (45 Raleigh rows, FY2022–FY2026); `docs/research/ordinances/nc-fee-lookups-todo.csv`.
- **Findings:** Asheville adopted "Missing Middle Housing Amendments" (26-02460PZ) permitting duplexes
  citywide and loosening ADU rules, effective 2026-08-25 per the City's table. That is after the
  estimation window, but it is part of the current-rules baseline. Direct fetching is not a workable route
  for NC rule histories: most city sites block scripts, and Municode-style code hosts do too.
- **Findings (fees):** Raleigh's per-home impact fees rose about 3–7% a year (single-family open space $1,582 in
  FY2022 to $1,916 in FY2027); the sewer capital facility fee fell from $2,522 to $2,223 in FY2023 and has
  not changed since.
- **Decisions:** none. Flag for thread 2: `scripts/dev/ordinance_records.py` rewrites `config/fees/nc.csv`
  from pipeline records, so a rerun would drop these hand-coded rows.
- **AI:** Claude Code (Opus 5.5) fetched and coded; the Asheville quote was re-read verbatim on a second
  fetch of the same page before coding. Fields not stated on the page are blank (D-022).
- **Open / next:** Ben fills the two CSVs in a browser; confirmed rows get coded in a follow-up PR.
