"""The cross-platform file lock (`lotline.io.filelock`), and that no module imports `fcntl` at top level,
which stopped the package loading on Windows (stability review, 2026-11-27)."""

import ast
from pathlib import Path

from lotline.io import filelock

SRC = Path(__file__).resolve().parents[2] / "src" / "lotline"


def test_lock_and_unlock_round_trip(tmp_path):
    f = tmp_path / "lockfile"
    with f.open("a+") as fh:
        fh.write("x")
        filelock.lock(fh)
        filelock.unlock(fh)
        filelock.lock(fh)  # can be taken again after release
        filelock.unlock(fh)


def test_no_module_imports_fcntl_at_top_level():
    offenders = []
    for path in SRC.rglob("*.py"):
        if path.name == "filelock.py":
            continue
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
            if isinstance(node, ast.ImportFrom) and node.module == "fcntl":
                names = ["fcntl"]
            if "fcntl" in names:
                offenders.append(str(path.relative_to(SRC)))
    assert offenders == [], f"use lotline.io.filelock instead of fcntl in: {offenders}"
