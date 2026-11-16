### LB-NNN · 2026-11-16 · ADU · D-099 result: first-years uptake

- **Question:** do places that first allow ADUs build less in their first five years? Ben accepted D-099
  ("I accept D-099").
- **Outputs:** `reports/adu-new-rule/` (profiles, held-out tables, summary, run log, `results.html`);
  `scripts/dev/adu_new_rule_page.py`; page https://claude.ai/artifact/GZoQ3mG5iVvKhRzwQGVLEb; the D-099
  result in `docs/analysis_plan.md`.
- **Result:** ν̂ 0.75 (0.70–0.85), but no held-out gain (−0.11, 2 SE 1.86), so ν stays 1 and config is
  unchanged. A first-years discount wouldn't close the Dallas and Fort Worth gap anyway (×0.77).
- **What Claude did:** ran the accepted script (profile, leave-one-place-out held-out check, three
  sensitivities) and built the page.
- **How it was checked:**
  - the unknown placeholder years were cut, as in the run log;
  - ν = 1's profile row matches the D-096 fit (θ 0.000240, α 1.439, core +1.670);
  - acceptance was committed (7fc974c2) before the run.
