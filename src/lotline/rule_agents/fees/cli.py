# ruff: noqa: E501  (plain-language strings and notes)
"""`python -m lotline.rule_agents.fees <command>`: the deterministic helpers the fees agents call.

    prototypes                         the prototype homes and valuations (from proforma.yaml)
    fetch RUN URL --geoid G [--doc-type T]   store-first polite fetch (common.fetch.get) -> JSON with doc_id or blocker
    quotecheck ITEMS                   check each item's quote against its stored document (verbatim / image_read)
    reconcile C1 C2 --out DIR          pair the two coders' items -> pairs.jsonl, items.merged.jsonl
    build ITEMS --out DIR              items -> rows.csv (schema-validated), rows_low.csv, build_report.md
    tasks JSONL... --out DIR           human tasks -> human_tasks.csv, human_tasks.md
    ingest-tasks CSV --out FILE        answered human tasks -> items (saved files go into the document store)
    compare ROWS --state ST [--places] run rows vs config/fees/<st>.csv

No command runs a model or reads outcome data. Reading documents, the spending ledger, `doctor` and `import` are
the shared core's: `python -m lotline.rule_agents docs|excerpts|outline|ledger|doctor|import ...`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from lotline.rule_agents.fees import build, compare, handoff, reconcile
from lotline.rule_agents.fees.prototype import prototypes
from lotline.rule_agents.fees.records import read_items, read_jsonl, write_items

CATEGORY = "fees"


def cmd_prototypes(_: argparse.Namespace) -> None:
    for t, p in prototypes().items():
        print(
            f"{t:6} units={p.units} sqft/unit={p.sqft_per_unit:,.0f} valuation=${p.valuation:,.0f} bedrooms={p.bedrooms_per_unit}"
        )


def cmd_fetch(a: argparse.Namespace) -> None:  # pragma: no cover - network
    """Store first, then robots.txt, known refusals, one spaced request (common.fetch.get)."""
    from lotline.rule_agents.common.fetch import get

    run = Path(a.run)
    facts = {"jurisdictions": [a.geoid], "states": [a.state] if a.state else None, "doc_type": a.doc_type}
    print(
        get(a.url, CATEGORY, run.name, refresh=a.refresh, **{k: v for k, v in facts.items() if v}).to_json()
    )


def check_quote(item, docs) -> tuple[str, str | None]:
    """(quote status, note) for one item. With a doc id held in the store: the store's check (`verbatim`,
    `image_read` for a scan, else not found). Without one: the shared text check against the saved file at
    `local_path`. Only a match gives `verbatim`; a `verbatim` claim that does not match becomes `not_checked`."""
    from lotline.rule_agents.common import pdftext
    from lotline.rule_agents.common.text import verify_quote

    if item.doc_id and docs is not None and docs.get(item.doc_id) is not None:
        status, page = docs.quote(item.doc_id, item.quote)
        if status == "verbatim":
            return "verbatim", None
        if status == "image_read":
            return ("image_read" if item.quote_status == "image_read" else "not_checked"), "scanned document"
        return "not_checked", f"quote not found in doc {item.doc_id[:12]}"
    if not item.local_path:
        return ("not_checked" if item.quote_status == "verbatim" else item.quote_status), "no stored document"
    path = _resolve(item.local_path)
    try:
        raw = path.read_bytes()
        text = pdftext.extract(path)[0] if raw[:5] == b"%PDF-" else raw.decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001 - a damaged file leaves the quote unchecked, never crashes the run
        keep = "image_read" if item.quote_status in ("verbatim", "image_read") else item.quote_status
        return keep, f"{path.name}: unreadable ({type(e).__name__})"
    if verify_quote(item.quote, text):
        return "verbatim", None
    return ("not_checked" if item.quote_status == "verbatim" else item.quote_status), (
        f"quote not found word for word in {item.local_path}"
    )


def cmd_quotecheck(a: argparse.Namespace) -> None:
    """Re-check every quote (`check_quote`); the item file is rewritten with the statuses found."""
    from lotline.rule_agents.common.docstore import DocStore

    docs = DocStore()
    items, n_ok, notes = read_items(a.items), 0, []
    for i, it in enumerate(items):
        if not it.quote:
            continue
        status, note = check_quote(it, docs)
        items[i] = it.model_copy(update={"quote_status": status})
        n_ok += status == "verbatim"
        if note:
            notes.append(f"{it.item_id}: {note}")
    write_items(items, a.items)
    print(f"{n_ok} quote(s) matched word for word")
    print("\n".join(notes))


def _resolve(local_path: str) -> Path:
    """A saved document's path: absolute as given, or relative to LOTLINE_DATA_DIR (as manifest paths are)."""
    p = Path(local_path).expanduser()
    if p.is_absolute():
        return p
    from lotline.io.store import data_dir

    return data_dir() / p


def cmd_reconcile(a: argparse.Namespace) -> None:
    c1, c2 = read_items(a.coder1), read_items(a.coder2)
    pairs = reconcile.pair(c1, c2)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pairs.jsonl").write_text("".join(json.dumps(p) + "\n" for p in pairs))
    write_items(reconcile.merge(c1, c2, pairs, date.today()), out / "items.merged.jsonl")
    print(json.dumps(reconcile.summary(pairs)))


def cmd_build(a: argparse.Namespace) -> None:
    res = build.build(read_items(a.items))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ok = "not run (no rows)"
    if not res.rows.empty:
        build.validate(res.rows)
        ok = "passed"
    res.rows.to_csv(out / "rows.csv", index=False, date_format="%Y-%m-%d")
    res.low_rows.to_csv(out / "rows_low.csv", index=False, date_format="%Y-%m-%d")
    lines = (
        [
            "# Build report",
            "",
            f"- rows: {len(res.rows)} (schema check {ok}); low-confidence rows for a person: {len(res.low_rows)}",
            f"- excluded items (escrows, totals, minimums): {len(res.excluded)}",
            "",
            "## Warnings",
            "",
        ]
        + [f"- {w}" for w in res.warnings]
        + ["", "## Excluded", ""]
        + [f"- {i.item_id}: {i.fee_type} ({i.applies_when or ''})" for i in res.excluded]
    )
    (out / "build_report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:4]))


def cmd_tasks(a: argparse.Namespace) -> None:
    from lotline.rule_agents.common.docstore import DocStore

    docs = DocStore()
    raw = [t for f in a.files for t in read_jsonl(Path(f))]
    count: dict[str, int] = {}
    tasks = []
    for t in raw:
        t.pop("task_id", None)
        # agents sometimes write lists; the task format holds plain text
        t = {k: (" ".join(map(str, v)) if isinstance(v, list) else v) for k, v in t.items()}
        count[t["place_geoid"]] = count.get(t["place_geoid"], 0) + 1
        tasks.append(handoff.make_task(count[t["place_geoid"]], docs=docs, **t))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    handoff.write_csv(tasks, out / "human_tasks.csv")
    (out / "human_tasks.md").write_text(handoff.to_markdown(tasks))
    print(f"{len(tasks)} task(s)")


def cmd_ingest(a: argparse.Namespace) -> None:
    from lotline.rule_agents.common.docstore import DocStore

    items = handoff.answers_to_items(handoff.read_csv(Path(a.csv)), docs=DocStore())
    write_items(items, Path(a.out))
    print(f"{len(items)} answered task(s) -> items")


def cmd_compare(a: argparse.Namespace) -> None:
    from lotline.config import load_fees

    run = pd.read_csv(a.rows, dtype={"jurisdiction_geoid": str})
    existing = load_fees(a.state)
    if existing is None:
        print(f"no config/fees/{a.state.lower()}.csv yet (a new state): nothing to compare with")
        return
    places = a.places.split(",") if a.places else sorted(run["jurisdiction_geoid"].unique())
    table = compare.compare(run, existing, places)
    print(table.to_string(index=False))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="python -m lotline.rule_agents.fees",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prototypes").set_defaults(fn=cmd_prototypes)
    p = sub.add_parser("fetch")
    p.add_argument("run")
    p.add_argument("url")
    p.add_argument("--geoid", required=True, help="the place whose fee this document sets")
    p.add_argument("--state")
    p.add_argument(
        "--doc-type", default="fee_schedule", help="fee_schedule, rate_ordinance, budget_book, ..."
    )
    p.add_argument("--refresh", action="store_true", help="look for a newer version even if held")
    p.set_defaults(fn=cmd_fetch)
    p = sub.add_parser("quotecheck")
    p.add_argument("items", type=Path)
    p.set_defaults(fn=cmd_quotecheck)  # noqa: E702
    p = sub.add_parser("reconcile")
    p.add_argument("coder1", type=Path)
    p.add_argument("coder2", type=Path)
    p.add_argument("--out", required=True)  # noqa: E702
    p.set_defaults(fn=cmd_reconcile)
    p = sub.add_parser("build")
    p.add_argument("items", type=Path)
    p.add_argument("--out", required=True)  # noqa: E702
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("tasks")
    p.add_argument("files", nargs="+")
    p.add_argument("--out", required=True)  # noqa: E702
    p.set_defaults(fn=cmd_tasks)
    p = sub.add_parser("ingest-tasks")
    p.add_argument("csv")
    p.add_argument("--out", required=True)  # noqa: E702
    p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("compare")
    p.add_argument("rows")
    p.add_argument("--state", required=True)
    p.add_argument("--places")  # noqa: E702
    p.set_defaults(fn=cmd_compare)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
