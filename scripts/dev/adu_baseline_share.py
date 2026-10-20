#!/usr/bin/env python3
"""Recompute `baseline_adu_share_of_one_unit` in config/params/aggregate.yaml from permits that flag ADUs.

    uv run python scripts/dev/adu_baseline_share.py

Census BPS counts a detached ADU as a 1-unit permit, so the baseline's single-family forecast already holds
some ADUs (judging finding MS-10). Two permit sources flag ADUs across many places: the Met Council's regional
residential permits (Twin Cities metro) and Austin's permits. For 2019-2022 (before the 2023 rate shock and
the newest reforms, and outside every holdout window) this prints, per source, ADU permits / (ADU + detached
single-family permits), and the pooled share. It reads only processed, holdout-filtered tables.
"""

from __future__ import annotations

from lotline.io import DataStore
from lotline.model.scenarios.adu import adu_share_of_one_unit

SOURCES = {"MN": "metc_residential_permits", "TX": "austin_permits"}
YEARS = (2019, 2022)


def main() -> None:
    store = DataStore()
    adu = one = 0
    for state, source in SOURCES.items():
        permits = store.read(state, "permits")
        a, o = adu_share_of_one_unit(permits[permits["source"] == source], *YEARS)
        adu, one = adu + a, one + o
        print(f"{source:26s} {YEARS[0]}-{YEARS[1]}: {a:>5,} ADU of {o:>7,} one-unit permits = {a / o:.4f}")
    print(f"pooled: {adu:,} / {one:,} = {adu / one:.4f}")


if __name__ == "__main__":
    main()
