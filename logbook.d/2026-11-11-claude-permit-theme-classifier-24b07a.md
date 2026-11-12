### LB-NNN · 2026-11-11 · CODE: the shared permit-to-theme classifier (D-082 §6), code and synthetic tests only
- **Question:** how can every processed permit get exactly one of ADU, new 2–4 unit building, conversion or
  other, so that the ADU fit and the missing-middle counts never count the same permit twice? The cases are
  Austin's post-HOME two-family ADUs (causal diagram §6.6) and Rochester's code 103 house + attached ADU
  (`reports/mn/adu-coverage-and-undercount.md` §4.1).
- **What I did:**
  - Wrote `src/lotline/build/permit_theme.py`, a pure function over the `schemas.Permits` columns. It returns
    `permit_theme` and `theme_rule`, with the precedence written in the module docstring: demolition →
    legalized ADU (D-080) → no new home → ADU signal (the ADU fit's own `_is_adu` test) → the Austin HOME
    "TWO UNIT RES" source rule → conversion → U2/U3_4/DTQ → other.
  - Wrote `tests/core/test_permit_theme.py` (25 tests) on hand-built rows. They cover:
    - the Austin two-family ADU;
    - both rows that the Rochester 103 adapter emits;
    - a 103 kept as one U2 row that names an ADU;
    - a Raleigh 103 duplex (D-074);
    - a fourplex and a Met Council DTQ;
    - a house converted to a triplex;
    - a garage converted to an ADU;
    - legalized ADUs in three forms;
    - a 5+ building, demolitions, the edges of the Austin rule, and switching source rules off.
  - Opened #404 (`contract-change`) for the wiring.
- **Inputs:** code and docs only. No data was read, and the classifier was not run on real permits.
- **Outputs:** `src/lotline/build/permit_theme.py`, `tests/core/test_permit_theme.py`, issue #404, and the PR.
- **Findings:**
  - Rochester's adapter already splits a 103 house + ADU into SFD and ADU rows, so it needs no source rule.
  - Rochester and Minneapolis keep a legalized ADU as a new 1-unit row, while the shared parser gives it 0
    units (D-080). The classifier reads an optional `is_legalization` column, proposed in #404.
  - `estimate_mm.local_counts` does not filter demolitions today.
- **Decisions:** none recorded in HANDOFF. Proposed in #404: compute the theme on read, not stored in the
  schema; an optional `is_legalization` column; a hand check of the Austin rule before wiring.
- **AI:** Claude Code wrote the module, the tests and the issue. Checked by `pytest` (25 new tests pass, plus
  `test_build_permits`), `ruff`, and `compliance_check.py` (0 FAIL). The tests also assert that the
  classifier's ADU test and 2–4 types match `scenarios.adu._is_adu` and `estimate_mm.MM_TYPES`.
- **Open / next:**
  - WS-CORE wires #404.
  - The before/after count by source × year waits for Ben's go-ahead (D-082 §9).
  - Austin rule hand check.
