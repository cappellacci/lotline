# ruff: noqa: E501  (plain-language strings and notes)
"""One central row for fees that vary by area, basin, tier or plat date (Ben, 2026-10-30; config/fees/README.md).

- Areas, basins and tiers: the median row is central. With an even count, the central value is the median of
  the amounts, carried by the row nearest it, the lower one on a tie.
- Plat-date cohorts: the newest cohort is central (most new homes go on recently platted lots).
- The central row carries the group's range (lowest and highest per-unit amount); the other rows keep their
  schedule amounts with `amount_per_unit_usd` blank.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from datetime import date


def central_index(amounts: Sequence[float], kind: str, cohort_starts: Sequence[date | None] = ()) -> int:
    """Index of the central member of a group."""
    if not amounts:
        raise ValueError("empty group")
    if kind == "plat_date":
        if len(cohort_starts) != len(amounts) or any(c is None for c in cohort_starts):
            raise ValueError("plat_date groups need a cohort_start for every member")
        return max(range(len(amounts)), key=lambda i: cohort_starts[i])
    if kind != "area":
        raise ValueError(f"unknown group kind {kind!r}")
    mid = statistics.median(amounts)
    # nearest to the median; ties -> the lower amount
    return min(range(len(amounts)), key=lambda i: (abs(amounts[i] - mid), amounts[i]))


def group_range(amounts: Sequence[float]) -> tuple[float, float]:
    return min(amounts), max(amounts)
