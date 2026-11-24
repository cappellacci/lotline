### LB-NNN · 2026-11-15 · Rules: ADU rules for the largest uncoded places in Minnesota and Ohio
- **Question:** What are the ADU rules (2016 to today) in the places with no coded rule that carry the most predicted
  added ADUs, and why did Blaine read as uncoded?
- **What I did:**
  - Ranked the gut check's `rule_class == "unknown"` places by `adu_permits_added_mean` and researched down each
    state's list until 20 were coded (40 places coded, 21 skipped with reasons).
  - Ohio county remainders: established county vs township zoning and township shares (Census 2020 housing units);
    coded only where one code governs most homes (Franklin, Miami).
  - Blaine: the 2025 moratorium row had status `suspended`, which every engine filter drops; recoded it as an
    in-force explicit no-ADU row ending at Ord. 26-2601 (2026-03-16) and added the 2026 rule.
  - Family-only or no-rental units coded as no ADU (Fort Worth convention), at the ADU session's request.
- **Inputs:** `reports/adu-gut-check/places.csv`; public municipal/county codes (Zoneomics mirrors, city/county PDFs,
  Wayback, news); Census 2020 DHC; conventions from `docs/research/adu-coverage-fix-2026-11.md` (PR #440).
- **Outputs:** `config/reforms/oh.csv` (+20 rows), `config/reforms/mn.csv` (+24 rows, Blaine moratorium row
  changed); `docs/research/adu-uncoded-rules-2026-11.md`; `reports/adu-coverage-audit/` rerun; place whitelist in
  `tests/states/{oh,mn}/test_reforms.py`.
- **Findings:**
  - The coded places hold 23.5% of Ohio's and 30.8% of Minnesota's uncoded added ADUs. 27 of the 40 have an explicit
    no-ADU rule for all or part of the period (Akron, the largest, has no ADU use at all).
  - 18 Ohio county remainders (206 of Ohio's 776 uncoded added ADUs) are zoned by many townships and can't be one rule.
  - The coverage audit shows no new blank rows (blank 4 → 4).
- **Decisions:** proposed for HANDOFF: (1) a citywide ADU moratorium is coded as an in-force no-ADU row, not
  `suspended`; (2) family-only / no-rental units coded as no ADU (Fort Worth convention), applied to 6 rows here.
- **AI:** Claude subagents did the research and an independent second pass re-opened every source to check the
  quote and key coding; Claude applied the corrections, wrote the rows with a script that appends without touching
  existing rows (CSV round trip checked byte-identical), and checked that every coded place has a live rule at the
  2025 origin. `pytest tests -k reform` 99 passed; `compliance_check.py` 0 FAIL.
- **Open / next:** ADU session refit. Rows that start after 2016 leave earlier years uncoded (10 places). Researched
  extras (Massillon, Aurora, Stow, Isanti, Wright, Douglas, Owatonna, Brooklyn Center …) are in the shared notes
  folder for a later round.
