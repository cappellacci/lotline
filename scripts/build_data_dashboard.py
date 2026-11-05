"""Build the data dashboard from LOTLINE_DATA_DIR: `python scripts/build_data_dashboard.py [--state MN ...]`.

Reads only processed tables (holdouts already removed), config/reforms and cached Census population
estimates; writes reports/data_dashboard/index.html and summary.json (gitignored: they hold aggregates of
downloaded data). `--fetch` downloads anything missing (Census PEP files) through the IO layer, so it lands in
manifest.jsonl. See docs/data_dashboard.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lotline.dashboard.render import write
from lotline.dashboard.summarize import summarize
from lotline.io import DataStore

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--state", action="append", help="limit to these states (default: every configured state)")
    p.add_argument("--out", type=Path, default=ROOT / "reports" / "data_dashboard")
    p.add_argument("--fetch", action="store_true", help="download missing population estimates")
    p.add_argument("--no-points", action="store_true", help="skip municipality dots (faster)")
    a = p.parse_args(argv)
    summary = summarize(DataStore(), a.state, fetch_missing=a.fetch, points=not a.no_points)
    if summary["population_source"] is None:
        print("note: Census PEP not cached; run with --fetch for population growth", file=sys.stderr)
    html = write(summary, a.out)
    print(f"{html}  ({', '.join(s['state'] for s in summary['states'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
