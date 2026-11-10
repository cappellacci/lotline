"""Undercount arithmetic shared by every state's roll-vs-permit check (D-074 step 1).

Moved from `lotline.adapters.states.nc.wake_roll_diff` on 2026-11-10 (Ben approved PR #367's proposal), so
Minnesota, Ohio, Texas and Oregon use one copy. The functions are unchanged. `wake_roll_diff` still imports
and re-exports them, so `wd.wilson`, `wd.chapman`, `wd.k_undercount`, `wd.flag_share` and `wd.Z90` keep
working.

- `wilson`: Wilson score interval for a proportion (95% by default).
- `chapman`: Chapman (bias-corrected Lincoln–Petersen) two-list total with a normal 95% interval.
- `flag_share`: share of roll finds that carry a flagged permit, with its Wilson interval.
- `k_undercount`: D-074's k = (|P∩R| + |a|) / |P∩R| with a binomial (Wilson) 90% interval.
"""

from __future__ import annotations

import math

__all__ = ["Z90", "chapman", "flag_share", "k_undercount", "wilson"]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n."""
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def chapman(roll: int, permits: int, both: int, z: float = 1.96) -> tuple[float, float, float]:
    """Chapman (bias-corrected Lincoln–Petersen) total and a normal 95% interval: (estimate, lo, hi)."""
    n = (roll + 1) * (permits + 1) / (both + 1) - 1
    var = (roll + 1) * (permits + 1) * (roll - both) * (permits - both) / ((both + 1) ** 2 * (both + 2))
    se = math.sqrt(var)
    seen = roll + permits - both
    return (n, max(seen, n - z * se), n + z * se)


def flag_share(both: int, roll: int) -> tuple[float, float, float]:
    """Share of roll-detected second homes that carry an ADU-flagged permit, with its 95% Wilson interval.

    Its inverse is the number of real (built and carded) ADUs per flagged one."""
    lo, hi = wilson(both, roll)
    return (both / roll if roll else math.nan, lo, hi)


Z90 = 1.6449  # two-sided 90%


def k_undercount(both: int, unflagged: int, z: float = Z90) -> tuple[float, float, float]:
    """D-072 flag undercount k = (|P∩R| + |a|) / |P∩R|, with a binomial (Wilson) 90% interval.

    The interval is the Wilson interval on the flagged share |P∩R| / (|P∩R| + |a|), inverted, so
    k's lower bound is 1 / (upper bound of the share)."""
    n = both + unflagged
    if both == 0:
        return (math.nan, math.nan, math.nan)
    lo, hi = wilson(both, n, z=z)
    return (n / both, 1 / hi, 1 / lo)
