#!/usr/bin/env python3
"""Fold logbook.d/*.md fragments into LOGBOOK.md (and claude/LOGBOOK.md if present).

Fragments are sorted by the date in their heading, then by the time the fragment was first committed (so
same-day entries keep the order the work happened), then by file name, and numbered LB-NNN after the last
entry already in LOGBOOK.md. The merged fragments are then deleted. Dry run by default. Standard library only.

    python scripts/dev/merge_logbook.py            # dry run
    python scripts/dev/merge_logbook.py --apply    # append, then delete fragments
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADING = re.compile(r"^### LB-(\w+) · (\d{4}-\d{2}-\d{2}) · ", re.M)


def last_number(logbook: str) -> int:
    nums = [int(n) for n, _ in HEADING.findall(logbook) if n.isdigit()]
    return max(nums, default=0)


def added_at(path: Path) -> int:
    """Unix time of the commit that added `path`; uncommitted or outside git sorts last."""
    r = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%ct", "-1", "--", path.name],
        cwd=path.parent,
        capture_output=True,
        text=True,
    )
    out = r.stdout.strip()
    return int(out) if r.returncode == 0 and out.isdigit() else sys.maxsize


def load_fragments(frag_dir: Path) -> list[tuple[str, Path, str]]:
    """Return (date, path, text) for each fragment, sorted by date, commit time, then file name."""
    out = []
    for path in sorted(frag_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        text = path.read_text().strip()
        heads = HEADING.findall(text)
        if len(heads) != 1:
            sys.exit(f"{path}: expected one 'LB-NNN · date' heading, found {len(heads)}")
        out.append((heads[0][1], path, text))
    return sorted(out, key=lambda t: (t[0], added_at(t[1]), t[1].name))


def merge(logbook: str, fragments: list[tuple[str, Path, str]]) -> tuple[str, list[str]]:
    """Return the new logbook text and the assigned entry ids."""
    n = last_number(logbook)
    entries, ids = [], []
    for _, _, text in fragments:
        n += 1
        ids.append(f"LB-{n:03d}")
        entries.append(HEADING.sub(lambda m, i=ids[-1]: f"### {i} · {m.group(2)} · ", text, count=1))
    if not entries:
        return logbook, ids
    return logbook.rstrip("\n") + "\n\n" + "\n\n".join(entries) + "\n", ids


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write LOGBOOK.md and delete merged fragments")
    a = ap.parse_args(argv)

    targets = [p for p in (root / "LOGBOOK.md", root / "claude" / "LOGBOOK.md") if p.exists()]
    if not targets:
        sys.exit("LOGBOOK.md not found")
    fragments = load_fragments(root / "logbook.d")
    if not fragments:
        print("no fragments to merge")
        return 0

    new_text, ids = merge(targets[0].read_text(), fragments)
    for (_, path, _), entry_id in zip(fragments, ids, strict=True):
        print(f"{entry_id}  <- {path.relative_to(root)}")
    if not a.apply:
        print("dry run; use --apply to write")
        return 0
    for target in targets:  # the project copy is kept identical to the repo copy (CLAUDE.md)
        target.write_text(new_text)
    for _, path, _ in fragments:
        path.unlink()
    print(f"appended {len(ids)} entries to {', '.join(str(t.relative_to(root)) for t in targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
