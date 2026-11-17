"""`python -m lotline.rule_agents.adu <command>`: the deterministic steps the ADU agents call.

Run folder (outside the repo): `$LOTLINE_DATA_DIR/rule_agents/adu/<ST>/<run_id>/`
    places.csv            worklist (rank, geoid, name, pop); existing_rows.csv: orchestrator only
    state_law.json        state-law baseline (rules-adu-state-law)
    coding_a/<geoid>.json primary coder        coding_b/<geoid>.json  blind second coder
    decisions/<geoid>.json verifier rulings    final/<geoid>.json     merged coding
    tasks.csv / tasks.md  human lookups        rows.csv               proposed `reforms` rows
    compare.md            comparison with config/reforms/<st>.csv (dry runs)

Commands: run-dir, worklist, fetch, check, verify-quotes, diff-coders, merge, rows, tasks, ingest, compare.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.io.store import DataStore
from lotline.rule_agents.adu import coding as C
from lotline.rule_agents.adu import handoff as H
from lotline.rule_agents.adu import places as P
from lotline.rule_agents.adu import reconcile as R
from lotline.rule_agents.adu import rows as W
from lotline.rule_agents.adu.fetch import Fetcher, quote_in_text


def run_dir(state: str, run_id: str, store: DataStore | None = None) -> Path:
    store = store or DataStore()
    return store.root / "rule_agents" / "adu" / state.upper() / run_id


def _load_all(folder: Path) -> list[C.PlaceCoding]:
    return [C.load(p) for p in sorted(folder.glob("*.json"))]


def cmd_worklist(a) -> int:
    store = DataStore()
    j = store.read(a.state, "jurisdictions")
    if j is None:
        print(f"no jurisdictions table for {a.state}; build it first (lotline build) or pass --places-csv")
        return 2
    path = CONFIG_DIR / "reforms" / f"{a.state.lower()}.csv"
    existing = pd.read_csv(path, dtype=str) if path.exists() else None
    wl = P.worklist(j, existing, a.min_pop, a.limit)
    if a.geoids:
        wl = wl[wl["geoid"].isin(a.geoids.split(","))]
    out = run_dir(a.state, a.run_id) / "places.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    # Existing reform ids reveal rule years: they go to an orchestrator-only file, never to the coders.
    wl.drop(columns="existing_adu_rows").to_csv(out, index=False)
    wl[["geoid", "name", "existing_adu_rows"]].to_csv(out.with_name("existing_rows.csv"), index=False)
    blind = P.blind_holdouts(a.state)
    print(f"{len(wl)} places -> {out}")
    print("blind holdouts (code rules only; open no outcomes):", json.dumps(blind) if blind else "none")
    return 0


def cmd_fetch(a) -> int:
    f = Fetcher(DataStore(), a.state)
    for url in a.urls:
        r = f.get(url)
        d = {k: (str(v) if isinstance(v, (Path, dt.date)) else v) for k, v in asdict(r).items()}
        print(json.dumps(d))
    return 0


def cmd_check(a) -> int:
    bad = 0
    for p in a.paths:
        try:
            probs = C.check(C.load(p))
        except Exception as exc:  # noqa: BLE001 (report every file's problem, then fail)
            probs = [f"does not parse: {exc}"]
        for msg in probs:
            print(f"{p}: {msg}")
        bad += bool(probs)
    print(f"{len(a.paths) - bad}/{len(a.paths)} codings pass")
    return 1 if bad else 0


def cmd_verify_quotes(a) -> int:
    """Every quote with a cached HTML text copy must appear verbatim; PDFs are listed for the Read tool."""
    store = DataStore()
    code = 0
    for p in a.paths:
        c = C.load(p)
        for era in c.eras:
            evs = [e for fv in era.fields.values() for e in fv.evidence] + [
                e for d in era.dates for e in d.evidence
            ]
            for e in evs:
                if not e.cache_path:
                    print(f"{c.geoid} {era.era_id}: no cached copy for {e.url} (verifier must re-open)")
                    continue
                src = store.root / e.cache_path
                txt = src.with_suffix(".txt")
                if txt.exists():
                    ok = quote_in_text(e.quote, txt.read_text())
                    print(f"{c.geoid} {era.era_id}: {'OK ' if ok else 'MISSING'} {e.url}")
                    code |= not ok
                else:
                    print(f"{c.geoid} {era.era_id}: READ-TOOL {src} (check quote by eye)")
    return code


def cmd_diff(a) -> int:
    diffs = R.compare(C.load(a.a), C.load(a.b))
    rows = [asdict(d) for d in diffs if a.all or d.status != "agree"]
    print(json.dumps(rows, default=str, indent=1))
    print(f"coder_agreement before verifier: {R.coder_agreement(diffs, verified=False)}", file=sys.stderr)
    return 0


def cmd_merge(a) -> int:
    A, B = C.load(a.a), C.load(a.b)
    decisions = [R.Decision(**d) for d in json.loads(Path(a.decisions).read_text())] if a.decisions else []
    final, unresolved = R.merge(A, B, decisions, a.verifier, dt.date.today())
    C.dump(final, a.out)
    meta = {
        "agreement": R.coder_agreement(R.compare(A, B), verified=bool(decisions)),
        "unresolved": [asdict(u) for u in unresolved],
    }
    Path(a.out).with_suffix(".meta").write_text(json.dumps(meta, default=str, indent=1))
    print(json.dumps(meta, default=str))
    return 0


def cmd_rows(a) -> int:
    rows = []
    for p in a.paths:
        c = C.load(p)
        meta_p = Path(p).with_suffix(".meta")
        meta = json.loads(meta_p.read_text()) if meta_p.exists() else {"agreement": "single_coder"}
        verified = dt.date.today() if meta["agreement"] != "single_coder" else None
        rows += W.build(c, meta["agreement"], verified)
    df = W.to_frame(rows)
    W.write_csv(df, a.out)
    print(f"{len(df)} rows valid against the reforms schema -> {a.out}")
    return 0


def cmd_tasks(a) -> int:
    """Collect every blocked source and unresolved diff in a run into tasks.csv / tasks.md."""
    d = Path(a.dir)
    pops = {}
    if (d / "places.csv").exists():
        pl = pd.read_csv(d / "places.csv", dtype={"geoid": str})
        pops = dict(zip(pl["geoid"], pl["pop_2020"], strict=False))
    tasks: list[H.HumanTask] = []
    for sub in ("coding_a", "coding_b", "final"):
        for c in _load_all(d / sub) if (d / sub).exists() else []:
            for b in c.blocked:
                tasks.append(
                    H.HumanTask(
                        state=c.state,
                        geoid=c.geoid,
                        place=c.name,
                        era_id=b.era_id or "",
                        question=b.what_to_look_for.split(".")[0],
                        reason=b.reason,
                        url=b.url,
                        what_to_look_for=b.what_to_look_for,
                        fields_to_fill=b.fields,
                        pop_2020=int(pops.get(c.geoid, 0)),
                        notes=b.note or "",
                    )
                )
    for meta in sorted((d / "final").glob("*.meta")) if (d / "final").exists() else []:
        geoid = meta.stem
        c = C.load(d / "final" / f"{geoid}.json")
        for u in json.loads(meta.read_text())["unresolved"]:
            field = u["field"] if u["field"] in H.ALLOWED else "effective_date"
            src = next((ev.url for era in c.eras for fv in era.fields.values() for ev in fv.evidence), "")
            tasks.append(
                H.HumanTask(
                    state=c.state,
                    geoid=geoid,
                    place=c.name,
                    era_id=u["era_key"],
                    question=f"{u['field']} for the rule in force from {u['era_key']}",
                    reason="conflicting_sources",
                    url=src or "(no source opened; search the city code)",
                    what_to_look_for=f"Coders read {u['a']!r} and {u['b']!r}.",
                    fields_to_fill=[field],
                    pop_2020=int(pops.get(geoid, 0)),
                )
            )
    queue, closed = H.triage(tasks)
    H.write_csv(queue + closed, d / "tasks.csv")
    H.write_markdown(queue, d / "tasks.md", f"ADU rule lookups — {d.parent.name} run {d.name}")
    print(f"{len(queue)} open lookups, {len(closed)} closed as no_usable_source -> {d / 'tasks.csv'}")
    return 0


def cmd_ingest(a) -> int:
    bad = 0
    for row in H.read_csv(a.path):
        ans, ev, probs = H.answered(row)
        if probs:
            bad += 1
            print(f"{row['task_id']}: NOT ACCEPTED: {'; '.join(probs)}")
        elif ev:
            print(f"{row['task_id']}: accepted {ans} <- {ev.url}")
    return 1 if bad else 0


def cmd_compare(a) -> int:
    proposed = pd.read_csv(a.rows, dtype={"jurisdiction_geoid": str})
    proposed["effective_date"] = pd.to_datetime(proposed["effective_date"])
    existing = W.read_config(CONFIG_DIR / "reforms" / f"{a.state.lower()}.csv")
    geoids = a.geoids.split(",") if a.geoids else sorted(proposed["jurisdiction_geoid"].unique())
    cmp = W.compare_with_config(proposed, existing, geoids)
    print(cmp.to_string(index=False))
    print("\n" + cmp["match"].value_counts().to_string())
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lotline.rule_agents.adu", description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("run-dir")
    s.add_argument("--state", required=True)
    s.add_argument("--run-id", required=True)
    s.set_defaults(fn=lambda a: print(run_dir(a.state, a.run_id)) or 0)
    s = sp.add_parser("worklist")
    s.add_argument("--state", required=True)
    s.add_argument("--run-id", required=True)
    s.add_argument("--min-pop", type=int, default=2500)
    s.add_argument("--limit", type=int)
    s.add_argument("--geoids")
    s.set_defaults(fn=cmd_worklist)
    s = sp.add_parser("fetch")
    s.add_argument("--state", required=True)
    s.add_argument("urls", nargs="+")
    s.set_defaults(fn=cmd_fetch)
    for name, fn in (("check", cmd_check), ("verify-quotes", cmd_verify_quotes)):
        s = sp.add_parser(name)
        s.add_argument("paths", nargs="+")
        s.set_defaults(fn=fn)
    s = sp.add_parser("diff-coders")
    s.add_argument("a")
    s.add_argument("b")
    s.add_argument("--all", action="store_true")
    s.set_defaults(fn=cmd_diff)
    s = sp.add_parser("merge")
    s.add_argument("a")
    s.add_argument("b")
    s.add_argument("--decisions")
    s.add_argument("--verifier", default=W.VERIFIER)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_merge)
    s = sp.add_parser("rows")
    s.add_argument("paths", nargs="+")
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_rows)
    s = sp.add_parser("tasks")
    s.add_argument("dir")
    s.set_defaults(fn=cmd_tasks)
    s = sp.add_parser("ingest")
    s.add_argument("path")
    s.set_defaults(fn=cmd_ingest)
    s = sp.add_parser("compare")
    s.add_argument("--state", required=True)
    s.add_argument("--rows", required=True)
    s.add_argument("--geoids")
    s.set_defaults(fn=cmd_compare)
    a = ap.parse_args(argv)
    return a.fn(a)
