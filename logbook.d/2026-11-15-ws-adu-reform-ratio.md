### LB-NNN · 2026-11-15 · ADU · Does the engine's reform ratio match real rule changes? (D-095)

- **Question:** the engine multiplies a place's own ADU rate by a ratio from its rules (D-093). Where coded rules
  changed while ADUs were counted, did permits move as that ratio says? Ben asked: "Test reform effect".
- **Outputs:**
  - `docs/analysis_plan.md` D-095 (method committed before any score, then its result);
  - `src/lotline/model/adu_reform_check.py` and `tests/model/test_adu_reform_check.py`;
  - `scripts/dev/adu_reform_ratio.py` and `_page.py`; `reports/adu-reform-ratio/`; page
    https://claude.ai/artifact/JggHUyaPLYuJxwMFBvMk6j.
- **Result:** "not shown either way". 10 events in 3 states; the ratio helps a little (+4.2, 2 SE 7.9). The best
  scaling of the ratio, b 1.3 (0.55–2.05), fits the engine and not "rules don't matter". Raleigh carries most of
  it. A coding mismatch: in 6 events the dose rises while the engine's rule share falls, mostly because newer rules
  are coded with a zoned coverage. Nothing to config.
- **What Claude did:** listed the events and model ratios (no outcomes), wrote and committed D-095, wrote the check
  with hand-worked tests, ran it offline, and built the page.
- **How it was checked:** unit tests (share path, event cut, draws, log score, b recovery, reading rule); the
  method commit precedes the scoring commit; ruff passes; the event list matches `joint_refit.events` on the fit
  set.
