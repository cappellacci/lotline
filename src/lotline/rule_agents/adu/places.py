"""Place enumeration (the worklist) and the holdout guard.

The worklist is every place (and, where one code governs it, county remainder) in the state's jurisdictions
table, largest first, with what is already coded. Lessons: uncoded is not "none" (15 NC places read as none
only because nobody coded them), and work ranked by size is the work that gets finished.

The holdout guard lists places whose outcomes are still blind. Rule coding of those places is allowed (rules
are inputs), but agents must not open permit counts, ADU dashboards, staff reports with activity numbers or
anything under `reports/`, and must drop search snippets that quote such numbers (lessons §6: Bend, St. Paul).
"""

from __future__ import annotations

import pandas as pd

from lotline.validation import holdout


def worklist(
    jurisdictions: pd.DataFrame,
    existing: pd.DataFrame | None,
    min_pop: int = 0,
    limit: int | None = None,
    kinds=("place", "county_unincorporated"),
) -> pd.DataFrame:
    """Places to code, largest first, with the ADU reform_ids already in config (`existing`)."""
    j = jurisdictions[jurisdictions["kind"].isin(kinds)].copy()
    j["pop_2020"] = pd.to_numeric(j["pop_2020"]).fillna(0).astype(int)
    j = j[j["pop_2020"] >= min_pop].sort_values(["pop_2020", "geoid"], ascending=[False, True])
    coded: dict[str, list[str]] = {}
    if existing is not None and len(existing):
        adu = existing[existing["theme"] == "adu"]
        for g, ids in adu.groupby("jurisdiction_geoid")["reform_id"]:
            coded[str(g)] = sorted(ids)
    j["existing_adu_rows"] = j["geoid"].map(lambda g: ";".join(coded.get(str(g), [])))
    j["rank"] = range(1, len(j) + 1)
    cols = ["rank", "geoid", "name", "kind", "county_geoid", "pop_2020", "existing_adu_rows"]
    out = j[[c for c in cols if c in j.columns]]
    return out.head(limit) if limit else out


def blind_holdouts(state: str) -> list[dict]:
    """Holdouts of the state still blind (the project's registry, lotline.validation.holdout)."""
    return [
        {"test_id": h.test_id, "geoid": h.geoid, "place": h.place, "outcome_from": str(h.outcome_from)}
        for h in holdout.still_blind(holdout.holdouts_for(state))
    ]


def covered_by_state_law(places: pd.DataFrame, min_pop_exclusive: int, kinds=("place",)) -> pd.DataFrame:
    """Places a population-threshold state law covers (strict inequality, as Oregon's SB 1051 '> 2,500').

    The state-law agent gives the threshold and which population source the statute uses; near-threshold
    places (within 5%) are flagged for a check against the state's certified estimates (Oregon: PSU)."""
    p = places[places["kind"].isin(kinds)].copy()
    p["covered"] = p["pop_2020"] > min_pop_exclusive
    p["near_threshold"] = (p["pop_2020"] - min_pop_exclusive).abs() <= 0.05 * min_pop_exclusive
    return p
