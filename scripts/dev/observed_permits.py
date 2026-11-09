#!/usr/bin/env python3
"""Observed ADU and missing-middle (2-4 unit) permits per state and year, for results pages (not a model run).

    uv run python scripts/dev/observed_permits.py [--first 2021 --last 2025] [--out observed.json]

- **ADUs:** permits flagged as ADUs (`building_type_std` ADU or an `adu_type`) in local permit sources that
  flag ADUs at all (`adu.observed_adu_counts`: where two sources cover a place, the larger count each year).
  Only those places are counted, so the state total is a floor; `adu_places` and `adu_population_share`
  (their share of the state's 2020 population) say how much of the state that is.
- **Missing middle:** homes in 2-unit and 3-4 unit buildings from the Census Building Permits Survey, every
  BPS place in the panel, on the baseline's basis (reported or with imputation, `use_reported_only`). This is
  all 2-4 unit building, not only what a missing-middle reform caused.

Every count comes from the holdout-filtered processed files (the store), so held-out places and years
(St. Paul from 2024, Charlotte) are missing from them; the output lists the holdouts that cut the window.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from lotline.build import eligible, panels
from lotline.config import load_params, load_state
from lotline.io import DataStore
from lotline.model import baseline
from lotline.model.scenarios import adu


def observed(state: str, store, first: int, last: int) -> dict:
    years = list(range(first, last + 1))
    reported = bool(load_params("baseline")["use_reported_only"].value)
    panel = panels.load(state, store, theme="adu", rule_version=eligible.RULE_VERSION)
    w = panel[panel["year"].between(first, last)]
    mm_cols = [baseline.outcome_column(s, reported) for s in ("2", "3_4")]
    mm = w.groupby("year")[mm_cols].sum().sum(axis=1).reindex(years, fill_value=0)

    permits = store.read(state, "permits")
    adu_by_year = pd.Series(0.0, index=years)
    adu_places, pop_share = [], 0.0
    if permits is not None and len(permits):
        counts = adu.observed_adu_counts(permits, first, last)
        adu_by_year = counts.groupby("year")["adu_permits"].sum().reindex(years, fill_value=0)
        adu_places = sorted(counts["geoid"].unique())
        pop = store.read(state, "jurisdictions").set_index("geoid")["pop_2020"].astype(float)
        pop_share = float(pop.reindex(adu_places).sum() / pop[pop.index.str.len() > 5].sum())

    cut = [
        f"{h.place} ({h.outcome_from:%Y}-)"
        for h in load_state(state).holdouts
        if h.released_on is None and h.outcome_from.year <= last
    ]
    return {
        "years": years,
        "adu": [int(adu_by_year[y]) for y in years],
        "adu_total": int(adu_by_year.sum()),
        "adu_places": len(adu_places),
        "adu_population_share": round(pop_share, 4),
        "mm_homes": [int(mm[y]) for y in years],
        "mm_total": int(mm.sum()),
        "mm_basis": "reported" if reported else "with_imputation",
        "holdouts_in_window": cut,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--states", nargs="+", default=["MN", "NC", "OH", "OR", "TX"])
    ap.add_argument("--first", type=int, default=2021)
    ap.add_argument("--last", type=int, default=2025)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    store = DataStore()
    doc = {st: observed(st, store, a.first, a.last) for st in a.states}
    for st, d in doc.items():
        share = d["adu_population_share"]
        adu_part = f"ADUs {d['adu_total']:,} in {d['adu_places']} places ({share:.0%} of pop)"
        mm_part = f"2-4 unit homes {d['mm_total']:,} {d['mm_homes']}"
        print(f"{st}: {adu_part} {d['adu']}; {mm_part}; holdouts {d['holdouts_in_window']}")
    if a.out:
        a.out.write_text(json.dumps(doc, indent=1) + "\n")
        print(a.out)


if __name__ == "__main__":
    main()
