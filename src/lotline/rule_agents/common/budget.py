"""Per-place spending limits and a ledger of what each run spent.

Why: in the 2026-11-17 dry runs MM spent ~370k tokens a place and ADU ~200k; a 100-place state would cost
20-35M tokens. Searching for a source that is not online is the most common waste (the place ends as a human
task anyway). So every place gets a budget; when any limit is reached the orchestrator stops researching that
place and hands the open fields to a person (`budget_spent` blocker).

The orchestrator (the main Claude session running `/rules-<cat>`) records each subagent's usage, which the
Agent tool reports when the subagent returns, with `ledger add`; scouts and coders record their own web
searches and fetches. `ledger status` says what is left and whether to stop.

Defaults are working limits, not model parameters. Set a run's own limits once with `ledger limits RUN
--tokens N` (saved in `RUN/limits.json`, so every agent's `ledger status` uses them); `--tokens/--fetches/
--searches` on a single `ledger status` call override both.

2026-11-19 (Burlington VT proof of concept): the scout alone used 88.5k tokens, because the count the Agent
tool reports includes everything the agent reads. At 120k no place got past the scout to a coder, so the
token default is 250k (scout, coder a, a selective coder b and the verifier on one well-documented place).
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Per place, all agents together (see the module note for why 250k).
DEFAULT_LIMITS = {"tokens": 250_000, "fetches": 12, "searches": 8}


@dataclass
class Spend:
    tokens: int = 0
    fetches: int = 0
    searches: int = 0


def ledger_path(run: Path) -> Path:
    return Path(run) / "ledger.jsonl"


def limits_path(run: Path) -> Path:
    return Path(run) / "limits.json"


def set_limits(run: Path, **lim: int) -> dict:
    """Save this run's limits (unset keys keep the default) and return the full set in force."""
    bad = [k for k in lim if k not in DEFAULT_LIMITS]
    if bad:
        raise ValueError(f"unknown limit(s) {bad}; use {sorted(DEFAULT_LIMITS)}")
    if any(v is not None and v <= 0 for v in lim.values()):
        raise ValueError("limits must be positive")
    cur = run_limits(run)
    cur.update({k: v for k, v in lim.items() if v is not None})
    p = limits_path(run)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cur))
    return cur


def run_limits(run: Path) -> dict:
    """The limits in force for a run: the defaults, then anything saved with `set_limits`."""
    p = limits_path(run)
    saved = json.loads(p.read_text()) if p.exists() else {}
    return {**DEFAULT_LIMITS, **saved}


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
    """What is left for `place` and whether to stop, against the run's limits (`run_limits`) with `limits`
    on top. By hand: limits tokens 100, spent 60 + 50 -> left tokens -10, stop True, reason ["tokens"]."""
    lim = {**run_limits(run), **(limits or {})}
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
