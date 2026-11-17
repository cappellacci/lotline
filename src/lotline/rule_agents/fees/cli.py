# ruff: noqa: E501  (plain-language strings and notes)
"""`python -m lotline.rule_agents.fees <command>`: the deterministic helpers the fees agents call.

    prototypes                         the prototype homes and valuations (from proforma.yaml)
    robots URL                         may we fetch URL? (robots.txt, our user agent)
    fetch URL --state ST --name FILE   polite download into LOTLINE_DATA_DIR (manifest); prints a block reason
    quotecheck ITEMS                   mark quotes found word for word in each item's saved file as verbatim
    reconcile C1 C2 --out DIR          pair the two coders' items -> pairs.jsonl, items.merged.jsonl
    build ITEMS --out DIR              items -> rows.csv (schema-validated), rows_low.csv, build_report.md
    tasks JSONL... --out DIR           human tasks -> human_tasks.csv, human_tasks.md
    ingest-tasks CSV --out FILE        answered human tasks -> items
    compare ROWS --state ST [--places] run rows vs config/fees/<st>.csv

No command runs a model or reads outcome data.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

from lotline.rule_agents.fees import access, build, compare, handoff, reconcile
from lotline.rule_agents.fees.prototype import assumptions, prototypes
from lotline.rule_agents.fees.records import read_items, read_jsonl, write_items

SOURCE = "rule-agents-fees"


def _text_of(path: Path) -> str:
    """Plain text of a saved HTML or text file. PDFs need a PDF reader (not a dependency yet): None."""
    raw = path.read_bytes()
    if raw[:5] == b"%PDF-":
        raise ValueError(
            f"{path} is a PDF: read it with the Read tool; quotes from it are image_read until a PDF text reader is approved"
        )
    s = raw.decode("utf-8", errors="replace")
    if path.suffix.lower() in (".html", ".htm") or "<html" in s[:2000].lower():
        s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", s)
        s = re.sub(r"(?s)<[^>]+>", " ", s)
        s = html.unescape(s)
    return s


def cmd_prototypes(_: argparse.Namespace) -> None:
    for t, p in prototypes().items():
        print(
            f"{t:6} units={p.units} sqft/unit={p.sqft_per_unit:,.0f} valuation=${p.valuation:,.0f} bedrooms={p.bedrooms_per_unit}"
        )


def _robots(url: str) -> bool:
    from lotline.io.http import client

    with client(timeout=30) as http:
        r = http.get(access.robots_url(url))
    if r.status_code in (401, 403):
        raise PermissionError(f"robots.txt answered HTTP {r.status_code}: http_403_waf")
    return access.robots_allows(r.text if r.status_code == 200 else None, url)


def cmd_robots(a: argparse.Namespace) -> None:
    try:
        ok = _robots(a.url)
    except PermissionError as e:
        print(json.dumps({"url": a.url, "allowed": False, "reason": "http_403_waf", "detail": str(e)}))
        return
    print(json.dumps({"url": a.url, "allowed": ok, "reason": None if ok else "robots_disallow"}))


def _space_requests(store_root: Path, host: str) -> None:
    gap = float(assumptions()["min_seconds_between_requests_per_host"])
    stamp = store_root / ".ratelimit" / f"{SOURCE}-{host}"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    last = float(stamp.read_text() or 0) if stamp.exists() else 0.0
    wait = last + gap - time.time()
    if wait > 0:
        time.sleep(wait)
    stamp.write_text(f"{time.time():.3f}")


def cmd_fetch(a: argparse.Namespace) -> None:
    import httpx

    from lotline.io.http import fetch
    from lotline.io.store import DataStore

    out = {"url": a.url, "path": None, "reason": None}
    try:
        if not _robots(a.url):
            out["reason"] = "robots_disallow"
    except PermissionError:
        out["reason"] = "http_403_waf"
    if out["reason"] is None:
        store = DataStore()
        dest = store.raw(SOURCE, a.state.lower()) / a.name
        _space_requests(store.root, httpx.URL(a.url).host)
        try:
            path = fetch(
                a.url,
                dest,
                store=store,
                source=SOURCE,
                license="public record (fee schedule)",
                adapter="rule_agents.fees",
                adapter_version="0.1",
                retries=1,
            )
            body = path.read_bytes()[:20000].decode("utf-8", errors="replace")
            out["reason"] = access.access_reason(200, body if not body.startswith("%PDF-") else "")
            out["path"] = str(path)
        except httpx.HTTPStatusError as e:
            out["reason"] = access.access_reason(e.response.status_code, e.response.text[:20000])
        except httpx.TransportError as e:
            out["reason"] = "http_error"
            out["detail"] = str(e)
    print(json.dumps(out))


def cmd_quotecheck(a: argparse.Namespace) -> None:
    items, n_ok, notes = read_items(a.items), 0, []
    for i, it in enumerate(items):
        if not (it.quote and it.local_path) or it.quote_status == "verbatim":
            continue
        try:
            text = _text_of(Path(it.local_path))
        except (OSError, ValueError) as e:
            notes.append(f"{it.item_id}: {e}")
            continue
        if access.quote_found(it.quote, text):
            items[i] = it.model_copy(update={"quote_status": "verbatim"})
            n_ok += 1
        else:
            notes.append(f"{it.item_id}: quote not found word for word in {it.local_path}")
    write_items(items, a.items)
    print(f"{n_ok} quote(s) matched word for word")
    print("\n".join(notes))


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
    raw = [t for f in a.files for t in read_jsonl(Path(f))]
    count: dict[str, int] = {}
    tasks = []
    for t in raw:
        t.pop("task_id", None)
        count[t["place_geoid"]] = count.get(t["place_geoid"], 0) + 1
        tasks.append(handoff.make_task(count[t["place_geoid"]], **t))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    handoff.write_csv(tasks, out / "human_tasks.csv")
    (out / "human_tasks.md").write_text(handoff.to_markdown(tasks))
    print(f"{len(tasks)} task(s)")


def cmd_ingest(a: argparse.Namespace) -> None:
    items = handoff.answers_to_items(handoff.read_csv(Path(a.csv)))
    write_items(items, Path(a.out))
    print(f"{len(items)} answered task(s) -> items")


def cmd_compare(a: argparse.Namespace) -> None:
    from lotline.config import load_fees

    run = pd.read_csv(a.rows, dtype={"jurisdiction_geoid": str})
    existing = load_fees(a.state)
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
    p = sub.add_parser("robots")
    p.add_argument("url")
    p.set_defaults(fn=cmd_robots)  # noqa: E702
    p = sub.add_parser("fetch")
    p.add_argument("url")
    p.add_argument("--state", required=True)
    p.add_argument("--name", required=True)  # noqa: E702
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
