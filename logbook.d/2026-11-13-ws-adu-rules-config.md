### LB-fragment · 2026-11-13 · ADU rules · Put PR #417's ADU rule rows into config

- **Outputs:** `config/reforms/{mn,nc,oh,or,tx}.csv` (153 rows for 65 places replace 112 old local rows),
  `scripts/dev/apply_adu_rules_proposed_2026_11.py`; branch `ws/adu-rules-config`.
- **Why:** Ben accepted #417's rows on 2026-11-13 ("Yes, do both") after the version C run showed they help on
  their own (test C passes in all five states, Franklin roll check passes, 10 rule-change events in 3 states).
- **Open items kept as coded:** Wayzata before 2022 (no ADU), the six conflicts with old rows (proposed value),
  Ramsey's 2023 lot minimum, Austin HOME's date (2024-02-05).
- **HANDOFF:** proposed decision in the PR description.
- **What Claude did:** ran the apply script (state-law rows untouched; superseded rows end on the successor's date;
  coverage_zones carried over); checked the result equals the config the version C run read; ran tests and
  `compliance_check.py`.
