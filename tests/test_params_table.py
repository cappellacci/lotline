"""scripts/dev/params_table.py renders config/params/*.yaml into the Model & Assumptions Overview."""

import importlib.util
from pathlib import Path

import pytest

from lotline.config import load_params

_spec = importlib.util.spec_from_file_location(
    "params_table", Path(__file__).resolve().parents[1] / "scripts" / "dev" / "params_table.py"
)
params_table = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(params_table)

PERMITS = """\
repeated_total_min_units:
  value: 50
  low: 20
  high: 100
  unit: units per permit
  source: "Ben, 2026-10-19 (decision D-008); calibrated on observed repeats"
fixed_thing:
  value: 50000
  low: 50000
  high: 50000
  unit: USD per unit
  source: "Handbook. Fixed by the Handbook"
"""


def _config(tmp_path: Path) -> Path:
    (tmp_path / "params").mkdir()
    (tmp_path / "params" / "permits.yaml").write_text(PERMITS)
    return tmp_path


def test_table_lists_every_parameter_of_the_real_config():
    text = params_table.render()
    for name in load_params("fees"):
        assert f"| `{name}` |" in text


def test_rows_by_hand(tmp_path):
    text = params_table.render(_config(tmp_path))
    assert "2 parameters in 1 file." in text
    row = "| `repeated_total_min_units` | 50 | 20–100 | units per permit | Ben, 2026-10-19 (decision D-008) |"
    assert row in text
    assert "| `fixed_thing` | 50,000 | fixed | USD per unit | Handbook |" in text


def test_short_source_keeps_ellipses_and_cuts_long_text():
    assert params_table.short_source("Plan V1: 'through 2018 ... Repeat'. Next sentence") == (
        "Plan V1: 'through 2018 ... Repeat'"
    )
    assert len(params_table.short_source("x" * 500)) == params_table.SOURCE_CHARS


def test_write_then_check(tmp_path):
    config = _config(tmp_path)
    doc = tmp_path / "doc.md"
    doc.write_text(f"# Doc\n\n{params_table.START}\nold\n{params_table.END}\n\nafter\n")
    assert params_table.main(["--check"], doc_path=doc, config_dir=config) == 1  # stale
    assert params_table.main([], doc_path=doc, config_dir=config) == 0
    assert params_table.main(["--check"], doc_path=doc, config_dir=config) == 0
    text = doc.read_text()
    assert "old" not in text and text.endswith("\n\nafter\n") and "`fixed_thing`" in text


def test_missing_markers_is_an_error():
    with pytest.raises(ValueError):
        params_table.splice("# no markers\n", "table")
