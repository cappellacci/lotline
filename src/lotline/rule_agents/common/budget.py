"""Per-place spending limits and a ledger of what each run spent.

Why: in the 2026-11-17 dry runs MM spent ~370k tokens a place and ADU ~200k; a 100-place state would cost
20-35M tokens. Searching for a source that is not online is the most common waste (the place ends as a human
task anyway). So every place gets a budget; when any limit is reached the orchestrator stops researching that
place and hands the open fields to a person (`budget_spent` blocker).

The orchestrator (the main Claude session running `/rules-<cat>`) records each subagent's usage, which the
Agent tool reports when the subagent returns, with `ledger add`; scouts and coders record their own web
searches and fetches. `ledger status` says what is left and whether to stop.

Defaults are working limits set from the 2026-11-17 dry runs, not model
parameters; override per run with `--tokens/--fetches/--searches` on `ledger status`.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Per place, all agents together. ADU's dry run after its scoring step needed ~120k for a well-documented
# place; anything beyond that was searching for sources that turned out not to be online.
DEFAULT_LIMITS = {"tokens": 120_000, "fetches": 12, "searches": 8}


@dataclass
class Spend:
    tokens: int = 0
    fetches: int = 0
    searches: int = 0


def ledger_path(run: Path) -> Path:
    return Path(run) / "ledger.jsonl"


def add(
    run: Path, place: str, agent: str, *, tokens: int = 0, fetches: int = 0, searches: int = 0, note: str = ""
) -> None:
    """Append one spending line (append-only)."""
    if min(tokens, fetches, searches) < 0:
        raise ValueError("spending cannot be negative")
    p = ledger_path(run)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        fh.write(
            json.dumps(
                {
                    "at": datetime.now(UTC).replace(microsecond=0).isoformat(),
                    "place": place,
                    "agent": agent,
                    "tokens": tokens,
                    "fetches": fetches,
                    "searches": searches,
                    "note": note,
                }
            )
            + "\n"
        )


def spent(run: Path) -> dict[str, Spend]:
    out: dict[str, Spend] = defaultdict(Spend)
    p = ledger_path(run)
    if not p.exists():
        return {}
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        s = out[r["place"]]
        s.tokens += r.get("tokens", 0)
        s.fetches += r.get("fetches", 0)
        s.searches += r.get("searches", 0)
    return dict(out)


def status(run: Path, place: str, limits: dict | None = None) -> dict:
    """What is left for `place` and whether to stop. By hand: limits tokens 100, spent 60 + 50 -> left
    tokens -10, stop True, reason ["tokens"]."""
    lim = {**DEFAULT_LIMITS, **(limits or {})}
    s = spent(run).get(place, Spend())
    left = {k: lim[k] - getattr(s, k) for k in lim}
    over = [k for k, v in left.items() if v <= 0]
    return {"place": place, "spent": vars(s), "left": left, "stop": bool(over), "reason": over}


def summary(run: Path) -> list[dict]:
    """One row per place plus a total row: tokens, fetches, searches."""
    rows = [{"place": k, **vars(v)} for k, v in sorted(spent(run).items())]
    if rows:
        rows.append(
            {"place": "TOTAL", **{k: sum(r[k] for r in rows) for k in ("tokens", "fetches", "searches")}}
        )
    return rows
