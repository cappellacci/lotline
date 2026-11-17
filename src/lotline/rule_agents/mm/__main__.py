"""Command line for the MM rule agent swarm's deterministic steps. The agents call these through Bash.

    python -m lotline.rule_agents.mm init STATE [--run RUN_ID]      # make the run folder, print its path
    python -m lotline.rule_agents.mm fetch RUN_DIR URL               # polite fetch -> JSON (snapshot/blocker)
    python -m lotline.rule_agents.mm quote SNAPSHOT "QUOTE"          # is the quote in the saved page?
    python -m lotline.rule_agents.mm check RUN_DIR                   # every findings/*.json passes the checks
    python -m lotline.rule_agents.mm reconcile RUN_DIR               # coder-a vs coder-b -> reconcile/*.json
    python -m lotline.rule_agents.mm handoff RUN_DIR                 # blockers -> out/human-lookups.{csv,md}
    python -m lotline.rule_agents.mm ingest RUN_DIR ANSWERS.csv      # answered lookups -> answers/*.json
    python -m lotline.rule_agents.mm build RUN_DIR                   # final/*.json -> out/reforms_mm_<st>.csv
    python -m lotline.rule_agents.mm compare RUN_DIR [--coded CSV]   # vs config/reforms/<st>.csv

The run folder lives under LOTLINE_DATA_DIR (`rule_agents/mm/<ST>/<run_id>/`), never in the repo.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from lotline.rule_agents.mm import compare as cmp
from lotline.rule_agents.mm import handoff, reconcile, rows
from lotline.rule_agents.mm.findings import PlaceFinding, check, verify_quote

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
    for d in ("sources", "findings", "reconcile", "final", "verify", "answers", "out"):
        (run / d).mkdir(parents=True, exist_ok=True)
    print(run)
    return 0


def cmd_fetch(a) -> int:  # pragma: no cover - network
    from lotline.rule_agents.mm.fetch import get

    r = get(a.url, Path(a.run).name)
    print(
        json.dumps(
            {
                "url": r.url,
                "path": str(r.path) if r.path else None,
                "status": r.status,
                "blocker": r.blocker,
                "detail": r.detail,
            }
        )
    )
    return 0


def cmd_quote(a) -> int:
    p = Path(a.snapshot)
    side = p.with_name(p.name + ".txt")  # PDFs: the text the agent read from it, saved beside it
    if p.suffix == ".pdf" and not side.exists():
        print(f"NOT CHECKED: save the PDF's text as {side.name} first")
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
            print(f"{geoid}: no second coding yet")
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
    return 0 if n else 1


def _finals(run: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((run / "final").glob("*.json"))]


def cmd_handoff(a) -> int:
    run = Path(a.run)
    finals = [PlaceFinding.model_validate(d["finding"]) for d in _finals(run)]
    # blockers recorded by either coder count too: the reconciler may not have copied them
    for p in sorted((run / "findings").glob("*.json")):
        finals.append(_load(p))
    pops = {}
    places = run / "places.csv"
    if places.exists():
        df = pd.read_csv(places, dtype={"geoid": str})
        pops = dict(
            zip(df["geoid"], df.get("pop", pd.Series(0, index=df.index)).fillna(0).astype(int), strict=True)
        )
    tasks = handoff.tasks(finals, pops)
    handoff.write_csv(tasks, run / "out" / "human-lookups.csv")
    md = handoff.to_markdown(tasks, f"{_state(run)} missing-middle lookups ({run.name})")
    (run / "out" / "human-lookups.md").write_text(md)
    print(f"{len(tasks)} task(s) -> {run / 'out' / 'human-lookups.csv'}")
    return 0


def cmd_ingest(a) -> int:
    run = Path(a.run)
    bad = 0
    for row in handoff.read_answers(Path(a.answers)):
        probs = handoff.answer_problems(row)
        if probs:
            bad += 1
            print(f"{row.get('task_id')}: " + "; ".join(probs))
            continue
        vals, ev = handoff.answer_to_evidence(row)
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
    s = sub.add_parser("fetch")
    s.add_argument("run")
    s.add_argument("url")
    s = sub.add_parser("quote")
    s.add_argument("snapshot")
    s.add_argument("quote")
    for name in ("check", "reconcile", "handoff", "build"):
        sub.add_parser(name).add_argument("run")
    s = sub.add_parser("ingest")
    s.add_argument("run")
    s.add_argument("answers")
    s = sub.add_parser("compare")
    s.add_argument("run")
    s.add_argument("--coded")
    a = p.parse_args(argv)
    return globals()[f"cmd_{a.cmd}"](a)


if __name__ == "__main__":
    sys.exit(main())
