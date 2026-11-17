"""Compare an agent run's MM rows with the already-coded rows (dry runs and regression checks).

For each place: the cap path (largest `unit_cap` in force on 1 July, as `rule_tags.cap_in_force` reads it)
over the comparison years, the first event year (first year the cap rises, ignoring `[predates]` rows,
which the engine puts in force from 1990), the date basis of the event row, and the by-right flag of the
highest-cap row. A place matches when the event year and final cap match; differences are listed for the
dry-run note. Reads only rule rows, never permit outcomes, so holdouts are untouched.
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from lotline.model import rule_tags
from lotline.rule_agents.mm import THEME
from lotline.rule_agents.mm.dates import basis_from_notes

YEARS = tuple(range(2010, 2027))


def summary(rows: pd.DataFrame, years: Sequence[int] = YEARS) -> pd.DataFrame:
    """One row per place: final_cap, event_year (None if none), event_basis, by_right, n_rules."""
    mm = rows[rows["theme"] == THEME].copy()
    for c in ("announced_date", "effective_date", "adoption_date", "end_date"):
        if c in mm:
            mm[c] = pd.to_datetime(mm[c], errors="coerce")
    mm = rule_tags.apply(mm)
    out = []
    for g, r in mm.groupby(mm["jurisdiction_geoid"].astype(str)):
        path = [rule_tags.cap_in_force(r, y) for y in years]
        ev = next((years[i] for i in range(1, len(years)) if path[i] > path[i - 1]), None)
        if ev is None and path[0] > 1:
            ev_label = "predates"
        else:
            ev_label = ev
        setting = rule_tags.event_setting_rows(r, years)
        basis = None
        if setting:
            row = r.loc[setting[0]]
            basis = basis_from_notes(row.get("coding_notes"), row.get("adoption_date"))
        caps = pd.to_numeric(r["unit_cap"], errors="coerce")
        top = r.loc[caps.idxmax()] if caps.notna().any() else None
        out.append(
            {
                "jurisdiction_geoid": g,
                "final_cap": path[-1],
                "event_year": ev_label,
                "event_basis": basis,
                "by_right": None if top is None else top.get("by_right"),
                "n_rules": len(r),
            }
        )
    return pd.DataFrame(out).set_index("jurisdiction_geoid") if out else pd.DataFrame()


def compare(agent: pd.DataFrame, coded: pd.DataFrame, years: Sequence[int] = YEARS) -> pd.DataFrame:
    """Side by side for the places in `agent`: `match` is True when event year and final cap agree.
    By hand: coded cap 3 from 2020 vs agent cap 3 from 2020 -> match; agent cap 2 -> no match."""
    a = summary(agent, years)
    c = summary(coded[coded["jurisdiction_geoid"].astype(str).isin(a.index)], years)
    both = a.join(c, lsuffix="_agent", rsuffix="_coded", how="left")
    both["match"] = (both["event_year_agent"].astype(str) == both["event_year_coded"].astype(str)) & (
        both["final_cap_agent"] == both["final_cap_coded"]
    )
    return both
