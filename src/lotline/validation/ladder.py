"""The validation ladder in one place, for `lotline validate`.

Two kinds of step:

- **Checks you run** on your own data: V0 (data gaps against the Census permit totals) and V1 (the baseline
  backtest on holdout-filtered data). `lotline validate --step V0|V1` runs them.
- **Blind tests already frozen** (V5 St. Paul and Charlotte, V8 Wisconsin, V9 Oregon): a prediction made and
  committed to `results/frozen/` before its outcomes were opened, then scored once by a maintainer after the
  holdout was released. `lotline validate` lists each with its freeze commit, where its score report is, and
  the script that scored it. Scoring is never rerun from here: it needs the released holdout
  (`check_unblind`), and a frozen prediction is never remade.

docs/research/lotline-validation-plan.md is the plan behind the ladder.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    runnable: bool  # True: `lotline validate --step <id>` runs it
    freeze: str | None = None  # results/frozen/<file> for a blind test
    report: str | None = None  # where its score report is
    scored_by: str | None = None  # the maintainer script that scored it


STEPS = (
    Step(
        "V0", "Data gaps: each state's permits against the Census permit survey", True, report="reports/<st>/"
    ),
    Step("V1", "Baseline backtest: forecast held-out years from earlier ones (holdout-filtered data)", True),
    Step(
        "V5-STPAUL",
        "Blind test: St. Paul, MN missing-middle reform",
        False,
        "V5-MN-STPAUL.json",
        "reports/v5-stpaul/",
        "scripts/dev/v5_stp_score.py",
    ),
    Step(
        "V5-CHARLOTTE",
        "Blind test: Charlotte, NC missing-middle reform",
        False,
        "V5-NC-CHARLOTTE.json",
        "reports/v5-charlotte/",
        "scripts/dev/v5_clt_score.py",
    ),
    Step(
        "V8",
        "Blind test: Wisconsin from the other states only (transfer)",
        False,
        "V8-WI-TRANSFER.json",
        "reports/wi/",
        "scripts/dev/v8_score.py",
    ),
    Step(
        "V9",
        "Blind test: Oregon from the other states only (transfer)",
        False,
        "V9-OR-TRANSFER.json",
        "reports/v9-oregon/",
        "scripts/dev/v9_or_score.py",
    ),
)


def get(step_id: str) -> Step:
    for s in STEPS:
        if s.id.upper() == step_id.upper():
            return s
    raise KeyError(step_id)


def status(step: Step, repo: Path = REPO) -> str:
    """One plain line: runnable, or frozen at a commit and scored (report present) or not yet."""
    if step.runnable:
        return f"run it: lotline validate --step {step.id} [--state XX]"
    frozen = repo / "results" / "frozen" / step.freeze
    if not frozen.is_file():
        return "not frozen yet"
    commit = str(json.loads(frozen.read_text(encoding="utf-8")).get("commit", ""))[:7]
    scored = step.report and (repo / step.report).is_dir() and any((repo / step.report).iterdir())
    where = f"scored: {step.report}" if scored else "frozen, not scored yet"
    return f"frozen at {commit or '?'}; {where} (by {step.scored_by})"
