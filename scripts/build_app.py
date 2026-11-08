"""Build the Lotline app page from results bundles: `python scripts/build_app.py [--bundle PATH ...]`.

Reads every `reports/results/<st>/bundle.json` (written by `lotline results --state XX`), validates each
against the `results_*` schemas and writes `reports/app/index.html` plus one `reports/app/states/<st>.js` per
state (all gitignored). Open `index.html` straight from disk, no server needed; keep the `states/` folder next
to it. Section 2 embeds the data dashboard when its summary exists (`scripts/build_data_dashboard.py`).
`--bundle` builds from named files instead, e.g. the synthetic fixture:

    uv run python scripts/build_app.py --bundle tests/fixtures/results/zz/bundle.json

`--from-release DIR` builds from a folder of release assets (`<st>.bundle.json`, `data-summary.json`), as
staged by `scripts/publish_app.py`; the Pages workflow uses it.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lotline.app.build import DATA_SUMMARY, OUT_DIR, RESULTS_DIR, build_app, release_inputs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--bundle", action="append", type=Path, help="bundle file(s) to use instead of --results")
    p.add_argument("--results", type=Path, default=RESULTS_DIR, help="folder of <st>/bundle.json")
    p.add_argument("--from-release", type=Path, help="folder of release assets (scripts/publish_app.py)")
    p.add_argument("--out", type=Path, default=OUT_DIR)
    p.add_argument(
        "--data-summary",
        type=Path,
        default=DATA_SUMMARY,
        help="data dashboard summary.json for section 2 (build_data_dashboard.py; skipped if missing)",
    )
    p.add_argument("--no-data-summary", action="store_true", help="section 2 without the dashboard")
    a = p.parse_args(argv)
    bundles, summary = a.bundle, a.data_summary
    if a.from_release:
        if a.bundle:
            p.error("--from-release and --bundle can't be combined")
        bundles, summary = release_inputs(a.from_release)
    if a.no_data_summary:
        summary = None
    page = build_app(bundles, results_dir=a.results, out_dir=a.out, data_summary=summary)
    print(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
