"""Handbook fee scenario: cut development fees by half (Handbook benchmark; fees causal diagram; methods
review §3c).

**How big is the cut?** Each place's fee level F per unit is either:

- `local` (default): the place's coded single-family fee per unit from config/fees (`local_fees`): SFD and
  OTHER rows' `amount_per_unit_usd`, each fee component at its newest coded year, summed. It is used only
  where a water/sewer fee is coded (the largest component, and the one most often missing); elsewhere F is the
  national prior, `handbook_fee_per_unit_usd` ($50,000). `fee_source` says which.
- `handbook`: $50,000 everywhere (the Rules' benchmark).

The cut is Δ = `handbook_fee_cut_share` × F. Builders keep (1 − λ) × Δ; the rest ends up in land prices
(λ = `land_capture_share`, C18). That builder saving s moves permits through one of two channels:

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

Every result is a range: P10/P50/P90 and the mean over `fee_simulation_draws` draws of ε, λ, the ramp and the
pro forma parameters (each triangular over low, central, high). The baseline enters as its mean per year, so
the range is the scenario's, not the baseline's. Places must be non-overlapping units to be summed (D-020).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.model import hazard, proforma

PARAM_FILES = ("fees", "proforma")
FIXED = proforma.NOT_SAMPLED | {"fee_simulation_draws", "fee_simulation_seed", "fee_feasibility_min_lots"}
MODES = ("local", "handbook")
SFD_TYPES = ("SFD", "OTHER")  # OTHER rows apply to any building type and are priced at the SFD prototype
REQUIRED_COMPONENT = "water_sewer"  # a local fee total without it is too incomplete to use (D-034)


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


def local_fees(fees: pd.DataFrame, types: Sequence[str] = SFD_TYPES) -> pd.DataFrame:
    """Coded fee per unit for a new single-family home, per place (config/fees rows).

    For each place and fee component, the newest year with any per-unit amount; those rows summed.
    Returns geoid, local_fee_per_unit, fee_components (sorted, comma-separated), fee_years ('component:year').
    By hand: permit 2023 $3,000 and 2026 $3,500; water_sewer 2025 $2,000 -> $5,500 (permit 2026 + w/s 2025).
    """
    cols = ["geoid", "local_fee_per_unit", "fee_components", "fee_years"]
    f = fees[fees["building_type_std"].isin(types) & fees["amount_per_unit_usd"].notna()]
    if f.empty:
        return pd.DataFrame(columns=cols)
    newest = f.groupby(["jurisdiction_geoid", "fee_component"])["year"].transform("max")
    f = f[f["year"] == newest]
    by = f.groupby(["jurisdiction_geoid", "fee_component"]).agg(
        amount=("amount_per_unit_usd", "sum"), year=("year", "max")
    )
    rows = []
    for geoid, g in by.groupby(level=0):
        comps = g.index.get_level_values(1)
        rows.append(
            {
                "geoid": geoid,
                "local_fee_per_unit": float(g["amount"].sum()),
                "fee_components": ",".join(sorted(comps)),
                "fee_years": ",".join(f"{c}:{int(y)}" for c, y in zip(comps, g["year"], strict=True)),
            }
        )
    return pd.DataFrame(rows, columns=cols)


def fee_levels(places: pd.DataFrame, mode: str, params: Mapping[str, float]) -> tuple[np.ndarray, np.ndarray]:
    """Fee per unit before the cut, and where it came from ('local' or 'national prior')."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
    prior = params["handbook_fee_per_unit_usd"]
    n = len(places)
    if mode == "handbook":
        return np.full(n, prior), np.full(n, "handbook", dtype=object)
    local = places.get("local_fee_per_unit", pd.Series(np.nan, index=places.index)).astype(float)
    comps = places.get("fee_components", pd.Series("", index=places.index)).fillna("").astype(str)
    usable = local.notna() & comps.str.split(",").apply(lambda c: REQUIRED_COMPONENT in c)
    level = np.where(usable, local, prior)
    return level.astype(float), np.where(usable, "local", "national prior").astype(object)


def builder_saving(fee: np.ndarray, params: Mapping[str, float]) -> np.ndarray:
    """(1 − λ) × cut share × fee: the part of the cut that reaches builders."""
    cut = params["handbook_fee_cut_share"] * np.asarray(fee, dtype=float)
    return proforma.builder_fee_saving(cut, params["land_capture_share"])


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


def pct_change(places: pd.DataFrame, fee: np.ndarray, params: Mapping[str, float]):
    """%Δ permits per place for one parameter set, and the channel used ('feasibility' or 'elasticity')."""
    saving = builder_saving(fee, params)
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


def central_path(places: pd.DataFrame, mode: str = "local", params: dict | None = None) -> dict:
    """Central values (hand checks): fee, saving, %Δ, channel and added units (places × years)."""
    p = central_params() | (params or {})
    horizon = int(load_params("baseline")["forecast_horizon_years"].value)
    fee, source = fee_levels(places, mode, p)
    pct, channel = pct_change(places, fee, p)
    return {
        "fee": fee,
        "fee_source": source,
        "saving": builder_saving(fee, p),
        "pct": pct,
        "channel": channel,
        "added": added_units(_baseline(places, horizon), pct, p),
    }


def run(
    places: pd.DataFrame,
    origin: int,
    *,
    mode: str = "local",
    draws: int | None = None,
    summary_by: str | None = None,
):
    """The fee scenario per place: (per-year table, five-year totals[, summary]), with P10/P50/P90 and mean.

    `places` columns: geoid; baseline_units (mean baseline units a year) or baseline_y1..baseline_y5;
    home_value (median home value, 2025 dollars: TDC for the elasticity route); optional local_fee_per_unit
    and fee_components (`local_fees`); optional new_home_value (2025 dollars) and lot_values (an array of
    candidate lots' land values, 2025 dollars) for the feasibility channel. Extra columns are carried through.
    With `summary_by`, a third table sums each draw over the group's places (non-overlapping units, D-020).
    """
    central = central_params()
    n = int(draws or central["fee_simulation_draws"])
    sets = draw_params(n, int(central["fee_simulation_seed"]))
    horizon = int(load_params("baseline")["forecast_horizon_years"].value)
    base = _baseline(places, horizon)
    fee, source = fee_levels(places, mode, central)
    out = np.zeros((n, len(places), horizon))
    used = np.zeros((n, len(places)), dtype=bool)  # feasibility channel used in this draw
    for d, p in enumerate(sets):
        pct, channel = pct_change(places, fee, p)
        out[d] = added_units(base, pct, p)
        used[d] = channel == "feasibility"
    c = central_path(places, mode)
    info = (
        places.drop(columns=["lot_values"], errors="ignore")
        .assign(
            mode=mode,
            fee_per_unit=fee,
            fee_source=source,
            fee_cut_per_unit=central["handbook_fee_cut_share"] * fee,
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
    yearly["year"] = origin + yearly["horizon"]
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
            label = f"{origin + 1}-{origin + horizon}" if h == horizon else str(origin + 1 + h)
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
