"""Shared command line for the rule swarms: the document store, passages for coders, and the spending ledger.

    python -m lotline.rule_agents docs find [--geoid G [--county C]] [--state ST] [--category C] [--text ..]
    python -m lotline.rule_agents docs show DOC                   # record + local path
    python -m lotline.rule_agents docs text DOC [--page N]        # stored text (one page)
    python -m lotline.rule_agents docs quote DOC "QUOTE"          # verbatim p.N / image_read / not_found
    python -m lotline.rule_agents docs add FILE --url URL --by INITIALS [--geoid G ...] [--type T]
    python -m lotline.rule_agents docs inbox                      # files a person dropped, not yet added
    python -m lotline.rule_agents docs annotate DOC [--title ..] [--type ..] [--geoid ..] [--outcomes]
    python -m lotline.rule_agents docs history DOC                # earlier and later versions
    python -m lotline.rule_agents docs cited-by DOC
    python -m lotline.rule_agents docs withdraw DOC "REASON"      # lists the citations to re-check
    python -m lotline.rule_agents docs backfill DIR [--by INITIALS]   # one-off import of a manual folder
    python -m lotline.rule_agents docs catalog [--write PATH]     # data-free catalogue (committable)
    python -m lotline.rule_agents excerpts DOC CATEGORY [--max-chars N] [--extra WORD ...] [--pages N ...]
    python -m lotline.rule_agents outline DOC
    python -m lotline.rule_agents ledger add RUN PLACE AGENT [--tokens N] [--fetches N] [--searches N]
    python -m lotline.rule_agents ledger status RUN PLACE [--tokens N] [--fetches N] [--searches N]
    python -m lotline.rule_agents ledger summary RUN

DOC is a doc id or a unique prefix of 8+ characters. Category-specific steps stay in each swarm's own command
line (`python -m lotline.rule_agents.mm ...`).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

from lotline.rule_agents.common import budget, excerpts
from lotline.rule_agents.common.docstore import CATEGORIES, DOC_TYPES, DocStore


def _docs(a) -> int:
    d = DocStore()
    if a.op == "find":
        hits = d.find(
            geoid=a.geoid,
            county=a.county,
            state=a.state,
            category=a.category,
            doc_type=a.type,
            url=a.url,
            text=a.text,
        )
        for h in hits[: a.limit]:
            r = h.doc
            flag = " [MAY CONTAIN OUTCOMES]" if r.may_contain_outcomes else ""
            pg = f" pages {h.pages[:10]}" if h.pages else ""
            print(
                f"{r.doc_id[:12]}  {r.doc_type:13} {r.text_status:9} "
                f"{(r.title or r.first_url)[:70]}{pg}{flag}"
            )
        print(f"{len(hits)} document(s)")
        return 0
    if a.op == "show":
        r = d.get(a.doc)
        if r is None:
            print("unknown document")
            return 1
        print(json.dumps({**asdict(r), "local_path": str(d.root / r.path)}, indent=1))
        return 0
    if a.op == "text":
        print(d.text(a.doc, a.page))
        return 0
    if a.op == "quote":
        status, page = d.quote(a.doc, a.quote)
        print(f"{status}" + (f" p.{page}" if page else ""))
        return 0 if status == "verbatim" else (2 if status == "image_read" else 1)
    if a.op == "add":
        r = d.add(
            Path(a.file),
            url=a.url,
            added_by=f"human:{a.by}",
            retrieved=a.retrieved,
            jurisdictions=a.geoid,
            doc_type=a.type,
            title=a.title,
            categories=a.category,
        )
        print(f"{r.doc_id} {r.text_status} {r.pages} page(s)")
        return 0
    if a.op == "inbox":
        for p in d.pending_inbox():
            print(p)
        return 0
    if a.op == "annotate":
        facts = {
            "title": a.title,
            "doc_type": a.type,
            "jurisdictions": a.geoid,
            "label": a.label,
            "adopted_date": a.adopted,
            "effective_date": a.effective,
            "supersedes": a.supersedes,
            "notes": a.note,
            "categories": a.category,
        }
        if a.outcomes:
            facts["may_contain_outcomes"] = True
        d.annotate(a.doc, **{k: v for k, v in facts.items() if v})
        return 0
    if a.op == "history":
        for r in d.history(a.doc):
            print(f"{r.doc_id[:12]}  {r.label or r.effective_date or r.first_seen[:10]}  {r.first_url}")
        return 0
    if a.op == "cited-by":
        for c in d.cited_by(a.doc):
            print(f"{c.category} {c.row_key} {c.field} p.{c.page} {c.quote[:60]!r}")
        return 0
    if a.op == "withdraw":
        cites = d.withdraw(a.doc, a.reason)
        print(f"withdrawn; {len(cites)} citation(s) to re-check")
        for c in cites:
            print(f"  {c.category} {c.row_key} {c.field}")
        return 0
    if a.op == "backfill":
        return _backfill(d, Path(a.dir), a.by)
    if a.op == "catalog":
        rows = d.catalog_rows()
        out = open(a.write, "w", newline="") if a.write else sys.stdout
        w = csv.DictWriter(out, fieldnames=list(rows[0]) if rows else ["doc_id"])
        w.writeheader()
        w.writerows(rows)
        if a.write:
            out.close()
            print(f"{len(rows)} document(s) -> {a.write}")
        return 0
    return 1


def _backfill(d: DocStore, folder: Path, by: str) -> int:
    """Import files saved by hand before the store existed. URLs come from any `downloads.jsonl` in the
    folder tree (fields `url` and `path`/`file`/`sha256`); files without a known URL are listed, not added."""
    from lotline.io.store import sha256_file

    urls: dict[str, str] = {}
    for log in folder.rglob("downloads.jsonl"):
        for line in log.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            for k in ("sha256", "path", "file", "filename", "local_path"):
                if r.get(k) and r.get("url"):
                    urls[Path(str(r[k])).name if k != "sha256" else r[k]] = r["url"]
    added, skipped = 0, []
    for f in sorted(
        p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in (".pdf", ".html", ".htm")
    ):
        url = urls.get(f.name) or urls.get(sha256_file(f))
        if not url:
            skipped.append(f)
            continue
        d.add(f, url=url, added_by=f"human:{by}")
        added += 1
    print(f"{added} added; {len(skipped)} without a known URL:")
    for f in skipped:
        print(f"  {f}")
    return 0


def _excerpts(a) -> int:
    d = DocStore()
    ps = excerpts.excerpts(d, a.doc, a.category, max_chars=a.max_chars, extra=a.extra, pages=a.pages)
    for p in ps:
        print(p.render() + "\n")
    print(f"-- {len(ps)} passage(s), {sum(len(p.text) for p in ps)} characters")
    return 0


def _outline(a) -> int:
    for page, h in excerpts.outline(DocStore(), a.doc):
        print(f"p.{page:<4} {h}")
    return 0


def _ledger(a) -> int:
    lim = {k: v for k, v in (("tokens", a.tokens), ("fetches", a.fetches), ("searches", a.searches)) if v}
    if a.op == "add":
        budget.add(
            Path(a.run),
            a.place,
            a.agent,
            tokens=a.tokens or 0,
            fetches=a.fetches or 0,
            searches=a.searches or 0,
            note=a.note or "",
        )
        return 0
    if a.op == "status":
        st = budget.status(Path(a.run), a.place, lim)
        print(json.dumps(st))
        return 3 if st["stop"] else 0
    for r in budget.summary(Path(a.run)):
        print(
            f"{r['place']:12} tokens {r['tokens']:>9,}  fetches {r['fetches']:>3}  "
            f"searches {r['searches']:>3}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m lotline.rule_agents", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    dp = sub.add_parser("docs").add_subparsers(dest="op", required=True)
    s = dp.add_parser("find")
    for o in ("--geoid", "--county", "--state", "--url", "--text"):
        s.add_argument(o)
    s.add_argument("--category", choices=CATEGORIES)
    s.add_argument("--type", choices=DOC_TYPES)
    s.add_argument("--limit", type=int, default=30)
    for name in ("show", "history", "cited-by"):
        dp.add_parser(name).add_argument("doc")
    s = dp.add_parser("text")
    s.add_argument("doc")
    s.add_argument("--page", type=int)
    s = dp.add_parser("quote")
    s.add_argument("doc")
    s.add_argument("quote")
    s = dp.add_parser("add")
    s.add_argument("file")
    s.add_argument("--url", required=True)
    s.add_argument("--by", required=True, help="your initials")
    s.add_argument("--retrieved")
    s.add_argument("--geoid", nargs="*")
    s.add_argument("--type", choices=DOC_TYPES)
    s.add_argument("--title")
    s.add_argument("--category", nargs="*", choices=CATEGORIES)
    dp.add_parser("inbox")
    s = dp.add_parser("annotate")
    s.add_argument("doc")
    for o in ("--title", "--label", "--adopted", "--effective", "--supersedes", "--note"):
        s.add_argument(o)
    s.add_argument("--type", choices=DOC_TYPES)
    s.add_argument("--geoid", nargs="*")
    s.add_argument("--category", nargs="*", choices=CATEGORIES)
    s.add_argument("--outcomes", action="store_true", help="may contain permit counts (holdout risk)")
    s = dp.add_parser("withdraw")
    s.add_argument("doc")
    s.add_argument("reason")
    s = dp.add_parser("backfill")
    s.add_argument("dir")
    s.add_argument("--by", default="ben")
    s = dp.add_parser("catalog")
    s.add_argument("--write")

    s = sub.add_parser("excerpts")
    s.add_argument("doc")
    s.add_argument("category", choices=sorted(excerpts.KEYWORDS))
    s.add_argument("--max-chars", type=int, default=6000)
    s.add_argument("--extra", nargs="*")
    s.add_argument("--pages", nargs="*", type=int)
    sub.add_parser("outline").add_argument("doc")

    lp = sub.add_parser("ledger").add_subparsers(dest="op", required=True)
    for name in ("add", "status"):
        s = lp.add_parser(name)
        s.add_argument("run")
        s.add_argument("place")
        if name == "add":
            s.add_argument("agent")
            s.add_argument("--note")
        for o in ("--tokens", "--fetches", "--searches"):
            s.add_argument(o, type=int)
    lp.add_parser("summary").add_argument("run")

    a = p.parse_args(argv)
    return {"docs": _docs, "excerpts": _excerpts, "outline": _outline, "ledger": _ledger}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
