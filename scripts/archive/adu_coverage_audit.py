#!/usr/bin/env python3
"""Audit of how ADU rule rows are coded for coverage and for "no ADUs" (follow-up to D-095).

    PYTHONPATH=src python scripts/archive/adu_coverage_audit.py --out reports/adu-coverage-audit

Reads `config/reforms/*.csv` and each rule's coverage as the engine and the fit compute it
(`scenarios.adu.coverage_map`, offline parcels). Flags, for hand review (no row is changed):

- **blank**: a row with every rubric field blank and no `adus_per_lot` = 0. The engine reads it as "ADUs
  allowed, every restriction unknown" (`current_rules`), whatever its text says ("not allowed", "unknown").
- **area_text_citywide**: the rule allows ADUs, its coverage is read as citywide (no `coverage_zones`, no lot
  minimum, no limited-area wording), but its coverage text names districts, zones or areas, so it may cover
  less. Marked `strong` where the text says "only", "not allowed in", "rural" or "overlay".
- **zones_switch**: consecutive rows of one place where one row lists `coverage_zones` and the other doesn't,
  so the read coverage changes between them (1 vs the measured or 0.75 judgment share) even where the text
  names the same districts.

Writes `rows.csv` (every flagged row) and `summary.json`. Nothing is fitted or scored.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore, offline
from lotline.model.scenarios import adu

FIELDS = [
    "by_right",
    "owner_occ",
    "adu_detached_allowed",
    "adus_per_lot",
    "parking",
    "adu_max_sqft",
    "unit_cap",
]
AREA = r"\b(?:r-?\d|rs-?\d|rsf|sf-?\d|r1|r2|rr\b|a-?\d|ldr|districts?|zones?\b|overlay|only in|rural)"
STRONG = r"\bonly\b|not allowed in|rural|overlay"


def audit(store) -> pd.DataFrame:
    central = {k: v.value for k, v in load_params("adu").items()}
    out = []
    for st in adu.REFORM_STATES:
        r = adu.load_reforms(st)
        cm = adu.coverage_map(st, store, r, central)
        a = r[(r["theme"] == "adu") & (r["jurisdiction_geoid"].str.len() > 2)]
        a = a.merge(
            cm[["reform_id", "coverage", "how"]].rename(columns={"coverage": "read_coverage"}), on="reform_id"
        )
        out.append(a.assign(state=st))
    df = pd.concat(out, ignore_index=True)
    text = (df["coverage"].fillna("") + " | " + df["coding_notes"].fillna("")).str.lower()
    no_adus = pd.to_numeric(df["adus_per_lot"], errors="coerce") == 0
    blank = df[FIELDS].isna().all(axis=1) & (
        pd.to_numeric(df["min_lot_sqft"], errors="coerce").fillna(0) == 0
    )
    df["flag_blank"] = blank & ~no_adus
    df["flag_area_text_citywide"] = (
        ~no_adus
        & ~blank
        & (df["how"] == "citywide")
        & df["coverage"].fillna("").str.lower().str.contains(AREA)
    )
    df["strong"] = df["flag_area_text_citywide"] & df["coverage"].fillna("").str.lower().str.contains(STRONG)
    df["flag_zones_switch"] = False
    for _, g in df.sort_values("effective_date").groupby("jurisdiction_geoid"):
        g = g[~(pd.to_numeric(g["adus_per_lot"], errors="coerce") == 0)]
        zs = g["coverage_zones"].notna().to_numpy()
        for i in range(1, len(g)):
            if zs[i] != zs[i - 1]:
                df.loc[g.index[[i - 1, i]], "flag_zones_switch"] = True
    df["says_not_allowed"] = text.str.contains(
        r"adus not allowed|do not allow|does not allow|coded as adus not allowed"
    )
    df["says_unknown"] = text.str.contains(
        r"unknown|not settled|not opened|could not be opened|not found online"
    )
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fit-places", type=Path, default=Path("reports/adu-type-spread/heldout_places.csv"))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        df = audit(store)
    fit_ids = set(pd.read_csv(a.fit_places, dtype={"geoid": str})["geoid"])
    df["in_fit"] = df["jurisdiction_geoid"].isin(fit_ids)
    flags = ["flag_blank", "flag_area_text_citywide", "flag_zones_switch"]
    keep = df[df[flags].any(axis=1)]
    cols = [
        "state",
        "jurisdiction_geoid",
        "reform_id",
        "effective_date",
        "end_date",
        "in_fit",
        *flags,
        "strong",
        "says_not_allowed",
        "says_unknown",
        "read_coverage",
        "how",
        "coverage_zones",
        "min_lot_sqft",
        "adus_per_lot",
        "by_right",
        "coverage",
        "coding_notes",
    ]
    keep[cols].sort_values(
        ["in_fit", "state", "jurisdiction_geoid", "effective_date"], ascending=[False, True, True, True]
    ).to_csv(a.out / "rows.csv", index=False)
    summ = {
        "adu_rows": len(df),
        "how": df["how"].value_counts().to_dict(),
        "flags": {
            f: {
                "rows": int(df[f].sum()),
                "fit_rows": int((df[f] & df.in_fit).sum()),
                "fit_places": int(df.loc[df[f] & df.in_fit, "jurisdiction_geoid"].nunique()),
            }
            for f in [*flags, "strong"]
        },
        "blank_rows": df.loc[
            df.flag_blank, ["reform_id", "in_fit", "says_not_allowed", "says_unknown"]
        ].to_dict(orient="records"),
    }
    (a.out / "summary.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
