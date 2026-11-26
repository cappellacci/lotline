"""The results bundle's context tables (`results.build_bundle` fills them; split out of `results.py` in
modularity plan step 3).

- `overlap_flag`: how far the state's places sit from the calibration range (meta).
- `fee_types_with_stops`: the fee slider's grid (`results_fee_types`).
- `adu_place_type_table`, `adu_baseline_years`: the ADU scenario by place type and its no-reform years.
- `affordability_table`, `shortfall_table`: who the homes serve and the need left after homes built anyway.
- `year_shares`, `_pct`, `_columns`: small helpers the bundle code shares.

Each function only reshapes draws the engine already made; none draws a random number.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.model import aggregate, baseline


def weighted_median(x, w) -> float:
    """The smallest x at which the cumulative weight reaches half the total (weights >= 0, total > 0)."""
    x, w = np.asarray(x, dtype=float), np.asarray(w, dtype=float)
    order = np.argsort(x, kind="stable")
    cum = np.cumsum(w[order])
    return float(x[order][np.searchsorted(cum, 0.5 * cum[-1])])


def overlap_flag(eligible: np.ndarray, distance: np.ndarray, params=None) -> tuple[str, float]:
    """State overlap flag from the eligible-weighted median calibration distance of its places.

    `distance` is `hazard.calibration_distance(...)["total"]` per place (log distance outside the calibration
    range, 0 inside). high at or below `overlap_flag_medium_distance` (0.5: the widening adds a log-sd of 0.5,
    P10-P90 about x0.5-x1.9 at the central widening), low above `overlap_flag_low_distance` (1.0), medium
    between. By hand: places with 60 and 40 eligible parcels at distances 0.3 and 2.0 -> median 0.3, high.
    """
    p = params or load_params("aggregate")
    e = np.asarray(eligible, dtype=float)
    if not e.sum() > 0:
        return "low", float("nan")
    median = weighted_median(distance, e)
    if median > p["overlap_flag_low_distance"].value:
        return "low", median
    if median > p["overlap_flag_medium_distance"].value:
        return "medium", median
    return "high", median


FEE_STOPS = tuple(round(x / 10, 1) for x in range(-5, 11) if x != 0)  # the slider: up 50% to abolished


def fee_types_with_stops(places: pd.DataFrame, origin: int, draws: int, types: pd.DataFrame) -> pd.DataFrame:
    """`results_fee_types` with every slider stop added for each size that is not linear in the fee change.

    The engine's grid (`fees.change_grid`, same draws as `fees.simulate`) at every stop in `FEE_STOPS`: a size
    whose homes added equal (s ÷ 0.5) × the half cut in every draw and stop (the elasticity route) keeps
    only its 0.5 rows, which the page scales. Any other size (houses on the lot-feasibility route, places
    with a parcel roll) gets the grid's value at every stop, with the draw's completion and the size's
    baseline. Raises if the grid's half cut differs from `types` (they must be the same draws).
    """
    from lotline.model.scenarios import fees

    if types is None or not len(types):
        return types
    grid = fees.change_grid(places, origin, list(FEE_STOPS), draws=draws)
    w = grid.pivot_table(index=["draw", "size"], columns="share", values="units_added", aggfunc="sum")
    tol = 1e-6 * max(1.0, float(w[0.5].abs().max()))
    t = types.assign(draw=types["draw"].astype(int)).set_index(["draw", "size"]).sort_index()
    if not np.allclose(
        w[0.5].reindex(t.index).to_numpy(dtype=float), t["units_added"].to_numpy(float), atol=tol
    ):
        raise ValueError("results_fee_types does not match the engine's grid at a cut of half")
    extra = []
    for size in sorted(set(t.index.get_level_values("size"))):
        ws = w.xs(size, level="size")
        if all(np.allclose(ws[s], (s / 0.5) * ws[0.5], atol=tol) for s in FEE_STOPS):
            continue
        half = t.xs(size, level="size")
        for s in FEE_STOPS:
            if s == 0.5:
                continue
            at_s = ws[s].reindex(half.index).to_numpy(float)
            extra.append(half.assign(fee_change_share=s, units_added=at_s).reset_index().assign(size=size))
    return pd.concat([types, *extra], ignore_index=True) if extra else types


def adu_place_type_table(state: str, places: pd.DataFrame, run_draws: Mapping) -> pd.DataFrame:
    """`results_adu_place_types`: the ADU scenario by place type (D-088), from `adu.run`'s draws.

    Per type: places; lots = the median over draws of its eligible lots; base and added = each draw's
    current-rules and added gross ADUs summed over the type's places, averaged over the window years, then
    P10/P50/P90 across draws. By hand: two suburb places with 3 and 5 current-rules ADUs a year and 1 and 2
    added, in every draw -> base 8, added 3.
    """
    kind = places["place_type"].fillna("suburb").to_numpy() if "place_type" in places else None
    cur = np.asarray(run_draws["current"], dtype=float)  # draws x places x years
    add = np.asarray(run_draws["added"], dtype=float)
    elig = np.asarray(run_draws["eligible"], dtype=float)
    rows = []
    for t in ("core", "suburb", "town"):
        on = (kind == t) if kind is not None else np.full(cur.shape[1], t == "suburb")
        if not on.any():
            continue
        b = cur[:, on, :].sum(axis=1).mean(axis=1)
        a = add[:, on, :].sum(axis=1).mean(axis=1)
        (b10, b50, b90), (a10, a50, a90) = np.percentile(b, [10, 50, 90]), np.percentile(a, [10, 50, 90])
        rows.append(
            {
                "state": state,
                "place_type": t,
                "places": int(on.sum()),
                "lots": float(np.median(elig[:, on].sum(axis=1))),
                "base_p10": b10,
                "base": b50,
                "base_p90": b90,
                "added_p10": a10,
                "added": a50,
                "added_p90": a90,
            }
        )
    return pd.DataFrame(rows, columns=["state", *_columns("adu_place_types")])


def adu_baseline_years(state: str, run_draws: Mapping, origin: int, own=None) -> pd.DataFrame:
    """`results_adu_baseline`: statewide current-rules gross ADUs per window year, P10/P50/P90 over draws.

    With `own` (a bool per place: its no-reform rate comes from its own ADU counts), each year also gets the
    mean and, where some places have own counts, `own_counts` and `model` rows: percentiles of each group's
    own sum, and means that add up to the `all` row's (the page splits the bar by them).
    By hand: places with 10 and 4 ADUs a year in every draw, the first with own counts -> all 14, own_counts
    10, model 4; means the same.
    """
    cur_by_place = np.asarray(run_draws["current"], dtype=float)  # draws x places x years
    _, _, first = baseline.window(origin)
    years = range(cur_by_place.shape[2])
    if own is None:
        cur = cur_by_place.sum(axis=1)
        rows = [{"state": state, "period": str(first + y), **_pct(cur[:, y])} for y in years]
        cols = [c for c in _columns("adu_baseline") if c not in ("basis", "mean")]
        return pd.DataFrame(rows, columns=["state", *cols])
    own = np.asarray(own, dtype=bool)
    groups = {"all": np.ones_like(own)} | ({"own_counts": own, "model": ~own} if own.any() else {})
    rows = []
    for basis, m in groups.items():
        cur = cur_by_place[:, m, :].sum(axis=1)
        for y in years:
            a = cur[:, y]
            rows.append(
                {"state": state, "period": str(first + y), "basis": basis, **_pct(a), "mean": a.mean()}
            )
    return pd.DataFrame(rows, columns=["state", *_columns("adu_baseline")])


def affordability_table(state: str, places, run_draws: Mapping, res_mm, fee_places, store) -> pd.DataFrame:
    """`results_affordability`: who the new homes serve (`model/affordability.py`), from the inputs the
    scenarios already used. Empty (no rows) when no HUD income limits file is registered."""
    from lotline.model import affordability

    market = store.read(state, "market_geo_year")
    inputs = affordability.inputs(places, run_draws, getattr(res_mm, "places", None), fee_places, market)
    out = affordability.table(state, inputs)
    return (
        out.astype({"places": "Int64"})
        if len(out)
        else pd.DataFrame(columns=["state", *_columns("affordability")])
    )


def state_stock(
    acs: pd.DataFrame | None, state: str, origin: int, fips: str | None = None
) -> tuple[float, int] | None:
    """The state's housing units (ACS B25024_001, newest 5-year vintage ending by `origin`) and its year."""
    from lotline.config import load_state

    if acs is None or acs.empty:
        return None
    geo = f"state:{fips or load_state(state).fips}"
    rows = acs[(acs["geo"] == geo) & (acs["variable"] == "B25024_001") & (acs["end_year"] <= origin)]
    rows = rows.dropna(subset=["estimate"]).sort_values("end_year")
    return (float(rows["estimate"].iloc[-1]), int(rows["end_year"].iloc[-1])) if len(rows) else None


def shortfall_table(
    state: str, base: pd.DataFrame, acs, origin: int, need_params=None, fips=None
) -> pd.DataFrame:
    """`results_shortfall`: the need left after homes built anyway (`model/shortfall.py`). No row when the
    state has no shortage estimate, no housing stock or no five-year all-sizes baseline."""
    from lotline.model import shortfall

    cols = ["state", *_columns("shortfall")]
    have = aggregate.need(state, need_params)
    stock = state_stock(acs, state, origin, fips)
    five = base[(base["size_class"] == "all") & base["period"].str.contains("-")] if len(base) else base
    if aggregate.SHORTAGE not in have or stock is None or not len(five):
        return pd.DataFrame(columns=cols)
    sh = have[aggregate.SHORTAGE]
    gr = have.get(aggregate.GROWTH)
    growth = (gr.low, gr.value, gr.high) if gr is not None else (0.0, 0.0, 0.0)
    r = load_params("aggregate")["stock_loss_rate"]
    b = five.iloc[0]
    g = shortfall.gap(
        (sh.low, sh.value, sh.high),
        growth,
        stock[0],
        (r.low, r.value, r.high),
        (b["p10"], b["p50"], b["p90"]),
    )
    row = {
        "state": state, "shortage_low": sh.low, "shortage": sh.value, "shortage_high": sh.high,
        "growth_low": growth[0], "growth": growth[1], "growth_high": growth[2],
        "stock": stock[0], "stock_year": stock[1],
        "built_p10": b["p10"], "built": b["p50"], "built_p90": b["p90"], **g,
    }  # fmt: skip
    return pd.DataFrame([row], columns=cols).astype({"stock_year": "Int64"})


def year_shares(run_draws: Mapping) -> np.ndarray:
    """Each draw's permits by year as a share of its five-year total (draws x years)."""
    from lotline.model.scenarios import year_shares_of

    return year_shares_of(np.asarray(run_draws["added"], dtype=float).sum(axis=1))


def _pct(a) -> dict[str, float]:
    p10, p50, p90 = np.percentile(np.asarray(a, dtype=float), [10, 50, 90])
    return {"p10": p10, "p50": p50, "p90": p90}


def _columns(part: str) -> list[str]:
    from lotline.schemas import columns

    return [c for c in columns(f"results_{part}") if c != "state"]
