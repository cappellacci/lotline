"""Buildings per project for missing middle (D-092 deviation 2026-11-15 (d)).

BPS counts buildings, but several 2-4 unit buildings can be one builder's project. If projects are lumpy, a
place-year's count is a compound Poisson: projects arrive at some rate and each brings S buildings. Then the
count's variance is its mean times the **inflation** E[S^2] / E[S] (1 if every project is one building).

Permits are grouped into projects two ways, a lower and an upper bound:
- **same lot** (`same_lot`): same source and parcel ID, issued within `window_days` of the project's first
  permit. Misses a project whose buildings sit on lots split from one parent lot.
- **same day** (`same_day`): same source and issue date. Joins unrelated permits issued on the same day.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MM_TYPES = ("U2", "U3_4")  # `permits.building_type_std` for 2-unit and 3-4 unit buildings
WINDOW_DAYS = 365
BIG = 3  # a "cluster": a project of at least this many buildings


def buildings(p: pd.DataFrame) -> pd.DataFrame:
    """New 2-4 unit building permits with a known type: `building_type_std` in MM_TYPES, type confidence not
    'unknown', not a demolition or conversion. Adds `bldgs` (n_buildings, else 1).

    By hand: U2 (n_buildings blank), U3_4 (n_buildings 2), SFD, U2 demolition -> two rows, bldgs 1 and 2."""
    keep = p["building_type_std"].isin(MM_TYPES) & (p["type_confidence"] != "unknown")
    keep &= ~p["is_demolition"].fillna(False).astype(bool) & ~p["is_conversion"].fillna(False).astype(bool)
    out = p.loc[keep].copy()
    nb = pd.to_numeric(out.get("n_buildings"), errors="coerce") if "n_buildings" in out else np.nan
    out["bldgs"] = pd.Series(nb, index=out.index).fillna(1.0).clip(lower=1.0)
    return out


def same_lot(b: pd.DataFrame, window_days: int = WINDOW_DAYS) -> pd.Series:
    """Buildings per project, grouping by source and parcel ID; within a parcel, a permit more than
    `window_days` after the current project's first permit starts a new project. Rows with no parcel ID or no
    issue date are left out.

    By hand: parcel A on 2020-01-01, 2020-06-01, 2021-03-01 (1 building each) and parcel B on 2020-01-01 with
    2 buildings -> A: {2020-01-01, 2020-06-01} = 2, {2021-03-01} = 1; B = 2 -> sizes [2, 1, 2]."""
    d = b[b["parcel_id"].notna() & b["issue_date"].notna()].copy()
    d["issue_date"] = pd.to_datetime(d["issue_date"])
    d = d.sort_values(["source", "parcel_id", "issue_date"])
    sizes: list[float] = []
    for _, g in d.groupby(["source", "parcel_id"], sort=False):
        start, total = None, 0.0
        for when, n in zip(g["issue_date"], g["bldgs"], strict=True):
            if start is not None and (when - start).days > window_days:
                sizes.append(total)
                start, total = None, 0.0
            if start is None:
                start = when
            total += n
        sizes.append(total)
    return pd.Series(sizes, dtype=float)


def same_day(b: pd.DataFrame) -> pd.Series:
    """Buildings per project, grouping by source and issue date; only rows dated to the day.

    By hand: 2020-01-01 (1 + 1 buildings), 2020-01-02 (3), one row dated to the month -> sizes [2, 3]."""
    d = b[(b["date_precision"] == "day") & b["issue_date"].notna()]
    return d.groupby(["source", pd.to_datetime(d["issue_date"])])["bldgs"].sum().reset_index(drop=True)


def inflation(sizes: pd.Series) -> float:
    """E[S^2] / E[S]: how much project size multiplies a count's variance over a Poisson's.

    By hand: sizes [1, 1, 2] -> (1 + 1 + 4) / 3 / (4 / 3) = 1.5; all ones -> 1."""
    s = np.asarray(sizes, dtype=float)
    return float((s**2).mean() / s.mean()) if len(s) else float("nan")


def share_in_big(sizes: pd.Series, k: int = BIG) -> float:
    """Share of buildings that are in projects of at least `k` buildings.

    By hand: sizes [1, 1, 2, 3] -> 3 / 7."""
    s = np.asarray(sizes, dtype=float)
    return float(s[s >= k].sum() / s.sum()) if s.sum() else float("nan")


def summary(sizes: pd.Series) -> dict:
    """Projects, buildings, mean size, inflation and share of buildings in clusters of BIG or more."""
    s = np.asarray(sizes, dtype=float)
    return {"projects": int(len(s)), "buildings": float(s.sum()),
            "mean_size": float(s.mean()) if len(s) else float("nan"),
            "inflation": inflation(s), f"share_in_{BIG}plus": share_in_big(s)}  # fmt: skip
