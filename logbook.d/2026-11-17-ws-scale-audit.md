### LB-NNN · 2026-11-17 · Build: WS-SCALE task 1, where the code is specific to one state
- **Question:** Where does the code branch on a state, and which adapters do more than reshape data?
- **What I did:** grep over `src/lotline` for state codes, GEOIDs and `state ==` tests, plus a read of every
  state adapter (a Claude subagent read them; I spot-checked its findings in the source).
- **Outputs:** `docs/build/ws-scale-audit.md`; brief task 1 ticked.
- **Findings:**
  - Outside adapters, one real state branch remains (`mm_routes`: Oregon), plus five copies of state
    lists and holdout GEOIDs repeated in model code.
  - Two Oregon Metro lists disagree (23 vs 24 places).
  - Inside adapters, about a dozen unsourced shares and thresholds, several copied across files
    (`DISTRICT_SHARE` 0.95 three times, `MERGE` 0.20 three times, onemap tier cutoffs copied from params).
  - The brief's "Austin HOME ADU share" is a yes/no rule (`build/permit_theme.py`) plus a measured share
    (`mm_counts.py`), not a share in an adapter.
- **Decisions:** none. The Metro lists and an Austin range are for Ben.
- **AI:** Claude ran the sweep and wrote the list.
- **Open / next:** task 7 (crosswalks), task 8 (rules as data).
