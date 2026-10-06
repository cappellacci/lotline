import re

import lotline
from lotline.cli import main


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", lotline.__version__)


def test_cli_version(capsys):
    try:
        main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert capsys.readouterr().out.strip() == f"lotline {lotline.__version__}"


def test_fetch_rejects_unknown_source(capsys):
    # no network: an unknown source fails before any download
    assert main(["fetch", "--state", "MN", "--source", "nope"]) == 2
    assert "unknown source" in capsys.readouterr().out
