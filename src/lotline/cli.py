"""Command-line entry point: `lotline fetch`, `sources`, `provenance`, `manifest`, `validate`, `schemas`."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lotline import __version__


def _fetch(args: argparse.Namespace) -> int:
    from contextlib import nullcontext

    from lotline import registry
    from lotline.config import all_states
    from lotline.io import DataStore
    from lotline.io.offline import OfflineError, offline_build
    from lotline.validation.holdout import assert_no_leak

    if args.offline and args.refresh:
        print("--offline reads only the cache; it can't be combined with --refresh")
        return 2
    states = [args.state.upper()] if args.state else all_states()
    store = DataStore()
    failed = []
    with offline_build(store) if args.offline else nullcontext() as sess:
        for state in states:
            available = registry.sources_for(state)
            names = [args.source] if args.source else sorted(available)
            unknown = [n for n in names if n not in available]
            if unknown:
                print(
                    f"{state}: unknown source(s) {', '.join(unknown)}; "
                    f"available: {', '.join(sorted(available))}"
                )
                return 2
            for name in names:
                src = available[name]
                try:
                    df = src.module.load(state, store, refresh=args.refresh)
                except OfflineError as exc:  # never falls back to the network: report and go on
                    failed.append(f"{state} {name}")
                    print(f"{state} {name}: FAILED offline: {exc}")
                    if sess:
                        sess.used.clear()
                        sess.notes.clear()
                    continue
                assert_no_leak(df, src.table, state)
                out = store.processed(state, src.table, name)
                out.parent.mkdir(parents=True, exist_ok=True)
                df.to_parquet(out, index=False)
                print(f"{state} {name}: {len(df):,} rows -> {out}")
                if sess:
                    for note in sess.notes:
                        print(f"  note: {note}")
                    rec = sess.record(state=state, source=name)
                    print(f"  offline build from {len(rec.snapshots)} cached snapshot(s)/file(s)")
    if failed:
        print(f"offline: {len(failed)} source(s) had no complete cached snapshot: {', '.join(failed)}")
        return 1
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


def _prune_candidates(args: argparse.Namespace) -> int:
    from lotline.io import DataStore
    from lotline.io.offline import prune_candidates

    rows = prune_candidates(DataStore())
    for folder, size, newer in rows:
        print(f"{size / 1e6:9.1f} MB  {folder}  (repeated by {newer})")
    total = sum(size for _, size, _ in rows)
    print(f"{len(rows)} older snapshot folder(s), {total / 1e9:.2f} GB; dry run: nothing deleted")
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


def _results(args: argparse.Namespace) -> int:
    from pathlib import Path

    from lotline.config import all_states
    from lotline.io import DataStore
    from lotline.model import results

    results_dir = Path("reports") / "results"
    if args.all and (args.state or args.role or args.out):
        print("--all writes every configured state with its default role and path; drop --state/--role/--out")
        return 2
    if not args.all and not args.state:
        print("give --state XX, or --all for every state and the page")
        return 2
    if not results.tree_is_clean():
        print(
            "warning: uncommitted changes; the bundle's commit_sha will not fully identify the code that ran"
        )

    def one(state: str, role=None, out=None) -> Path:
        out = Path(out) if out else results_dir / state.lower() / "bundle.json"
        bundle = results.build_bundle(state, store, role=role, origin=args.origin, draws=args.draws)
        path = results.write_bundle(bundle, out)
        m = bundle["meta"].iloc[0]
        print(
            f"wrote {path} ({m['state_role']}, tier {m['data_tier']}, overlap {m['overlap_flag']}; "
            f"pending: {m['scenarios_pending']})"
        )
        return path

    store = DataStore()
    if not args.all:
        one(args.state.upper(), args.role, args.out)
        return 0
    try:  # the page build is WS-APP's (scripts/build_app.py, PR #313)
        from lotline.app.build import build_app
    except ImportError:
        print(
            "lotline results --all needs WS-APP's page build (lotline.app.build, PR #313); not on this branch"
        )
        return 2
    failed = []
    for state in all_states():
        try:
            one(state)
        except Exception as exc:  # a state without built tables must not stop the others
            failed.append(state)
            print(f"{state}: no bundle ({type(exc).__name__}: {exc})")
    page = build_app(results_dir=results_dir, out_dir=Path("reports") / "app")
    print(f"built {page}" + (f"; no bundle for {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


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
    fetch.add_argument(
        "--offline",
        action="store_true",
        help="rebuild tables from the newest complete raw snapshot already in LOTLINE_DATA_DIR; sends no "
        "request and fails if a source isn't cached (recorded in manifest.builds.jsonl)",
    )
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
    pc = man_sub.add_parser(
        "prune-candidates",
        help="list older raw snapshot folders that a newer vintage repeats (dry run; deletes nothing)",
    )
    pc.set_defaults(func=_prune_candidates)
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

    res = sub.add_parser(
        "results",
        help="run the engine for a state and write its results bundle for the app (reports/results/<st>/)",
    )
    res.add_argument("--state", help="two-letter state code, e.g. MN")
    res.add_argument(
        "--all",
        action="store_true",
        help="every configured state's bundle, then the page (reports/app/index.html)",
    )
    res.add_argument(
        "--role",
        choices=["benchmark", "development", "transfer", "national_only"],
        help="how the app labels the state (default: national_only for a state with no parcel data, "
        "else development)",
    )
    res.add_argument("--origin", type=int, help="forecast origin year (default: config results_origin_year)")
    res.add_argument("--draws", type=int, help="draws per scenario (default: config results_draws)")
    res.add_argument("--out", help="output path (default: reports/results/<st>/bundle.json)")
    res.set_defaults(func=_results)

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
