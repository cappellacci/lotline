### LB-NNN · 2026-10-20 · Policy analysis: NC ADU rules, partial (S.L. 2026-59 per city; Raleigh, Wilmington, Charlotte)
- **Question:** Which ADU rule applied in NC's 20 largest places, year by year since 2010?
- **What I did:**
  - Replaced the statewide S.L. 2026-59 row (GEOID 37, which the ADU scenario would apply to every NC place) with 19
    per-city rows plus Wake Forest and Holly Springs as `pending` (sensitivity only, decision 1).
  - Four research subagents covered the 20 places plus Wilmington, Hickory, Salisbury, Statesville; the shared
    search budget (200 calls) ran out early and most city code hosts block bots. Coded only rows from pages opened:
    Raleigh's 2019 ADU overlay (not by right; date inferred), Wilmington LDC-7-424 (2024-05-21), Charlotte petition
    2012-067A (2012-07-16, ends at the UDO). Unopened leads are listed in the PR.
  - Checked each place's class with `scenarios/adu.current_rules` at 2016, 2021, 2026 and 2027.
- **Outputs:** `config/reforms/nc.csv`, `tests/states/nc/test_reforms.py`.
- **Findings:** at 2026-01-01 only Charlotte, Raleigh, Greensboro, Durham and Wilmington have a coded rule (all read
  as Handbook-equivalent, several with uncoded fields); the other 15 read as "none" because they are not coded, not
  because they ban ADUs. A research subagent fetched three Charlotte UDO PDFs from a host whose robots.txt disallows
  all crawling; it deleted them unread and nothing here uses them.
- **AI:** Claude (WS-NC) and four research subagents; rows single-coded (`claude`).
- **Open / next:** Ben to decide on the search budget and/or modelling "not coded" as unknown.
