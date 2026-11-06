"""Statewide aggregation outputs. This module so far: the share of housing need (WS-ENGINE brief; D-056).

A scenario's five-year statewide homes are shown against one of two denominators from
config/params/housing_need.yaml, which are **never mixed** without their label:

- `household_growth_5y`: households the state's own projection implies over five years (onboarded states;
  derived from the demographer's population projection at constant headship). Reads "x% of the homes the
  state expects to need over five years".
- `shortage_stock`: the state's estimated housing shortage (every state; Up for Growth with Freddie Mac as a
  second estimate). Reads "x% of the state's estimated shortage".

`headline_kind` picks growth where a state has a positive projection and the shortage otherwise (a falling
projection, as in Ohio, has no growth to share). `share_of_need` returns the share for each percentile of
the homes draws plus the share at the denominator's low and high, and always carries `denominator_kind`.

By hand: draws with P10/P50/P90 = 100/200/400 homes and a shortage of 1,000 (low 800, high 2,000) give shares
0.10/0.20/0.40; at the median, 200/2,000 = 0.10 against the high shortage and 200/800 = 0.25 against the low.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from lotline.config import Parameter, load_params

GROWTH = "household_growth_5y"
SHORTAGE = "shortage_stock"
KINDS = (GROWTH, SHORTAGE)
LABELS = {
    GROWTH: "of the homes the state expects to need over five years",
    SHORTAGE: "of the state's estimated shortage",
}


def need(state: str, params: Mapping[str, Parameter] | None = None) -> dict[str, Parameter]:
    """The denominators coded for one state: kind -> Parameter (a state may have one or both)."""
    p = params if params is not None else load_params("housing_need")
    return {kind: p[f"{kind}_{state.lower()}"] for kind in KINDS if f"{kind}_{state.lower()}" in p}


def headline_kind(state: str, params: Mapping[str, Parameter] | None = None) -> str:
    """Household growth where the state's projection is positive, else the shortage."""
    have = need(state, params)
    if GROWTH in have and have[GROWTH].value > 0:
        return GROWTH
    if SHORTAGE in have:
        return SHORTAGE
    raise KeyError(f"no housing-need denominator coded for {state}")


def share_of_need(
    homes: np.ndarray,
    state: str,
    kind: str | None = None,
    params: Mapping[str, Parameter] | None = None,
) -> dict:
    """Share of need for a statewide five-year homes total given as draws (any shape; flattened).

    Returns `denominator_kind`, the plain-language `label`, the denominator (value, low, high), the share at
    P10/P50/P90 of the draws against the central denominator, and the median share against the
    denominator's high and low (`share_p50_at_need_high` is the smaller). A denominator at or below zero has
    no share and raises ValueError.
    """
    kind = kind or headline_kind(state, params)
    if kind not in KINDS:
        raise ValueError(f"unknown denominator kind {kind!r}")
    d = need(state, params).get(kind)
    if d is None:
        raise KeyError(f"{state} has no {kind} denominator")
    if d.low <= 0:
        raise ValueError(f"{state} {kind} is {d.low:,.0f} at its low: no share of need")
    p10, p50, p90 = np.percentile(np.asarray(homes, dtype=float).ravel(), [10, 50, 90])
    return {
        "state": state.upper(),
        "denominator_kind": kind,
        "label": LABELS[kind],
        "denominator": d.value,
        "denominator_low": d.low,
        "denominator_high": d.high,
        "share_p10": p10 / d.value,
        "share_p50": p50 / d.value,
        "share_p90": p90 / d.value,
        "share_p50_at_need_high": p50 / d.high,
        "share_p50_at_need_low": p50 / d.low,
        "denominator_source": d.source,
    }


# ---- the headline from exported draws (the browser's arithmetic; parity target, #310) ----------------------

TIER_COLUMNS = ("eligible_tier1", "eligible_tier2", "eligible_tier3")


def homes_from_draws(draws) -> dict[str, np.ndarray]:
    """Per-draw statewide homes from a `results_draws` table: the only model arithmetic the app repeats.

    eligible = Σ tiers; pencils = eligible × pencil_out_share; permits = pencils × theta × (1 − overlap);
    homes in place = permits × completion_factor × net_new_share; net statewide = homes in place ×
    (1 − displacement_share). A null overlap_share (a single scenario) counts as 0.

    By hand: 1,000 eligible, pencil-out 0.5, θ 0.04, overlap 0, completion 1.0, net-new 0.6, displacement 0.25
    -> 500 pencil out, 20 permits, 12 homes in place, 9 net statewide.
    """
    eligible = sum(np.asarray(draws[c], dtype=float) for c in TIER_COLUMNS)
    pencils = eligible * np.asarray(draws["pencil_out_share"], dtype=float)
    overlap = np.nan_to_num(np.asarray(draws["overlap_share"], dtype=float), nan=0.0)
    permits = pencils * np.asarray(draws["theta"], dtype=float) * (1 - overlap)
    in_place = (
        permits * np.asarray(draws["completion_factor"], dtype=float) * np.asarray(draws["net_new_share"])
    )
    net = in_place * (1 - np.asarray(draws["displacement_share"], dtype=float))
    return {
        "legal": eligible,
        "pencils": pencils,
        "permits_added": permits,
        "homes_in_place": in_place,
        "homes_net_statewide": net,
    }
