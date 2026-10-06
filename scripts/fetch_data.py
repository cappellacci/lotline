#!/usr/bin/env python3
"""Single entry point for automated data acquisition (challenge gate T10).

Thin wrapper around `lotline fetch`; all downloads go through the IO layer into LOTLINE_DATA_DIR.

    uv run python scripts/fetch_data.py --state MN --source bps
"""

import sys

from lotline.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["fetch", *sys.argv[1:]]))
