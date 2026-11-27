"""Command line for the MM rule agent swarm's deterministic steps. The agents call these through Bash.

    python -m lotline.rule_agents.mm init STATE [--run RUN_ID]      # make the run folder, print its path
    python -m lotline.rule_agents.mm places RUN_DIR [--limit N] [--only GEOID ...]   # + brief.md
    python -m lotline.rule_agents.mm fetch RUN_DIR URL [--geoid G]   # store-first fetch -> JSON (doc_id)
    python -m lotline.rule_agents.mm quote DOC_ID "QUOTE"            # quote in the stored document? page
    python -m lotline.rule_agents.mm check RUN_DIR                   # every findings/*.json passes the checks
    python -m lotline.rule_agents.mm select-b RUN_DIR                # which places get the second coder
    python -m lotline.rule_agents.mm reconcile RUN_DIR               # coder-a vs coder-b -> reconcile/*.json
    python -m lotline.rule_agents.mm handoff RUN_DIR                 # blockers -> out/human-lookups.{csv,md}
    python -m lotline.rule_agents.mm ingest RUN_DIR ANSWERS.csv      # answered lookups -> answers/*.json
    python -m lotline.rule_agents.mm build RUN_DIR                   # final/*.json -> out/reforms_mm_<st>.csv
    python -m lotline.rule_agents.mm compare RUN_DIR [--coded CSV]   # vs config/reforms/<st>.csv

The run folder lives under LOTLINE_DATA_DIR (`rule_agents/mm/<ST>/<run_id>/`), never in the repo. Documents
live in the shared store (`python -m lotline.rule_agents docs ...`); passages for coders come from
`python -m lotline.rule_agents excerpts DOC_ID mm`; spending from `python -m lotline.rule_agents ledger ...`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from lotline.rule_agents.common import budget, pdftext
from lotline.rule_agents.mm import brief, handoff, reconcile, rows
from lotline.rule_agents.mm import compare as cmp
from lotline.rule_agents.mm.findings import PlaceFinding, check, verify_quote
from lotline.rule_agents.mm.places import enumerate_places

REPO = Path(__file__).resolve().parents[4]
CODERS = ("coder-a", "coder-b")


def run_root() -> Path:
    from lotline.io.store import data_dir

    return data_dir() / "rule_agents" / "mm"


def _load(path: Path) -> PlaceFinding:
    return PlaceFinding.model_validate_json(path.read_text())


def _state(run: Path) -> str:
    return run.parent.name.upper()


def cmd_init(a) -> int:
    run = run_root() / a.state.upper() / (a.run or date.today().isoformat())
    for d in ("sources", "findings", "reconcile", "final", "verify", "answers", "text", "out"):
        (run / d).mkdir(parents=True, exist_ok=True)
    print(run)
    return 0


def cmd_places(a) -> int:
    run = Path(a.run)
    st = _state(run)
    from lotline.rule_agents.common.places import read_jurisdictions

    j = read_jurisdictions(st, a.jurisdictions)
    if j is None:
        print(f"no jurisdictions table for {st}: pass --jurisdictions CSV (geoid, name, pop_2020)")
        return 1
    coded_path = REPO / "config" / "reforms" / f"{st.lower()}.csv"
    coded = pd.read_csv(coded_path, dtype={"jurisdiction_geoid": str}) if coded_path.exists() else None
    out = enumerate_places(j, coded, min_pop=a.min_pop, limit=a.limit, only=a.only, skip_coded=a.skip_coded)
    out.to_csv(run / "places.csv", index=False)
    (run / "brief.md").write_text(brief.render(st, run.name, out, coded, REPO / "config"))
    print(out.to_string(index=False))
    print(f"brief -> {run / 'brief.md'}")
    return 0


def cmd_fetch(a) -> int:  # pragma: no cover - network
    from lotline.rule_agents.mm.fetch import get

    facts = {
        "jurisdictions": [a.geoid] if a.geoid else None,
        "states": [_state(Path(a.run))],
        "doc_type": a.doc_type,
    }
    print(get(a.url, Path(a.run).name, refresh=a.refresh, **facts).to_json())
    return 0


def sidecar(snapshot: Path, run: Path | None) -> Path:
    """Where the text an agent read from a PDF outside the store is kept: `<RUN>/text/<name>.txt`."""
    if run is not None:
        return run / "text" / (snapshot.name + ".txt")
    return snapshot.with_name(snapshot.name + ".txt")


def cmd_quote(a) -> int:
    """Check a quote against a stored document (a doc id or an 8+ character prefix) or, for older runs, a
    snapshot path. Prints `found p.N`, `NOT FOUND`, or `NOT CHECKED` for a scan (read the page image)."""
    import re

    if re.fullmatch(r"[0-9a-f]{8,64}", a.snapshot):
        from lotline.rule_agents.common.docstore import DocStore

        status, page = DocStore().quote(a.snapshot, a.quote)
        if status == "image_read":
            print("NOT CHECKED: scanned document; read the page image and set quote_status image_read")
            return 2
        print(f"found p.{page}" if status == "verbatim" else "NOT FOUND")
        return 0 if status == "verbatim" else 1
    p = Path(a.snapshot)
    run = Path(a.run) if a.run else None
    side = sidecar(p, run)
    if p.suffix == ".pdf" and not side.exists():
        alt = p.with_name(p.name + ".txt")
        if alt.exists():
            side = alt
        else:
            pages, chars = pdftext.write_sidecar(p, side)
            if chars / max(pages, 1) < 200:
                print(f"NOT CHECKED: scanned PDF ({chars} characters over {pages} pages); read the page")
                return 2
    text = (side if p.suffix == ".pdf" else p).read_text(errors="replace")
    ok = verify_quote(a.quote, text)
    print("found" if ok else "NOT FOUND")
    return 0 if ok else 1


def cmd_check(a) -> int:
    run = Path(a.run)
    bad = 0
    for p in sorted((run / "findings").glob("*.json")) + sorted((run / "final").glob("*.json")):
        try:
            raw = json.loads(p.read_text())
            f = PlaceFinding.model_validate(raw.get("finding", raw))
        except Exception as exc:  # noqa: BLE001 - report every malformed file, keep going
            print(f"{p.name}: does not parse: {exc}")
            bad += 1
            continue
        for msg in check(f):
            print(f"{p.name}: {msg}")
            bad += 1
    print(f"{bad} problem(s)")
    return 1 if bad else 0


def cmd_reconcile(a) -> int:
    run = Path(a.run)
    n = 0
    for pa in sorted((run / "findings").glob(f"*.{CODERS[0]}.json")):
        geoid = pa.name.split(".")[0]
        pb = run / "findings" / f"{geoid}.{CODERS[1]}.json"
        if not pb.exists():
            print(f"{geoid}: one coder only (nothing to reconcile; write final/ from coder a)")
            n += 1
            continue
        diffs = reconcile.compare(_load(pa), _load(pb))
        out = {
            "geoid": geoid,
            "agreement": reconcile.agreement(diffs),
            "diffs": [{**d.__dict__, "a": str(d.a), "b": str(d.b)} for d in diffs],
        }
        (run / "reconcile" / f"{geoid}.json").write_text(json.dumps(out, indent=1))
        print(f"{geoid}: {len(diffs)} diff(s) ({sum(d.severity == 'major' for d in diffs)} major)")
        n += 1
    if not n:
        print("no coder-a findings in this run yet")
    return 0 if n else 1


def cmd_select_b(a) -> int:
    """Places whose coder-a finding needs the blind second coder (`reconcile.needs_second_coder`)."""
    run = Path(a.run)
    order = []
    if (run / "places.csv").exists():
        order = list(pd.read_csv(run / "places.csv", dtype={"geoid": str})["geoid"])
    n = 0
    for pa in sorted((run / "findings").glob(f"*.{CODERS[0]}.json")):
        geoid = pa.name.split(".")[0]
        pos = order.index(geoid) + 1 if geoid in order else 0
        if budget.status(run, geoid)["stop"]:
            print(f"{geoid}\t- (budget spent: hand off, no coder b)")
            continue
        why = reconcile.needs_second_coder(_load(pa), pos, a.audit_every)
        print(f"{geoid}\t{why or '-'}")
        n += bool(why)
    print(f"{n} place(s) need coder b")
    return 0


def _finals(run: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((run / "final").glob("*.json"))]


def cmd_handoff(a) -> int:
    run = Path(a.run)
    finals = [PlaceFinding.model_validate(d["finding"]) for d in _finals(run)]
    # places not reconciled yet: use the coders' blockers
    done = {f.jurisdiction_geoid for f in finals}
    for p in sorted((run / "findings").glob("*.json")):
        f = _load(p)
        if f.jurisdiction_geoid not in done:
            finals.append(f)
    pops = {}
    places = run / "places.csv"
    if places.exists():
        df = pd.read_csv(places, dtype={"geoid": str})
        pops = dict(
            zip(df["geoid"], df.get("pop", pd.Series(0, index=df.index)).fillna(0).astype(int), strict=True)
        )
    from lotline.rule_agents.common.docstore import DocStore

    tasks = handoff.tasks(finals, pops, docs=DocStore())
    handoff.write_csv(tasks, run / "out" / "human-lookups.csv")
    md = handoff.to_markdown(tasks, f"{_state(run)} missing-middle lookups ({run.name})")
    (run / "out" / "human-lookups.md").write_text(md)
    print(f"{len(tasks)} task(s) -> {run / 'out' / 'human-lookups.csv'}")
    return 0


def cmd_ingest(a) -> int:
    run = Path(a.run)
    bad = 0
    from lotline.rule_agents.common.docstore import DocStore
    from lotline.rule_agents.common.handoff import take_saved_file

    docs = DocStore()
    for row in handoff.read_answers(Path(a.answers)):
        probs = handoff.answer_problems(row)
        if probs:
            bad += 1
            print(f"{row.get('task_id')}: " + "; ".join(probs))
            continue
        doc_id = None
        if (row.get("result") or "").strip() == "found":
            try:
                doc_id = take_saved_file(docs, row, geoid=row["geoid"], category="mm", state=_state(run))
            except FileNotFoundError as exc:
                bad += 1
                print(f"{row.get('task_id')}: {exc}")
                continue
        vals, ev = handoff.answer_to_evidence(row, doc_id=doc_id)
        res = (row.get("result") or "").strip()
        if not res:
            continue
        out = {
            "task_id": row["task_id"],
            "geoid": row["geoid"],
            "result": res,
            "values": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in vals.items()},
            "evidence": [json.loads(e.model_dump_json()) for e in ev],
            "notes": row.get("notes", ""),
        }
        (run / "answers" / f"{row['task_id']}.json").write_text(json.dumps(out, indent=1))
    print(f"{bad} answer(s) need fixing")
    return 1 if bad else 0


def cmd_build(a) -> int:
    run = Path(a.run)
    out_rows = []
    for d in _finals(run):
        f = PlaceFinding.model_validate(d["finding"])
        vd = d.get("verified_date")
        out_rows += rows.place_rows(
            f,
            coder_2=d.get("coder_2"),
            agreement=d.get("agreement", "single_coder"),
            verified_by=d.get("verified_by"),
            verified_date=date.fromisoformat(vd) if vd else None,
            adjudication=d.get("adjudication", ""),
        )
    df = rows.table(out_rows)
    path = run / "out" / f"reforms_mm_{_state(run).lower()}.csv"
    rows.write_csv(df, path)
    print(f"{len(df)} row(s), schema OK -> {path}")
    return 0


def cmd_compare(a) -> int:
    run = Path(a.run)
    st = _state(run).lower()
    agent = pd.read_csv(run / "out" / f"reforms_mm_{st}.csv", dtype={"jurisdiction_geoid": str})
    coded_path = Path(a.coded) if a.coded else REPO / "config" / "reforms" / f"{st}.csv"
    if not coded_path.exists():
        print(f"no coded table at {coded_path} (a new state): nothing to compare with")
        return 0
    coded = pd.read_csv(coded_path, dtype={"jurisdiction_geoid": str})
    res = cmp.compare(agent, coded)
    res.to_csv(run / "out" / "compare.csv")
    print(res.to_string())
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m lotline.rule_agents.mm", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("state")
    s.add_argument("--run")
    s = sub.add_parser("places")
    s.add_argument("run")
    s.add_argument("--jurisdictions")
    s.add_argument("--min-pop", type=int, default=0)
    s.add_argument("--limit", type=int)
    s.add_argument("--only", nargs="*")
    s.add_argument("--skip-coded", action="store_true")
    s = sub.add_parser("fetch")
    s.add_argument("run")
    s.add_argument("url")
    s.add_argument("--geoid", help="place the document governs (recorded in the document store)")
    s.add_argument("--doc-type", help="code_section, ordinance, minutes, staff_report, ...")
    s.add_argument("--refresh", action="store_true", help="look for a newer version even if held")
    s = sub.add_parser("quote")
    s.add_argument("snapshot", help="doc id (or 8+ character prefix), or a snapshot path")
    s.add_argument("quote")
    s.add_argument("--run", help="run folder holding text/ sidecars")
    for name in ("check", "reconcile", "handoff", "build"):
        sub.add_parser(name).add_argument("run")
    s = sub.add_parser("select-b")
    s.add_argument("run")
    s.add_argument("--audit-every", type=int, default=10)
    s = sub.add_parser("ingest")
    s.add_argument("run")
    s.add_argument("answers")
    s = sub.add_parser("compare")
    s.add_argument("run")
    s.add_argument("--coded")
    a = p.parse_args(argv)
    return globals()[f"cmd_{a.cmd.replace('-', '_')}"](a)


if __name__ == "__main__":
    sys.exit(main())
