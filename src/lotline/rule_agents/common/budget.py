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

**Shares (2026-11-19).** One pool per place let whichever agent ran first spend what the others needed: in
South Burlington's ADU run the scout (78k) and the hand-off agent (48k) left nothing for the blind second
coder, the agent that checks the work. So each role also has its own share of the place's tokens
(`ROLE_SHARES`, summing to the pool); an agent that reaches its share stops and hands off, and cannot spend
the coders' part. `ledger status RUN PLACE --agent NAME` checks both the place and the agent's share. Shares
are starting guesses from five one-place test runs (scouts 24-48k, first coders 20-45k, fees enumerators
17-19k); they scale with `--tokens` and can be set per run with `ledger limits RUN --share scout=80000`.
Agents that work for the whole state (ADU's state-law agent) record under the place `_state`, not a town.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Per place, all agents together (see the module note for why 250k).
DEFAULT_LIMITS = {"tokens": 250_000, "fetches": 12, "searches": 8}

# Each role's share of a place's tokens (sums to DEFAULT_LIMITS["tokens"]). "setup": per-place listing before
# the scout (fees enumerator); "review": verifier or reconciler; "handoff": the lookup-list agent.
ROLE_SHARES = {
    "setup": 30_000,
    "scout": 60_000,
    "coder_a": 60_000,
    "coder_b": 50_000,
    "review": 30_000,
    "handoff": 20_000,
}
RESERVED = ("coder_b", "review")  # the checking roles: their unspent shares are held back from the others
STATE = "_state"  # the ledger "place" for agents that work for the whole state


def role(agent: str) -> str:
    """The budget role of an agent name as the commands and agents write it. By hand: 'rules-mm-scout' ->
    'scout'; 'coder-b', 'rules-adu-second-coder', 'rules-fees-second-coder' -> 'coder_b'; 'coder-a',
    'rules-fees-reader' -> 'coder_a'; 'rules-mm-reconciler' -> 'review'; anything else -> 'other' (counted
    against the place only)."""
    a = agent.lower().replace("_", "-")
    if "enumerator" in a or "state-law" in a:
        return "setup"
    if "scout" in a:
        return "scout"
    if "second" in a or "coder-b" in a or "blind" in a or a.endswith("-b"):
        return "coder_b"
    if "coder" in a or "reader" in a:
        return "coder_a"
    if "verifier" in a or "reconciler" in a:
        return "review"
    if "handoff" in a or "hand-off" in a:
        return "handoff"
    return "other"


@dataclass
class Spend:
    tokens: int = 0
    fetches: int = 0
    searches: int = 0


def ledger_path(run: Path) -> Path:
    return Path(run) / "ledger.jsonl"


def limits_path(run: Path) -> Path:
    return Path(run) / "limits.json"


def set_limits(run: Path, shares: dict | None = None, **lim: int) -> dict:
    """Save this run's limits (unset keys keep the default) and any role shares, and return what is in
    force (`run_limits`)."""
    bad = [k for k in (shares or {}) if k not in ROLE_SHARES]
    if bad:
        raise ValueError(f"unknown role(s) {bad}; use {sorted(ROLE_SHARES)}")
    if any(v <= 0 for v in (shares or {}).values()):
        raise ValueError("shares must be positive")
    bad = [k for k in lim if k not in DEFAULT_LIMITS]
    if bad:
        raise ValueError(f"unknown limit(s) {bad}; use {sorted(DEFAULT_LIMITS)}")
    if any(v is not None and v <= 0 for v in lim.values()):
        raise ValueError("limits must be positive")
    p = limits_path(run)
    saved = json.loads(p.read_text()) if p.exists() else {}
    saved.update({k: v for k, v in lim.items() if v is not None})
    if shares:
        saved["shares"] = {**saved.get("shares", {}), **shares}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(saved))
    return run_limits(run)


def run_limits(run: Path) -> dict:
    """The limits in force for a run: the defaults, then anything saved with `set_limits`. `shares` are the
    default shares scaled to the run's token pool, then any saved share. By hand: tokens 150,000 -> scout
    60,000 x 0.6 = 36,000."""
    p = limits_path(run)
    saved = json.loads(p.read_text()) if p.exists() else {}
    out = {**DEFAULT_LIMITS, **{k: v for k, v in saved.items() if k in DEFAULT_LIMITS}}
    scale = out["tokens"] / DEFAULT_LIMITS["tokens"]
    out["shares"] = {r: round(v * scale) for r, v in ROLE_SHARES.items()} | saved.get("shares", {})
    return out


def spent_by_role(run: Path, place: str) -> dict[str, int]:
    """Tokens spent on `place` per role."""
    out: dict[str, int] = defaultdict(int)
    p = ledger_path(run)
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r["place"] == place:
                    out[role(r["agent"])] += r.get("tokens", 0)
    return dict(out)


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


def status(run: Path, place: str, limits: dict | None = None, agent: str | None = None) -> dict:
    """What is left for `place` and whether to stop, against the run's limits (`run_limits`) with `limits`
    on top; with `agent`, also against that agent's role share. By hand: limits tokens 100, spent 60 + 50 ->
    left tokens -10, stop True, reason ["tokens"]. Shares at the default 250k: the scout spent 61,000 -> for
    `--agent rules-mm-scout` stop True, reason ["share:scout"]; for `--agent coder-a` the place still has
    189,000 and coder_a its 60,000, so stop False. The checking roles' unspent shares (`RESERVED`: coder b
    50,000 + review 30,000 = 80,000) are held back from every other role: with 175,000 spent by others the
    place has 75,000 left, less than the 80,000 held, so a hand-off agent stops (reason "held_back") while
    coder b may still run."""
    run_lim = run_limits(run)
    lim = {k: v for k, v in {**run_lim, **(limits or {})}.items() if k in DEFAULT_LIMITS}
    s = spent(run).get(place, Spend())
    left = {k: lim[k] - getattr(s, k) for k in lim}
    over = [k for k, v in left.items() if v <= 0]
    out = {"place": place, "spent": vars(s), "left": left}
    if agent:
        r = role(agent)
        share = run_lim["shares"].get(r)
        if share is not None:
            used = spent_by_role(run, place).get(r, 0)
            out["share"] = {"role": r, "share": share, "spent": used, "left": share - used}
            if used >= share:
                over.append(f"share:{r}")
        if r not in RESERVED:
            by_role = spent_by_role(run, place)
            held = sum(max(0, run_lim["shares"].get(x, 0) - by_role.get(x, 0)) for x in RESERVED)
            out["held_back"] = held
            if left["tokens"] - held <= 0 and "tokens" not in over:
                over.append("held_back")
    out.update(stop=bool(over), reason=over)
    return out


def summary(run: Path) -> list[dict]:
    """One row per place plus a total row: tokens, fetches, searches."""
    rows = [{"place": k, **vars(v)} for k, v in sorted(spent(run).items())]
    if rows:
        rows.append(
            {"place": "TOTAL", **{k: sum(r[k] for r in rows) for k in ("tokens", "fetches", "searches")}}
        )
    return rows
