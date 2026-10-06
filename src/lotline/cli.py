"""Command-line entry point: `lotline --version`, `lotline fetch`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lotline import __version__


def _fetch(args: argparse.Namespace) -> int:
    from lotline.adapters.national import SOURCES
    from lotline.config import all_states
    from lotline.io import DataStore

    states = [args.state.upper()] if args.state else all_states()
    sources = [args.source] if args.source else sorted(SOURCES)
    unknown = [s for s in sources if s not in SOURCES]
    if unknown:
        print(f"unknown source(s): {', '.join(unknown)}; available: {', '.join(sorted(SOURCES))}")
        return 2
    store = DataStore()
    for state in states:
        for source in sources:
            adapter, table = SOURCES[source]
            df = adapter.load(state, store, refresh=args.refresh)
            out = store.processed(state, table, source)
            out.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(out, index=False)
            print(f"{state} {source}: {len(df):,} rows -> {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lotline", description="Lotline housing reform simulator.")
    parser.add_argument("--version", action="version", version=f"lotline {__version__}")
    sub = parser.add_subparsers(dest="command")

    fetch = sub.add_parser(
        "fetch", help="download source data into LOTLINE_DATA_DIR and build canonical tables"
    )
    fetch.add_argument("--state", help="two-letter state code, e.g. MN (default: every configured state)")
    fetch.add_argument("--source", help="source id, e.g. bps (default: every registered source)")
    fetch.add_argument("--refresh", action="store_true", help="re-check sources for newer files")
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
