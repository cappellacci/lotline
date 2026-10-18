"""Command-line entry point: `lotline fetch`, `sources`, `provenance`, `manifest`, `validate`, `schemas`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lotline import __version__


def _fetch(args: argparse.Namespace) -> int:
    from lotline import registry
    from lotline.config import all_states
    from lotline.io import DataStore
    from lotline.validation.holdout import assert_no_leak

    states = [args.state.upper()] if args.state else all_states()
    store = DataStore()
    for state in states:
        available = registry.sources_for(state)
        names = [args.source] if args.source else sorted(available)
        unknown = [n for n in names if n not in available]
        if unknown:
            print(
                f"{state}: unknown source(s) {', '.join(unknown)}; available: {', '.join(sorted(available))}"
            )
            return 2
        for name in names:
            src = available[name]
            df = src.module.load(state, store, refresh=args.refresh)
            assert_no_leak(df, src.table, state)
            out = store.processed(state, src.table, name)
            out.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(out, index=False)
            print(f"{state} {name}: {len(df):,} rows -> {out}")
    return 0


def _sources(args: argparse.Namespace) -> int:
    from lotline import registry
    from lotline.config import all_states

    for state in [args.state.upper()] if args.state else all_states():
        for name, src in sorted(registry.sources_for(state).items()):
            scope = "national" if src.states is None else state
            title = getattr(src.module, "PROVENANCE", {}).get("title", "")
            print(f"{state}  {name:<16} {scope:<9} -> {src.table:<16} {title}")
    return 0


def _provenance(args: argparse.Namespace) -> int:
    from lotline import provenance
    from lotline.io import DataStore

    store = DataStore()
    if args.write:
        print(f"wrote {provenance.write(store)}")
    for name in provenance.other_branch_sources(store):
        print(
            f"note: {name!r} was downloaded by another worktree (no adapter on this branch); not documented"
        )
    for rel in provenance.unregistered_processed(store):
        print(f"note: {rel} comes from a source not registered on this branch; skipped")
    problems = provenance.check(store)
    for p in problems:
        print(f"FAIL {p}")
    if not problems:
        print("provenance OK: every processed source is documented and the document is current")
    return 1 if problems else 0


def _supersede(args: argparse.Namespace) -> int:
    from fnmatch import fnmatch

    from lotline.io import DataStore
    from lotline.io.store import entry_key
    from lotline.provenance import current_files

    if args.abandoned and not args.path:
        print("--abandoned needs --path: name the folder of the query that was replaced")
        return 2
    if not (args.stale or args.before or args.path):
        print("narrow the selection with --stale, --before and/or --path (never a whole source at once)")
        return 2
    store = DataStore()
    live = store.manifest(include_superseded=False)
    current = {entry_key(e) for e in current_files(live)}
    picked, kept = [], 0
    for e in live:
        if e.source != args.source:
            continue
        if args.before and not e.accessed_at < args.before:
            continue
        if args.path and not fnmatch(e.path, args.path):
            continue
        stale = store.is_stale(e)
        if args.stale and not stale:
            continue
        if entry_key(e) in current and not stale and not args.abandoned:
            kept += 1  # the latest download of a file that is still intact on disk: never superseded
            continue
        picked.append(e)
    print(f"{args.source}: {len(picked)} entr{'y' if len(picked) == 1 else 'ies'} selected", end="")
    print(
        f"; {kept} kept because they are the current, intact record of their file (use --abandoned with "
        "--path for a replaced query)"
        if kept
        else ""
    )
    for e in picked[:10]:
        print(f"  {e.accessed_at}  {e.path}")
    if len(picked) > 10:
        print(f"  ... and {len(picked) - 10} more")
    if not picked:
        return 0
    if not args.apply:
        print("dry run: nothing written; add --apply to record these as superseded")
        return 0
    written = store.supersede(picked, args.reason)
    print(f"recorded {len(written)} in {store.superseded_path}; run `lotline provenance --write` next")
    return 0


def _register(args: argparse.Namespace) -> int:
    import datetime as dt
    from pathlib import Path

    from lotline.io import DataStore

    file = Path(args.file).expanduser()
    if not file.is_file():
        print(f"no such file: {file}")
        return 2
    vintage = args.vintage or dt.date.fromtimestamp(file.stat().st_mtime).isoformat()
    try:
        entry = DataStore().register(
            file, source=args.source, url=args.url, license=args.license, vintage=vintage
        )
    except FileExistsError as exc:
        print(exc)
        return 1
    print(f"registered {entry.path} ({entry.bytes:,} bytes, sha256 {entry.sha256[:12]}...)")
    return 0


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

    srcs = sub.add_parser("sources", help="list the data sources available for each state")
    srcs.add_argument("--state", help="two-letter state code (default: every configured state)")
    srcs.set_defaults(func=_sources)

    prov = sub.add_parser("provenance", help="generate or check docs/data_provenance.md from the manifest")
    prov.add_argument("--write", action="store_true", help="regenerate the document before checking it")
    prov.add_argument("--check", action="store_true", help="check only (the default)")
    prov.set_defaults(func=_provenance)

    man = sub.add_parser("manifest", help="maintain the download manifest (append-only)")
    man_sub = man.add_subparsers(dest="manifest_command", required=True)
    sup = man_sub.add_parser(
        "supersede",
        help="mark download entries as no longer current, with a reason (never deletes them)",
        description="Record manifest entries as superseded in manifest.superseded.jsonl. The entries stay in "
        "manifest.jsonl; provenance leaves them out. Dry run unless --apply. The latest download of a file "
        "that is still intact on disk is never superseded.",
    )
    sup.add_argument("--source", required=True, help="manifest source id, e.g. durham_permits")
    sup.add_argument("--stale", action="store_true", help="only entries whose file is missing or has changed")
    sup.add_argument("--before", help="only entries accessed before this UTC time, e.g. 2026-10-14T22:30")
    sup.add_argument("--path", help="only entries whose path matches this glob, e.g. 'raw/x/2026-10-14/*'")
    sup.add_argument(
        "--abandoned",
        action="store_true",
        help="also mark intact files: the pages of a query that was replaced by another one (needs --path)",
    )
    sup.add_argument("--reason", required=True, help="why these entries are no longer current")
    sup.add_argument("--apply", action="store_true", help="write the records (default: dry run)")
    sup.set_defaults(func=_supersede)
    reg = man_sub.add_parser(
        "register",
        help="record a file downloaded by hand (e.g. in a browser) as a raw download",
        description="Link (or copy) a hand-downloaded file to raw/<source>/<vintage>/ and append a manifest "
        "entry with its sha256, so adapters and provenance treat it like any other download. Use it when a "
        "site can only be downloaded in a browser. The original file is left in place.",
    )
    reg.add_argument("file", help="the downloaded file, e.g. ~/lotline-data/manual/tcad/2026_certified.zip")
    reg.add_argument("--source", required=True, help="manifest source id the adapter reads, e.g. tcad")
    reg.add_argument("--url", required=True, help="the page or link the file was downloaded from")
    reg.add_argument("--license", required=True, help="license or terms of use, as published")
    reg.add_argument("--vintage", help="vintage folder (default: the file's modification date)")
    reg.set_defaults(func=_register)

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
