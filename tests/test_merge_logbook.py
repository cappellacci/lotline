import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "merge_logbook", Path(__file__).resolve().parents[1] / "scripts" / "dev" / "merge_logbook.py"
)
merge_logbook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(merge_logbook)

LOGBOOK = "# Logbook\n\n### LB-001 · 2026-09-29 · Rules: a\n- x\n\n### LB-002 · 2026-09-30 · Scope: b\n- y\n"


def _write(root: Path, fragments: dict[str, str]) -> None:
    (root / "LOGBOOK.md").write_text(LOGBOOK)
    (root / "logbook.d").mkdir()
    (root / "logbook.d" / "README.md").write_text("### LB-NNN · YYYY-MM-DD · template\n")
    for name, text in fragments.items():
        (root / "logbook.d" / name).write_text(text)


def test_numbers_fragments_in_date_order_and_deletes_them(tmp_path):
    _write(
        tmp_path,
        {
            "2026-10-08-ws-b.md": "### LB-NNN · 2026-10-08 · Build: later\n- b\n",
            "2026-10-06-ws-a.md": "### LB-NNN · 2026-10-06 · Build: earlier\n- a\n",
        },
    )
    assert merge_logbook.main(["--apply"], root=tmp_path) == 0
    text = (tmp_path / "LOGBOOK.md").read_text()
    assert "### LB-003 · 2026-10-06 · Build: earlier" in text
    assert "### LB-004 · 2026-10-08 · Build: later" in text
    assert text.index("LB-003") < text.index("LB-004")
    assert sorted(p.name for p in (tmp_path / "logbook.d").iterdir()) == ["README.md"]


def test_dry_run_changes_nothing(tmp_path):
    _write(tmp_path, {"2026-10-06-ws-a.md": "### LB-NNN · 2026-10-06 · Build: a\n- a\n"})
    assert merge_logbook.main([], root=tmp_path) == 0
    assert (tmp_path / "LOGBOOK.md").read_text() == LOGBOOK
    assert (tmp_path / "logbook.d" / "2026-10-06-ws-a.md").exists()
