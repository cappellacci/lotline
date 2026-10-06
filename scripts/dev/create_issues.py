#!/usr/bin/env python3
"""Create Lotline's GitHub labels, milestones and issue backlog from docs/build/issues.csv.

Dry run by default (prints what it would do). Use --apply to make changes.
Idempotent: existing labels, milestones and issues (matched by exact title) are skipped.
Needs the GitHub CLI (`gh`) logged in, run from inside the repo. Standard library only.

    python scripts/dev/create_issues.py            # dry run
    python scripts/dev/create_issues.py --apply    # create
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "docs" / "build" / "issues.csv"

# Milestone due dates (ET dates; GitHub stores them as UTC timestamps).
MILESTONES = {
    "M0 Bootstrap": ("2026-10-07", "Repo bootstrap, pushed before Oct 7 09:00 ET (registration period)."),
    "M1 Core contracts": ("2026-10-20", "schemas-v1, IO, holdouts, national adapters."),
    "M2 MN+NC V0": ("2026-10-31", "Minnesota and North Carolina ingestion and V0 reports."),
    "M3 TX+OH V0, V1/V2": ("2026-11-10", "Texas and Ohio V0; baseline (V1) and mechanism (V2); comparables v1; benchmark state chosen."),
    "M4 Prereg, V3/V4, freezes": ("2026-11-24", "prereg-v1 tag; causal estimates; backtests; blind predictions frozen by Nov 17."),
    "M5 Unblind + scorecard": ("2026-12-01", "Unblind V5 tests; V7; validation scorecard."),
    "M6 Product + submission": ("2026-12-16", "App, documents, deck, video; submit before 23:59 ET."),
}

LABEL_COLORS = {
    "ws:": "1f6b52",
    "ladder:": "6f42c1",
    "ben": "b3541e",
    "contract-change": "d73a4a",
    "data-source": "0e8a16",
    "blocked": "000000",
}
EXTRA_LABELS = ["contract-change", "data-source", "blocked"]


def gh(args: list[str], *, apply: bool, capture: bool = True) -> str:
    """Run a gh command; in dry-run mode, print state-changing commands instead of running them."""
    mutating = args[:2] in (["label", "create"], ["issue", "create"]) or (args[0] == "api" and "-X" in args)
    if mutating and not apply:
        print("DRY RUN:", "gh", " ".join(args))
        return ""
    r = subprocess.run(["gh", *args], capture_output=capture, text=True)
    if r.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed:\n{r.stderr}")
    return r.stdout


def color_for(label: str) -> str:
    for prefix, color in LABEL_COLORS.items():
        if label.startswith(prefix) or label == prefix:
            return color
    return "cccccc"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="actually create labels, milestones and issues")
    ap.add_argument("--owner", default="cappellacci", help="expected GitHub owner of the repo (safety check)")
    a = ap.parse_args()

    rows = list(csv.DictReader(CSV_PATH.open(newline="")))
    labels = sorted({l for r in rows for l in r["labels"].split(";") if l} | set(EXTRA_LABELS))

    repo = json.loads(gh(["repo", "view", "--json", "nameWithOwner"], apply=True))["nameWithOwner"]
    if repo.split("/")[0].lower() != a.owner.lower():
        sys.exit(f"Refusing to run: this checkout points at {repo}, expected owner '{a.owner}'. Check `git remote -v`.")

    existing_labels = {l["name"] for l in json.loads(gh(["label", "list", "--limit", "500", "--json", "name"], apply=True) or "[]")}
    for name in labels:
        if name not in existing_labels:
            gh(["label", "create", name, "--color", color_for(name)], apply=a.apply)
    existing_ms = {m["title"]: m["number"] for m in json.loads(gh(["api", f"repos/{repo}/milestones?state=all&per_page=100"], apply=True) or "[]")}
    for title, (due, desc) in MILESTONES.items():
        if title not in existing_ms:
            gh(["api", "-X", "POST", f"repos/{repo}/milestones", "-f", f"title={title}", "-f", f"description={desc}",
                "-f", f"due_on={due}T23:59:00Z"], apply=a.apply)

    existing_issues = {i["title"] for i in json.loads(gh(["issue", "list", "--state", "all", "--limit", "1000", "--json", "title"], apply=True) or "[]")}
    created = skipped = 0
    for r in rows:
        if r["title"] in existing_issues:
            skipped += 1
            continue
        args = ["issue", "create", "--title", r["title"], "--body", r["body"], "--milestone", r["milestone"]]
        for l in filter(None, r["labels"].split(";")):
            args += ["--label", l]
        gh(args, apply=a.apply)
        created += 1
    mode = "created" if a.apply else "would create"
    print(f"{mode} {created} issues; skipped {skipped} existing. Labels: {len(labels)}. Milestones: {len(MILESTONES)}.")


if __name__ == "__main__":
    main()
