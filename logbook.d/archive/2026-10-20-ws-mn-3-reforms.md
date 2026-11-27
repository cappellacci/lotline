### LB-NNN · 2026-10-20 · Policy analysis: WS-MN reform coding (config/reforms/mn.csv)
- **Question:** When did Minneapolis, St. Paul and the 20 largest metro suburbs adopt ADU and missing-middle rules,
  coded with the protocol §5.4 rubric?
- **What I did:**
  - Coded 24 rows against `schemas.Reforms`: Minneapolis (ADU 2014, owner-occupancy change 2021, three-unit
    amendment 2020, parking 2021, two 2040-plan injunction windows as `suspended` sensitivity rows); St. Paul (ADU
    2016 Green Line, 2018 citywide, 2022 Ord. 22-1, 2023 Ord. 23-43; H1/H2 missing middle 2023); 13 suburban ADU rows.
  - A research subagent read suburban code history notes (via the Zoneomics code mirror; city sites blocked bots),
    ordinance PDFs and council agendas; each row says which kind of source it rests on.
- **Inputs:** city amendment archive (Minneapolis Smartsheet), St. Paul project and ADU pages, news (FOX 9, MPR,
  KSTP, MinnPost, Planetizen), Bloomington ordinance PDF, Eagan agenda, Zoneomics code history notes.
- **Outputs:** `config/reforms/mn.csv`, `tests/states/mn/test_reforms.py`.
- **Findings:** Six of the 20 largest suburbs still have no single-family-zone ADUs (Brooklyn Park, Woodbury, Maple
  Grove, Eden Prairie, Shakopee, Coon Rapids): a never-treated pool. Several adoptions predate the 2016 start of ADU
  recording (Apple Valley 2003, Plymouth 2002 limited, Eagan 2014, Minnetonka 1986). Blaine rolled back detached ADUs
  in 2026.
- **Decisions:** two-coder rule: all rows are `single_coder`; Ben spot-checks.
- **AI:** Claude and a research subagent found and read sources; dates not seen in a source are flagged in
  `coding_notes`.
- **Open / next:** dates not found for Bloomington (~2009), Roseville (~2010), Richfield (2015), Burnsville (2018),
  Lakeville (2013/2014), Cottage Grove; injunction reversion date.
