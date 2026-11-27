"""D-099: uptake in the first years after a place first allows ADUs.

f_i is the year a place's first ADU-allowing rule took effect: the earliest ADU row that is neither an
explicit no-ADU row (`adus_per_lot` 0) nor marked `UNKNOWN-PLACEHOLDER`. A first row starting on
`WINDOW_START` (2016-01-01, the start of the coding window) means "allowed before 2016", so the place has no
f. For years with 0 <= t - f_i < K the place's expected count is multiplied by ν; ν = 1 is A + P as fitted
(D-096). Fitted by scaling each place's base exposure in those years (`scaled`) and refitting A + P at each ν.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace

import numpy as np
import pandas as pd

from lotline.calibrate.adu import calibrate_adu as cal

K = 5  # years after f_i that take ν, fixed in D-099 (the engine's five-year window)
WINDOW_START = pd.Timestamp("2016-01-01")
PLACEHOLDER = "UNKNOWN-PLACEHOLDER"
NU_GRID = tuple(round(v, 2) for v in np.arange(0.05, 1.5001, 0.05))


def first_allowing_year(rows: pd.DataFrame) -> dict[str, int]:
    """{geoid: f} from ADU reform rows (`scenarios.adu.load_reforms`, any states). Places allowing ADUs from
    the window start, or never, are left out.

    By hand: A has a no-ADU row from 2016-01-01 then an allowing row from 2019-05-20 -> 2019; B's first
    allowing row starts 2016-01-01 -> left out; C's only allowing row is a placeholder -> left out."""
    r = rows[rows["theme"] == "adu"].copy()
    no = pd.to_numeric(r["adus_per_lot"], errors="coerce") == 0
    ph = r["coding_notes"].fillna("").astype(str).str.contains(PLACEHOLDER)
    eff = pd.to_datetime(r["effective_date"])
    allow = r.assign(eff=eff)[~no & ~ph & eff.notna()]
    first = allow.groupby(allow["jurisdiction_geoid"].astype(str))["eff"].min()
    return {g: int(d.year) for g, d in first.items() if d > WINDOW_START}


def new_rule_flags(years: Iterable[int], f: int | None, k: int = K) -> np.ndarray:
    """True for the years within k of f (0 <= t - f < k). By hand: years 2018-2023, f 2019, k 3 ->
    (F, T, T, T, F, F); f None -> all False."""
    y = np.asarray(list(years), dtype=int)
    if f is None:
        return np.zeros(len(y), dtype=bool)
    return (y - f >= 0) & (y - f < k)


def scaled(pl: cal.PlaceData, nu: float, flags: np.ndarray) -> cal.PlaceData:
    """The place with its base exposure × ν in flagged years. By hand: base (10, 10, 10), flags (F, T, T),
    ν 0.5 -> (10, 5, 5)."""
    if not np.any(flags) or nu == 1.0:
        return pl
    return replace(pl, base=np.where(flags, pl.base * nu, pl.base))


def scaled_all(places: Iterable[cal.PlaceData], nu: float, first: Mapping[str, int], k: int = K):
    """Every place scaled at ν by its own flags (`first`: `first_allowing_year`)."""
    return [scaled(p, nu, new_rule_flags(p.years, first.get(p.geoid), k)) for p in places]
