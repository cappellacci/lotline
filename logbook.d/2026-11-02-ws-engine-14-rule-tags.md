### LB-NNN · 2026-11-02 · [engine] · How do the D-024 and D-025 panels read the data threads' date tags?
- **Question:** thread 14, task 1. The four `config/reforms/*.csv` files mark uncertain dates in
  `coding_notes` (`[predates]`, `[earliest-known]` or a blank adoption date, `DATE UNCONFIRMED`) and "none"
  rows (no ADUs; one home per lot), but no engine code read them. How should both panel builders read them,
  with the two sensitivities?
- **What I did:**
  - Wrote one helper, `src/lotline/model/rule_tags.py`: `flags` (per row: predates, earliest-known,
    unconfirmed, none row, event), `apply` (`[predates]` rules in force from 1990-01-01, before any panel
    year) and `dropped_places` (places whose in-panel event carries a dropped flag).
  - Used it in `estimate_mm.build_panel` (and so `adoption_year`) and `estimate_adu.build_panel`, which also
    feeds `pooled_adu`. New `drop_tags` option on both; dropped places are listed (`excluded["dropped by tag
    sensitivity"]`, `Panel.excluded_by_tags`).
  - Before the code: rebuilt Ohio's and Texas's `eligible_parcels` tables, which predated #252 (OH: 154 rows
    in 13 Montgomery places, Dayton 2020 45,399 -> 43,719 as in #252; TX: 1,964 rows in 198 places with 2019
    and 2025 rolls, median -0.8%, 5th-95th percentile -16% to +11%; Houston is on ACS and unchanged).
- **Inputs:** `config/reforms/{mn,nc,oh,tx}.csv`; `~/lotline-data/processed/{oh,tx}` (rebuilt, previous
  tables backed up outside the repo).
- **Outputs:** `src/lotline/model/rule_tags.py`; `src/lotline/model/estimate_mm.py`,
  `src/lotline/model/estimate_adu.py`; `tests/model/test_rule_tags.py` (10 tests).
- **Decisions:**
  - Proposed for HANDOFF: a `DATE UNCONFIRMED` row counts as an event at its coded date; engines also run
    without it (Ben, 2026-11-02).
  - Proposed: a tag sensitivity drops the whole place (neither treated nor a comparison), and only events
    that change a panel year count. Goes into the task 3 amendment entries.
- **AI:** Claude Code (Opus 5.5) wrote the helper, the wiring and the tests. Checked with hand-worked
  synthetic rows per tag, synthetic panels for both builders, the full suite (1,312 passed), ruff and
  `compliance_check.py` (0 FAIL). Two test-fixture mistakes and one wrong test expectation (an
  announcement year) were found by the tests and fixed. No model run; no panel built on real data.
