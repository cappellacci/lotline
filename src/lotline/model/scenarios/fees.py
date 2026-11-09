"""Handbook fee scenario: cut development fees by half (Handbook benchmark; fees causal diagram; methods
review §3c).

**How big is the cut?** Three labeled scenarios (D-065):

- `handbook` ("Benchmark: a $50,000 fee cut in half"): F = `handbook_fee_per_unit_usd` ($50,000, 2025
  dollars) everywhere; Δ = `handbook_fee_cut_share` × F = $25,000. The Rules' benchmark.
- `local_half` ("Real local fees cut in half"; `local` is accepted as its old name): F = the place's local
  single-family fee per unit (`local_fee_per_unit`, from `lotline.model.fee_levels.place_fees`: coded rows in
  2025 dollars, missing permit and water/sewer parts filled from a prior, D-065); Δ = cut share × F.
- `local_25k` ("Real local fees cut by up to $25,000"): the same F; Δ = min(cut share × $50,000, F).

In the local scenarios F is drawn in each simulation draw within the place's range (`local_fee_low`,
`local_fee_high`: fees that vary by area, basin or plat date, and the spread of a filled prior; #247), as a
triangular(low, central, high). The $50,000 is never a fallback there: a place with no local fee is an error.

Builders keep (1 − λ) × Δ; the rest ends up in land prices (λ = `land_capture_share`, C18). That builder
saving s moves permits through one of two channels:

- **(a) Feasibility** (places with parcel data): the single-family pro forma at the place's new-home value
  gives the residual land value before the cut (fee F) and after it (fee F − s). A candidate lot is feasible
  when that value beats its land value plus the margin (`proforma.is_feasible`). Permits are taken to scale
  with the number of feasible lots:  %Δ = feasible after / feasible before − 1. Used only where at least
  `fee_feasibility_min_lots` lots were feasible before the cut.
- **(b) Elasticity** (everywhere else, D-010):  %Δ = ε × s / TDC, where TDC, the total development cost of a
  home at the margin of feasibility, is taken as its price: the place's median home value (2025 dollars).

Either way the change phases in:  added units(t) = baseline units(t) × %Δ × ramp(t), with
ramp(t) = 1 / (1 + exp(−(t − half) / slope)) (`fee_ramp_half_years`, `fee_ramp_slope_years`).
A zero cut adds nothing, and a bigger cut never adds less (both channels are monotone in s).

Every result is a range: P10/P50/P90 and the mean over `fee_simulation_draws` draws of ε, λ, the ramp, the
pro forma parameters and, in the local scenarios, the local fee (each triangular over low, central, high).
The baseline enters as its mean per year, so
the range is the scenario's, not the baseline's. Places must be non-overlapping units to be summed (D-020).
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.model import baseline as baseline_model
from lotline.model import fee_levels as fee_level_rules
from lotline.model import hazard, proforma

PARAM_FILES = ("fees", "proforma")
FIXED = proforma.NOT_SAMPLED | {"fee_simulation_draws", "fee_simulation_seed", "fee_feasibility_min_lots"}
MODES = ("handbook", "local_half", "local_25k")
ALIASES = {"local": "local_half"}  # the name before D-065
LABELS = {
    "handbook": "Benchmark: a $50,000 fee cut in half",
    "local_half": "Real local fees cut in half",
    "local_25k": "Real local fees cut by up to $25,000",
}


def specs() -> dict:
    out = {}
    for name in PARAM_FILES:
        out.update(load_params(name))
    return out


def central_params() -> dict[str, float]:
    return {k: s.value for k, s in specs().items()}


def draw_params(n: int, seed: int) -> list[dict[str, float]]:
    """n parameter sets: each uncertain parameter triangular(low, central, high); fixed ones held."""
    rng = np.random.default_rng(seed)
    cols = {
        k: np.full(n, s.value) if k in FIXED or s.low == s.high else rng.triangular(s.low, s.value, s.high, n)
        for k, s in specs().items()
    }
    return [{k: float(v[i]) for k, v in cols.items()} for i in range(n)]


# ---------------------------------------------------------------------------------------------------------
# Fee level
# ---------------------------------------------------------------------------------------------------------


def _mode(mode: str) -> str:
    mode = ALIASES.get(mode, mode)
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
    return mode


def local_fees(fees: pd.DataFrame, index: pd.Series | None = None) -> pd.DataFrame:
    """Coded fee per unit for a new single-family home, per coded place, before any fill.

    A thin wrapper over `lotline.model.fee_levels.coded_fees` (building type SFD), kept for callers of the
    pre-D-065 API. Per component, the newest year with a per-unit amount, plus older rows still in force
    (#247).
    By hand: permit 2023 $3,000 and 2026 $3,500; water_sewer 2025 $2,000 -> $5,500 (permit 2026 + w/s 2025).
    """
    return fee_level_rules.coded_fees(fees, "SFD", index=index)


def fee_levels(places: pd.DataFrame, mode: str, params: Mapping[str, float]) -> tuple[np.ndarray, np.ndarray]:
    """Central fee per unit before the cut, and where it came from (`fee_source`, or 'handbook')."""
    mode = _mode(mode)
    n = len(places)
    if mode == "handbook":
        return np.full(n, float(params["handbook_fee_per_unit_usd"])), np.full(n, "handbook", dtype=object)
    if "local_fee_per_unit" not in places:
        raise ValueError("local fee scenarios need local_fee_per_unit (fee_levels.place_fees)")
    level = places["local_fee_per_unit"].to_numpy(dtype=float)
    if np.isnan(level).any():
        raise ValueError("a place has no local fee; the $50,000 is not a fallback (D-065)")
    source = places.get("fee_source", pd.Series("local", index=places.index)).fillna("local")
    return level, source.to_numpy(dtype=object)


def fee_draws(places: pd.DataFrame, mode: str, params: Mapping[str, float], n: int, seed: int) -> np.ndarray:
    """(draws × places) fee per unit: the central value in the benchmark; triangular(low, central, high) in
    the local scenarios where a range is given (`local_fee_low`, `local_fee_high`), else the central value."""
    central, _ = fee_levels(places, mode, params)
    out = np.repeat(central[None, :], n, axis=0)
    if _mode(mode) == "handbook" or "local_fee_low" not in places or "local_fee_high" not in places:
        return out
    low = places["local_fee_low"].fillna(places["local_fee_per_unit"]).to_numpy(dtype=float)
    high = places["local_fee_high"].fillna(places["local_fee_per_unit"]).to_numpy(dtype=float)
    low, high = np.minimum(low, central), np.maximum(high, central)
    rng = np.random.default_rng(seed)
    for i in np.flatnonzero(high > low):
        out[:, i] = rng.triangular(low[i], central[i], high[i], n)
    return out


def fee_cut(fee: np.ndarray, params: Mapping[str, float], mode: str = "handbook") -> np.ndarray:
    """Δ per unit: cut share × fee; in `local_25k`, the Handbook's dollar cut capped at the fee."""
    fee = np.asarray(fee, dtype=float)
    share = params["handbook_fee_cut_share"]
    if _mode(mode) == "local_25k":
        return np.minimum(share * params["handbook_fee_per_unit_usd"], fee)
    return share * fee


def builder_saving(fee: np.ndarray, params: Mapping[str, float], mode: str = "handbook") -> np.ndarray:
    """(1 − λ) × Δ: the part of the cut that reaches builders."""
    return proforma.builder_fee_saving(fee_cut(fee, params, mode), params["land_capture_share"])


# ---------------------------------------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------------------------------------


def elasticity_change(saving, tdc, params: Mapping[str, float]) -> np.ndarray:
    """(b) %Δ permits = ε × saving / TDC (D-010). By hand: ε 0.3, saving $12,500, TDC $250,000 -> 0.015."""
    tdc = np.asarray(tdc, dtype=float)
    return params["fee_permit_elasticity"] * np.asarray(saving, dtype=float) / tdc


def feasible_lots(new_home_value: float, fee: float, lot_values, params: Mapping[str, float]) -> int:
    """How many candidate lots the single-family prototype is feasible on at this fee per unit.

    Residual land value from the for-sale pro forma at the place's new-home value (price per sq ft = value /
    prototype size); a lot is feasible when that beats its land value × (1 + `existing_use_margin`).
    """
    market = proforma.Market(new_home_value / params["single_family_sqft"], 0.0)
    rlv = proforma.residual_land_value("single_family", "for_sale", market, fee, params)
    lots = np.asarray(lot_values, dtype=float)
    return int(np.sum(rlv >= lots * (1 + params["existing_use_margin"])))


def feasibility_change(
    new_home_value: float, fee: float, saving: float, lot_values, params: Mapping[str, float]
) -> tuple[float, int, int]:
    """(a) %Δ permits = feasible after / feasible before − 1, with both counts. NaN below the minimum."""
    before = feasible_lots(new_home_value, fee, lot_values, params)
    after = feasible_lots(new_home_value, fee - saving, lot_values, params)
    if before < params["fee_feasibility_min_lots"]:
        return float("nan"), before, after
    return after / before - 1.0, before, after


def pct_change(places: pd.DataFrame, fee: np.ndarray, params: Mapping[str, float], mode: str = "handbook"):
    """%Δ permits per place for one parameter set, and the channel used ('feasibility' or 'elasticity')."""
    saving = builder_saving(fee, params, mode)
    pct = elasticity_change(saving, places["home_value"].to_numpy(dtype=float), params)
    channel = np.full(len(places), "elasticity", dtype=object)
    if "lot_values" in places and "new_home_value" in places:
        for i, (lots, value) in enumerate(zip(places["lot_values"], places["new_home_value"], strict=True)):
            # a place without parcel data has NaN (from a merge) or None here, not an array
            if not isinstance(lots, np.ndarray | list) or len(lots) == 0 or not np.isfinite(value):
                continue
            change, _, _ = feasibility_change(value, fee[i], saving[i], lots, params)
            if np.isfinite(change):
                pct[i], channel[i] = change, "feasibility"
    return pct, channel


def ramp(horizon: int, params: Mapping[str, float]) -> np.ndarray:
    """Share of the full response reached in years 1..horizon after the cut."""
    t = np.arange(1, horizon + 1)
    return hazard.ramp(t, params["fee_ramp_half_years"], params["fee_ramp_slope_years"])


def added_units(baseline: np.ndarray, pct: np.ndarray, params: Mapping[str, float]) -> np.ndarray:
    """Units added (places × years) = baseline(t) × %Δ × ramp(t)."""
    b = np.asarray(baseline, dtype=float)
    return b * np.asarray(pct, dtype=float)[:, None] * ramp(b.shape[1], params)[None, :]


# ---------------------------------------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------------------------------------


def _baseline(places: pd.DataFrame, horizon: int) -> np.ndarray:
    cols = [f"baseline_y{t}" for t in range(1, horizon + 1)]
    if all(c in places for c in cols):
        return places[cols].to_numpy(dtype=float)
    return np.repeat(places["baseline_units"].to_numpy(dtype=float)[:, None], horizon, axis=1)


def central_path(places: pd.DataFrame, mode: str = "local_half", params: dict | None = None) -> dict:
    """Central values (hand checks): fee, saving, %Δ, channel and added units (places × years)."""
    p = central_params() | (params or {})
    _, horizon, _ = baseline_model.window(0)
    fee, source = fee_levels(places, mode, p)
    pct, channel = pct_change(places, fee, p, mode)
    return {
        "fee": fee,
        "fee_source": source,
        "cut": fee_cut(fee, p, mode),
        "saving": builder_saving(fee, p, mode),
        "pct": pct,
        "channel": channel,
        "added": added_units(_baseline(places, horizon), pct, p),
    }


def run(
    places: pd.DataFrame,
    origin: int,
    *,
    mode: str = "local_half",
    draws: int | None = None,
    summary_by: str | None = None,
):
    """The fee scenario per place: (per-year table, five-year totals[, summary]), with P10/P50/P90 and mean.

    `origin` is the last year of data; the years reported are the window `baseline.window(origin)` (D-061),
    and the fee cut takes effect at its start, so ramp year 1 is the window's first year. baseline_y1..y5 are
    the baseline's window years (`baseline_forecast`'s horizon 1..5), not the years right after the origin.

    `places` columns: geoid; baseline_units (mean baseline units a year) or baseline_y1..baseline_y5;
    home_value (median home value, 2025 dollars: TDC for the elasticity route); for the local scenarios
    local_fee_per_unit, optional local_fee_low/local_fee_high and fee_source (`fee_levels.place_fees`);
    optional new_home_value (2025 dollars) and lot_values (an array of
    candidate lots' land values, 2025 dollars) for the feasibility channel. Extra columns are carried through.
    With `summary_by`, a third table sums each draw over the group's places (non-overlapping units, D-020).
    """
    central = central_params()
    n = int(draws or central["fee_simulation_draws"])
    sets = draw_params(n, int(central["fee_simulation_seed"]))
    _, horizon, first = baseline_model.window(origin)
    base = _baseline(places, horizon)
    mode = _mode(mode)
    fee, source = fee_levels(places, mode, central)
    fees_d = fee_draws(places, mode, central, n, int(central["fee_simulation_seed"]) + 1)
    out = np.zeros((n, len(places), horizon))
    used = np.zeros((n, len(places)), dtype=bool)  # feasibility channel used in this draw
    for d, p in enumerate(sets):
        pct, channel = pct_change(places, fees_d[d], p, mode)
        out[d] = added_units(base, pct, p)
        used[d] = channel == "feasibility"
    c = central_path(places, mode)
    info = (
        places.drop(columns=["lot_values"], errors="ignore")
        .assign(
            mode=mode,
            scenario_label=LABELS[mode],
            fee_per_unit=fee,
            fee_source=source,
            fee_cut_per_unit=c["cut"],
            builder_saving_central=c["saving"],
            pct_change_central=c["pct"],
            channel_central=c["channel"],
            feasibility_share_of_draws=used.mean(axis=0) if n else 0.0,
            baseline_five_year=base.sum(axis=1),
        )
        .reset_index(drop=True)
    )
    yearly = info.loc[info.index.repeat(horizon)].reset_index(drop=True)
    yearly["horizon"] = np.tile(np.arange(1, horizon + 1), len(places))
    yearly["year"] = first - 1 + yearly["horizon"]
    yearly["baseline_units_year"] = base.reshape(-1)
    totals = info.copy()
    for table, a in ((yearly, out.reshape(n, -1)), (totals, out.sum(axis=2))):
        table["units_added_mean"] = a.mean(axis=0)
        for q in (10, 50, 90):
            table[f"units_added_p{q}"] = np.percentile(a, q, axis=0)
    if summary_by is None:
        return yearly, totals
    rows = []
    for group, idx in pd.Series(range(len(places)), index=places[summary_by].to_numpy()).groupby(level=0):
        sums = out[:, idx.to_numpy(), :].sum(axis=1)  # (draws, years)
        for h in range(horizon + 1):
            a = sums.sum(axis=1) if h == horizon else sums[:, h]
            label = f"{first}-{first + horizon - 1}" if h == horizon else str(first + h)
            p10, p50, p90 = np.percentile(a, [10, 50, 90])
            rows.append(
                {summary_by: group, "period": label, "p10": p10, "p50": p50, "p90": p90, "mean": a.mean()}
            )
    return yearly, totals, pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Inputs from a state's processed tables (real data; the development run)
# ---------------------------------------------------------------------------------------------------------


def parcel_inputs(parcels: pd.DataFrame, origin: int, params: Mapping[str, float]) -> pd.DataFrame:
    """Per place: candidate lots' land values and a new-home value, from its newest parcel roll <= origin + 1.

    Candidate lots: vacant residential parcels (VACANT_RESIDENTIAL) with a land value. New-home value:
    median (land + building value) per building sq ft of detached homes built in the last `fee_new_home_years`
    up to the origin, times the single-family prototype's size. Assessed values in the roll's own dollars.
    """
    need = ["land_use_std", "year_built", "bldg_sqft", "land_value", "bldg_value"]
    parcels = parcels.assign(**{c: np.nan for c in need if c not in parcels})  # a roll without a column
    p = parcels[parcels["vintage"] <= origin + 1]
    p = p[p["vintage"] == p.groupby("jurisdiction_geoid")["vintage"].transform("max")]
    first = origin - int(params["fee_new_home_years"])
    new = p[
        (p["land_use_std"] == "SF_DETACHED")
        & p["year_built"].between(first, origin)
        & (p["bldg_sqft"] > 0)
        & p["land_value"].notna()
        & p["bldg_value"].notna()
    ]
    per_sqft = ((new["land_value"] + new["bldg_value"]) / new["bldg_sqft"]).groupby(new["jurisdiction_geoid"])
    vacant = p[(p["land_use_std"] == "VACANT_RESIDENTIAL") & p["land_value"].notna()]
    lots = vacant.groupby("jurisdiction_geoid")["land_value"].apply(lambda s: s.to_numpy(dtype=float))
    out = pd.DataFrame({"new_home_value": per_sqft.median() * params["single_family_sqft"]})
    out["new_homes_seen"] = per_sqft.size()
    out = out.join(lots.rename("lot_values"), how="outer")
    out["parcel_vintage"] = p.groupby("jurisdiction_geoid")["vintage"].max()
    return out.rename_axis("geoid").reset_index()
