### LB-NNN · 2026-11-08 · Engine: D-064 current rules are those in force by the end of the window's first year
- **Question:** With the 2027–2031 window (D-061), which coded rules count as "current" in the baseline?
- **What I did:** Ben chose "rules in force by window start" (end of 2027). I wrote D-064 before writing any code
  and before any run. Then I added the parameter `current_rules_window_years` = 1, the helper
  `baseline.rules_as_of` and its use in `adu.places_from_store`. I listed the 28 ADU rows that enter the
  baseline (NC 21, 19 of them S.L. 2026-59; TX 5; MN 2). I also classified the 26 affected places before and
  after, using the rules config only with no model run. That check found the effect is small: D-053 already
  counts partial rules in full, so only places that allowed no ADUs or had no coded rule move. Most of the
  movement is in one TX place. Two pointers were added to the D-061 entry: item 1 → D-064 and item 3 → #333.
- **Outputs:** D-064 in `docs/analysis_plan.md`; `config/params/baseline.yaml`; `src/lotline/model/baseline.py`
  (`rules_as_of`); `src/lotline/model/scenarios/adu.py`; `docs/model_and_assumptions.md` (the c row and the
  parameter table); tests in `tests/model/test_current_rules_date.py` and `tests/model/test_scenario_adu.py`.
  HANDOFF decision proposed in the PR description.
- **How Claude helped and how it was checked:** Claude (Claude Code) drafted the entry, code and tests. The
  hand-worked tests cover the date (2027-12-31; 2026-12-31 at the low value or with no lead) and a local
  "no ADUs" code being replaced by a state law in force 2027-01-15. The related test modules (532 tests),
  ruff and `compliance_check.py` (0 FAIL) pass. No model or scenario run was made.
