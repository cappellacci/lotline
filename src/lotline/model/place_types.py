"""Place types from national data only: core city, suburb, town (ADU D-088's rule; missing middle D-092
deviation 2026-11-15 (c)).

**Rule** (`assign_types`): in each metropolitan area (OMB 2023, `jurisdictions` `cbsa_code` / `cbsa_type`),
the Census place with the most housing units is a core city, and so is any place in that metro with at least
a third of the largest's units (a twin core, such as Minneapolis-St. Paul). Every other place in a metro is a
suburb. Places in a micropolitan area or in none are towns. Townships and unincorporated county areas are
never core cities: a suburb in a metro, else a town (`raw_types`).

**Size measure** (`units_table`): ACS B25024_001 (all housing units), the latest vintage ending in 2015 or
earlier that `holdout.apply_acs` lets through, else the latest it lets through, else the place's largest
eligible-lot count for the theme (flagged in `units_source`). Unincorporated county areas take the county
total less its places. The type reads no outcome, so a held-out place can be typed; it still stays out of
every fit and score.

**Minimum size** (`merge_small`): a type needs at least 8 fit places in at least 3 states; a type short of
that is merged into suburb, town first, then core city.

The ADU stack (PR #432, `adu_types.assign_types`) has the same rule; once both are on main, one copy goes.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from lotline.validation import holdout

TYPES = ("core", "suburb", "town")
REFERENCE = "suburb"
TERMS = ("core", "town")  # the non-reference types, in this order everywhere
CORE_SHARE = 1.0 / 3.0
UNITS_END = 2015  # ACS 2011-15
MIN_PLACES, MIN_STATES = 8, 3


def assign_types(juris: pd.DataFrame, core_share: float = CORE_SHARE) -> pd.Series:
    """Type per geoid for Census places. `juris` has geoid, cbsa_code, cbsa_type ('metro', 'micro' or missing)
    and units (missing counts as 0 for the ranking).

    By hand: metro M with A 300, B 120, C 90 units; micro m with D 50; E with no area ->
    A core (largest), B core (120 >= 300 / 3), C suburb (90 < 100), D town, E town."""
    j = juris.copy()
    j["units"] = pd.to_numeric(j["units"], errors="coerce").fillna(0.0)
    out = pd.Series("town", index=j["geoid"].astype(str).to_numpy(), dtype=object)
    for _, m in j[j["cbsa_type"] == "metro"].groupby("cbsa_code"):
        top = float(m["units"].max())
        for g, u in zip(m["geoid"].astype(str), m["units"], strict=True):
            out[g] = "core" if top > 0 and u >= core_share * top else "suburb"
    return out


def merge_small(
    fit_types: pd.DataFrame, min_places: int = MIN_PLACES, min_states: int = MIN_STATES
) -> tuple[dict[str, str], list[str]]:
    """The minimum size rule over the fit places (`fit_types`: state, type).
    Returns ({type: merged type}, notes).

    By hand: core 10 places in 3 states, suburb 30 in 4, town 5 in 2 -> town merged into suburb, core kept."""
    mapping = {t: t for t in TYPES}
    notes = []

    def ok(t: str) -> bool:
        rows = fit_types[fit_types["type"].map(mapping) == t]
        return len(rows) >= min_places and rows["state"].nunique() >= min_states

    for t in ("town", "core"):
        if not ok(t):
            for k, v in mapping.items():
                if v == t:
                    mapping[k] = REFERENCE
            notes.append(
                f"{t} has fewer than {min_places} fit places in {min_states} states: merged into suburb"
            )
    return mapping, notes


def indicators(type_: str, terms: Sequence[str] = TERMS) -> np.ndarray:
    """d for one place. By hand: 'core' -> (1, 0); 'suburb' -> (0, 0); 'town' -> (0, 1)."""
    return np.array([1.0 if type_ == t else 0.0 for t in terms])


def pick_units(ser: pd.Series | None, end: int = UNITS_END) -> tuple[float, int | None, str]:
    """(units, vintage, source) from one place's units by ACS end year.

    By hand: {2013: 90, 2015: 100, 2017: 120} -> (100, 2015, 'acs 2011-15'); {2014: 80} -> (80, 2014, 'acs
    early'); {2018: 70} -> (70, 2018, 'acs latest let through'); None -> (nan, None, 'none')."""
    if ser is None or not len(ser):
        return float("nan"), None, "none"
    early = ser[ser.index <= end]
    if len(early):
        v = int(early.index.max())
        return float(early.loc[v]), v, "acs 2011-15" if v == end else "acs early"
    v = int(ser.index.max())
    return float(ser.loc[v]), v, "acs latest let through"


def units_table(store, st: str, theme: str = "missing_middle") -> pd.DataFrame:
    """Housing units per jurisdiction of state `st` (lower case), with its OMB area (module docstring)."""
    a = holdout.apply_acs(store.read(st, "acs_geo_year"), st)
    a = a[(a["table_id"] == "B25024") & (a["variable"].astype(str) == "B25024_001")]
    by = a.groupby(["geo", "end_year"])["estimate"].sum()
    geos = set(by.index.get_level_values("geo"))
    juris = store.read(st, "jurisdictions")
    juris = juris.assign(geoid=juris["geoid"].astype(str))
    elig = store.read(st, "eligible_parcels")
    elig = elig[elig["theme"] == theme].groupby("jurisdiction_geoid")["eligible_parcels"].max()
    elig.index = elig.index.astype(str)
    prefix = {"place": "place", "township": "cousub"}
    rows = []
    for r in juris.itertuples():
        ser = None
        if r.kind == "county_unincorporated":
            cg = f"county:{r.county_geoid}"
            if cg in geos:
                ser = by.xs(cg, level="geo")
                inside = juris[
                    (juris["county_geoid"].astype(str) == str(r.county_geoid)) & (juris["kind"] == "place")
                ]
                for g in inside["geoid"]:
                    if f"place:{g}" in geos:
                        ser = ser.sub(by.xs(f"place:{g}", level="geo").reindex(ser.index).fillna(0.0))
        elif r.kind in prefix and f"{prefix[r.kind]}:{r.geoid}" in geos:
            ser = by.xs(f"{prefix[r.kind]}:{r.geoid}", level="geo")
        units, vintage, source = pick_units(ser)
        if not np.isfinite(units) and r.geoid in elig.index:
            units, source = float(elig.loc[r.geoid]), "eligible lots (flag)"
        rows.append({"state": st.upper(), "geoid": r.geoid, "name": r.name, "kind": r.kind,
                     "cbsa_code": r.cbsa_code, "cbsa_type": r.cbsa_type, "units": units,
                     "units_vintage": vintage, "units_source": source})  # fmt: skip
    return pd.DataFrame(rows)


def raw_types(u: pd.DataFrame) -> pd.Series:
    """Raw type for every row of a units table: places by `assign_types`; townships and unincorporated areas
    suburb in a metro, else town.

    By hand: place A (metro M, 300), township T (metro M, 900), area U (no area) -> A core, T suburb, U town
    (T outranks A on units but is not a place, so it neither is nor sets the core)."""
    t = pd.Series(index=u["geoid"].astype(str).to_numpy(), dtype=object)
    places = u[u["kind"] == "place"]
    t.loc[places["geoid"].astype(str).to_numpy()] = assign_types(places).to_numpy()
    other = u["kind"] != "place"
    t.loc[u.loc[other, "geoid"].astype(str).to_numpy()] = np.where(
        u.loc[other, "cbsa_type"] == "metro", "suburb", "town"
    )
    return t


def type_table(store, states: Sequence[str], theme: str = "missing_middle") -> pd.DataFrame:
    """Every jurisdiction's units, area and raw type, for `states` (upper or lower case)."""
    out = []
    for st in states:
        u = units_table(store, st.lower(), theme)
        u["type_raw"] = raw_types(u).to_numpy()
        out.append(u)
    return pd.concat(out, ignore_index=True)
