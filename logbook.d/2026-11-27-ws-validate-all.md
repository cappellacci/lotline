### LB-NNN · 2026-11-27 · review · One command for the validation ladder

**Question:** Where does a judge see every validation step, and which ones can they run?

**Outputs:**
- `src/lotline/validation/ladder.py` (new): every step in one list.
  - The checks a user runs: V0 data gaps and V1 baseline backtest.
  - The frozen blind tests: V5 St. Paul and Charlotte, V8 Wisconsin and V9 Oregon. Each has its freeze
    file, its score report and the script that scored it.
- `src/lotline/cli.py`:
  - `lotline validate` lists the ladder with each step's status: frozen at which commit, and scored where.
  - `--step V1` runs the backtest.
  - `--state XX` still runs V0, as the guide and the app say.
  - A frozen test is reported, never rescored: scoring needs the released holdout.
- `tests/core/test_validate_ladder.py` (new).

**What Claude did:** Worked modularity-review finding 6 (2026-11-27). Left out finding 5, the four copies of
D-040's verdict that disagree when the prediction and the outcome are both 0. One rule would change how
scored blind tests read, which is Ben's decision.

**Checked:** fast tier passed; ruff clean; compliance 0 FAIL.
