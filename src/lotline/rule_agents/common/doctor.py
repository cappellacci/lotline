"""Setup check before a first rule-agent run: is everything a run needs in place for this state?

Each check returns (ok, label, what to do). Nothing here changes anything; it only looks.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path

CATEGORY_COMMANDS = {"mm": "rules-mm", "adu": "rules-adu", "fees": "rules-fees"}


def checks(
    state: str, repo: Path, *, category: str | None = None, data_root: Path | None = None
) -> list[tuple[bool, str, str]]:
    """Every check for `state`; with `category`, a missing command for that category is a problem (others are
    listed for information)."""
    from lotline.io.store import DataStore, data_dir

    out: list[tuple[bool, str, str]] = []
    root = Path(data_root or data_dir()).expanduser()

    for mod in ("pypdf", "httpx", "pandas", "pydantic"):
        ok = importlib.util.find_spec(mod) is not None
        out.append((ok, f"Python package {mod}", "run `uv sync` in the repo"))

    ok = root.exists() and os.access(root, os.W_OK)
    out.append(
        (
            ok,
            f"data folder {root} exists and is writable",
            "create it, or set LOTLINE_DATA_DIR in .env to a folder you can write to",
        )
    )

    claude = shutil.which("claude") is not None
    out.append(
        (
            claude,
            "Claude Code (`claude`) is installed",
            "install Claude Code (claude.com/claude-code); without it, fill the lookup sheet by hand",
        )
    )

    for cat, cmd in CATEGORY_COMMANDS.items():
        there = (repo / ".claude" / "commands" / f"{cmd}.md").exists()
        need = category in (None, cat) if category else False
        label = f"/{cmd} ({cat}) " + ("is in this repo" if there else "is not in this version of the repo")
        out.append((there or not need, label, "update the repo (git pull) to get this category's agents"))

    j = DataStore(root).read(state.lower(), "jurisdictions") if root.exists() else None
    out.append(
        (
            j is not None and len(j) > 0,
            f"jurisdictions table for {state.upper()}",
            f"run `lotline fetch {state.lower()}` if the state has an adapter, or pass "
            "`--jurisdictions <csv>` (columns geoid, name, pop_2020, county_geoid) to the places step",
        )
    )

    for table in ("reforms", "fees"):
        p = repo / "config" / table / f"{state.lower()}.csv"
        out.append(
            (
                True,
                f"config/{table}/{state.lower()}.csv "
                + (
                    "exists (agents compare with it; coders never see it)"
                    if p.exists()
                    else "not there yet (the import step creates it)"
                ),
                "",
            )
        )

    try:
        from lotline.validation import holdout

        hs = holdout.holdouts_for(state.upper())
        blind = [h for h in hs if not getattr(h, "released_on", None)]
        note = (
            f"{len(blind)} held-back place(s): agents never open outcome data for them"
            if blind
            else "no held-back places"
        )
        out.append((True, f"validation holdouts for {state.upper()}: {note}", ""))
    except Exception:  # noqa: BLE001 - a state with no holdout registry simply has none
        out.append((True, f"validation holdouts for {state.upper()}: none registered", ""))
    return out


def render(results: list[tuple[bool, str, str]]) -> str:
    lines = []
    for ok, label, fix in results:
        lines.append(f"{'ok  ' if ok else 'FIX '} {label}" + ("" if ok or not fix else f"\n       -> {fix}"))
    bad = sum(not ok for ok, _, _ in results)
    lines.append("Ready." if not bad else f"{bad} thing(s) to fix before a run.")
    return "\n".join(lines)
