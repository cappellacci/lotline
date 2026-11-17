"""The run brief every agent reads first (`brief.md` in the run folder).

Facts, not instructions to search: the state's holdouts (from `config/states/<st>.yaml`), the state-law MM
rows already coded (so coders code local rules only, LESSONS DT-7), the places already coded, and the default
effective-date rule where the lessons record one (DT-1). For a state not listed, coders read each ordinance's
own effective-date clause and hand off when it is silent.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from lotline.rule_agents.mm import THEME

# Default effective-date readings recorded in the Oct-Nov 2026 lessons (LESSONS DT-1). A coder still quotes
# the ordinance; the default only says what a silent ordinance means, and the date is marked "(computed)".
STATE_EFFECTIVE_RULES = {
    "OH": "Ohio R.C. 731.29: 30 days after passage, unless passed as an emergency (then on passage) or the "
    "city charter says otherwise (oh-lookups-brief-2026-11-01.md).",
    "MN": "Minn. Stat. §645.15 and the city charter: usually on publication after adoption; quote the "
    "published-ordinance date (mn second coding 2026-11-02).",
    "OR": "Oregon: 30 days after adoption unless the ordinance has an emergency clause (ws-or-local-rules).",
}
NO_DEFAULT = "No default recorded: read each ordinance's own effective-date clause; if silent, hand off."


def holdouts(state: str, config_dir: Path) -> list[dict]:
    path = config_dir / "states" / f"{state.lower()}.yaml"
    if not path.exists():
        return []
    return list((yaml.safe_load(path.read_text()) or {}).get("holdouts") or [])


def render(
    state: str, run_id: str, places: pd.DataFrame, coded: pd.DataFrame | None, config_dir: Path
) -> str:
    """The brief as Markdown. By hand: a state with a holdout St. Paul and a state-law row "27" -> both listed."""
    st = state.upper()
    lines = [
        f"# /rules-mm brief: {st}, run {run_id}",
        "",
        "Question per place: when did 2-4 homes first become allowed on lots zoned single-family, by right or",
        "by permit, in which districts, and what did the code allow just before? Window: rules in force from",
        "2010-01-01; anything older still in force is coded with date_basis 'predates' (never dropped).",
        "",
        f"Effective-date default: {STATE_EFFECTIVE_RULES.get(st, NO_DEFAULT)}",
        "",
        "## Holdouts (code their rules; never write any permit, housing or outcome number)",
    ]
    hs = holdouts(st, config_dir)
    lines += [f"- {h.get('place')} ({h.get('geoid')}): {h.get('test_id', '')}" for h in hs] or ["- none"]
    lines += ["", "## State-law MM rows already coded (do not re-code; note 'state law also applies')"]
    state_rows = []
    if coded is not None and len(coded):
        mm = coded[coded["theme"] == THEME]
        geo = mm["jurisdiction_geoid"].astype(str)
        state_rows = mm[
            (geo.str.len() == 2) | mm["reform_id"].astype(str).str.contains("-landdiv|state", regex=True)
        ]
    if len(state_rows):
        lines += [f"- {r.reform_id}: {str(r.component)[:120]}" for r in state_rows.itertuples()][:40]
    else:
        lines += ["- none"]
    lines += ["", "## Places in this run (priority order)"]
    for r in places.itertuples():
        done = f" - already coded: {r.coded_mm_ids}" if r.coded_mm_ids else ""
        lines.append(f"{r.priority}. {r.place} ({r.geoid}, pop {r.pop:,}){done}")
    lines += [
        "",
        "## Rules (every agent)",
        "- Network only through `python -m lotline.rule_agents.mm fetch RUN URL` (robots first, one try) or",
        "  WebSearch. Never retry a refused URL with curl, another user agent or browser headers.",
        "- No records requests, emails or forms. Write nothing outside this run folder. Run no model scripts.",
    ]
    return "\n".join(lines) + "\n"
