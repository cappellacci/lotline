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

    A state outside `REFORM_STATES` reads what it borrows (field counts and priors) from the saved tables of
    calibration step `adu_rule_priors` (`saved_priors`), so its results never depend on which other states'
    tables are in the data folder; only its own reforms and parcels are read.
    Returns (table: geoid, rule_class, p_* over TYPES, coverage, rule_age, …, prior_source; info dict).
    """
    from lotline.config import load_state

    prior_as_of = as_of if prior_as_of is None else prior_as_of
    p = load_params("adu")
    central = {k: v.value for k, v in p.items()}
    min_count, edges = _counts_and_edges(central)
    reforms = {st: r.assign(state=st) for st, r in reforms_with(state).items()}
    if state not in REFORM_STATES:  # borrow only: the saved pools, never the other states' tables
        counts, priors = saved_priors(state, prior_as_of)
        covs = {state: coverage_map(state, store, reforms[state], central)}
        coded = coded_prior = pd.DataFrame(columns=["state", "geoid", "rule_class", *P_COLS])
    else:
        counts, covs, coded_on = _pools(store, reforms, prior_as_of, central)
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
            priors = pd.concat([priors, _every(coded_prior, edges, min_count, state)], ignore_index=True)
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


def _counts_and_edges(central: Mapping[str, float]) -> tuple[int, tuple[float, float]]:
    return int(central["adu_rule_min_coded"]), (
        central["adu_rule_band_small_max_pop"],
        central["adu_rule_band_mid_max_pop"],
    )


def _pools(store, reforms: Mapping[str, pd.DataFrame], prior_as_of: pd.Timestamp, central):
    """What the `REFORM_STATES` contribute: field-restriction counts on `prior_as_of`, every state's rule
    coverage (D-021, on its parcels), and `coded_on(date)`, the coded places of the pooled states on a date
    with their population and kind. Reads every pooled state's reforms, parcels and jurisdictions."""
    from lotline.config import load_state

    min_count, _ = _counts_and_edges(central)
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

    return counts, covs, coded_on


def _every(coded_prior: pd.DataFrame, edges, min_count: int, state: str) -> pd.DataFrame:
    """A state outside `REFORM_STATES` (e.g. Wisconsin) borrows from every coded place by size band, not the
    all-bands mean `apply_priors` falls back to."""
    every = no_state_rule_priors(coded_prior.dropna(subset=["population"]), edges, min_count, (), state)
    every["source"] = every["source"].str.replace("states without a coded state ADU law", "all states")
    return every


# ---------------------------------------------------------------------------------------------------------
# Saved pools for borrowing states (calibration step `adu_rule_priors`, Ben 2026-11-27)
# ---------------------------------------------------------------------------------------------------------

PRIORS_FILE = "adu_rule_priors.csv"  # config/params/: rule_priors rows, plus the borrowed rows as state "*"
COUNTS_FILE = "adu_field_counts.csv"  # config/params/: field_restrict_counts of the pooled states
PRIOR_YEARS = range(2016, 2026)  # origins saved (Ben 2026-11-27): priors as of 31 December of each
BORROWER = "*"
PRIORS_DIR = CONFIG_DIR / "params"


def borrowed_pools(store, years=PRIOR_YEARS) -> dict[str, str]:
    """The two saved tables as CSV text, one block per origin year: what a state outside `REFORM_STATES`
    borrows (`saved_priors`). Computed from the pooled states' reforms, parcels and jurisdictions, exactly as
    `rule_inputs` pools them for a listed state."""
    central = {k: v.value for k, v in load_params("adu").items()}
    min_count, edges = _counts_and_edges(central)
    reforms = {st: r.assign(state=st) for st, r in reforms_with(REFORM_STATES[0]).items()}
    priors, counts = [], []
    for year in years:
        date = pd.Timestamp(f"{year}-12-31")
        c, _, coded_on = _pools(store, reforms, date, central)
        coded = coded_on(date)
        pr = pd.concat(
            [
                rule_priors(coded.dropna(subset=["population"]), edges, min_count),
                _every(coded, edges, min_count, BORROWER),
            ],
            ignore_index=True,
        )
        priors.append(pr.assign(origin=year))
        counts.append(c.assign(origin=year))
    first = lambda df: df[["origin", *[k for k in df if k != "origin"]]]  # noqa: E731
    return {
        PRIORS_FILE: first(pd.concat(priors, ignore_index=True)).to_csv(index=False),
        COUNTS_FILE: first(pd.concat(counts, ignore_index=True)).to_csv(index=False),
    }


def saved_priors(state: str, prior_as_of: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(field counts, priors) for a state outside `REFORM_STATES`, from the saved tables for the origin whose
    31 December is `prior_as_of`. The borrowed rows (state "*") are labelled `state`. No other state's data
    is read; an origin not saved is an error (rerun `lotline calibrate --run --step adu_rule_priors`)."""
    year = pd.Timestamp(prior_as_of).year
    if pd.Timestamp(prior_as_of) != pd.Timestamp(f"{year}-12-31"):
        raise ValueError(f"saved ADU priors are as of 31 December; got {prior_as_of:%Y-%m-%d}")
    priors = pd.read_csv(PRIORS_DIR / PRIORS_FILE, dtype={"state": str})
    counts = pd.read_csv(PRIORS_DIR / COUNTS_FILE, dtype={"state": str, "field": str})
    priors, counts = priors[priors["origin"] == year], counts[counts["origin"] == year]
    if priors.empty or counts.empty:
        raise KeyError(
            f"no saved ADU rule priors for origin {year} in config/params/{PRIORS_FILE}; add the year to "
            "PRIOR_YEARS and run `lotline calibrate --run --write --step adu_rule_priors`"
        )
    priors = priors.drop(columns="origin").reset_index(drop=True)
    priors.loc[priors["state"] == BORROWER, "state"] = state
    return counts.drop(columns="origin").reset_index(drop=True), priors


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
