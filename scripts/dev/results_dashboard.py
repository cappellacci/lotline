#!/usr/bin/env python3
"""Write the engine results dashboard: one self-contained HTML page comparing estimation runs.

    uv run python scripts/dev/results_dashboard.py                      # every run under reports/
    uv run python scripts/dev/results_dashboard.py reports/mm-d024-nb reports/mm-d024-4state --out /tmp/x.html

A run is a folder with the CSVs of a `--full` run and a `run.yaml` manifest (`lotline.model.runs`); the
estimation scripts write the manifest. Open the page in any browser; it needs no server or network.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lotline.model import dashboard, runs

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folders", nargs="*", type=Path, help="run folders (default: all under reports/)")
    ap.add_argument("--out", type=Path, default=REPO / "reports" / "dashboard" / "index.html")
    a = ap.parse_args()
    folders = a.folders or runs.find_runs(REPO / "reports")
    if not folders:
        raise SystemExit("no run folders found (a run folder holds run.yaml)")
    page = dashboard.render([runs.load_run(f) for f in folders])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(page)
    print(f"wrote {a.out} ({len(folders)} runs: {', '.join(f.name for f in folders)})")


if __name__ == "__main__":
    main()
