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


# Source check of every overturned value and moved date, 2026-11-13 (reports in the PR). Each entry: id, field,
# value, why. Applied to the research rows before anything else.
OVERRIDES = [
    ("MN-2706616-adu-2016", "adu_max_sqft", "960", "'less than 960 square feet' coded 960, as Ben coded the same wording for Chanhassen"),
    ("MN-2706616-adu-2019", "adu_max_sqft", "960", "'less than 960 square feet' coded 960, as Ben coded the same wording for Chanhassen"),
    ("MN-2706616-adu-2022", "adu_max_sqft", "960", "'less than 960 square feet' coded 960 (source check kept the config value)"),
    ("MN-2735180-adu-2013", "parking_min_per_unit", "1", "3 garage stalls for the home with an ADU less the 2 a single-family home needs (§11-19-13.A)"),
    ("MN-2754880-adu-2023", "parking_min_per_unit", "0", "source check unresolved (legend 'No Requirement' vs Director sets); config value kept"),
    ("NC-3712000-adu-2023", "supersedes", None, "the UDO replaced the 2012 ordinance outright; no field inherits from it (config rule, tests/states/nc)"),
    ("OR-4105800-adu-2016b", "effective_date", "2016-03-18", "Ord. NS-2260 adopted 2016-02-17 with no effective clause; city rule: effective 30 days later"),
]  # fmt: skip

# Ben ruled on 2026-11-13 ("Take research"): the research reading replaces four of his 2026-11-02 adjudications.
RULED = [
    ("MN-2754214-adu-2015", "adu_detached_allowed: research reading (detached as part of a garage) replaces Ben's 2026-11-02 False"),
    ("MN-2731076-adu-2018", "min_lot_sqft: research reading (no lot minimum) replaces Ben's 2026-11-02 43560"),
    ("MN-2710918-adu-2025", "by_right: research reading (Ord. 744, attached ADUs need only a building permit) replaces Ben's 2026-11-02 False"),
    ("MN-2755852-adu-2011", "adu_max_sqft: research reading (650 enacted) replaces Ben's 2026-11-02 600"),
]  # fmt: skip


# Research rows that describe the same ordinance as a replaced config row keep that row's id (source check of the
# dates, 2026-11-13), so references and tests stay stable.
RENAMES = {
    "MN-2743000-adu-2014a": "MN-2743000-adu-2014",
    "MN-2757220-adu-2020a": "MN-2757220-adu-2020",
    "MN-2722814-adu-2022a": "MN-2722814-adu-2022",
    "MN-2745430-adu-2024a": "MN-2745430-adu-2024",
    "MN-2710918-adu-1986": "MN-2710918-adu-none",
    "NC-3719000-adu-2019a": "NC-3719000-adu-2019",
    "NC-3719000-adu-2024": "NC-3719000-adu-2023",
    "NC-3755000-adu-2020a": "NC-3755000-adu-2020",
    "OR-4105800-adu-2016b": "OR-4105800-adu-2016",
    "TX-4805000-adu-2023a": "TX-4805000-adu-2023",
    "TX-4815976-adu-2023a": "TX-4815976-adu-2023",
}


def override(prop: pd.DataFrame) -> pd.DataFrame:
    prop = prop.copy()
    for rid, field, value, why in OVERRIDES:
        i = prop.index[prop["reform_id"] == rid]
        assert len(i) == 1, rid
        prop.loc[i, field] = pd.NA if value is None else value
        prop.loc[i, "coding_notes"] = _note(prop.loc[i[0], "coding_notes"], f"[source check 2026-11-13] {field} = {value}: {why}.")
    for rid, why in RULED:
        i = prop.index[prop["reform_id"] == rid]
        assert len(i) == 1, rid
        prop.loc[i, "coding_notes"] = _note(prop.loc[i[0], "coding_notes"], f"[Ben ruled 2026-11-13] {why}.")
    return prop


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
    - a blank announced or adoption date keeps the replaced row's (same id).
    - coder is "claude" (the workstream is named in the notes, "WS-ADU-RULES proposed").
    - a no-ADU row (adus_per_lot 0) is not by right and its notes start "NO ADU RULE".
    """
    mine = mine.copy()
    mine["coder"] = "claude"
    for i, r in mine.iterrows():
        same = old[old["reform_id"] == r["reform_id"]]
        for c in ("announced_date", "adoption_date"):  # the research did not code these; keep the config's
            if pd.isna(r[c]) and len(same) and pd.notna(same[c].iloc[0]):
                mine.at[i, c] = same[c].iloc[0]
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
    prop = override(prop)
    prop[["reform_id", "supersedes"]] = prop[["reform_id", "supersedes"]].replace(RENAMES)
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
        prior_end = mine["reform_id"].map(old.set_index("reform_id")["end_date"]) if len(old) else pd.NA
        mine["end_date"] = mine["reform_id"].map(succ).fillna(mine["end_date"]).fillna(prior_end)
        mine = conform(mine, old, todo)
        mine = keep_unchanged(mine, old)
        out = pd.concat([cur[~own], mine[cols]], ignore_index=True)
        out.to_csv(path, index=False)
        print(f"{st}: replaced {int(own.sum())} rows for {len(geoids)} places with {len(mine)} proposed rows")


if __name__ == "__main__":
    main()
