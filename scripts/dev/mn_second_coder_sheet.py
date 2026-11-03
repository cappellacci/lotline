"""Write the Minnesota second-coder worksheet from config/reforms/mn.csv (thread 13, M5).

    uv run python scripts/dev/mn_second_coder_sheet.py

One line per rule row (every MN row has one coder), in the Texas and NC worksheet format, sorted so the rows
that would act as dated events come first:

- priority 1: `panel_event` set. D-025: an in-window ADU change in a place Met Council's or Minneapolis's
  permits cover (St. Paul never). D-024: an in-window missing-middle change in a BPS place of 10,000+.
- priority 2: other rows dated in the window (2010-01-02 to 2025-12-31), including "none" rows (controls).
- priority 3: rows dated before the window or after it, and moratorium windows.

A `[predates]` row is not an event. Rerunning rewrites the sheet and keeps answers already filled in.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.validation import holdout

ROOT = Path(__file__).resolve().parents[2]
REFORMS = ROOT / "config" / "reforms" / "mn.csv"
SHEET = ROOT / "docs" / "research" / "ordinances" / "mn-second-coder-2026-11-02.csv"
WINDOW = ("2010-01-02", "2025-12-31")
ST_PAUL = "2758000"
ANSWERS = ["second_coder", "agrees (yes/no/partly)", "correct_value", "second_coder_note"]
COLUMNS = [
    "priority",
    "panel_event",
    "reform_id",
    "place",
    "theme",
    "status",
    "adoption_date",
    "effective_date",
    "coded_as",
    "coverage",
    "what_to_check",
    "source_url",
    *ANSWERS,
]
CODED_FIELDS = [
    "by_right",
    "owner_occ",
    "unit_cap",
    "adus_per_lot",
    "adu_max_sqft",
    "adu_detached_allowed",
    "parking",
]


def coded_as(r: pd.Series) -> str:
    return "; ".join(f"{c}={r[c]}" for c in CODED_FIELDS if isinstance(r[c], str) and r[c])


def checks(r: pd.Series) -> str:
    notes = r["coding_notes"] if isinstance(r["coding_notes"], str) else ""
    out = []
    if "earliest-known" in notes or not isinstance(r["adoption_date"], str):
        out.append("confirm the first date: the coded date may be the code's adoption, later than the rule")
    if "snippet" in notes:
        out.append("a date comes from a search snippet: open the city page or ordinance")
    if r["none_row"]:
        out.append("confirm the rule allows none (no ADUs / one home) in the districts listed")
    out.append("confirm by-right vs permit, districts and the coded fields against the source")
    return "; ".join(out)


def main() -> None:
    r = pd.read_csv(REFORMS, dtype=str)
    store = DataStore()
    j = pd.read_parquet(store.processed("MN", "jurisdictions", "jurisdictions")).set_index("geoid")
    covered: set[str] = set()
    for s in ("metc_permits", "mpls_permits"):
        p = pd.read_parquet(
            store.processed("MN", "permits", s), columns=["jurisdiction_geoid", "issue_date", "issue_year"]
        )
        p = holdout.apply(
            p, "MN", geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
        )
        covered |= set(p["jurisdiction_geoid"])
    covered.discard(ST_PAUL)
    big = set(j.index[(j["kind"] == "place") & j["in_bps"].fillna(False) & (j["pop_2020"] >= 10_000)]) - {
        ST_PAUL
    }

    in_window = pd.to_datetime(r["effective_date"]).between(*WINDOW)
    predates = r["coding_notes"].str.contains("[predates]", na=False, regex=False)
    r["none_row"] = (r["theme"].eq("adu") & r["adus_per_lot"].eq("0")) | (
        r["theme"].eq("missing_middle") & r["unit_cap"].eq("1")
    )
    event = in_window & ~predates & ~r["none_row"]
    d025 = event & r["theme"].eq("adu") & r["jurisdiction_geoid"].isin(covered)
    d024 = event & r["theme"].eq("missing_middle") & r["jurisdiction_geoid"].isin(big)
    r["panel_event"] = ""
    r.loc[d025, "panel_event"] = "D-025"
    r.loc[d024, "panel_event"] = "D-024"
    r["priority"] = 3
    r.loc[in_window, "priority"] = 2
    r.loc[d025 | d024, "priority"] = 1

    old = {}
    if SHEET.exists():
        with SHEET.open(newline="") as f:
            old = {row["reform_id"]: row for row in csv.DictReader(f)}
    rows = []
    for _, x in r.sort_values(["priority", "panel_event", "jurisdiction_geoid", "effective_date"]).iterrows():
        row = {
            "priority": x["priority"],
            "panel_event": x["panel_event"],
            "reform_id": x["reform_id"],
            "place": j["name"].get(x["jurisdiction_geoid"], x["jurisdiction_geoid"]),
            "theme": x["theme"],
            "status": x["status"],
            "adoption_date": x["adoption_date"] if isinstance(x["adoption_date"], str) else "",
            "effective_date": x["effective_date"],
            "coded_as": coded_as(x),
            "coverage": x["coverage"] if isinstance(x["coverage"], str) else "",
            "what_to_check": checks(x),
            "source_url": x["source_url"] if isinstance(x["source_url"], str) else "",
        } | dict.fromkeys(ANSWERS, "")
        row |= {k: v for k, v in old.get(x["reform_id"], {}).items() if k in ANSWERS and v}
        rows.append(row)
    with SHEET.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    s = pd.DataFrame(rows)
    print(
        f"{len(s)} rows -> {SHEET}: priority {s['priority'].value_counts().sort_index().to_dict()}, "
        f"panel {s['panel_event'].value_counts().to_dict()}"
    )


if __name__ == "__main__":
    main()
