"""Build the Lotline app page from results bundles: `python scripts/build_app.py [--bundle PATH ...]`.

Reads every `reports/results/<st>/bundle.json` (written by `lotline results --state XX`), validates each
against the `results_*` schemas and writes one self-contained page, `reports/app/index.html` (gitignored),
that opens from disk with no server. `--bundle` builds from named files instead, e.g. the synthetic fixture:

    uv run python scripts/build_app.py --bundle tests/fixtures/results/zz/bundle.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lotline.app.build import OUT_DIR, RESULTS_DIR, build_app


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--bundle", action="append", type=Path, help="bundle file(s) to use instead of --results")
    p.add_argument("--results", type=Path, default=RESULTS_DIR, help="folder of <st>/bundle.json")
    p.add_argument("--out", type=Path, default=OUT_DIR)
    a = p.parse_args(argv)
    page = build_app(a.bundle, results_dir=a.results, out_dir=a.out)
    print(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
