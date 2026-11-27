### LB-NNN · 2026-11-11 · WS-CORE: parser negation for "can not be used as second dwelling unit"
- **Question:** why did the 2026-11-11 rebuild count a Dallas storage-shed permit as a new ADU?
- **What I did:** the shared parser's negation guard (`_ADU_NEGATED` in `src/lotline/parse/permit_text.py`)
  needed "not (to be) used" and only ADU names, so "DETACHED STORAGE SHED- CAN NOT BE USED AS SECOND DWELLING
  UNIT" slipped through the new Rule 3b ("additional / second dwelling unit", #376). The guard now also takes
  "be" without "to", "cannot", and the Rule 3b names. Three synthetic test rows added to
  `tests/core/test_permit_text.py`.
- **Inputs:** one permit description seen in the rebuild report (`reports/adu-rebuild-2026-11-11.md`); the tests
  use hand-written strings, no data.
- **Outputs:** `src/lotline/parse/permit_text.py`, `tests/core/test_permit_text.py`.
- **Findings:** Dallas ADU permits should go back from 2 to 1 on the next rebuild. Only the gained/lost examples
  in the rebuild report were read; other sources were not searched for the same phrasing.
- **AI:** Claude Code found the miss, wrote the fix and tests, and ran pytest (1,976 passed), ruff and
  `compliance_check.py` (0 FAIL).
- **Open / next:** not merged; Ben to review. A rebuild of TX `dallas_permits` after merge picks it up.
