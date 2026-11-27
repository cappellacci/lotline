### LB-NNN · 2026-11-05 · validation · Release the scored V9 holdout so Oregon's full data can be built

- **Question:** V9 is frozen (#298) and scored (#299, #301). Ben said "start it" for the full Oregon build and
  pooling, and chose to release the holdout with a dated field rather than delete it.
- **Outputs:**
  - `Holdout.released_on` and `released_note` (`src/lotline/config/__init__.py`), a shared-contract change
    approved by Ben in chat on 2026-11-05;
  - `holdout.still_blind` and `check_release` (`src/lotline/validation/holdout.py`): the filter, the central
    leak guard, national state totals and V0's blocked years skip released tests;
  - `config/states/or.yaml`: `V9-OR-TRANSFER` released on 2026-11-05 (Ben's decision);
  - tests in `tests/core/test_holdout.py`.
- **Design:**
  - A released test stays in the registry, so `scripts/dev/v9_or_score.py` still reruns with `unblind`.
  - A release is refused unless the frozen prediction file exists. Only the file is checked, not its git
    history, because CI and judges' clones are shallow; the release itself is a reviewed config change.
  - A release date before the outcome window opens, or without a note, is rejected.
- **What Claude did and how it was checked:** wrote the change and the tests (release lifts the filter only
  with a freeze present; refused without one; validation of date and note; guard and state totals follow the
  release; the real Oregon config is released and its freeze is in the repo). The BPS state-totals test now
  pins the blind fixture instead of the real config. Full suite, ruff and `compliance_check.py` run.
- **Next:** rebuild Oregon's tables from `main` (`lotline fetch --state OR`), then add OR to `REFORM_STATES`
  and refit (WS-OR step 8).
