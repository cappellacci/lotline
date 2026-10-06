"""Command-line entry point: `lotline --version`, `lotline fetch`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lotline import __version__


def _fetch(args: argparse.Namespace) -> int:
    # Adapters register sources here from week 1 (WS-CORE); until then there is nothing to download.
    print("no sources registered yet")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lotline", description="Lotline housing reform simulator.")
    parser.add_argument("--version", action="version", version=f"lotline {__version__}")
    sub = parser.add_subparsers(dest="command")

    fetch = sub.add_parser("fetch", help="download source data into LOTLINE_DATA_DIR")
    fetch.add_argument("--state", help="two-letter state code, e.g. MN")
    fetch.add_argument("--source", help="source id, e.g. bps")
    fetch.set_defaults(func=_fetch)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
