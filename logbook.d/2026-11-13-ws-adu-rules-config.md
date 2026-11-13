### LB-fragment · 2026-11-13 · ADU rules · Put PR #417's ADU rule rows into config

- **Outputs:** `config/reforms/{mn,nc,oh,or,tx}.csv` (153 rows for 65 places replace 112 old local rows),
  `scripts/dev/apply_adu_rules_proposed_2026_11.py`; branch `ws/adu-rules-config`.
- **Why:** Ben accepted #417's rows on 2026-11-13 ("Yes, do both") after the version C run showed they help on
  their own (test C passes in all five states, Franklin roll check passes, 10 rule-change events in 3 states).
- **Open items kept as coded:** Wayzata before 2022 (no ADU), the six conflicts with old rows (proposed value),
  Ramsey's 2023 lot minimum, Austin HOME's date (2024-02-05).
- **Source check (2026-11-13, Ben: "Yes, check each"):** a subagent re-read the sources for every overturned value
  (43, in 30 rows) and every moved date (35 replaced rows): `docs/research/ordinances/adu-rules-source-check-*.csv`.
  Values: 40 research, 1 config (Bloomington 960), 1 other (Lakeville parking 1), 1 unresolved (Rochester parking,
  config 0 kept). Dates: 9 research, 1 config (Bend 2016-03-18), 1 unresolved (St. Louis Park), 24 restructured.
  Four research values that reverse Ben's 2026-11-02 adjudications are held at Ben's value until he rules.
- **Config conventions:** https sources (local copies named in the notes), single-coder rows without coder_2,
  NO ADU RULE rows, unchanged hand-checked rows kept, same-ordinance rows keep their old ids, superseded versions
  end on the successor's date (MN test updated to allow it). Pinned tests updated with dated comments.
- **HANDOFF:** proposed decision in the PR description.
- **What Claude did:** ran the apply script (state-law rows untouched; superseded rows end on the successor's date;
  coverage_zones carried over); checked the result equals the config the version C run read; ran tests and
  `compliance_check.py`.
