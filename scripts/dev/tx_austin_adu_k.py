#!/usr/bin/env python3
"""Austin ADU counts from TCAD's 2026 improvements and the city's permits (report §2–§3). Read-only.

    uv run python scripts/dev/tx_austin_adu_k.py [--cache improvements.pkl]

`--cache` keeps the parsed improvement rows (prop and improvement IDs, type codes, segment years; no personal
field) in a local pickle so a re-run skips the 15 GB read; put it in a scratch folder, never in the repo.
The addition-permit check reads the raw pages fetched by `tx_austin_additions_fetch.py` (cached).

Rules: `reports/tx/adu-coverage-and-undercount.md` §0 (committed in 8d1e7c3d before any count). Functions:
`lotline.adapters.states.tx.austin_adu_roll`; k and Chapman from `nc.wake_roll_diff`. Reads the registered
TCAD zip through `DataStore.registered("tcad")` and the processed Austin parcels and permits (written
after `holdout.apply`; TX has no holdouts). Writes aggregates only, to
`reports/tx/austin-adu-roll.json`; no parcel-level table is written. No model run.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import pandas as pd

from lotline.adapters.states.nc import wake_roll_diff as wrd
from lotline.adapters.states.tx import austin_adu_roll as ar
from lotline.io import DataStore

OUT = Path(__file__).resolve().parents[2] / "reports" / "tx" / "austin-adu-roll.json"
AUSTIN = "4805000"
P_WINDOW = ("2018-07-01", "2023-06-30")
P_WINDOW_D074 = ("2019-01-01", "2023-06-30")
UNFLAGGED_CODES = {"101", "103", "104", "436"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path)
    args = ap.parse_args()
    store = DataStore()
    parcels = pd.read_parquet(store.processed("TX", "parcels") / "tcad_parcels.parquet")
    ids = set(parcels.loc[parcels["jurisdiction_geoid"] == AUSTIN, "parcel_id"])
    zips = [e for e in store.registered("tcad") if e.path.lower().endswith(".zip")]
    path = store.root / zips[-1].path
    if args.cache and args.cache.exists():
        det, types = pickle.loads(args.cache.read_bytes())
    else:
        det, types = ar.read_improvements(path, ids)
        if args.cache:
            args.cache.write_bytes(pickle.dumps((det, types)))
    years = ar.improvement_years(det, 2026)
    roll = ar.classify_parcels(types, years)
    res: dict = {"austin_tcad_parcels": len(ids), "parcels_with_improvements": int(len(roll))}
    res["universe"] = int(roll["universe"].sum())
    res["groups_2019_2023"] = roll.loc[roll["universe"], "group"].value_counts().to_dict()

    # roll-based series by year built of the newest second dwelling (one window per year)
    by_year = {}
    for y in range(2015, 2026):
        g = ar.classify_parcels(types, years, window=(y, y))
        by_year[y] = g.loc[g["universe"], "group"].value_counts().to_dict()
    res["roll_by_year"] = by_year

    permits = pd.read_parquet(store.processed("TX", "permits") / "austin_permits.parquet")
    permits = permits[permits["jurisdiction_geoid"] == AUSTIN].copy()
    permits["issued"] = pd.to_datetime(permits["issue_date"], errors="coerce")
    code = permits["permit_class_raw"].astype("string").str.extract(r"(\d{3})", expand=False)
    is_adu = permits["building_type_std"] == "ADU"
    new_res = code.isin(UNFLAGGED_CODES) & ~permits["is_demolition"].fillna(False).astype(bool)

    for name, (a, b) in {"main": P_WINDOW, "d074_window": P_WINDOW_D074}.items():
        w = permits["issued"].between(a, b)
        m = ar.match(roll, permits.loc[w & is_adu, "parcel_id"], permits.loc[w & new_res & ~is_adu])
        m["k"] = wrd.k_undercount(m["both"], m["a"])
        m["k_as_written"] = wrd.k_undercount(m["both"], m["a_as_written"])
        m["chapman"] = wrd.chapman(m["R"], m["P"], m["both"])
        m["flag_share_of_R"] = wrd.flag_share(m["both"], m["R"])
        res[f"match_{name}"] = m
        # strict (ALQ/garage apartment only) R
        strict = roll.assign(in_r=roll["group"] == "alq")
        ms = ar.match(strict, permits.loc[w & is_adu, "parcel_id"], permits.loc[w & new_res & ~is_adu])
        ms["k"] = wrd.k_undercount(ms["both"], ms["a"])
        res[f"match_{name}_strict"] = ms

    # addition permits (R-434/435) in the window: unflagged ADUs filed as additions (sensitivity, §2)
    sys.path.insert(0, str(Path(__file__).parent))
    from tx_austin_additions_fetch import fetch as fetch_additions

    from lotline.parse.permit_text import parse_description

    add = fetch_additions(store)
    add = add[add["jurisdiction"].isin(["AUSTIN FULL PURPOSE", "AUSTIN LTD"])].copy()
    add["parcel_id"] = "48453" + add["tcad_id"].fillna("").str.replace(r"\D", "", regex=True)
    add["issued"] = pd.to_datetime(add["issue_date"].str[:10], errors="coerce")
    add = add[add["issued"].between(*P_WINDOW)]
    add["adu"] = [parse_description(t if isinstance(t, str) else "").building_type_std == "ADU"
                  for t in add["description"]]  # fmt: skip
    m = res["match_main"]
    w = permits["issued"].between(*P_WINDOW)
    rest = (set(roll.index[roll["in_r"]]) - set(permits.loc[w & is_adu, "parcel_id"])) - set(
        permits.loc[w & new_res & ~is_adu, "parcel_id"]
    )
    b_add = rest & set(add["parcel_id"])
    b_add_adu = rest & set(add.loc[add["adu"], "parcel_id"])
    res["b_check"] = {
        "b": len(rest),
        "b_with_addition_permit": len(b_add),
        "b_with_adu_named_addition": len(b_add_adu),
        "b_by_group": roll.loc[sorted(rest), "group"].value_counts().to_dict(),
        "universe_share_with_addition_permit": float(
            roll.index[roll["universe"]].isin(set(add["parcel_id"])).mean()
        ),
        "addition_permits_in_window": int(len(add)),
        "adu_named_addition_permits": int(add["adu"].sum()),
    }
    res["k_with_adu_additions"] = wrd.k_undercount(m["both"], m["a"] + len(b_add_adu))

    # P permits by class of the unflagged (a) permits, for the report
    w = permits["issued"].between(*P_WINDOW)
    r_not_p = set(roll.index[roll["in_r"]]) - set(permits.loc[w & is_adu, "parcel_id"])
    a_rows = permits[w & new_res & ~is_adu & permits["parcel_id"].isin(r_not_p)]
    res["a_permit_classes"] = a_rows["permit_class_raw"].value_counts().to_dict()
    res["a_reform_flag"] = a_rows["reform_flag_raw"].value_counts(dropna=False).astype(int).to_dict()

    # HOME rule series, every year 2015-2025
    home = ar.home_adu(
        permits[["parcel_id", "issue_date", "permit_class_raw", "is_demolition"]],
        roll["main_year"],
        roll["attached"],
    )
    permits["home_adu"] = home
    permits["year"] = permits["issued"].dt.year
    permits["code"] = code
    tab = {}
    for y in range(2015, 2026):
        py = permits[permits["year"] == y]
        h = py[py["home_adu"]]
        post = py["issued"] >= ar.HOME_START
        tab[y] = {
            "r102_flagged": int((py["building_type_std"] == "ADU").sum()),
            "home_rule_permits": int(len(h)),
            "home_rule_homes": float(h["units_new"].fillna(1).sum()),
            "home_rule_by_class": h["code"].value_counts().to_dict(),
            "home_rule_post_home_permits": int(h[post.reindex(h.index)].shape[0]),
            "home_phrase_permits": int(py["reform_flag_raw"].notna().sum()),
            "home_phrase_and_rule": int((py["reform_flag_raw"].notna() & py["home_adu"]).sum()),
            "new_101_103": int(py["code"].isin({"101", "103"}).sum()),
            "r102_id_on_roll": int(py.loc[py["code"] == "102", "parcel_id"].isin(ids).sum()),
            "r102_pass_rule": int((py["home_adu"] & (py["code"] == "102")).sum()),
        }
    res["permits_by_year"] = tab
    # recall of the HOME rule on R-102 permits (the rule's known ADUs), and the corrected count:
    # rule-passing permits / recall, recall from the same years' R-102 permits (2024-2025 pooled)
    est = {}
    for y, t in tab.items():
        yrs = [2024, 2025] if y >= 2024 else [y]
        f = sum(tab[v]["r102_flagged"] for v in yrs)
        ok = sum(tab[v]["r102_pass_rule"] for v in yrs)
        rec = wrd.flag_share(ok, f)
        est[y] = {
            "recall": rec,
            "adu_estimate": t["home_rule_permits"] / rec[0] if rec[0] else None,
            "adu_estimate_lo": t["home_rule_permits"] / rec[2],
            "adu_estimate_hi": t["home_rule_permits"] / rec[1],
        }
    res["home_rule_estimate"] = est
    OUT.write_text(json.dumps(res, indent=1, default=lambda o: o if not hasattr(o, "item") else o.item()))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
