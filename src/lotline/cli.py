"""Command-line entry point.

Main commands: `lotline run` (fetch, results and the page in one go), `fetch`, `results`, `app`, `sources`,
`onboard`. Maintenance: `validate`, `calibrate`, `unlisted`, `provenance`, `manifest`, `schemas`.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from lotline import __version__


class UserError(Exception):
    """A mistake the user can fix (unknown state, missing data): printed as one line, no traceback."""


def _states(code: str | None) -> list[str]:
    """`[CODE]` for a configured state, every configured state for None; a clear error otherwise."""
    from lotline.config import all_states

    configured = all_states()
    if code is None:
        return configured
    code = code.upper()
    if code not in configured:
        raise UserError(
            f"{code} is not set up. Configured states: {' '.join(configured)}. "
            "To add a state, see docs/adding_a_state.md (or run `lotline onboard --state XX`)."
        )
    return [code]


def _fetch_states(states, source=None, refresh=False, offline=False) -> list[str]:
    """Fetch every source for `states` (or one `source`), in dependency order. A source that fails is
    reported and skipped, so the rest still build; returns the failures as "ST source: reason"."""
    from contextlib import nullcontext

    from lotline import registry
    from lotline.io import DataStore
    from lotline.io.offline import OfflineError, offline_build
    from lotline.validation.holdout import assert_no_leak

    store = DataStore()
    print(f"data folder: {store.root}")
    failed = []
    with offline_build(store) if offline else nullcontext() as sess:
        for state in states:
            available = registry.sources_for(state)
            # each source after the tables it reads; place_inputs (RUN_LAST) after the rest
            names = [source] if source else registry.fetch_order(available)
            unknown = [n for n in names if n not in available]
            if unknown:
                raise UserError(
                    f"{state}: unknown source(s) {', '.join(unknown)}; "
                    f"available: {', '.join(sorted(available))}"
                )
            for i, name in enumerate(names, 1):
                src = available[name]
                print(
                    f"{state} {name} ({i}/{len(names)}): {'reading cache' if offline else 'fetching'}...",
                    flush=True,
                )
                try:
                    df = src.module.load(state, store, refresh=refresh)
                except (OfflineError, FileNotFoundError) as exc:  # missing cache or a hand-download source
                    failed.append(f"{state} {name}: {exc}")
                    print(f"{state} {name}: SKIPPED: {exc}")
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
        print(f"{len(failed)} source(s) were skipped; the others were built:")
        for f in failed:
            print(f"  {f}")
        if any("manifest register" in f for f in failed):
            print("A hand-download source needs its file registered first: see the message above.")
    return failed


def _require_national_tables(state: str, store) -> None:
    """Stop with the fetch command when a state's national tables are missing, instead of a traceback deep
    in the model (usability review, 2026-11-27)."""
    from lotline import onboarding

    missing = onboarding.missing_national_tables(state, store)
    if missing:
        raise UserError(
            f"{state} has no {', '.join(missing)} table(s) in {store.root} yet. "
            f"Run `uv run lotline fetch --state {state}` first (or `uv run lotline run --state {state}`)."
        )


def _fetch(args: argparse.Namespace) -> int:
    if args.offline and args.refresh:
        raise UserError("--offline reads only the cache; it can't be combined with --refresh")
    failed = _fetch_states(_states(args.state), args.source, args.refresh, args.offline)
    return 1 if failed else 0


def _sources(args: argparse.Namespace) -> int:
    from lotline import registry
    from lotline.config import all_states

    for state in [args.state.upper()] if args.state else all_states():
        for name, src in sorted(registry.sources_for(state).items()):
            scope = "national" if src.states is None else state
            title = getattr(src.module, "PROVENANCE", {}).get("title", "")
            print(f"{state}  {name:<22} {scope:<9} -> {src.table:<18} {title}")
    return 0


def _onboard(args: argparse.Namespace) -> int:
    """The adding-a-state checklist for one state: each step, whether it is done, and its commands."""
    import json

    from lotline import onboarding
    from lotline.io import DataStore

    plan = onboarding.plan(args.state, DataStore())
    if args.json:
        print(json.dumps(plan, indent=1))
        return 0
    mark = {True: "done", False: "todo", None: "  - "}
    for s in plan:
        print(f"[{mark[s['done']]}] {s['n']:>2}. {s['title']}  ({s['detail']})")
        for cmd in s["commands"] if s["done"] is not True else []:
            print(f"          $ {' '.join(cmd)}")
    print("Guide: docs/adding_a_state.md (steps come from config/onboarding/steps.yaml)")
    return 0


def _unlisted(args: argparse.Namespace) -> int:
    from lotline.build.jurisdictions import config_orphans, unlisted
    from lotline.config import all_states
    from lotline.io import DataStore

    store = DataStore()
    found = 0
    for state in [args.state.upper()] if args.state else all_states():
        df = unlisted(state, store)
        found += len(df)
        for r in df.itertuples():
            print(f"{state}  {r.geoid:<11} {r.table:<8} {r.rows:>9,} rows")
    if found:
        print("Add each government above to local_jurisdictions in config/states/<st>.yaml (GEOID: name),")
        print("then rerun `lotline fetch --source jurisdictions` and the adapters.")
    else:
        print("every GEOID your permit and parcel tables use is in the jurisdictions list")
    blocking = 0
    for state in [args.state.upper()] if args.state else all_states():
        orphans = config_orphans(state, store)
        blocking += int(orphans["blocking"].sum())
        for r in orphans.itertuples():
            tag = "matches nothing" if r.blocking else "not modeled (county-filed or outside the set)"
            print(f"{state}  {r.geoid:<11} config {r.where:<20} {tag}")
    if blocking:
        print(
            "Config names GEOIDs the jurisdictions table lacks (a renamed or re-keyed place?): fix the GEOID"
        )
        print("in config, or add the place to local_jurisdictions.")
    from lotline.adapters.national import bps

    for state in [args.state.upper()] if args.state else all_states():
        report = bps.read_rekeys(state, store)
        for r in [] if report is None else report.itertuples():
            print(
                f"{state}  {r.old_geoid:<11} permits {r.first_year}-{r.last_year} moved to {r.new_geoid} "
                f"({r.name}, BPS ID {r.bps_id})"
            )
        if report is not None and len(report):
            print("Census gave these permit IDs a new GEOID; their history now sits under the new one. Check")
            print("that config naming the old GEOID (holdouts, train_until, reforms, sources) is updated.")
    return 1 if found or blocking else 0


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


def _calibrate(args: argparse.Namespace) -> int:
    from lotline import calibrate

    if args.run:
        rows = calibrate.run(args.step or None, quick=args.quick, write=args.write)
        for r in rows:
            if r["name"] is None:
                print(f"{r['step']:24} {r['status']}")
            else:
                d = "" if r["rel_diff"] is None else f"{100 * r['rel_diff']:.2f}%"
                n = r["new"] if isinstance(r["new"], str) else f"{r['new']:.6g}"
                same = "  (identical)" if r.get("same") else ""
                if "bounds_diff" in r:
                    same += f"  low/high diff {100 * r['bounds_diff']:.2f}%"
                print(f"{r['step']:24} {r['name']:48} config {r['config']}  new {n}  diff {d}{same}")
        if args.write:
            print("wrote config and the lock")
    if args.write_lock:
        print(f"wrote {calibrate.write_lock()}")
    if args.list:
        for s in calibrate.order():
            outs = [f"{f}:{','.join(k)}" for f, k in s.produces.items()] + list(s.tables)
            after = f" (after {', '.join(s.after)})" if s.after else ""
            print(f"{s.name:24} {s.decision:22} {s.how:4} {s.status:7} {'; '.join(outs)}{after}")
    problems = calibrate.check()
    for p in problems:
        print(f"FAIL {p}")
    if not problems:
        n, k = len(calibrate.produced()), len(calibrate.STEPS)
        print(f"calibration OK: {k} steps account for {n} fitted values; the lock matches config")
    return 1 if problems else 0


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


def _commit_note() -> None:
    from lotline.model import results

    clean = results.tree_state()
    if clean is False:
        print(
            "warning: uncommitted changes; the bundle's commit_sha will not fully identify the code that ran"
        )
    elif clean is None:
        print(
            f"note: not a git checkout; the bundle's commit_sha is {results.commit_sha()[:7]} "
            "(from LOTLINE_COMMIT or src/lotline/COMMIT; all zeros if neither is set)"
        )


def _one_bundle(state: str, store, role=None, out=None, origin=None, draws=None):
    """Run every scenario for `state` and write its results bundle; returns the path."""
    from pathlib import Path

    from lotline.app.build import RESULTS_DIR
    from lotline.model import results

    _require_national_tables(state, store)
    out = Path(out) if out else RESULTS_DIR / state.lower() / "bundle.json"
    print(f"{state}: running the scenarios (a few minutes)...", flush=True)
    bundle = results.build_bundle(state, store, role=role, origin=origin, draws=draws)
    path = results.write_bundle(bundle, out)
    m = bundle["meta"].iloc[0]
    print(
        f"{state}: wrote {path} ({m['state_role']}, tier {m['data_tier']}, overlap {m['overlap_flag']}; "
        f"pending: {m['scenarios_pending']})"
    )
    return path


def _bundles_for(states, store, origin=None, draws=None):
    """A bundle per state; a state that fails is reported and skipped.

    Returns (written paths, failed states)."""
    failed, written = [], []
    for state in states:
        try:
            written.append(_one_bundle(state, store, origin=origin, draws=draws))
        except Exception as exc:  # a state without built tables must not stop the others
            failed.append(state)
            print(f"{state}: no bundle ({type(exc).__name__}: {exc})")
    return written, failed


def _page(bundles=None, data_tab: bool = True) -> int:
    """Build the data dashboard summary (when the data is there) and the page; print where it is."""
    from lotline.app.build import DATA_SUMMARY, OUT_DIR, build_app, find_bundles

    bundles = list(bundles) if bundles is not None else find_bundles()
    if not bundles:
        raise UserError(
            "no results to show yet: run `uv run lotline run --state XX` (or `lotline results`) first"
        )
    summary = None
    if data_tab:
        try:
            from lotline.dashboard.render import write
            from lotline.dashboard.summarize import summarize
            from lotline.io import DataStore

            print("building the data tab (data dashboard)...", flush=True)
            write(summarize(DataStore(), None, fetch_missing=False, points=True), DATA_SUMMARY.parent)
            summary = DATA_SUMMARY
        except Exception as exc:  # the page still builds; its data tab then lists sources only
            print(f"note: no data tab ({type(exc).__name__}: {exc}); the page lists sources only")
    page = build_app(bundles=bundles, out_dir=OUT_DIR, data_summary=summary)
    print(f"built {page}  (open it in a browser)")
    return 0


def _results(args: argparse.Namespace) -> int:
    from lotline.io import DataStore

    if args.all and (args.state or args.role or args.out):
        raise UserError(
            "--all writes every configured state with its default role and path; drop --state/--role/--out"
        )
    if not args.all and not args.state:
        raise UserError("give --state XX, or --all for every state and the page")
    states = _states(args.state if not args.all else None)  # an unknown state stops here, before any work
    _commit_note()
    store = DataStore()
    if not args.all:
        _one_bundle(states[0], store, args.role, args.out, args.origin, args.draws)
        return 0
    written, failed = _bundles_for(states, store, args.origin, args.draws)
    if not written:
        print("no state produced a bundle, so no page was built")
        return 1
    # Only this run's bundles: a failed state's bundle from an earlier run must not reach the page.
    _page(written)
    if failed:
        print(f"no bundle for {', '.join(failed)}")
    return 1 if failed else 0


def _app(args: argparse.Namespace) -> int:
    return _page(data_tab=not args.no_data_tab)


def _run(args: argparse.Namespace) -> int:
    """The whole path in one command: fetch, results, data tab and page."""
    from lotline.app.build import find_bundles
    from lotline.io import DataStore

    states = _states(args.state)
    print(f"step 1 of 3: data for {', '.join(states)}" + (" (cache only)" if args.offline else ""))
    if not args.skip_fetch:
        skipped = _fetch_states(states, offline=args.offline)
    else:
        skipped = []
        print("  skipped (--skip-fetch)")
    print("step 2 of 3: results")
    _commit_note()
    written, failed = _bundles_for(states, DataStore(), draws=args.draws)
    if not written:
        print("no state produced a bundle, so no page was built")
        return 1
    print("step 3 of 3: the page")
    # This run's bundles, plus other states' bundles already on disk when only some states were run.
    others = [b for b in find_bundles() if b.parent.name.upper() not in states]
    _page(written + others)
    if failed or skipped:
        print(
            f"finished with problems: {len(skipped)} source(s) skipped"
            + (f"; no bundle for {', '.join(failed)}" if failed else "")
        )
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lotline",
        description="Lotline estimates how much new housing state reforms would add over five years.",
        epilog="Start here: `lotline run --state MN` fetches the data, runs the reforms and builds the "
        "page.\n"
        "Main: run, fetch, results, app, sources, onboard.  "
        "Maintenance: validate, calibrate, unlisted, provenance, manifest, schemas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lotline {__version__}")
    parser.add_argument("--debug", action="store_true", help="show the full Python traceback on an error")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    run = sub.add_parser(
        "run",
        help="the whole path in one command: fetch the data, run every reform, build the page",
        description="Fetch the data a state needs, run every reform, and build the page "
        "(reports/app/index.html). A first fetch downloads several GB for a state with local data "
        "(Minnesota about 4.5 GB) and can take "
        "an hour; later runs reuse the cache.",
    )
    run.add_argument("--state", help="two-letter state code, e.g. MN (default: every configured state)")
    run.add_argument(
        "--offline", action="store_true", help="use only data already downloaded; send no request"
    )
    run.add_argument("--skip-fetch", action="store_true", help="don't fetch; use the tables already built")
    run.add_argument("--draws", type=int, help="model runs per reform (default: config results_draws)")
    run.set_defaults(func=_run)

    app = sub.add_parser(
        "app", help="rebuild the page from the results already written (reports/app/index.html)"
    )
    app.add_argument(
        "--no-data-tab", action="store_true", help="skip the data tab (faster; lists sources only)"
    )
    app.set_defaults(func=_app)

    fetch = sub.add_parser(
        "fetch", help="download the source data into your data folder (LOTLINE_DATA_DIR) and build its tables"
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

    onb = sub.add_parser(
        "onboard", help="the adding-a-state checklist for one state: what is done, what is next"
    )
    onb.add_argument("--state", required=True, help="two-letter state code")
    onb.add_argument("--json", action="store_true", help="print the plan as JSON (for the app)")
    onb.set_defaults(func=_onboard)

    unl = sub.add_parser(
        "unlisted",
        help="places in your permit and parcel data missing from the state's list of places (Census codes)",
    )
    unl.add_argument("--state", help="two-letter state code (default: every state)")
    unl.set_defaults(func=_unlisted)

    prov = sub.add_parser("provenance", help="generate or check docs/data_provenance.md from the manifest")
    prov.add_argument("--write", action="store_true", help="regenerate the document before checking it")
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

    val = sub.add_parser("validate", help="check a state's data for gaps before running it (step V0)")
    val.add_argument("--state", help="two-letter state code (default: every configured state)")
    val.add_argument("--step", default="V0", help="ladder step (V0 so far)")
    val.set_defaults(func=_validate)

    res = sub.add_parser(
        "results",
        help="run every reform for a state and write its results file (reports/results/<st>/bundle.json)",
    )
    res.add_argument("--state", help="two-letter state code, e.g. MN")
    res.add_argument(
        "--all",
        action="store_true",
        help="every configured state's bundle, then the page (reports/app/index.html)",
    )
    res.add_argument(
        "--role",
        choices=["benchmark", "development", "transfer", "national_only", "ingestion_test"],
        help="how the page labels the state (default: national_only with no parcel data, else development)",
    )
    res.add_argument("--origin", type=int, help="forecast origin year (default: config results_origin_year)")
    res.add_argument("--draws", type=int, help="model runs per reform (default: config results_draws)")
    res.add_argument("--out", help="output path (default: reports/results/<st>/bundle.json)")
    res.set_defaults(func=_results)

    sch = sub.add_parser("schemas", help="generate or check the data dictionary docs/schemas.md")
    sch.add_argument("--write", action="store_true", help="regenerate docs/schemas.md")
    sch.set_defaults(func=_schemas)

    cal = sub.add_parser(
        "calibrate",
        help="check, or rerun, the steps that produce every fitted value in config/params/",
        description="Every fitted value in config/params/ comes from a calibration step. With no flag this "
        "checks that the step registry, config and config/calibration.lock.json agree; --run recomputes the "
        "steps and compares.",
    )
    cal.add_argument("--list", action="store_true", help="print the steps in run order")
    cal.add_argument(
        "--check", action="store_true", help="check registry, config and lock agree (the default)"
    )
    cal.add_argument(
        "--write-lock",
        action="store_true",
        help="record config's fitted values in config/calibration.lock.json",
    )
    cal.add_argument("--run", action="store_true", help="recompute the ported steps and compare with config")
    cal.add_argument("--step", action="append", help="only this step (repeatable); default every step")
    cal.add_argument("--quick", action="store_true", help="with --run: fewer draws, minutes; can't --write")
    cal.add_argument(
        "--write", action="store_true", help="with --run: write new values into config and the lock"
    )
    cal.set_defaults(func=_calibrate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    from lotline.adapters.national.acs import CensusKeyError
    from lotline.io.offline import OfflineError

    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except UserError as exc:
        print(f"error: {exc}")
        return 2
    except (CensusKeyError, OfflineError, FileNotFoundError) as exc:  # setup problems, not bugs
        if args.debug:
            raise
        print(f"error: {exc}")
        if isinstance(exc, CensusKeyError):
            print(
                "Get a free key at https://api.census.gov/data/key_signup.html "
                "and put CENSUS_API_KEY=... in .env"
            )
        print("(rerun with --debug for the full traceback)")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
