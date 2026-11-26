"""Place enumeration: which jurisdictions a run researches, in what order.

Input: the state's `jurisdictions` table (`LOTLINE_DATA_DIR/processed/<st>/jurisdictions`, built by the state
adapter) or, for a state with no adapter yet, any CSV with `geoid`, `name` and `pop_2020` columns (e.g. the
Census place list). Zoning is set by places, townships (MN) and counties for their unincorporated area, so
those kinds are kept; regions and the state row are not.

Order: largest first (population is the leverage proxy, LESSONS S-6), with places that already have coded MM
rows marked so a run can skip or re-check them. `limit` keeps a run small (dry runs use 5).
"""

from __future__ import annotations

import pandas as pd

from lotline.rule_agents.mm import THEME

ZONING_KINDS = ("place", "township", "county_unincorporated")
COLUMNS = ["geoid", "county", "place", "kind", "pop", "coded_mm_ids", "priority"]


def enumerate_places(
    jurisdictions: pd.DataFrame,
    coded: pd.DataFrame | None = None,
    *,
    min_pop: int = 0,
    limit: int | None = None,
    only: list[str] | None = None,
    skip_coded: bool = False,
) -> pd.DataFrame:
    """The run's place list. By hand: places A (pop 900), B (pop 5,000, coded), a region R -> B then A,
    R dropped; with skip_coded -> A only; with min_pop 1,000 -> B only."""
    j = jurisdictions.copy()
    if "kind" not in j:
        j["kind"] = "place"
    j = j[j["kind"].isin(ZONING_KINDS)]
    pop = pd.to_numeric(j.get("pop_2020", pd.Series(0, index=j.index)), errors="coerce").fillna(0).astype(int)
    county = j["county_geoid"].astype("string") if "county_geoid" in j else pd.Series("", index=j.index)
    out = pd.DataFrame(
        {
            "geoid": j["geoid"].astype(str),
            "county": county.fillna(""),
            "place": j["name"],
            "kind": j["kind"],
            "pop": pop,
        }
    )
    out = out[out["pop"] >= min_pop]
    ids: dict[str, str] = {}
    if coded is not None and len(coded):
        mm = coded[coded["theme"] == THEME]
        ids = mm.groupby(mm["jurisdiction_geoid"].astype(str))["reform_id"].agg(";".join).to_dict()
    out["coded_mm_ids"] = out["geoid"].map(ids).astype("str").fillna("")
    if only:
        out = out[out["geoid"].isin([str(g) for g in only])]
    if skip_coded:
        out = out[out["coded_mm_ids"] == ""]
    out = out.sort_values(["pop", "geoid"], ascending=[False, True]).head(limit)
    out["priority"] = range(1, len(out) + 1)
    return out[COLUMNS].reset_index(drop=True)
