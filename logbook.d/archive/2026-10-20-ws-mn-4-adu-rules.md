### LB-NNN · 2026-10-20 · Policy analysis: WS-MN ADU rule details (sizes, parking, zones, none rows)
- **Question:** What exactly did Minneapolis's ADU rules allow since 2014, and what are the ADU rules (or their
  absence) in the rest of Minnesota's 20 largest places, coded so `scenarios/adu.current_rules` can class them?
- **What I did:**
  - Three research subagents read ordinances, code history notes (Zoneomics mirror where city sites, Municode and
    American Legal blocked bots; Wayback where allowed), the St. Paul Legistar API and city documents.
  - `config/reforms/mn.csv`: Minneapolis rows filled (800 sq ft attached/internal, no ADU parking, owner occupancy
    for all ADUs until 2021-03-06) plus a 2016 detached-size amendment and the 2023 zoning-code row; St. Paul sizes,
    lot minimums, parking and Ord. 21-27; details for nine suburban rules; first rules for Bloomington and Roseville;
    new rows for Rochester, Duluth, St. Cloud, Lakeville, Burnsville, Richfield, Cottage Grove; six "NO ADU RULE"
    rows (`adus_per_lot = 0`). 24 → 43 rows.
  - Classed every place with `scenarios.adu.current_rules` at 2016-07-01, 2020-07-01 and 2026-10-20.
- **Inputs:** sources listed per row; `src/lotline/model/scenarios/adu.py` (#162, #164).
- **Outputs:** `config/reforms/mn.csv`, `tests/states/mn/test_reforms.py`.
- **Findings:** Minneapolis 2014-2021 is "partial" only because of owner occupancy (size ≥ 800 sq ft, no ADU parking,
  detached allowed, by right); Handbook-equivalent from 2021-03-06. St. Paul partial 2016-2022, Handbook-equivalent
  from 2022-03-05. Today 4 of the 20 largest are Handbook-equivalent (Minneapolis, St. Paul, Bloomington, Edina),
  6 have none, the rest are partial. Plymouth 2002 and Burnsville 2018 class as Handbook only because their narrow
  limits sit in coverage / lot minimum, not in the rubric fields.
- **Decisions:** none new; low-confidence dates flagged in `coding_notes`.
- **AI:** Claude and research subagents found and read sources; every unverified date or attribution is flagged.
- **Open / next:** ordinance dates for Burnsville, Richfield, Duluth's ADU start, Cottage Grove's origin, Lakeville's
  2025/2026 change; Minneapolis 2023 vs 2025 attribution of the detached-ADU edits.
