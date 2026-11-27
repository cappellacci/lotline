"""Legal lots from a state's tables: coded reforms, the states that feed shared pools, parcel coverage and the
rule inputs `places_from_store` reads. Part of `scenarios.adu`; the method is in that module's docstring.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.config import CONFIG_DIR, load_params
from lotline.model.scenarios.adu_rule_priors import (
    REMAINDER_BAND,
    apply_priors,
    no_state_rule_priors,
    rule_priors,
)
from lotline.model.scenarios.adu_rules import (
    P_COLS,
    current_rules,
    field_probabilities,
    field_restrict_counts,
    rule_coverage,
)


def load_reforms(state: str, config_dir: Path | None = None) -> pd.DataFrame:
    """The state's coded reforms (config/reforms/<st>.csv) with dates parsed.

    A state outside `REFORM_STATES` with no reforms file gets an empty table (no coded rules), so a new
    state runs on borrowed priors alone (WS-SCALE task 0). A listed state must have its file.
    """
    path = (config_dir or CONFIG_DIR) / "reforms" / f"{state.lower()}.csv"
    if not path.exists() and state.upper() not in REFORM_STATES:
        from lotline.schemas import Reforms

        df = pd.DataFrame({c: pd.Series(dtype=object) for c in Reforms.to_schema().columns})
    else:
        df = pd.read_csv(path, dtype={"jurisdiction_geoid": str})
    for col in ("announced_date", "adoption_date", "effective_date", "end_date"):
        if col in df:
            df[col] = pd.to_datetime(df[col])
    return df


# States whose coded rules feed field probabilities, rule priors and blank shares. Oregon joined on
# 2026-11-05 (D-053), after V9 was scored; V9 itself keeps the four states it was frozen from.
# A state not listed here borrows from these states but feeds nothing back ("borrow only", Ben 2026-11-17,
# WS-SCALE task 0): `reforms_with` adds it to the run on the fly, after the shared pools are built.
REFORM_STATES = ("MN", "NC", "OH", "TX", "OR")


def reforms_with(state: str, load=None) -> dict[str, pd.DataFrame]:
    """`{state: reforms}` for every state in `REFORM_STATES`, then `state` itself if it is not listed.

    Callers pool only the `REFORM_STATES` entries (`pooled_states`); the extra state's own rules still
    apply to its own places. `load` defaults to `load_reforms`.
    """
    load = load or load_reforms
    out = {st: load(st) for st in REFORM_STATES}
    st = state.upper()
    if st not in out:
        out[st] = load(st)
    return out


def pooled_states(reforms: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """The entries of `reforms` that feed shared pools (field probabilities, priors, blank shares)."""
    return {st: r for st, r in reforms.items() if st in REFORM_STATES}


_PARCEL_CACHE: dict[str, pd.DataFrame] = {}


def _sf_parcels(state: str, store) -> pd.DataFrame | None:
    """Single-family detached parcels of each jurisdiction's latest roll (zoning and lot size), cached. None
    for a state with no parcel table (Oregon on the ACS fallback): its zone-limited rules then take the
    judgment share, as `rule_coverage` does for any place without parcels (D-021)."""
    if state not in _PARCEL_CACHE:
        cols = ["jurisdiction_geoid", "vintage", "land_use_std", "lot_sqft", "zoning_raw"]
        p = store.read(state, "parcels")
        if p is None:
            return None
        p = p[[c for c in cols if c in p]]
        p = p[p["land_use_std"] == "SF_DETACHED"]
        latest = p.groupby("jurisdiction_geoid")["vintage"].transform("max")
        _PARCEL_CACHE[state] = p[p["vintage"] == latest]
    return _PARCEL_CACHE[state]


def coverage_map(state: str, store, reforms: pd.DataFrame, params: Mapping[str, float]) -> pd.DataFrame:
    """D-021: coverage share of every coded ADU rule in a state, measured on parcels where possible.

    Returns reform_id, geoid, coverage, how. Rules with no zone list or lot minimum need no parcels.
    """
    adu = reforms[reforms["theme"] == "adu"]
    needs = adu["coverage_zones"].notna() | (pd.to_numeric(adu["min_lot_sqft"], errors="coerce") > 0)
    parcels = _sf_parcels(state, store) if needs.any() else None
    rows = []
    for r in adu.itertuples():
        mine = parcels[parcels["jurisdiction_geoid"] == r.jurisdiction_geoid] if parcels is not None else None
        cov, how = rule_coverage(r._asdict(), mine, params)
        rows.append({"reform_id": r.reform_id, "geoid": r.jurisdiction_geoid, "coverage": cov, "how": how})
    return pd.DataFrame(rows, columns=["reform_id", "geoid", "coverage", "how"])


def rule_inputs(
    state: str, store, geoids, as_of: pd.Timestamp, prior_as_of: pd.Timestamp | None = None
) -> tuple[pd.DataFrame, dict]:
    """Rule-type probabilities for `geoids` in `state` (D-021, D-022), and the counts behind them.

    Field probabilities come from every state's coded rules in force (`field_restrict_counts`); coverage from
    each rule's zones and lot minimum on the place's parcels (`coverage_map`); priors for places with no ADU
    row from the coded places of every state, by state and size band (`rule_priors`). Reads
    config/reforms/*.csv at run time, so newly coded rules shrink the unknowns with no code change.

    Dates (D-067): each place's own rules are read on `as_of`; what a place borrows (field probabilities and
    the coded places behind the priors) on `prior_as_of` (default `as_of`). `info["coded"]` holds the coded
    places on `as_of` (their own rules, used by `county_mix`); `info["coded_prior"]` those behind the priors.

    D-068: in a state flagged `adu_state_law_rows_complete`, a place with no ADU row is outside the state law,
    so it takes `no_state_rule_priors` (coded places of the unflagged states, by size band).
    Returns (table: geoid, rule_class, p_* over TYPES, coverage, rule_age, …, prior_source; info dict).
    """
    from lotline.config import load_state

    prior_as_of = as_of if prior_as_of is None else prior_as_of
    p = load_params("adu")
    central = {k: v.value for k, v in p.items()}
    min_count = int(central["adu_rule_min_coded"])
    edges = (central["adu_rule_band_small_max_pop"], central["adu_rule_band_mid_max_pop"])
    reforms = {st: r.assign(state=st) for st, r in reforms_with(state).items()}
    pooled = pooled_states(reforms)
    counts = field_restrict_counts(pd.concat(pooled.values(), ignore_index=True), prior_as_of)
    covs = {st: coverage_map(st, store, r, central) for st, r in reforms.items()}

    def coded_on(date: pd.Timestamp) -> pd.DataFrame:
        out = []
        for st, r in pooled.items():
            local = sorted(g for g in r.loc[r["theme"] == "adu", "jurisdiction_geoid"].unique() if len(g) > 2)
            if not local:
                continue
            cm = covs[st]
            fp_st = field_probabilities(counts, st, min_count)
            cr = current_rules(
                r, local, load_state(st).fips, date, fp_st, dict(zip(cm.reform_id, cm.coverage, strict=True))
            )
            cr = cr[cr["rule_class"] != "unknown"]
            pop = store.read(st, "jurisdictions").set_index("geoid")["pop_2020"]
            j = store.read(st, "jurisdictions").set_index("geoid")
            kind = j["kind"] if "kind" in j else pd.Series(dtype=object)
            out.append(
                cr.assign(state=st, population=cr["geoid"].map(pop).astype(float), kind=cr["geoid"].map(kind))
            )
        return pd.concat(out, ignore_index=True)

    coded_prior = coded_on(prior_as_of)
    coded = coded_prior if prior_as_of == as_of else coded_on(as_of)
    priors = rule_priors(coded_prior.dropna(subset=["population"]), edges, min_count)
    law_states = {st for st in REFORM_STATES if load_state(st).adu_state_law_rows_complete}
    if state in law_states:  # D-068: an uncoded place is outside the state law
        outside = no_state_rule_priors(
            coded_prior.dropna(subset=["population"]), edges, min_count, law_states, state
        )
        keep = (priors["state"] != state) | (
            priors["band"] == REMAINDER_BAND
        )  # (b): own remainders still apply
        priors = pd.concat([priors[keep], outside], ignore_index=True)
    elif not ((priors["state"] == state) & (priors["band"] != REMAINDER_BAND)).any():
        # A state outside REFORM_STATES (e.g. Wisconsin): borrow from every coded place by size band, not
        # the all-bands mean `apply_priors` falls back to.
        every = no_state_rule_priors(coded_prior.dropna(subset=["population"]), edges, min_count, (), state)
        every["source"] = every["source"].str.replace("states without a coded state ADU law", "all states")
        priors = pd.concat([priors, every], ignore_index=True)
    fp = field_probabilities(counts, state, min_count)
    cm = covs[state]
    rules = current_rules(
        reforms[state],
        geoids,
        load_state(state).fips,
        as_of,
        fp,
        dict(zip(cm.reform_id, cm.coverage, strict=True)),
    )
    juris = store.read(state, "jurisdictions").set_index("geoid")
    rules = rules.assign(
        state=state, population=rules["geoid"].map(juris["pop_2020"]).astype(float),
        kind=rules["geoid"].map(juris["kind"] if "kind" in juris else pd.Series(dtype=object)),
    )  # fmt: skip
    rules = apply_priors(rules, priors, edges).drop(columns=["state", "band", "kind"])
    info = {
        "field_counts": counts,
        "field_probs": fp,
        "priors": priors,
        "coded": coded,
        "coded_prior": coded_prior,
        "coverage": covs,
    }
    return rules, info


def county_mix(places: pd.DataFrame, state: str, store, origin: int, coded: pd.DataFrame) -> pd.DataFrame:
    """D-021: blend the rules of coded places that BPS files under a county row (no jurisdiction of their own,
    e.g. Wilmington) into that row, weighted by their share of the row's eligible parcels.

    Share = the place's ACS one-unit detached homes in the county (newest vintage <= origin; Census county
    shares for places spanning counties) / the row's eligible parcels, capped at 1. Row p_* becomes
    (1 − w)·p_row + w·p_place. The mean c is right; a draw still picks one type for the whole row.
    """
    from lotline.adapters.national import geoparts
    from lotline.config import load_state

    juris = set(store.read(state, "jurisdictions")["geoid"])
    orphans = coded[(coded["state"] == state) & ~coded["geoid"].isin(juris) & (coded["geoid"].str.len() == 7)]
    if orphans.empty:
        return places
    shares = geoparts.county_shares(load_state(state).fips, sorted(orphans["geoid"]), store)
    acs = store.read(state, "acs_geo_year")
    acs = acs[(acs["variable"] == "B25024_002") & (acs["end_year"] <= origin) & acs["estimate"].notna()]
    homes = acs.sort_values("end_year").groupby("geo")["estimate"].last()
    out = places.copy()
    rows = out.index[out["kind"] == "county_unincorporated"]
    for o in orphans.itertuples():
        h = float(homes.get(f"place:{o.geoid}", np.nan))
        for sh in shares[shares["place_geoid"] == o.geoid].itertuples():
            target = [i for i in rows if out.at[i, "county_geoid"] == sh.county_geoid]
            if not target or np.isnan(h):
                continue
            i = target[0]
            w = min(1.0, h * sh.share / max(float(out.at[i, "eligible_parcels"]), 1.0))
            for col in P_COLS:
                out.at[i, col] = (1 - w) * out.at[i, col] + w * getattr(o, col)
            out.at[i, "rule_note"] = f"{out.at[i, 'rule_note']}; mixes {o.geoid}'s rule on {w:.0%} of lots"
    out["p_partial"] = out[["p_owner", "p_other", "p_both"]].sum(axis=1)
    return out
