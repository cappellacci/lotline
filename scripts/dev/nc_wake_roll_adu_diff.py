"""Counts behind `reports/nc/wake-roll-adu-diff.md`: second homes added to Wake single-family lots, 2019-23.

    uv run python scripts/dev/nc_wake_roll_adu_diff.py [--cache DIR]

Descriptive counts only (data thread): no engine, scenario or calibration run. Reads the two
registered pre-revaluation rolls (Nov 2019, Dec 2023) through `DataStore` and the manifest, non-personal
columns only, and Raleigh's processed permits through `holdout.apply`. The rule is in the report's §1 and
`lotline.adapters.states.nc.wake_roll_diff`.

`--cache DIR` keeps the card columns read from each roll as parquet in DIR (outside the repo; reading the two
spreadsheets takes several minutes). Writes the aggregate counts to `reports/nc/wake-roll-adu-diff.json`;
no parcel-level table is written.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from lotline.adapters.states.nc import wake_realestate as wr
from lotline.adapters.states.nc import wake_roll_diff as wd
from lotline.io import DataStore
from lotline.validation import holdout

STATE = "NC"
BEFORE_FILE = "Real_Est_Data_Final_Nov2019.xlsx"
AFTER_FILE = wr.ROLL_FILE
YEARS = (wr.ROLLS[AFTER_FILE] - wr.ROLLS[BEFORE_FILE]).days / 365.25  # 4.08
RALEIGH = "3755000"
EXTRA = ["NUMBER_OF_CARDS", "Parcel_Identification", "Year_of_Addition"]
COLS = sorted(set(wr.USECOLS) | set(EXTRA))  # still none of wr.PERSONAL
OUT_JSON = Path(__file__).resolve().parents[2] / "reports" / "nc" / "wake-roll-adu-diff.json"
NAMES = {
    "3755000": "Raleigh", "3710740": "Cary", "3701520": "Apex", "3770540": "Wake Forest",
    "3725300": "Fuquay-Varina", "3732260": "Holly Springs", "3725480": "Garner", "3744520": "Morrisville",
    "3736080": "Knightdale", "3771860": "Wendell", "3776220": "Zebulon", "3757640": "Rolesville",
    "37183": "Unincorporated Wake",
}  # fmt: skip


def read_cards(store: DataStore, name: str, cache: Path | None) -> pd.DataFrame:
    assert not set(COLS) & wr.PERSONAL
    if cache is not None and (cache / f"{name}.parquet").exists():
        cached = pd.read_parquet(cache / f"{name}.parquet")
        if set(COLS) <= set(cached.columns):
            return cached[COLS]
    entry = wr.roll_entries(store, name)[-1]
    if store.is_stale(entry):
        raise FileNotFoundError(f"registered Wake roll missing or changed since registration: {entry.path}")
    cards = pd.read_excel(store.root / entry.path, usecols=COLS, dtype=str, engine="openpyxl")
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        cards.to_parquet(cache / f"{name}.parquet")
    return cards


def land_use_and_place(cards: pd.DataFrame, vintage: pd.Timestamp) -> tuple[pd.Series, pd.Series]:
    """The adapter's own land use and jurisdiction for each REID (partial cities dropped, as there)."""
    p = wr.build(cards[wr.USECOLS], vintage_date=vintage)
    reid = p["parcel_id"].str.removeprefix(wr.COUNTY)
    return (
        pd.Series(p["land_use_std"].values, index=reid),
        pd.Series(p["jurisdiction_geoid"].values, index=reid),
    )


def raleigh_check(diff: pd.DataFrame, store: DataStore) -> dict:
    p = pd.read_parquet(store.processed(STATE, "permits", "raleigh_permits"))
    p = holdout.apply(p, STATE, geoid_col="jurisdiction_geoid", date_col="issue_date")
    flagged = p.loc[p["adu_type"].notna() & p["issue_date"].between("2019-01-01", "2023-12-31")]
    ral = diff.loc[diff["jurisdiction_geoid"] == RALEIGH]
    roll_pins = ral.loc[ral["gained"], "pin10"]
    strict_pins = ral.loc[ral["strict"], "pin10"]
    out: dict = {"flagged_permits_2019_2023": int(len(flagged))}
    cohorts = {
        "issued_2019_2022": flagged["issue_date"] < "2023-01-01",
        "issued_2019_2021_rule_learned_on": flagged["issue_date"] < "2022-01-01",
        "issued_2022_unseen": flagged["issue_date"].between("2022-01-01", "2022-12-31"),
        "issued_2023_lag": flagged["issue_date"] >= "2023-01-01",
    }
    for name, mask in cohorts.items():
        f = flagged.loc[mask]
        m = wd.match_permits(roll_pins, f["parcel_id"], ral["pin10"])
        m["permits"] = int(len(f))
        m["permit_parcels"] = int(f["parcel_id"].nunique())
        m["by_adu_type_found"] = (
            f.loc[f["parcel_id"].isin(set(roll_pins))]
            .drop_duplicates("parcel_id")["adu_type"]
            .value_counts()
            .to_dict()
        )
        m["by_adu_type_all"] = f.drop_duplicates("parcel_id")["adu_type"].value_counts().to_dict()
        m["strict"] = wd.match_permits(strict_pins, f["parcel_id"], ral["pin10"])
        out[name] = m
    # Roll-only parcels: any flagged permit later (2024-26), or any other Raleigh permit 2018-2023?
    main = out["issued_2019_2022"]
    any_flag = set(p.loc[p["adu_type"].notna(), "parcel_id"])
    roll_only = set(roll_pins) - set(flagged["parcel_id"])
    recent = p.loc[p["issue_date"].between("2018-01-01", "2023-12-31")]
    new_res = recent.loc[
        recent["permit_class_raw"].astype("string").str.contains("New Residential", na=False)
    ]
    out["roll_only_any_year_flag"] = len(roll_only & any_flag)
    out["roll_only_any_permit_2018_2023"] = len(roll_only & set(recent["parcel_id"]))
    out["roll_only_new_residential_permit_2018_2023"] = len(roll_only & set(new_res["parcel_id"]))
    out["roll_only_total"] = len(roll_only)
    out["ratio_as_committed"] = ratios(
        main["both"], main["both"] + main["roll_only"], main["permits_in_denominator"]
    )
    # ADU-only adjustment (report §2, deviation of 2026-11-10): a roll parcel with a duplex permit (code
    # 103, building type U2) issued 2018-2023 is a duplex, not an ADU, and leaves the roll set; a roll parcel
    # with an ADU flag issued outside 2019-2022 is a flagged ADU, so it joins the flagged set.
    duplex = set(recent.loc[recent["building_type_std"] == "U2", "parcel_id"]) - any_flag
    roll_adu = set(roll_pins) - duplex
    flag_main = set(flagged.loc[flagged["issue_date"] < "2023-01-01", "parcel_id"]) & set(ral["pin10"])
    flag_set = flag_main | (roll_adu & any_flag)
    both = len(roll_adu & flag_set)
    out["adu_only"] = {
        "roll_parcels_dropped_as_duplex": len(set(roll_pins) & duplex),
        "roll": len(roll_adu),
        "flagged": len(flag_set),
        "flagged_added_other_issue_year": len(flag_set - flag_main),
        "both": both,
        "roll_only": len(roll_adu - flag_set),
        "permits_only": len(flag_set - roll_adu),
        **ratios(both, len(roll_adu), len(flag_set)),
    }
    return out


def ratios(both: int, roll: int, flagged: int) -> dict:
    """Ratio of real ADUs to flagged permits, three ways (report §2)."""
    share, s_lo, s_hi = wd.flag_share(both, roll)
    est, lo, hi = wd.chapman(roll, flagged, both)
    return {
        "flag_share_of_roll": share,
        "flag_share_lo": s_lo,
        "flag_share_hi": s_hi,
        "real_per_flagged": 1 / share,
        "real_per_flagged_lo": 1 / s_hi,
        "real_per_flagged_hi": 1 / s_lo,
        "seen_over_flagged": (roll + flagged - both) / flagged,
        "roll_over_flagged": roll / flagged,
        "chapman_total": est,
        "chapman_over_flagged": est / flagged,
        "chapman_over_flagged_lo": lo / flagged,
        "chapman_over_flagged_hi": hi / flagged,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cache", type=Path, default=None)
    args = ap.parse_args()
    store = DataStore()
    cb = read_cards(store, BEFORE_FILE, args.cache)
    ca = read_cards(store, AFTER_FILE, args.cache)
    land_use, place = land_use_and_place(cb, wr.ROLLS[BEFORE_FILE])
    b, a = wd.summarize_cards(cb), wd.summarize_cards(ca)
    diff = wd.diff_rolls(b, a, land_use, place)
    r = wd.rates(diff, YEARS)
    r.index = [NAMES.get(g, g) for g in r.index]
    order = [n for n in NAMES.values() if n in r.index]
    r = r.loc[order]
    total = wd.rates(diff.assign(all="Wake County"), YEARS, by="all")
    table = pd.concat([r, total])
    pd.set_option("display.width", 200)
    print(table.round(2).to_string())
    groups = diff["group"].value_counts().to_dict()
    new_years = diff.loc[diff["strict"], "extra_year"].value_counts().sort_index()
    vac = wd.vacant_two_homes(b, a, land_use)
    check = raleigh_check(diff, store)
    summary = {
        "rule": "reports/nc/wake-roll-adu-diff.md §1",
        "years": YEARS,
        "sf_2019": diff.attrs["sf_2019"],
        "sf_2019_reid_gone_by_2023": diff.attrs["sf_2019_dropped"],
        "groups": {k: int(v) for k, v in groups.items()},
        "strict_new_card_year_built": {int(k): int(v) for k, v in new_years.items()},
        "vacant_2019_two_homes_2023": int(len(vac)),
        "by_jurisdiction": json.loads(table.round(4).to_json(orient="index")),
        "raleigh_check": check,
    }
    print(json.dumps({k: v for k, v in summary.items() if k != "by_jurisdiction"}, indent=1, default=int))
    OUT_JSON.write_text(json.dumps(summary, indent=1, default=int) + "\n")


if __name__ == "__main__":
    main()
