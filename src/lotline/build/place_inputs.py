"""`place_inputs`: one table of every shared per-place input, for all three models and the baseline
(WS-SCALE task 4, contract-change #455).

**Key** (state, geoid, year). One row per jurisdiction in the state's `jurisdictions` table and per origin
year. A row for year Y holds the inputs a run with origin Y reads: the parcel roll nearest Y, the newest ACS
vintage ending by Y, the observed ADU window ending at Y, and BPS permits issued in Y.

**Behaviour-preserving.** Every column is filled by the function the models use today, called here once
instead of in each model, so the table reproduces today's inputs exactly, including where the models disagree
(WS-SCALE § Audit A: ADU drops a place with no ACS rent; MM keeps it; parcel vintages differ by model). Those
disagreements are task 5, each Ben's call. `tests/build/test_place_inputs.py` checks the table against
`adu.places_from_store` and `mm.places_from_store` on a synthetic state.

**Not in it:** anything model-specific or parameter-dependent (ADU rule probabilities and priors, the MM
dose, fee levels, lot-value arrays, baseline forecasts).

**Missing values:** a column is null where its source has nothing for the place; it is never filled here.
Each model keeps its own fill rule until task 5 makes them one (`models` / `models_note` say which model
reads the row).
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from lotline.config import load_params

SOURCE = "place_inputs"
TABLE = "place_inputs"
RUN_LAST = True  # `lotline fetch` with no --source builds it after every other source
# what the table is built from (all already in the manifest under their own sources)
MANIFEST_SOURCES = ["census_acs5", "census_bps_place_annual", "census_dec_pl", "census_geo_codes"]
PROVENANCE = {
    "title": "Lotline place inputs (derived): every shared per-place input, built from the canonical tables",
    "landing_url": "https://github.com/cappellacci/lotline/blob/main/src/lotline/build/place_inputs.py",
    "table": "place_inputs",
    "cleaning": [
        "Built after every other table, from jurisdictions, eligible_parcels, bps_place_year, acs_geo_year, "
        "market_geo_year, parcels and permits (holdout-filtered)",
        "Each column filled by the function the models use; no fills",
    ],
    "limitations": ["Reproduces today's model inputs, including where the models disagree (WS-SCALE task 5)"],
}

KEY = ["state", "geoid", "year"]
UNITS = ["units_1", "units_2", "units_3_4", "units_5p"]
THEMES = {"adu": "adu", "mm": "missing_middle"}
PLACE_COLS = ["name", "kind", "county_geoid", "in_bps", "pop_2020", "data_tier", "cbsa_code", "cbsa_type"]


def nearest_roll(elig: pd.DataFrame, theme: str, origin: int) -> pd.DataFrame:
    """Per jurisdiction, the eligible-parcel row from the newest roll <= origin, else the earliest later one
    (flagged `parcels_after_origin`): the rule ADU and MM both use (`adu.places_from_store`, `mm._nearest`).
    Returns geoid, eligible_parcels, parcels_year, parcels_after_origin, denominator_source,
    denominator_quality, data_tier."""
    from lotline.build import eligible as eligible_rule

    e = elig[(elig["theme"] == theme) & (elig["rule_version"] == eligible_rule.RULE_VERSION)]
    e = e.assign(after=e["year"] > origin, gap=(e["year"] - origin).abs())
    e = e.sort_values(["after", "gap"]).groupby("jurisdiction_geoid").first().reset_index()
    return e.rename(
        columns={"jurisdiction_geoid": "geoid", "year": "parcels_year", "after": "parcels_after_origin"}
    ).drop(columns=["gap", "state", "theme", "rule_version"], errors="ignore")


def _eligible(state, store, elig, juris, theme, origin, shares) -> pd.DataFrame:
    """Eligible parcels of one theme at `origin`, net of the D-020 overlap (`adu.non_overlapping`), for the
    places with any; as the models compute them."""
    from lotline.model.scenarios import adu

    e = nearest_roll(elig, theme, origin)
    places = e.merge(juris[["geoid", "kind", "county_geoid", "in_bps"]], on="geoid", how="left")
    places = places[places["eligible_parcels"].fillna(0) > 0].reset_index(drop=True)
    places = adu.non_overlapping(places, juris, shares)
    keep = [
        "geoid",
        "eligible_parcels",
        "eligible_parcels_reported",
        "overlap_removed",
        "parcels_year",
        "parcels_after_origin",
        "denominator_source",
        "denominator_quality",
    ]
    return places[[c for c in keep if c in places]]


def build(state: str, store, years: Iterable[int] | None = None) -> pd.DataFrame:
    """`place_inputs` for one state: every jurisdiction x every year in `years` (default: the BPS years)."""
    from lotline.build import panels
    from lotline.config import load_state
    from lotline.model import money
    from lotline.model.scenarios import adu, fees, mm

    st = state.upper()
    juris = store.read(st, "jurisdictions")
    elig = store.read(st, "eligible_parcels")
    bps = store.read(st, "bps_place_year")
    market = store.read(st, "market_geo_year")
    acs = store.read(st, "acs_geo_year")
    parcels = store.read(st, "parcels")
    permits = store.read(st, "permits")
    if years is None:
        years = sorted(int(y) for y in bps["year"].unique()) if bps is not None else []
    years = list(years)

    pa = {k: v.value for k, v in load_params("adu").items()}
    edges = (pa["adu_rule_band_small_max_pop"], pa["adu_rule_band_mid_max_pop"])
    n_obs = int(pa["adu_observed_years"])
    stops = adu.holdout_stops(load_state(st).holdouts)
    cpi = money.index_by_year(market, "cpi_u")
    fee_params = fees.central_params()

    base = juris[["geoid", *[c for c in PLACE_COLS if c in juris]]].copy()
    base["acs_geo"] = base["kind"].map(adu.ACS_PREFIX) + ":" + base["geoid"]
    pop = pd.to_numeric(base["pop_2020"], errors="coerce").fillna(0)
    base["size_band"] = adu.size_band(pop, edges)  # county remainders: no pop_2020 -> band 0 (as MM today)
    house = mm.house_shares(st, store)
    base["house_share"] = base["geoid"].map(house)  # latest roll, no origin cap (as MM today)
    base = base.merge(place_tags(st, store, juris, parcels, permits), on="geoid", how="left")

    # county shares of the local-only places with eligible parcels (`adu._county_shares`, the places the
    # models ask for): one cached Census lookup for every year
    with_parcels = set()
    if elig is not None:
        with_parcels = set(elig.loc[elig["eligible_parcels"].fillna(0) > 0, "jurisdiction_geoid"])
    shares = adu._county_shares(st, store, base[base["geoid"].isin(with_parcels)])
    counts = adu.observed_adu_counts(permits, 1900, max(years, default=1900), adu_undercount())
    units = None
    if bps is not None:
        units = panels.numerator(bps)[["geoid", "year", "county_geoid", *UNITS, "imputed"]]
        units = units.rename(columns={"county_geoid": "bps_county_geoid"})

    frames = []
    for year in years:
        row = base.assign(year=year)
        for short, theme in THEMES.items():
            if elig is None:
                continue
            e = _eligible(st, store, elig, juris, theme, year, shares)
            e = e.rename(columns={c: f"{c}_{short}" for c in e if c != "geoid"})
            row = row.merge(e, on="geoid", how="left")
        a = adu.acs_values(acs, row["acs_geo"], year, cpi) if acs is not None else pd.DataFrame()
        row = row.merge(a, left_on="acs_geo", right_index=True, how="left")
        if parcels is not None:
            fp = fees.parcel_inputs(parcels, year, fee_params)[["geoid", "new_home_value", "parcel_vintage"]]
            fp = fp.rename(columns={"parcel_vintage": "fee_parcel_vintage"})
            row = row.merge(fp, on="geoid", how="left")
        row["observed_adu_per_year"] = row["geoid"].map(adu.observed_per_year(counts, year, n_obs, stops))
        frames.append(row)
    out = pd.concat(frames, ignore_index=True) if frames else base.assign(year=pd.Series(dtype=int))
    if units is not None:
        out = out.merge(units, on=["geoid", "year"], how="left")
    # the baseline's FHFA index (`panels._hpi`): first of county, cbsa, state non-CBSA, state
    if market is not None and len(out):
        # the jurisdictions table's county, as the baseline panel now reads it (task 5 rule 5)
        frame = out.assign(cbsa_code=out["cbsa_code"].astype("string"))
        hpi = panels._hpi(frame, market, panels.HPI_LEVELS)
        out["hpi"], out["hpi_geo"] = hpi["hpi"].astype(float), hpi["hpi_geo"]
    out["state"] = st
    return _flag_models(out)[[*KEY, *[c for c in out if c not in KEY]] + ["models", "models_note"]]


def place_tags(state: str, store, juris: pd.DataFrame, parcels, permits) -> pd.DataFrame:
    """Per-place tags the models read, computed once (WS-SCALE straight-line build, Ben 2026-11-17).

    - `place_type`, `place_type_source`: D-088 core / suburb / town from national data
      (`adu_types.jurisdiction_types`); a place the type table doesn't know is a town (D-089), source
      "default_town".
    - `is_holdout`: the place's outcomes are hidden by a holdout still blind (or the state is, statewide).
    - `parcel_sources`, `permit_sources`: the sources in the parcel and permit tables tagged to the place,
      sorted and `;`-joined; null where none.
    """
    from lotline.config import load_state
    from lotline.model import adu_types
    from lotline.model.scenarios.adu import TOWN
    from lotline.validation.holdout import still_blind

    out = juris[["geoid"]].copy()
    types = adu_types.jurisdiction_types(store, state)
    out["place_type"] = out["geoid"].astype(str).map(types)
    out["place_type_source"] = np.where(out["place_type"].notna(), "acs_cbsa", "default_town")
    out["place_type"] = out["place_type"].fillna(TOWN)
    blind = still_blind(load_state(state).holdouts)
    held = {g for h in blind for g in h.geoids}
    out["is_holdout"] = out["geoid"].isin(held) | any(h.statewide for h in blind)
    for col, table in (("parcel_sources", parcels), ("permit_sources", permits)):
        if table is None or "source" not in table:
            out[col] = None
            continue
        pairs = table[["jurisdiction_geoid", "source"]].dropna().drop_duplicates()
        joined = pairs.groupby("jurisdiction_geoid")["source"].agg(lambda s: ";".join(sorted(s.astype(str))))
        out[col] = out["geoid"].map(joined)
    return out


def load(state: str, store, *, refresh: bool = False) -> pd.DataFrame:
    """`lotline fetch --source place_inputs`: build and validate the table. Reads only processed tables (no
    download; `refresh` is ignored). Run it after every other source."""
    from lotline.schemas import validate

    return validate(build(state, store), TABLE)


def adu_undercount():
    """The central flag-undercount factors (D-078), as `adu.places_from_store` applies them."""
    from lotline.model import undercount as uc

    return uc.factors_arg("table")


def _flag_models(df: pd.DataFrame) -> pd.DataFrame:
    """`models`: which models read the row today, and `models_note`: why it is out of the others."""
    adu_in = df.get("eligible_parcels_adu", pd.Series(np.nan, index=df.index)).fillna(0) > 0
    adu_priced = (
        df.get("rent", pd.Series(np.nan, index=df.index)).notna()
        & df.get("home_value", pd.Series(np.nan, index=df.index)).notna()
    )
    mm_in = df.get("eligible_parcels_mm", pd.Series(np.nan, index=df.index)).fillna(0) > 0
    in_bps = df["in_bps"].astype("boolean").fillna(True).astype(bool)
    models, notes = [], []
    for a, p, m, b in zip(adu_in, adu_priced, mm_in, in_bps, strict=True):
        tags = [t for t, ok in (("adu", a and p), ("missing_middle", m), ("fees", b), ("baseline", b)) if ok]
        why = []
        if not a:
            why.append("adu: no eligible parcels")
        elif not p:
            why.append("adu: no ACS rent or value (dropped, results.py)")
        if not m:
            why.append("missing_middle: no eligible parcels")
        if not b:
            why.append("fees, baseline: not a BPS place")
        models.append(";".join(tags))
        notes.append("; ".join(why) or None)
    out = df.drop(columns=["models", "models_note"], errors="ignore")
    return out.assign(models=models, models_note=notes)
