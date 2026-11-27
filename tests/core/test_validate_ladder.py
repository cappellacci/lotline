"""`lotline validate` lists the whole ladder and runs only the checks a user can run (review, 2026-11-27)."""

import json

from lotline import cli
from lotline.validation import ladder


def test_every_frozen_test_has_its_freeze_file_and_scorer():
    for step in ladder.STEPS:
        if step.runnable:
            continue
        assert (ladder.REPO / "results" / "frozen" / step.freeze).is_file(), step.id
        assert (ladder.REPO / step.scored_by).is_file(), step.id
        assert step.id.startswith(
            json.loads((ladder.REPO / "results/frozen" / step.freeze).read_text())["test_id"][:2]
        )


def test_status_says_frozen_and_scored(tmp_path):
    step = ladder.Step("VX", "a test", False, "VX.json", "reports/vx/", "scripts/dev/vx_score.py")
    assert ladder.status(step, tmp_path) == "not frozen yet"
    (tmp_path / "results/frozen").mkdir(parents=True)
    (tmp_path / "results/frozen/VX.json").write_text(json.dumps({"commit": "abcdef123456"}))
    assert ladder.status(step, tmp_path).startswith("frozen at abcdef1; frozen, not scored yet")
    (tmp_path / "reports/vx").mkdir(parents=True)
    (tmp_path / "reports/vx/score.json").write_text("{}")
    assert "scored: reports/vx/" in ladder.status(step, tmp_path)


def test_validate_lists_the_ladder_and_never_rescores(capsys):
    assert cli.main(["validate"]) == 0
    out = capsys.readouterr().out
    for step in ladder.STEPS:
        assert step.id in out
    assert cli.main(["validate", "--step", "v9"]) == 0  # a frozen test: reported, not run
    assert "frozen blind test" in capsys.readouterr().out
    assert cli.main(["validate", "--step", "V7"]) == 2


def test_validate_with_a_state_still_runs_v0(monkeypatch):
    """The guide's `lotline validate --state XX` keeps running the data check."""
    from lotline.validation import v0

    seen = []
    monkeypatch.setattr(v0, "write_report", lambda state, store: seen.append(state) or ("r.md", True))
    assert cli.main(["validate", "--state", "mn"]) == 0
    assert seen == ["MN"]
