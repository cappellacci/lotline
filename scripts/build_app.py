"""Build the Lotline app page from results bundles: `python scripts/build_app.py [--bundle PATH ...]`.

Reads every `reports/results/<st>/bundle.json` (written by `lotline results --state XX`), validates each
against the `results_*` schemas and writes the page, `reports/app/index.html`, plus one file per state,
`reports/app/states/<st>.js`, loaded when that state is picked (all gitignored). Keep the folder together;
the page opens from disk with no server. Section 2 embeds the data dashboard when its summary exists
(`scripts/build_data_dashboard.py`). `--bundle` builds from named files instead, e.g. the synthetic fixture:

    uv run python scripts/build_app.py --bundle tests/fixtures/results/zz/bundle.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lotline.app.build import DATA_SUMMARY, OUT_DIR, RESULTS_DIR, build_app


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--bundle", action="append", type=Path, help="bundle file(s) to use instead of --results")
    p.add_argument("--results", type=Path, default=RESULTS_DIR, help="folder of <st>/bundle.json")
    p.add_argument("--out", type=Path, default=OUT_DIR)
    p.add_argument(
        "--data-summary",
        type=Path,
        default=DATA_SUMMARY,
        help="data dashboard summary.json for section 2 (build_data_dashboard.py; skipped if missing)",
    )
    p.add_argument("--no-data-summary", action="store_true", help="section 2 without the dashboard")
    a = p.parse_args(argv)
    summary = None if a.no_data_summary else a.data_summary
    page = build_app(a.bundle, results_dir=a.results, out_dir=a.out, data_summary=summary)
    print(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
