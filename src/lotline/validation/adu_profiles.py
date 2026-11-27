"""D-089: a profile of each state's places by type, how much of each state lies outside the fit's evidence, a
prior for towns, and statewide ADU totals under Form A + place types (D-088).

- `profile`: per (state, type) the jurisdictions, population, eligible lots and their share of the state, and
  the lot-weighted medians of home value, rent and owner share.
- `outside_evidence`: a jurisdiction is outside the evidence if it is a town (no fit place is one), or if any
  of its measures lies outside the 5th-95th percentile of the fit places of its own type.
- `town_sd`: the town prior's s = |β̂_core| / z_90, so the 90% range of a town's multiplier over a suburb's
  matches the one measured type gap, either way.
- `current_totals`: the scenario's current-rules path (`scenarios.adu.pool_paths`, pool depletion with the
  observed floor) for many draws at once, summed over places and years.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from lotline.model import hazard

Z_90 = 1.6448536269514722
LABEL_SHARE = 0.25  # D-089: a state with more than this share of its lots outside the evidence is labeled
RANGE_Q = (0.05, 0.95)


def weighted_median(values, weights) -> float:
    """The value where the cumulative weight first reaches half. Missing values are dropped.
    By hand: values (1, 2, 3), weights (1, 1, 3) -> 3; weights (3, 1, 1) -> 1; (1, 1, 1, 1) on (1..4) -> 2."""
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    ok = np.isfinite(v) & np.isfinite(w) & (w > 0)
    if not ok.any():
        return float("nan")
    v, w = v[ok], w[ok]
    order = np.argsort(v)
    v, w = v[order], w[order]
    cum = np.cumsum(w)
    return float(v[np.searchsorted(cum, 0.5 * cum[-1])])


def profile(df: pd.DataFrame, measures: Sequence[str] = ("home_value", "rent", "owner")) -> pd.DataFrame:
    """Per (state, type): jurisdictions, population, eligible lots, the type's share of the state's lots, and
    lot-weighted medians of `measures`. `df` has state, type, pop, lots and the measures."""
    rows = []
    tot = df.groupby("state")["lots"].sum()
    for (st, ty), g in df.groupby(["state", "type"]):
        row = {
            "state": st,
            "type": ty,
            "jurisdictions": len(g),
            "pop": float(g["pop"].sum()),
            "lots": float(g["lots"].sum()),
            "lot_share": float(g["lots"].sum() / tot[st]) if tot[st] > 0 else float("nan"),
        }
        for m in measures:
            row[m] = weighted_median(g[m], g["lots"])
        rows.append(row)
    return pd.DataFrame(rows)


def fit_ranges(
    fit: pd.DataFrame, measures: Sequence[str], q=RANGE_Q
) -> dict[str, dict[str, tuple[float, float]]]:
    """{type: {measure: (low, high)}}: the q-quantiles of the fit places of each type (unweighted)."""
    out = {}
    for ty, g in fit.groupby("type"):
        out[ty] = {m: (float(g[m].quantile(q[0])), float(g[m].quantile(q[1]))) for m in measures}
    return out


def outside_evidence(df: pd.DataFrame, ranges: Mapping, measures: Sequence[str]) -> pd.DataFrame:
    """Flags per jurisdiction: `is_town`, `beyond_range` (a measure outside its type's fit range; a missing
    measure does not count), `outside` (either). A type with no fit places is entirely outside.

    By hand: ranges {suburb: {v: (10, 20)}}; rows (suburb, 15), (suburb, 25), (suburb, NaN), (town, 15) ->
    beyond (F, T, F, F), town (F, F, F, T), outside (F, T, F, T)."""
    is_town = (df["type"] == "town").to_numpy()
    beyond = np.zeros(len(df), dtype=bool)
    for i, (ty, *vals) in enumerate(df[["type", *measures]].itertuples(index=False)):
        r = ranges.get(ty)
        if r is None:
            beyond[i] = True
            continue
        for m, v in zip(measures, vals, strict=True):
            lo, hi = r[m]
            if v is not None and np.isfinite(v) and (v < lo or v > hi):
                beyond[i] = True
    return pd.DataFrame({"is_town": is_town, "beyond_range": beyond & ~is_town, "outside": is_town | beyond})


def label(share_outside: float, cut: float = LABEL_SHARE) -> bool:
    """D-089's rule: label the state's range when more than `cut` of its lots are outside the evidence.
    By hand: 0.3 -> True; 0.25 -> False."""
    return bool(share_outside > cut)


def town_sd(beta_core: float) -> float:
    """s = |β̂_core| / z_90. By hand: 1.199 -> 0.729."""
    return abs(beta_core) / Z_90


def current_totals(
    eligible,
    hm: np.ndarray,
    rule_share,
    floor,
    rule_age,
    params: Mapping[str, float],
    horizon: int,
    lead: int,
) -> np.ndarray:
    """Draws: Σ over places and the `horizon` window years of the current-rules path of
    `scenarios.adu.pool_paths`, with the mature hazard per draw and place (`hm`, draws × places). Same steps:
    `lead` years deplete the pool and are not counted; each year h = min(max(c × hm × ramp(age + t), floor),
    1) and the pool shrinks by what it adds. Matches `pool_paths(...).current.sum()` draw by draw (tested)."""
    e = np.asarray(eligible, dtype=float)[None, :]
    c = np.asarray(rule_share, dtype=float)[None, :]
    fl = np.nan_to_num(np.asarray(floor, dtype=float), nan=0.0)[None, :]
    age = np.nan_to_num(np.asarray(rule_age, dtype=float), nan=0.0)
    hm = np.asarray(hm, dtype=float)
    r = np.broadcast_to(e, hm.shape).copy()
    for s in range(1, int(lead) + 1):
        h = np.minimum(np.maximum(c * hm * hazard.adu_ramp(age + s, params)[None, :], fl), 1.0)
        r = r - r * h
    age = age + int(lead)
    total = np.zeros(hm.shape[0])
    for t in range(1, int(horizon) + 1):
        h = np.minimum(np.maximum(c * hm * hazard.adu_ramp(age + t, params)[None, :], fl), 1.0)
        add = r * h
        total += add.sum(axis=1)
        r = r - add
    return total
