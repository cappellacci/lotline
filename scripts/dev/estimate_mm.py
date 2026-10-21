#!/usr/bin/env python3
"""The D-024 missing-middle panel: smoke counts only (no estimate is computed or printed).

    uv run python scripts/dev/estimate_mm.py --smoke

Prints, for the main panel (Census BPS 2-4 unit homes, MN NC OH TX, 2010-2025, places of 10,000+ people plus
every place with a coded missing-middle rule) under both comparison rules D-024 asks Ben to choose between,
for the 50,000+ robustness sample, and for the Met Council local-permit check: places, adopters per year,
comparisons, places with no 2-4 unit home in any year (the D-023 lesson: can the data carry place fixed
effects?) and treated place-years per event-time bin. Excluded places are counted by reason.
"""

from __future__ import annotations

import argparse

from lotline.io import DataStore
from lotline.model import estimate_mm as mm


def show(title: str, c: dict) -> None:
    print(f"\n== {title} (comparisons: {c['comparisons']})")
    print(f"  places {c['places']} ({c['by_state']}), place-years with an outcome {c['place_years']}")
    print(
        f"  treated {c['treated']} (adopting inside the panel years: {c['adopted_in_window']}); "
        f"adopters by year {c['adopters_by_year']}"
    )
    print(f"  comparison places {c['comparison_places']}")
    print(
        f"  places with no 2-4 unit home in any year: {c['all_zero_places']} "
        f"(treated {c['all_zero_treated']}, comparisons {c['all_zero_comparisons']}); "
        f"a place fixed-effects Poisson model keeps {c['kept_by_place_fe']}"
    )
    print(f"  share of place-years with zero: {c['zero_share_place_years']:.2f}")
    print(
        f"  treated place-years by event-time bin {c['treated_place_years_by_bin']}; "
        f"treated places per bin {c['treated_places_by_bin']}"
    )


def smoke(store) -> None:
    main = mm.build_panel(store)
    d = main.data
    span = f"{d['year'].min()}-{d['year'].max()}"
    print(f"Main panel: {d['place'].nunique()} places × {d['year'].nunique()} years ({span})")
    for reason, g in main.excluded.items():
        print(f"  excluded, {reason}: {len(g)}")
    print(f"  missing outcome place-years (no BPS row): {int(d['y'].isna().sum())}")
    print(f"  denominators: {d.drop_duplicates('place')['denominator_source'].value_counts().to_dict()}")
    tr = d[d["status"] == "treated"].drop_duplicates("place")
    for r in tr.itertuples():
        print(
            f"  treated: {r.state} {r.place} {r.name}, T = {int(r.T)}, dose in 2025 = "
            f"{d.loc[(d['place'] == r.place) & (d['year'] == d['year'].max()), 'dose'].iloc[0]:.2f}, "
            f"modifiers missing: {[m for m in mm.MODIFIERS if r._asdict()[m] != r._asdict()[m]]}"
        )
    cnt = d.drop_duplicates("place")["status"].value_counts().to_dict()
    print(f"  places by status: {cnt}")
    n_adu = int(d.drop_duplicates("place")["adu_coded"].sum())
    print(f"  ADU rule coded for {n_adu} places (others take the prior)")
    for note in main.notes:
        print("  note:", note)
    show("Main: BPS, 10,000+ people", mm.smoke_counts(d, "uncoded"))
    show("Main: BPS, 10,000+ people", mm.smoke_counts(d, "coded"))
    big = d[(d["pop_2020"] >= 50000) | (d["status"] != "uncoded")]
    show("Robustness: BPS, 50,000+ people", mm.smoke_counts(big, "uncoded"))
    local = mm.build_panel(store, states=("MN",), years=range(2016, 2026), source="metc_residential_permits")
    show("Local check: Met Council 2-4 unit permits, 2016-2025", mm.smoke_counts(local.data, "uncoded"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", required=True)
    ap.parse_args()
    smoke(DataStore())


if __name__ == "__main__":
    main()
