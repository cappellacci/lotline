"""Local development fee per new unit, by place and building type (D-034 as replaced by D-065; D-066; #247).

Input: the hand-coded `fees` table (config/fees/<st>.csv, `lotline.config.load_fees`). Output: one fee per
unit for a place and building type, with a low-central-high range and a label saying what was coded and what
was filled.

**1. Which rows count** (`coded_fees`), for building type T and one place, fee component by component:

- T = SFD: the SFD and OTHER rows (OTHER rows apply to any building type and are priced at the single-family
  prototype; config/fees/README.md).
- T = U2, U3_4 or ADU: the T rows if the component has any; else its OTHER rows; else the place's own SFD
  amount for that component (`from SFD`), on the reading that a fee coded for houses applies per unit to the
  other types unless the schedule says otherwise.
- Only rows with a per-unit amount. Within a component, the newest year with such a row counts, plus older
  rows whose `in_force_through` reaches that year (#247: a separate agency's schedule, or an impact-fee
  ordinance still in force next to newer meter charges).

**2. Real dollars.** Each row is converted from its `dollar_year` to 2025 dollars with CPI-U
(`money.deflate`; protocol §5.9). A schedule year newer than the index's last year is taken at the last year
(2026 schedules against a 2025 index: no adjustment, a small overstatement). Without an index the amounts stay
nominal and `fee_dollars` says so.

**3. Range.** A row's low and high are `amount_per_unit_low_usd` and `amount_per_unit_high_usd` (fees that
vary by area, basin, tier or plat date), else its central amount. A place's low, central and high are the
sums of its rows' lows, centrals and highs.

**4. Filling what is missing** (`place_fees`, D-065). Every new home pays for a building permit and a utility
connection, so a place missing `water_sewer` or `permit` for T gets that component from a prior. Missing
`impact`, `planning` and `other` count as zero: many places charge none, so filling them would invent fees.
A place with no coded rows at all gets the prior for the whole fee. The prior is, in order:

  the state's coded places for T  ->  every coded place for T  ->  the same two for SFD,

the first with at least `min_places` places (5, as D-022's minimum for priors). Its central value is the
median over those places and its low and high the 25th and 75th percentiles, so a filled fee carries the
spread of the places it came from. The Handbook's $50,000 is never a fallback here; it is the benchmark only.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from lotline.model import money

TYPES = ("SFD", "U2", "U3_4", "ADU")
FILLED = ("water_sewer", "permit")  # every new home pays these; other components missing count as zero
MIN_PLACES = 5  # places needed for a state prior (D-022's minimum)
OUT = [
    "state",
    "geoid",
    "building_type",
    "local_fee_per_unit",
    "local_fee_low",
    "local_fee_high",
    "fee_components",
    "fee_years",
    "fee_dollars",
]


def _rows(fees: pd.DataFrame, index: pd.Series | None, to_year: int | None) -> pd.DataFrame:
    """Rows with a per-unit amount, in real dollars, with low/high filled from the central value."""
    f = fees[fees["amount_per_unit_usd"].notna()].copy()
    if "state" not in f:
        f["state"] = ""
    f["geoid"] = f["jurisdiction_geoid"].astype(str)
    f["year"] = f["year"].astype(int)
    f["through"] = (
        f["in_force_through"].astype("Float64").fillna(f["year"]).astype(int)
        if "in_force_through" in f
        else f["year"]
    )
    mid = f["amount_per_unit_usd"].astype(float)
    low = f["amount_per_unit_low_usd"].astype(float).fillna(mid) if "amount_per_unit_low_usd" in f else mid
    high = f["amount_per_unit_high_usd"].astype(float).fillna(mid) if "amount_per_unit_high_usd" in f else mid
    if index is None:
        factor = pd.Series(1.0, index=f.index)
    else:
        if to_year is None:
            to_year = money.base_year()
        years = f["dollar_year"].astype(int).clip(upper=int(index.index.max()))
        factor = money.deflate(1.0, years, index, to_year).astype(float)
        if factor.isna().any():
            raise ValueError(f"no price index for dollar years {sorted(years[factor.isna()].unique())}")
    f["mid"], f["low"], f["high"] = mid * factor, low * factor, high * factor
    return f


def _newest(f: pd.DataFrame) -> pd.DataFrame:
    """Per place and component: rows of the newest year, plus older rows in force through that year."""
    newest = f.groupby(["geoid", "fee_component"])["year"].transform("max")
    return f[(f["year"] == newest) | (f["through"] >= newest)]


def _components(f: pd.DataFrame, building_type: str) -> pd.DataFrame:
    """Per place and component: central, low, high and year for one building type (docstring rule 1)."""
    if building_type == "SFD":
        rows = _newest(f[f["building_type_std"].isin(["SFD", "OTHER"])]).assign(how="")
    else:
        own = _newest(f[f["building_type_std"] == building_type]).assign(how="")
        other = _newest(f[f["building_type_std"] == "OTHER"]).assign(how="")
        have = set(zip(own["geoid"], own["fee_component"], strict=True))
        other = other[[k not in have for k in zip(other["geoid"], other["fee_component"], strict=True)]]
        rows = pd.concat([own, other])
    agg = rows.groupby(["state", "geoid", "fee_component"]).agg(
        mid=("mid", "sum"),
        low=("low", "sum"),
        high=("high", "sum"),
        year=("year", "max"),
        how=("how", "first"),
    )
    if building_type != "SFD":
        sfd = _components(f, "SFD")
        missing = sfd.index.difference(agg.index)
        agg = pd.concat([agg, sfd.loc[missing].assign(how="from SFD")]).sort_index()
    return agg


def _summarize(comp: pd.DataFrame, building_type: str, dollars: str) -> pd.DataFrame:
    rows = []
    for (state, geoid), g in comp.groupby(level=["state", "geoid"]):
        names = g.index.get_level_values("fee_component")
        rows.append(
            {
                "state": state,
                "geoid": geoid,
                "building_type": building_type,
                "local_fee_per_unit": float(g["mid"].sum()),
                "local_fee_low": float(g["low"].sum()),
                "local_fee_high": float(g["high"].sum()),
                "fee_components": ",".join(sorted(names)),
                "fee_years": ",".join(
                    f"{c}:{int(y)}" + (f" ({h})" if h else "")
                    for c, y, h in zip(names, g["year"], g["how"], strict=True)
                ),
                "fee_dollars": dollars,
            }
        )
    return pd.DataFrame(rows, columns=OUT)


def coded_fees(
    fees: pd.DataFrame,
    building_type: str = "SFD",
    index: pd.Series | None = None,
    to_year: int | None = None,
) -> pd.DataFrame:
    """What each coded place charges per unit of `building_type`, before any fill (rules 1-3)."""
    if building_type not in TYPES:
        raise ValueError(f"building_type must be one of {TYPES}, not {building_type!r}")
    f = _rows(fees, index, to_year)
    if f.empty:
        return pd.DataFrame(columns=OUT)
    dollars = "nominal" if index is None else f"{to_year or money.base_year()} dollars"
    return _summarize(_components(f, building_type), building_type, dollars)


def _prior(values: pd.DataFrame, state: str, min_places: int) -> tuple[float, float, float, str] | None:
    """(central, low, high, label) from per-place values (columns state, value): state first, then pooled."""
    for scope, v in (("state", values[values["state"] == state]), ("pooled", values)):
        if len(v) >= min_places:
            q = np.percentile(v["value"].to_numpy(dtype=float), [50, 25, 75])
            return float(q[0]), float(q[1]), float(q[2]), f"{scope} median"
    return None


def place_fees(
    places: pd.DataFrame,
    fees: pd.DataFrame,
    building_type: str = "SFD",
    index: pd.Series | None = None,
    to_year: int | None = None,
    min_places: int = MIN_PLACES,
) -> pd.DataFrame:
    """Fee per unit for every place in `places` (columns geoid, state), coded or not (rule 4).

    Adds `fee_source`: 'local' (all from coded rows), 'local + filled: <components> (<prior>)', or
    '<state|pooled> median' (nothing coded). `fees` should hold every coded state, so pooled priors work.
    """
    if building_type not in TYPES:
        raise ValueError(f"building_type must be one of {TYPES}, not {building_type!r}")
    f = _rows(fees, index, to_year)
    dollars = "nominal" if index is None else f"{to_year or money.base_year()} dollars"
    types = (building_type,) if building_type == "SFD" else (building_type, "SFD")
    comps = {t: _components(f, t) if not f.empty else None for t in types}

    def prior_component(state: str, component: str):
        for t in types:
            c = comps[t]
            if c is None:
                continue
            v = c.xs(component, level="fee_component")["mid"].rename("value").reset_index()
            got = _prior(v, state, min_places)
            if got:
                return got[:3] + (f"{got[3]}{'' if t == building_type else ', SFD'}",)
        return None

    def prior_total(state: str):
        for t in types:
            c = comps[t]
            if c is None:
                continue
            v = c.groupby(level=["state", "geoid"])["mid"].sum().rename("value").reset_index()
            got = _prior(v, state, min_places)
            if got:
                return got[:3] + (f"{got[3]}{'' if t == building_type else ', SFD'}",)
        return None

    own = comps[building_type]
    rows = []
    for _, place in places[["geoid", "state"]].drop_duplicates().iterrows():
        geoid, state = str(place["geoid"]), place["state"]
        has = own is not None and geoid in own.index.get_level_values("geoid")
        if not has:
            got = prior_total(state)
            mid, low, high, label = got if got else (np.nan, np.nan, np.nan, "no prior")
            rows.append(
                {
                    "state": state,
                    "geoid": geoid,
                    "building_type": building_type,
                    "local_fee_per_unit": mid,
                    "local_fee_low": low,
                    "local_fee_high": high,
                    "fee_components": "",
                    "fee_years": "",
                    "fee_dollars": dollars,
                    "fee_source": label,
                }
            )
            continue
        g = own.xs(geoid, level="geoid").droplevel("state")
        mid, low, high = float(g["mid"].sum()), float(g["low"].sum()), float(g["high"].sum())
        filled, labels = [], set()
        for component in FILLED:
            if component in g.index:
                continue
            got = prior_component(state, component)
            if got is None:
                continue
            mid, low, high = mid + got[0], low + got[1], high + got[2]
            filled.append(component)
            labels.add(got[3])
        years = ",".join(
            f"{c}:{int(y)}" + (f" ({h})" if h else "")
            for c, y, h in zip(g.index, g["year"], g["how"], strict=True)
        )
        rows.append(
            {
                "state": state,
                "geoid": geoid,
                "building_type": building_type,
                "local_fee_per_unit": mid,
                "local_fee_low": low,
                "local_fee_high": high,
                "fee_components": ",".join(sorted(g.index)),
                "fee_years": years,
                "fee_dollars": dollars,
                "fee_source": (
                    f"local + filled: {', '.join(filled)} ({'; '.join(sorted(labels))})"
                    if filled
                    else "local"
                ),
            }
        )
    return pd.DataFrame(rows, columns=[*OUT, "fee_source"])


def all_types(places: pd.DataFrame, fees: pd.DataFrame, types: Sequence[str] = TYPES, **kw) -> pd.DataFrame:
    """`place_fees` for several building types, stacked (one row per place and type)."""
    return pd.concat([place_fees(places, fees, t, **kw) for t in types], ignore_index=True)
