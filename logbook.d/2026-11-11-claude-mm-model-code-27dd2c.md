### LB-NNN · 2026-11-11 · WS-MM: model code for D-082 §1, §1b and §5 (proposed; code only, nothing fitted)
- **Question:** can the D-082 model (event-setting-row tag rule, standards dose class S, level component L,
  challengers C1, C3, C4 and §5's choosing rule) be written and proven on synthetic fixtures before Ben
  approves D-082 and any run?
- **What I did:**
  - `rule_tags.dropped_places(rule="event_setting_row")`: a tag drops a place only on the row that sets its
    first in-window cap rise (`event_setting_rows`, `cap_in_force`). The old reading stays the default.
  - `rule_tags`: a `[standards]` flag, plus `always_allowed_places` and `none_places`.
  - In `calibrate_mm`: `Event` with dose class `cap` or `S`, `standards_classes`, `standards_year`,
    `classify_event`, `retarget_events` and `standards_variant` (S excluded, S dose 1).
  - The level model: `level_rate` (state-band, then band pool, then all), `level_places` and `fit_level`.
  - Challengers: C1 `not_yet_treated_series`, C3 `conditional_z` (fitted with `fit_capacity`), and C4 as an
    optional lognormal prior on θ in `fit` (`log_prior`, `level_prior`).
  - §5's rule: `paired_delta` and `select_model`.
  - `[standards]` added to the start of Houston's `TX-4835000-missing_middle-2023` notes. Four method
    constants added to `config/params/mm.yaml`, sourced "D-082 (proposed)".
  - `scripts/dev/calibrate_mm_d082.py` wires the five-state fit set.
- **Inputs:** `config/reforms/*.csv`. For `--dry` only: the processed panel tables, read for structure. No
  counts were printed and nothing was fitted.
- **Outputs:**
  - `src/lotline/model/calibrate_mm.py`, `src/lotline/model/rule_tags.py`;
  - `tests/model/test_calibrate_mm_d082.py`, `tests/model/test_rule_tags.py` (5 new tests);
  - `scripts/dev/calibrate_mm_d082.py`, `config/params/mm.yaml`, `config/reforms/tx.csv` (one tag).
- **AI:** Claude Code wrote the code and the hand-worked tests. Checks:
  - existing and new MM tests pass;
  - `fit_level` recovered a simulated θ_L inside its 90% interval for 6 of 6 seeds;
  - `compliance_check.py` shows 0 FAIL;
  - `--dry` was run once (structure only, output in the PR).
  - No full run, no download, no `--unblind`. St. Paul, Ramsey County, Charlotte and Mecklenburg are
    asserted absent.
- **Open / next:** Ben approves (or amends) D-082. Then the full run, with his go-ahead. Tests A–C need their
  own code before `--tests-passed` can feed §5's rule. Choices made without Ben are listed in the PR.
