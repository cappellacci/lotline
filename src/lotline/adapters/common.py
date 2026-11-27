"""Small helpers several permit adapters share, so each rule is written once.

- `multi_type`: Census size class of a building of 2 or more units (U2, U3_4, MF5), else None.
- `size_class`: the same, with UNKNOWN below 2 units or no count (the Oregon permit adapters).
- `units_fit`: whether a reported unit count fits a building type's range in an adapter's `FITS` table.

Adapters with their own variant keep it: Minneapolis splits 5+ into U5_6 and U7P, Durham and Cincinnati also
class 1-unit buildings, and College Station treats a missing count differently. Moved here from identical
copies on 2026-11-27 (modularity review, finding 9); each adapter's tests cover the behaviour.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def multi_type(n: object) -> str | None:
    """Building type from a unit count of 2 or more (Census size classes), else None."""
    if n is None or pd.isna(n) or n < 2:
        return None
    return "U2" if n == 2 else "U3_4" if n <= 4 else "MF5"


def size_class(n: object) -> str:
    """Census size class of a unit count; UNKNOWN below 2 units or when the count is missing."""
    return multi_type(n) or "UNKNOWN"


def units_fit(fits: Mapping[str, tuple[int, int]], btype: str | None, n: object) -> bool:
    """True when `n` is within `fits[btype]` (inclusive); False for an unlisted type or a missing count."""
    if btype not in fits or n is None or pd.isna(n):
        return False
    lo, hi = fits[btype]
    return lo <= n <= hi
