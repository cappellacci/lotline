"""`python -m lotline.rule_agents.adu <command>`: the deterministic steps the ADU agents call.

Run folder (outside the repo): `$LOTLINE_DATA_DIR/rule_agents/adu/<ST>/<run_id>/`
    places.csv            worklist (rank, geoid, name, pop); existing_rows.csv: orchestrator only
    state_law.json        state-law baseline (rules-adu-state-law)
    coding_a/<geoid>.json primary coder        score/<geoid>.json     which values get a second look
    coding_b/<geoid>.json blind second coder (targeted to weak values, or full for the audit sample)
    decisions/<geoid>.json verifier rulings    final/<geoid>.json     merged coding
    tasks.csv / tasks.md  human lookups        rows.csv               proposed `reforms` rows
    compare.md            comparison with config/reforms/<st>.csv (dry runs)

Commands: run-dir, worklist, fetch, check, verify-quotes, score, diff-coders, merge, rows, tasks, ingest,
compare.
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
from lotline.rule_agents.adu import fetch as F
from lotline.rule_agents.adu import handoff as H
from lotline.rule_agents.adu import places as P
from lotline.rule_agents.adu import reconcile as R
from lotline.rule_agents.adu import rows as W
from lotline.rule_agents.adu import score as S
from lotline.rule_agents.common import handoff as CH
from lotline.rule_agents.common.docstore import DocStore

CATEGORY_ADU = "adu"


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
    """Store-first fetch into the shared document store; prints one JSON line per URL (doc_id, blocker,
    and `text_path`, the page-marked text sidecar coders read)."""
    docs = DocStore()
    facts = {"jurisdictions": [a.geoid] if a.geoid else None, "states": [a.state.upper()]}
    for url in a.urls:
        r = F.get(url, a.run_id, docs=docs, **facts)
        d = json.loads(r.to_json())
        d["text_path"] = str(docs.sidecar(r.doc_id)) if r.doc_id else None
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
    """Every verbatim quote with a cached text copy (HTML or text PDF) must be found in it; for PDFs the page
    is reported and must match `page` when the coder gave one. Image-read and human quotes are listed only."""
    docs = DocStore()
    code = 0
    for p in a.paths:
        c = C.load(p)
        for era in c.eras:
            evs = [e for fv in era.fields.values() for e in fv.evidence] + [
                e for d in era.dates for e in d.evidence
            ]
            for e in evs:
                status, page = S.quote_check(e, docs)
                note = f" p.{page}" if page else ""
                if page and e.page and e.page != page:
                    note += f" (coder said p.{e.page})"
                label = {"found": "OK     ", "missing": "MISSING", "unchecked": "BY-EYE "}[status]
                print(f"{c.geoid} {era.era_id}: {label} {e.url}{note}")
                code |= status == "missing"
    return code


def cmd_score(a) -> int:
    """Score coder A's values; write score/<geoid>.json; print who needs which second look."""
    docs = DocStore()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tally = {"none": 0, "targeted": 0, "full": 0}
    for p in a.paths:
        c = C.load(p)
        src = Path(a.sources) / f"{c.geoid}.json" if a.sources else None
        sources = json.loads(src.read_text()) if src and src.exists() else None
        card = S.score(c, docs, sources, a.audit_rate)
        (out / f"{c.geoid}.json").write_text(S.to_json(card) + "\n")
        tally[card.mode] += 1
        extra = f"; {len(card.uncoded_amendments)} uncoded amendment(s)" if card.uncoded_amendments else ""
        counts = f"strong {card.strong}, weak {card.weak}, looks {len(card.looks)}"
        print(f"{c.geoid} {c.name}: {card.mode:8} {counts}{extra}")
    t = tally
    print(f"second coder: {t['full']} full (audit), {t['targeted']} targeted, {t['none']} skipped")
    return 0


def _scope(score_path: str | None) -> set[str] | None:
    if not score_path:
        return None
    card = json.loads(Path(score_path).read_text())
    return set(card["second_coder_fields"]) if card["mode"] == "targeted" else None


def cmd_diff(a) -> int:
    diffs = R.compare(C.load(a.a), C.load(a.b), _scope(a.score))
    rows = [asdict(d) for d in diffs if a.all or d.status != "agree"]
    print(json.dumps(rows, default=str, indent=1))
    print(f"coder_agreement before verifier: {R.coder_agreement(diffs, verified=False)}", file=sys.stderr)
    return 0


def cmd_merge(a) -> int:
    A, B = C.load(a.a), C.load(a.b)
    decisions = [R.Decision(**d) for d in json.loads(Path(a.decisions).read_text())] if a.decisions else []
    fields = _scope(a.score)
    final, unresolved = R.merge(A, B, decisions, a.verifier, dt.date.today(), fields)
    C.dump(final, a.out)
    agreement = R.coder_agreement(
        R.compare(A, B, fields), verified=bool(decisions), targeted=fields is not None
    )
    meta = {
        "agreement": agreement,
        "second_look": sorted(fields) if fields is not None else None,
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
        rows += W.build(c, meta["agreement"], verified, meta.get("second_look"))
    df = W.to_frame(rows)
    W.write_csv(df, a.out)
    print(f"{len(df)} rows valid against the reforms schema -> {a.out}")
    return 0


def settled_fields_dropped(fields: list[str], final: C.PlaceCoding | None) -> list[str]:
    """Fields a blocked page would answer, minus those every final era already has on primary evidence."""
    if "all" in fields:
        fields = list(H.ALLOWED)
    if final is None or not final.eras:
        return fields

    def settled(f: str) -> bool:
        return all(
            (fv := e.fields.get(f)) is not None
            and fv.value is not None
            and any(x.primary for x in fv.evidence)
            for e in final.eras
        )

    return [f for f in fields if f not in C.RUBRIC_FIELDS or not settled(f)]


def cmd_tasks(a) -> int:
    """Collect every blocked source and unresolved diff in a run into tasks.csv / tasks.md."""
    d = Path(a.dir)
    pops = {}
    if (d / "places.csv").exists():
        pl = pd.read_csv(d / "places.csv", dtype={"geoid": str})
        pops = dict(zip(pl["geoid"], pl["pop_2020"], strict=False))
    tasks: list[H.HumanTask] = []
    docs = DocStore()
    finals = {c.geoid: c for c in _load_all(d / "final")} if (d / "final").exists() else {}
    for sub in ("coding_a", "coding_b", "final"):
        for c in _load_all(d / sub) if (d / sub).exists() else []:
            for b in c.blocked:
                fields = settled_fields_dropped(b.fields, finals.get(c.geoid))
                if b.fields and not fields:
                    continue  # the verifier already settled every field this page would answer
                tasks.append(
                    H.HumanTask(
                        state=c.state,
                        geoid=c.geoid,
                        place=c.name,
                        era_id=b.era_id or "",
                        question=b.look_for.split(".")[0],
                        blocker=b.kind,
                        url=b.url,
                        what_to_look_for=b.look_for,
                        fields_to_fill=fields,
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
                    blocker="conflicting_sources",
                    url=src or "(no source opened; search the city code)",
                    what_to_look_for=f"Coders read {u['a']!r} and {u['b']!r}.",
                    fields_to_fill=[field],
                    pop_2020=int(pops.get(geoid, 0)),
                )
            )
    for t in tasks:
        t.held_docs = CH.held_docs(docs, t.geoid, CATEGORY_ADU)
    queue, closed = H.triage(tasks)
    H.write_csv(queue + closed, d / "tasks.csv")
    H.write_markdown(queue, d / "tasks.md", f"ADU rule lookups — {d.parent.name} run {d.name}")
    n_opt = sum(t.optional for t in queue)
    print(f"{len(queue)} lookups ({n_opt} optional: records request only) -> {d / 'tasks.csv'}")
    return 0


def cmd_ingest(a) -> int:
    bad = 0
    docs = DocStore()
    for row in H.read_csv(a.path):
        ans, ev, probs = H.answered(row, docs)
        if probs:
            bad += 1
            print(f"{row['task_id']}: NOT ACCEPTED: {'; '.join(probs)}")
        elif ev:
            held = f" (saved file {ev.doc_id[:12]})" if ev.doc_id else ""
            print(f"{row['task_id']}: accepted {ans} <- {ev.url}{held}")
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
    s.add_argument("--run-id", required=True)
    s.add_argument("--geoid", help="the place the document is for (recorded on the stored document)")
    s.add_argument("urls", nargs="+")
    s.set_defaults(fn=cmd_fetch)
    for name, fn in (("check", cmd_check), ("verify-quotes", cmd_verify_quotes)):
        s = sp.add_parser(name)
        s.add_argument("paths", nargs="+")
        s.set_defaults(fn=fn)
    s = sp.add_parser("score")
    s.add_argument("paths", nargs="+")
    s.add_argument("--sources", help="RUN_DIR/sources (for uncoded-amendment leads)")
    s.add_argument("--out", required=True)
    s.add_argument("--audit-rate", type=float, default=S.AUDIT_RATE)
    s.set_defaults(fn=cmd_score)
    s = sp.add_parser("diff-coders")
    s.add_argument("a")
    s.add_argument("b")
    s.add_argument("--all", action="store_true")
    s.add_argument("--score", help="score/<geoid>.json: compare only the targeted fields")
    s.set_defaults(fn=cmd_diff)
    s = sp.add_parser("merge")
    s.add_argument("a")
    s.add_argument("b")
    s.add_argument("--decisions")
    s.add_argument("--score", help="score/<geoid>.json: a targeted second look compares only its fields")
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
