#!/usr/bin/env python3
"""Apply PR #417's proposed ADU rule rows to config/reforms/*.csv.

Ben accepted the rows on 2026-11-13 ("Yes, do both"); the same script built the rows the version C test read
(branch ws/adu-version-c). Open items in #417 stay as the research coded them. For each place in the proposed file, its own local ADU rows (`<ST>-<geoid>-...`) are replaced by
the proposed rows; state-law rows are untouched. A superseded row ends on its successor's effective date.
`coverage_zones` carries over from the existing row with the same id, else from the place's existing row in
force on the proposed row's effective date.

    python scripts/dev/apply_adu_rules_proposed_2026_11.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROPOSED = ROOT / "docs/research/ordinances/adu-fit-rules-proposed-2026-11.csv"
FILES = {"MN": "mn.csv", "NC": "nc.csv", "OH": "oh.csv", "OR": "or.csv", "TX": "tx.csv"}


def main() -> None:
    prop = pd.read_csv(PROPOSED, dtype=str, keep_default_na=False).replace("", pd.NA)
    succ = prop.dropna(subset=["supersedes"]).set_index("supersedes")["effective_date"]
    for st, fn in FILES.items():
        path = ROOT / "config/reforms" / fn
        cur = pd.read_csv(path, dtype=str, keep_default_na=False).replace("", pd.NA)
        cols = list(cur.columns)
        mine = prop[prop["state"] == st].copy()
        geoids = set(mine["jurisdiction_geoid"])
        own = (cur["theme"] == "adu") & cur.apply(
            lambda r: r["jurisdiction_geoid"] in geoids
            and str(r["reform_id"]).startswith(f"{st}-{r['jurisdiction_geoid']}-"),
            axis=1,
        )
        old = cur[own]
        zones = []
        for r in mine.itertuples():
            same = old[old["reform_id"] == r.reform_id]
            z = same["coverage_zones"].iloc[0] if len(same) else pd.NA
            if pd.isna(z):
                o = old[old["jurisdiction_geoid"] == r.jurisdiction_geoid]
                eff = pd.to_datetime(o["effective_date"], errors="coerce")
                end = pd.to_datetime(o["end_date"], errors="coerce")
                d = pd.Timestamp(r.effective_date)
                o = o[(eff <= d) & (end.isna() | (end > d))]
                z = o["coverage_zones"].dropna().iloc[0] if o["coverage_zones"].notna().any() else pd.NA
            zones.append(z)
        mine["coverage_zones"] = zones
        mine["end_date"] = mine["reform_id"].map(succ)
        out = pd.concat([cur[~own], mine[cols]], ignore_index=True)
        out.to_csv(path, index=False)
        print(f"{st}: replaced {int(own.sum())} rows for {len(geoids)} places with {len(mine)} proposed rows")


if __name__ == "__main__":
    main()
