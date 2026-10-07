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


def _provenance(args: argparse.Namespace) -> int:
    from lotline import provenance
    from lotline.io import DataStore

    store = DataStore()
    if args.write:
        print(f"wrote {provenance.write(store)}")
    problems = provenance.check(store)
    for p in problems:
        print(f"FAIL {p}")
    if not problems:
        print("provenance OK: every processed source is documented and the document is current")
    return 1 if problems else 0


def _validate(args: argparse.Namespace) -> int:
    from lotline.config import all_states
    from lotline.io import DataStore
    from lotline.validation import v0

    if args.step != "V0":
        print(f"step {args.step} is not implemented yet")
        return 2
    ok = True
    for state in [args.state.upper()] if args.state else all_states():
        path, passed = v0.write_report(state, DataStore())
        ok &= passed
        print(f"{state} V0: {'PASS' if passed else 'gaps to explain'} -> {path}")
    return 0 if ok else 1


def _schemas(args: argparse.Namespace) -> int:
    from pathlib import Path

    from lotline.schemas import data_dictionary

    doc = Path(__file__).resolve().parents[2] / "docs" / "schemas.md"
    text = data_dictionary()
    if args.write:
        doc.write_text(text)
        print(f"wrote {doc}")
        return 0
    current = doc.exists() and doc.read_text() == text
    print(
        "docs/schemas.md is current"
        if current
        else "docs/schemas.md is out of date: run `lotline schemas --write`"
    )
    return 0 if current else 1


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

    prov = sub.add_parser("provenance", help="generate or check docs/data_provenance.md from the manifest")
    prov.add_argument("--write", action="store_true", help="regenerate the document before checking it")
    prov.add_argument("--check", action="store_true", help="check only (the default)")
    prov.set_defaults(func=_provenance)

    val = sub.add_parser("validate", help="run a validation-ladder step and write its report")
    val.add_argument("--state", help="two-letter state code (default: every configured state)")
    val.add_argument("--step", default="V0", help="ladder step (V0 so far)")
    val.set_defaults(func=_validate)

    sch = sub.add_parser("schemas", help="generate or check the data dictionary docs/schemas.md")
    sch.add_argument("--write", action="store_true", help="regenerate docs/schemas.md")
    sch.set_defaults(func=_schemas)
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
