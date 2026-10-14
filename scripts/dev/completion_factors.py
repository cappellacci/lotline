#!/usr/bin/env python3
"""Recompute the completion factors in config/params/aggregate.yaml from Census data (via FRED).

    uv run python scripts/dev/completion_factors.py

Downloads monthly, not seasonally adjusted permits and completions by building size (Census New Residential
Construction, republished by FRED) through the IO layer, so each file is cached and logged in the manifest,
then prints the long-run completion ratios per window (see lotline.model.completion for the method).
"""

from __future__ import annotations

import io
from datetime import date

import pandas as pd

from lotline.adapters.national import fred
from lotline.io import DataStore, fetch
from lotline.model.completion import annual_totals, completion_ratio

SERIES = {  # FRED id: Census New Residential Construction, thousands of units, NSA
    "permits_all": "PERMITNSA",
    "completions_all": "COMPUTNSA",
    "permits_1": "PERMIT1NSA",
    "completions_1": "COMPU1UNSA",
    "permits_2_4": "PERMIT24NSA",
    "completions_2_4": "COMPU24UNSA",
    "permits_5p": "PERMIT5NSA",
    "completions_5p": "COMPU5MUNSA",
}
WINDOWS = [(1990, 2019), (2000, 2019), (2010, 2022)]
GROUPS = {  # label: (completions, permits, lag in years)
    "all units": (["completions_all"], ["permits_all"], 1),
    "single-family (1 unit)": (["completions_1"], ["permits_1"], 1),
    "2+ units": (["completions_2_4", "completions_5p"], ["permits_2_4", "permits_5p"], 2),
}
LICENSE = "Public domain (Census Bureau New Residential Construction, U.S. Government work), via FRED"


def load(store: DataStore) -> dict[str, pd.Series]:
    vintage = date.today().isoformat()[:7]
    out = {}
    for name, series_id in SERIES.items():
        url = f"{fred.BASE_URL}?id={series_id}"
        path = fetch(
            url,
            store.raw(fred.SOURCE, vintage) / f"{series_id}.csv",
            store=store,
            source=fred.SOURCE,
            license=LICENSE,
            adapter="scripts.dev.completion_factors",
            adapter_version="1.0",
        )
        df = pd.read_csv(io.StringIO(path.read_text()))
        out[name] = annual_totals(pd.Series(df.iloc[:, 1].to_numpy(), index=pd.to_datetime(df.iloc[:, 0])))
    return out


def main() -> None:
    data = load(DataStore())
    print(f"{'group':<24}" + "".join(f"{a}-{b:<6}" for a, b in WINDOWS))
    for label, (comp, perm, lag) in GROUPS.items():
        c = sum(data[k] for k in comp)
        p = sum(data[k] for k in perm)
        print(f"{label:<24}" + "".join(f"{completion_ratio(c, p, a, b, lag):<11.3f}" for a, b in WINDOWS))


if __name__ == "__main__":
    main()
