"""Handbook fee scenario: cut development fees by half (Handbook benchmark; fees causal diagram; methods
review §3c).

**How big is the cut?** Three labeled scenarios (D-065):

- `handbook` ("Benchmark: a $50,000 fee cut in half"): F = `handbook_fee_per_unit_usd` ($50,000, 2025
  dollars) everywhere; Δ = `handbook_fee_cut_share` × F = $25,000. The Rules' benchmark.
- `local_half` ("Real local fees cut in half"; `local` is accepted as its old name): F = the place's local
  single-family fee per unit (`local_fee_per_unit`, from `lotline.model.fee_levels.place_fees`: coded rows in
  2025 dollars, missing permit and water/sewer parts filled from a prior, D-065); Δ = cut share × F.
- `local_25k` ("Real local fees cut by up to $25,000"): the same F; Δ = min(cut share × $50,000, F).
- `local_rise` ("Sensitivity: real local fees raised by half", D-073): the same F; Δ = −`fee_rise_share` × F,
  a negative cut through the same λ, ε and ramp. It shows what a fee increase costs in homes (A4); it is a
  sensitivity, not one of the Handbook's scenarios.

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

**Dose by building size (D-073).** When `places` carries the baseline by BPS size class
(`baseline_y<h>_1`, `_2`, `_3_4`, `_5p`), each class takes its own %Δ: 1-unit buildings the house's (either
channel above, with the house fee); 2-unit and 3-4 unit buildings the elasticity route with their own fee per
unit (`local_fee_per_unit_U2`, `_U3_4`, from `fee_levels.place_fees`; the Handbook's $50,000 in the benchmark)
and their own cost per unit, the place's home value scaled to the unit's size (`plex_unit_sqft` /
`single_family_sqft`). The same fee per unit is a bigger share of a smaller unit's cost, which is the density
point of office hours A5. 5+ unit buildings have no coded fees and take no dose (a stated limit). Without the
size split, the house's %Δ applies to every unit (D-032's interim rule).

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
MODES = ("handbook", "local_half", "local_25k", "local_rise")
ALIASES = {"local": "local_half"}  # the name before D-065
LABELS = {
    "handbook": "Benchmark: a $50,000 fee cut in half",
    "local_half": "Real local fees cut in half",
    "local_25k": "Real local fees cut by up to $25,000",
    "local_rise": "Sensitivity: real local fees raised by half",
}
# BPS size class -> fee building type (D-073). 5+ unit buildings have no coded fees and no dose: unchanged.
SIZE_TYPES = {"1": "SFD", "2": "U2", "3_4": "U3_4"}
SIZE_CLASSES = ("1", "2", "3_4", "5p")
TYPE_SQFT = {"SFD": "single_family_sqft", "U2": "plex_unit_sqft", "U3_4": "plex_unit_sqft"}


def _suffix(building_type: str) -> str:
    """Column suffix for a building type's local fee: '' for SFD (the original columns), else '_U2' etc."""
    return "" if building_type == "SFD" else f"_{building_type}"


def specs() -> dict:
    out = {}
    for name in PARAM_FILES:
        out.update(load_params(name))
    return out


def central_params() -> dict[str, float]:
    return {k: s.value for k, s in specs().items()}


# Drawn lognormal with median = value and 95th percentile = high (D-076): the elasticity's range (0 to 1.75,
# central 0.3) is so lopsided that a triangular draw has median 0.62 and mean 0.68, twice the central value.
LOGNORMAL = frozenset({"fee_permit_elasticity"})
Z_95 = 1.644854


def lognormal_draw(median: float, p95: float, n: int, rng: np.random.Generator) -> np.ndarray:
    """Lognormal with the given median and 95th percentile. By hand, median 0.3 and p95 1.75: log-SD =
    (ln 1.75 − ln 0.3) / 1.6449 = 1.7636 / 1.6449 = 1.0722, so the 5th percentile is 0.3 / 5.833 = 0.0514."""
    sd = (np.log(p95) - np.log(median)) / Z_95
    return median * np.exp(sd * rng.standard_normal(n))


def draw_params(n: int, seed: int) -> list[dict[str, float]]:
    """n parameter sets: each uncertain parameter triangular(low, central, high), except `LOGNORMAL` ones
    (median central, 95th percentile high); fixed ones held."""
    rng = np.random.default_rng(seed)
    cols = {}
    for k, s in specs().items():
        if k in FIXED or s.low == s.high:
            cols[k] = np.full(n, s.value)
        elif k in LOGNORMAL:
            cols[k] = lognormal_draw(s.value, s.high, n, rng)
        else:
            cols[k] = rng.triangular(s.low, s.value, s.high, n)
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


def _type_columns(places: pd.DataFrame, building_type: str) -> tuple[str, str]:
    """(column suffix, note) for a building type's local fee: its own columns, else the house's (D-073)."""
    s = _suffix(building_type)
    if f"local_fee_per_unit{s}" in places:
        return s, ""
    if building_type == "SFD":
        raise ValueError("local fee scenarios need local_fee_per_unit (fee_levels.place_fees)")
    return "", f" (house fee: no {building_type} level given)"


def fee_levels(
    places: pd.DataFrame, mode: str, params: Mapping[str, float], building_type: str = "SFD"
) -> tuple[np.ndarray, np.ndarray]:
    """Central fee per unit before the cut, and where it came from (`fee_source`, or 'handbook').

    `building_type` 'U2' or 'U3_4' reads `local_fee_per_unit_U2` etc. (`fee_levels.place_fees` for that
    type); without those columns it uses the house's fee and says so in the source."""
    mode = _mode(mode)
    n = len(places)
    if mode == "handbook":
        return np.full(n, float(params["handbook_fee_per_unit_usd"])), np.full(n, "handbook", dtype=object)
    s, note = _type_columns(places, building_type)
    level = places[f"local_fee_per_unit{s}"].to_numpy(dtype=float)
    if np.isnan(level).any():
        raise ValueError("a place has no local fee; the $50,000 is not a fallback (D-065)")
    source = places.get(f"fee_source{s}", pd.Series("local", index=places.index)).fillna("local")
    return level, (source.astype(str) + note).to_numpy(dtype=object)


def fee_draws(
    places: pd.DataFrame,
    mode: str,
    params: Mapping[str, float],
    n: int,
    seed: int,
    building_type: str = "SFD",
) -> np.ndarray:
    """(draws × places) fee per unit: the central value in the benchmark; triangular(low, central, high) in
    the local scenarios where a range is given (`local_fee_low`, `local_fee_high`, with the type's suffix),
    else the central value."""
    central, _ = fee_levels(places, mode, params, building_type)
    out = np.repeat(central[None, :], n, axis=0)
    if _mode(mode) == "handbook":
        return out
    s, _ = _type_columns(places, building_type)
    if f"local_fee_low{s}" not in places or f"local_fee_high{s}" not in places:
        return out
    low = places[f"local_fee_low{s}"].fillna(places[f"local_fee_per_unit{s}"]).to_numpy(dtype=float)
    high = places[f"local_fee_high{s}"].fillna(places[f"local_fee_per_unit{s}"]).to_numpy(dtype=float)
    low, high = np.minimum(low, central), np.maximum(high, central)
    rng = np.random.default_rng(seed)
    for i in np.flatnonzero(high > low):
        out[:, i] = rng.triangular(low[i], central[i], high[i], n)
    return out


def fee_cut(fee: np.ndarray, params: Mapping[str, float], mode: str = "handbook") -> np.ndarray:
    """Δ per unit: cut share × fee; in `local_25k`, the Handbook's dollar cut capped at the fee; in
    `local_rise`, a rise of `fee_rise_share` × fee, entered as a negative cut (D-073)."""
    fee = np.asarray(fee, dtype=float)
    share = params["handbook_fee_cut_share"]
    if _mode(mode) == "local_rise":
        return -params["fee_rise_share"] * fee
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


def type_pct_change(
    places: pd.DataFrame, fee: np.ndarray, params: Mapping[str, float], mode: str, building_type: str
) -> np.ndarray:
    """%Δ permits of one building type by elasticity (D-073): ε × saving per unit / cost per unit, where the
    cost per unit is the place's home value scaled to the type's unit size (`TYPE_SQFT`).

    By hand: ε 0.3, λ 0.5, duplex fee $10,000 cut in half -> saving $2,500; home value $430,000 for 2,150 sq
    ft -> $200 a sq ft, a 1,000 sq ft unit $200,000 -> 0.3 × 2,500 / 200,000 = 0.00375.
    """
    saving = builder_saving(fee, params, mode)
    scale = params[TYPE_SQFT[building_type]] / params["single_family_sqft"]
    tdc = places["home_value"].to_numpy(dtype=float) * scale
    return elasticity_change(saving, tdc, params)


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


def _by_size(places: pd.DataFrame, horizon: int) -> dict[str, np.ndarray] | None:
    """Baseline by BPS size class (`baseline_y<h>_<class>` for every year and class), or None (D-073)."""
    cols = {c: [f"baseline_y{t}_{c}" for t in range(1, horizon + 1)] for c in SIZE_CLASSES}
    if not all(all(k in places for k in v) for v in cols.values()):
        return None
    return {c: places[v].to_numpy(dtype=float) for c, v in cols.items()}


def _added(
    places: pd.DataFrame,
    fees: Mapping[str, np.ndarray],
    params: Mapping[str, float],
    mode: str,
    base: np.ndarray,
    by_size: dict[str, np.ndarray] | None,
):
    """Added units (places × years), per-class added units, house %Δ, its channel and per-type %Δ.

    Without a baseline by size, the house's %Δ applies to all units (the interim rule of D-032). With one
    (D-073): 1-unit buildings take the house's %Δ (feasibility or elasticity), 2-unit and 3-4 unit buildings
    their own type's elasticity %Δ, and 5+ unit buildings none.
    """
    pct, channel = pct_change(places, fees["SFD"], params, mode)
    if by_size is None:
        return added_units(base, pct, params), {}, pct, channel, {}
    parts = {"1": added_units(by_size["1"], pct, params)}
    pcts = {"1": pct}
    for cls in ("2", "3_4"):
        t = SIZE_TYPES[cls]
        pcts[cls] = type_pct_change(places, fees[t], params, mode, t)
        parts[cls] = added_units(by_size[cls], pcts[cls], params)
    return sum(parts.values()), parts, pct, channel, pcts


def _types(by_size) -> tuple[str, ...]:
    return ("SFD",) if by_size is None else ("SFD", "U2", "U3_4")


def central_path(places: pd.DataFrame, mode: str = "local_half", params: dict | None = None) -> dict:
    """Central values (hand checks): fee, saving, %Δ, channel and added units (places × years); with a
    baseline by size class, also each type's fee and %Δ and each class's added units."""
    p = central_params() | (params or {})
    _, horizon, _ = baseline_model.window(0)
    by_size = _by_size(places, horizon)
    base = _baseline(places, horizon) if by_size is None else sum(by_size.values())
    levels = {t: fee_levels(places, mode, p, t) for t in _types(by_size)}
    fees = {t: v[0] for t, v in levels.items()}
    added, parts, pct, channel, pcts = _added(places, fees, p, mode, base, by_size)
    fee, source = levels["SFD"]
    return {
        "fee": fee,
        "fee_source": source,
        "cut": fee_cut(fee, p, mode),
        "saving": builder_saving(fee, p, mode),
        "pct": pct,
        "channel": channel,
        "added": added,
        "fee_by_type": fees,
        "source_by_type": {t: v[1] for t, v in levels.items()},
        "pct_by_size": pcts,
        "added_by_size": parts,
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
    by_size = _by_size(places, horizon)
    base = _baseline(places, horizon) if by_size is None else sum(by_size.values())
    mode = _mode(mode)
    fee, source = fee_levels(places, mode, central)
    seed = int(central["fee_simulation_seed"])
    # the house fee keeps seed + 1 (results without a size split are unchanged); duplex + 2, fourplex + 3
    fees_d = {t: fee_draws(places, mode, central, n, seed + 1 + k, t) for k, t in enumerate(_types(by_size))}
    out = np.zeros((n, len(places), horizon))
    out_size = {c: np.zeros((n, len(places))) for c in (SIZE_TYPES if by_size is not None else ())}
    used = np.zeros((n, len(places)), dtype=bool)  # feasibility channel used in this draw
    for d, p in enumerate(sets):
        added, parts, _, channel, _ = _added(
            places, {t: v[d] for t, v in fees_d.items()}, p, mode, base, by_size
        )
        out[d] = added
        for c, a in parts.items():
            out_size[c][d] = a.sum(axis=1)
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
    if by_size is not None:
        for t in ("U2", "U3_4"):
            info[f"fee_per_unit_{t}"] = c["fee_by_type"][t]
            info[f"fee_source_{t}"] = c["source_by_type"][t]
        for cls in SIZE_CLASSES:
            info[f"baseline_five_year_{cls}"] = by_size[cls].sum(axis=1)
        for cls in SIZE_TYPES:
            info[f"pct_change_central_{cls}"] = c["pct_by_size"][cls]
    yearly = info.loc[info.index.repeat(horizon)].reset_index(drop=True)
    yearly["horizon"] = np.tile(np.arange(1, horizon + 1), len(places))
    yearly["year"] = first - 1 + yearly["horizon"]
    yearly["baseline_units_year"] = base.reshape(-1)
    totals = info.copy()
    for table, a in ((yearly, out.reshape(n, -1)), (totals, out.sum(axis=2))):
        table["units_added_mean"] = a.mean(axis=0)
        for q in (10, 50, 90):
            table[f"units_added_p{q}"] = np.percentile(a, q, axis=0)
    for cls, a in out_size.items():  # five-year units added in each size class
        totals[f"units_added_mean_{cls}"] = a.mean(axis=0)
        for q in (10, 50, 90):
            totals[f"units_added_p{q}_{cls}"] = np.percentile(a, q, axis=0)
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
