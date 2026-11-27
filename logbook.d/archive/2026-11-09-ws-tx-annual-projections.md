### LB-NNN · 2026-11-09 · Engine: Texas housing need from the Center's annual state totals
- **Question:** Can Texas's household growth use its published 2026 and 2031 instead of interpolating to 2040,
  and why did its low and high 2030 differ by 0.03%?
- **What I did:** Ben downloaded the Texas Demographic Center's annual state totals for all three scenarios
  (Projections Download Tool). I registered the file with `lotline manifest register` (source
  `state_pop_projections`) and compared it with the stored points. Mid matches exactly. Low and high differ
  from the figures transcribed under D-057 by 1,456 to 9,210 people, but agree with the Center's projections
  table, so the earlier transcription was off. `scripts/dev/housing_need.py` now uses the file's 2025, 2026,
  2030 and 2031 for every scenario. Texas: 681,001 households, range 583,510–837,656 (was 675,323,
  578,694–835,119). The D-061 item-2 note in `docs/analysis_plan.md` is updated.
- **Outputs:** `scripts/dev/housing_need.py`; `config/params/housing_need.yaml`; `docs/model_and_assumptions.md`
  (parameter table); `docs/analysis_plan.md`; `tests/test_housing_need_window.py`.
- **How Claude helped and how it was checked:** Claude (Claude Code) compared the file with the stored and
  table values, updated the script and regenerated the YAML. Checked by hand: 1,870,161 people × 0.3641 ≈
  681,000 households. Ruff, the need tests and `compliance_check.py` (0 FAIL) pass. No model run was made.
