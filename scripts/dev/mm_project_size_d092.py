#!/usr/bin/env python3
"""Missing middle: buildings per project in city permit files (D-092 deviation 2026-11-15 (d)).

    uv run python scripts/dev/mm_project_size_d092.py --out /tmp/x --dry                  # inputs only
    uv run python scripts/dev/mm_project_size_d092.py --out reports/mm-d092/run13-projects  # Ben's go-ahead

Reads every state's `permits` table through `holdout.apply` (St. Paul, Ramsey, Charlotte and Mecklenburg
also dropped by GEOID and by source). The dry run prints, per source, only the share of all permits with a
parcel ID and dated to the day, and the year range: no count by building type. The run groups 2-4 unit
building permits into projects (`lotline.model.project_size`, same lot and same day) and reports, per source
and pooled, the inflation E[S^2]/E[S] and the share of buildings in projects of 3 or more. Offline:
cached tables only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.model import project_size as ps
from lotline.validation import holdout

STATES = ("MN", "NC", "OH", "TX", "OR")
HOLDOUT_GEOIDS = {"2758000", "27123", "3712000", "37119"}  # St. Paul, Ramsey, Charlotte, Mecklenburg
HOLDOUT_SOURCES = {"stpaul_permits", "meck_permits"}
NOT_PERMITS = {"columbus_variances"}  # zoning variances, not building permits
FIRST_YEAR = 2010
MIN_SHARE = 0.9  # a source is usable for a grouping if this share of its permits carries the field
STOP_BELOW = 1.5  # pre-registered: same-day (upper bound) inflation under this -> stop


def permits(store: DataStore) -> pd.DataFrame:
    out = []
    for st in STATES:
        p = store.read(st.lower(), "permits")
        if p is None or p.empty:
            continue
        p = holdout.apply(p, st.lower(), geoid_col="jurisdiction_geoid", date_col="issue_date",
                          year_col="issue_year")  # fmt: skip
        p = p[
            ~p["jurisdiction_geoid"].astype(str).isin(HOLDOUT_GEOIDS)
            & ~p["source"].isin(HOLDOUT_SOURCES | NOT_PERMITS)
        ]
        out.append(p[p["issue_year"] >= FIRST_YEAR].assign(st=st))
    return pd.concat(out, ignore_index=True)


def coverage(p: pd.DataFrame) -> pd.DataFrame:
    """Per source, over all permits (any type): share with a parcel ID, share dated to the day, years."""
    g = p.groupby(["st", "source"])
    return pd.DataFrame({
        "parcel_id": g["parcel_id"].apply(lambda s: s.notna().mean()),
        "day_dated": g.apply(lambda d: ((d["date_precision"] == "day") & d["issue_date"].notna()).mean(),
                             include_groups=False),
        "first": g["issue_year"].min(), "last": g["issue_year"].max(),
    }).round(3)  # fmt: skip


def main(out: Path, dry: bool) -> None:
    p = permits(DataStore())
    assert not set(p["source"]) & HOLDOUT_SOURCES
    cov = coverage(p)
    cov["same_lot_ok"] = (cov["parcel_id"] >= MIN_SHARE) & (cov["day_dated"] >= MIN_SHARE)
    cov["same_day_ok"] = cov["day_dated"] >= MIN_SHARE
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(cov.to_string())
    if dry:
        return

    # ================= Not run without Ben's go-ahead (D-092 §9) =================
    b = ps.buildings(p)
    res = {"by_source": {}, "pooled": {}}
    for how, fn, ok in (("same_lot", ps.same_lot, "same_lot_ok"), ("same_day", ps.same_day, "same_day_ok")):
        keep = [s for (_, s), v in cov[ok].items() if v]
        sizes = []
        for s in keep:
            z = fn(b[b["source"] == s])
            sizes.append(z)
            res["by_source"].setdefault(s, {})[how] = ps.summary(z)
        res["pooled"][how] = ps.summary(pd.concat(sizes, ignore_index=True)) | {"sources": keep}
    lo, hi = res["pooled"]["same_lot"]["inflation"], res["pooled"]["same_day"]["inflation"]
    res["verdict"] = ("stop" if hi < STOP_BELOW else "raise the compound model" if lo >= STOP_BELOW
                      else "in between: report, Ben decides")  # fmt: skip
    print(json.dumps(res, indent=1, default=float))
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(res, indent=2, default=float))
    cov.to_csv(out / "coverage.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry", action="store_true", help="print the inputs only; write nothing")
    a = ap.parse_args()
    main(a.out, a.dry)
