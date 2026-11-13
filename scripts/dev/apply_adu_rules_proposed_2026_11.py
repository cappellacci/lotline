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

import re
import subprocess
from io import StringIO
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROPOSED = ROOT / "docs/research/ordinances/adu-fit-rules-proposed-2026-11.csv"
FILES = {"MN": "mn.csv", "NC": "nc.csv", "OH": "oh.csv", "OR": "or.csv", "TX": "tx.csv"}
TODO = ROOT / "docs/research/ordinances/adu-fit-rules-todo-2026-11-12.csv"
BASE = "86b9ce50"  # main when the rows were applied (config/reforms untouched by #417)
URL = re.compile(r"https://[^\s;,)\]]+")


def _note(notes, add: str) -> str:
    return add if pd.isna(notes) or not str(notes).strip() else f"{notes} {add}"


def _https(s) -> bool:
    return isinstance(s, str) and all(u.strip().startswith("https://") for u in s.split(";"))


MODEL_FIELDS = ["effective_date", "status", "supersedes", "by_right", "owner_occ", "min_lot_sqft", "adu_max_sqft",
                "adu_detached_allowed", "adus_per_lot", "parking_min_per_unit"]  # fmt: skip


def keep_unchanged(mine: pd.DataFrame, old: pd.DataFrame) -> pd.DataFrame:
    """Where a research row has the id of a replaced row and agrees with it on every model field, keep the replaced
    row (its hand-checked citation and coder) and only set its end date."""
    o = old.set_index("reform_id")
    out = []
    for r in mine.to_dict("records"):
        rid = r["reform_id"]
        if rid in o.index and all(str(o.at[rid, f]) == str(r[f]) for f in MODEL_FIELDS):
            k = o.loc[rid].to_dict() | {"reform_id": rid, "end_date": r["end_date"],
                                        "coverage_zones": r["coverage_zones"]}  # fmt: skip
            out.append(k)
        else:
            out.append(r)
    return pd.DataFrame(out, columns=mine.columns)


def conform(mine: pd.DataFrame, old: pd.DataFrame, todo: pd.DataFrame) -> pd.DataFrame:
    """Bring research rows to config conventions (tests/states/*/test_reforms.py), keeping every fact in the row.

    - source_url must be https URLs only. A local copy moves into coding_notes. The link is taken, in order, from
      the source field itself, the replaced config row with the same id, the place's replaced ADU rows, the row's
      own notes, then the worklist; the notes say which.
    - single_coder rows carry no coder_2: the second coder's name moves into the notes.
    - coder is "claude" (the workstream is named in the notes, "WS-ADU-RULES proposed").
    - a no-ADU row (adus_per_lot 0) is not by right and its notes start "NO ADU RULE".
    """
    mine = mine.copy()
    mine["coder"] = "claude"
    for i, r in mine.iterrows():
        src = r["source_url"]
        if not _https(src):
            src_txt = "" if pd.isna(src) else str(src)
            same = old.loc[old["reform_id"] == r["reform_id"], "source_url"]
            place = old.loc[old["jurisdiction_geoid"] == r["jurisdiction_geoid"], "source_url"]
            row_txt = " ".join(str(r[c]) for c in ("coding_notes", "source_section", "second_coder_flags")
                               if pd.notna(r.get(c)))  # fmt: skip
            tt = todo[todo["geoid"] == r["jurisdiction_geoid"]]
            tries = [
                ("the source field", URL.findall(src_txt)),
                ("the replaced row", [u for u in same if _https(u)]),
                ("the place's replaced rows", [u for u in place if _https(u)][:1]),
                ("the row's notes", URL.findall(row_txt)[:1]),
                ("the worklist", URL.findall(" ".join(tt["source_url"]) + " " + " ".join(tt["notes"]))[:1]),
            ]
            where, urls = next(((w, u) for w, u in tries if u), (None, []))
            if not urls:
                raise SystemExit(f"{r['reform_id']}: no https source found")
            mine.at[i, "source_url"] = "; ".join(dict.fromkeys(u.rstrip(".") for u in urls))
            local = f" Local copy read: {src_txt}." if src_txt else ""
            mine.at[i, "coding_notes"] = _note(r["coding_notes"], f"[config 2026-11-13] Source link from {where}.{local}")
        if r["coder_agreement"] == "single_coder" and pd.notna(r["coder_2"]):
            mine.at[i, "coding_notes"] = _note(mine.at[i, "coding_notes"],
                                               f"[config 2026-11-13] Second coder {r['coder_2']} reviewed; not every field agreed.")  # fmt: skip
            mine.at[i, "coder_2"] = pd.NA
        if str(r["adus_per_lot"]) == "0":
            mine.at[i, "by_right"] = "False"
            if not str(mine.at[i, "coding_notes"]).startswith("NO ADU RULE"):
                mine.at[i, "coding_notes"] = "NO ADU RULE. " + str(mine.at[i, "coding_notes"])
    return mine


def main() -> None:
    prop = pd.read_csv(PROPOSED, dtype=str, keep_default_na=False).replace("", pd.NA)
    todo = pd.read_csv(TODO, dtype=str, keep_default_na=False)
    succ = prop.dropna(subset=["supersedes"]).set_index("supersedes")["effective_date"]
    for st, fn in FILES.items():
        path = ROOT / "config/reforms" / fn
        base = subprocess.run(["git", "show", f"{BASE}:config/reforms/{fn}"], capture_output=True, text=True,
                              check=True, cwd=ROOT).stdout  # fmt: skip
        cur = pd.read_csv(StringIO(base), dtype=str, keep_default_na=False).replace("", pd.NA)
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
        mine = conform(mine, old, todo)
        mine = keep_unchanged(mine, old)
        out = pd.concat([cur[~own], mine[cols]], ignore_index=True)
        out.to_csv(path, index=False)
        print(f"{st}: replaced {int(own.sum())} rows for {len(geoids)} places with {len(mine)} proposed rows")


if __name__ == "__main__":
    main()
