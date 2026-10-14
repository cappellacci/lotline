"""Eligible-parcel rule: the denominator for every rate (BUILD_PLAN §5.3, protocol §5.1-5.2 and §6).

One versioned rule, applied the same way to every state and comparable place. A parcel is eligible for:

- **adu**: an existing single-family house (`land_use_std == SF_DETACHED`), at most one unit where the
  roll records units, lot at least `min_lot_sqft_adu`, not excluded (HOA, floodplain, historic district,
  where known). Handbook: "one ADU per parcel with an existing single-family building".
- **missing_middle**: the same, on a lot zoned single-family-only (`sf_only_zoned`), lot at least
  `min_lot_sqft_missing_middle`. Handbook: "2-6 units on single-family-only parcels".

Unknown is never silently dropped or counted as known. A parcel whose zoning is unknown counts as
single-family-only (WS-NC brief: "assume SF-only unless known"), a missing lot size passes the floor only
while the floor is 0, and an unknown exclusion flag keeps the parcel. Each such parcel is an *assumption*,
and the share of eligible parcels resting on one sets `denominator_quality`.

Where a state has no usable parcels, `from_acs` falls back to ACS one-unit detached homes (B25024_002),
always quality `low` (protocol §6: "fall back to ACS SF units"). Every number comes from
config/params/eligibility.yaml.
"""

from __future__ import annotations

import pandas as pd

from lotline.config import Parameter, load_params
from lotline.io import DataStore
from lotline.schemas import validate

RULE_VERSION = "1.0"
THEMES = ("adu", "missing_middle")
ACS_SF_DETACHED = "B25024_002"  # units in structure: 1, detached
EXCLUSIONS = {
    "hoa": "exclude_hoa",
    "in_floodplain": "exclude_floodplain",
    "in_historic_district": "exclude_historic_district",
}


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """A nullable column, or all-unknown if the source doesn't have it."""
    if name in df:
        return df[name]
    return pd.Series(
        pd.NA, index=df.index, dtype="boolean" if name not in ("units", "lot_sqft") else "Float64"
    )


def classify(parcels: pd.DataFrame, theme: str, params: dict[str, Parameter] | None = None) -> pd.DataFrame:
    """Per parcel: `eligible` and `assumed` (eligible only because an unknown input was given the benefit of
    the doubt). Input is the canonical `parcels` table."""
    if theme not in THEMES:
        raise ValueError(f"no eligibility rule for theme {theme!r}; known: {THEMES}")
    p = params or load_params("eligibility")
    floor = p[f"min_lot_sqft_{theme}"].value

    sf_house = parcels["land_use_std"] == "SF_DETACHED"
    units = pd.to_numeric(_col(parcels, "units"), errors="coerce")
    one_unit = units.isna() | (units <= 1)
    lot = pd.to_numeric(_col(parcels, "lot_sqft"), errors="coerce")
    lot_ok = (lot >= floor) | (lot.isna() & (floor <= 0))
    excluded = pd.Series(False, index=parcels.index)
    for column, toggle in EXCLUSIONS.items():
        if p[toggle].value >= 1:
            excluded |= _col(parcels, column).fillna(False).astype(bool)
    eligible = sf_house & one_unit & lot_ok & ~excluded
    assumed = units.isna() | lot.isna()

    if theme == "missing_middle":
        zoning = _col(parcels, "sf_only_zoned")
        eligible &= zoning.fillna(True).astype(bool)  # unknown zoning: assume SF-only, and say so
        assumed |= zoning.isna()

    return pd.DataFrame({"eligible": eligible.astype(bool), "assumed": (eligible & assumed).astype(bool)})


def quality(assumed_share: float, params: dict[str, Parameter]) -> str:
    if assumed_share >= params["quality_low_min_unknown_share"].value:
        return "low"
    if assumed_share > params["quality_medium_max_unknown_share"].value:
        return "medium"
    return "high"


def from_parcels(
    parcels: pd.DataFrame,
    jurisdictions: pd.DataFrame,
    themes: tuple[str, ...] = THEMES,
    params: dict[str, Parameter] | None = None,
) -> pd.DataFrame:
    """Count eligible parcels per jurisdiction, roll vintage and theme -> the `eligible_parcels` table."""
    p = params or load_params("eligibility")
    tiers = jurisdictions.set_index("geoid")["data_tier"]
    rows = []
    for theme in themes:
        flags = classify(parcels, theme, p)
        df = parcels[["state", "jurisdiction_geoid", "vintage"]].join(flags)
        for (state, geoid, year), g in df.groupby(["state", "jurisdiction_geoid", "vintage"], sort=True):
            n = int(g["eligible"].sum())
            share = g["assumed"].sum() / n if n else 0.0
            rows.append(
                {
                    "state": state,
                    "jurisdiction_geoid": geoid,
                    "year": year,
                    "theme": theme,
                    "rule_version": RULE_VERSION,
                    "eligible_parcels": n,
                    "data_tier": int(tiers.get(geoid, 3)),
                    "denominator_source": "parcels",
                    "denominator_quality": quality(share, p),
                }
            )
    return validate(pd.DataFrame(rows), "eligible_parcels")


def allocate_homes(
    acs_sf: pd.DataFrame,
    jurisdictions: pd.DataFrame,
    county_shares: pd.DataFrame,
    township_shares: pd.DataFrame,
) -> pd.DataFrame:
    """Homes per permit-issuing jurisdiction and ACS year, with nothing counted twice.

    - **place**: its ACS total.
    - **township**: its ACS total minus the permit-issuing places that sit inside it (Ohio villages that
      aren't their own county subdivision), each subtracted in proportion to its 2020 housing units there.
    - **county_unincorporated** ("rest of county"): the county's ACS total minus every permit-issuing place's
      homes in that county (split by 2020 housing-unit shares when a place spans counties) and every
      township's net homes. A negative remainder (sampling noise) is set to 0 and flagged `clipped`.

    `acs_sf`: rows of B25024_002 with `geo` (`county:`, `place:`, `cousub:`), `end_year`, `estimate`.
    `county_shares`: place_geoid, county_geoid, share (each place's shares sum to 1).
    `township_shares`: place_geoid, township_geoid, share (dependent places only).
    """
    est = acs_sf.assign(geoid=acs_sf["geo"].str.split(":").str[1]).dropna(subset=["estimate"])
    est = est.set_index(["geoid", "end_year"])["estimate"]
    j = jurisdictions.set_index("geoid")
    places = j.index[j["kind"] == "place"]
    townships = j.index[j["kind"] == "township"]
    counties = j.index[j["kind"] == "county_unincorporated"]
    shares_c = county_shares[county_shares["place_geoid"].isin(places)]
    shares_t = township_shares[
        township_shares["place_geoid"].isin(places) & township_shares["township_geoid"].isin(townships)
    ]
    out = []
    for year in sorted(est.index.get_level_values("end_year").unique()):
        get = est.xs(year, level="end_year")
        homes = {g: float(get[g]) for g in places if g in get.index}
        for t in townships:
            if t not in get.index:
                continue
            inside = shares_t[shares_t["township_geoid"] == t]
            homes[t] = float(get[t]) - sum(
                homes.get(p, 0.0) * s for p, s in zip(inside["place_geoid"], inside["share"], strict=True)
            )
        in_county: dict[str, float] = {}
        for p, c, s in zip(shares_c["place_geoid"], shares_c["county_geoid"], shares_c["share"], strict=True):
            in_county[c] = in_county.get(c, 0.0) + homes.get(p, 0.0) * s
        for t in townships:
            if t in homes:
                in_county[t[:5]] = in_county.get(t[:5], 0.0) + homes[t]
        for c in counties:
            if c in get.index:
                homes[c] = float(get[c]) - in_county.get(c, 0.0)
        for g, h in homes.items():
            out.append(
                {"jurisdiction_geoid": g, "end_year": int(year), "homes": max(h, 0.0), "clipped": h < 0}
            )
    return pd.DataFrame(out, columns=["jurisdiction_geoid", "end_year", "homes", "clipped"])


def from_acs(
    acs: pd.DataFrame,
    jurisdictions: pd.DataFrame,
    themes: tuple[str, ...] = THEMES,
    county_shares: pd.DataFrame | None = None,
    township_shares: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Fallback denominator: ACS one-unit detached homes per permit-issuing jurisdiction, by 5-year end year,
    including unincorporated county areas ("rest of county"). See `allocate_homes`.

    Counts *homes*, not parcels, and can't see zoning, so it is the same for every theme and always `low`.
    Without share tables, every place is assumed to lie in the county BPS files it under and no place is
    assumed to sit inside a township.
    """
    sf = acs[(acs["variable"] == ACS_SF_DETACHED) & acs["geo"].str.match(r"^(county|place|cousub):")]
    j = jurisdictions.set_index("geoid")
    if county_shares is None:
        pl = jurisdictions[jurisdictions["kind"] == "place"]
        county_shares = pd.DataFrame(
            {"place_geoid": pl["geoid"], "county_geoid": pl["county_geoid"], "share": 1.0}
        )
    if township_shares is None:
        township_shares = pd.DataFrame(columns=["place_geoid", "township_geoid", "share"])
    homes = allocate_homes(sf, jurisdictions, county_shares, township_shares)
    rows = [
        {
            "state": j.loc[r.jurisdiction_geoid, "state"],
            "jurisdiction_geoid": r.jurisdiction_geoid,
            "year": int(r.end_year),
            "theme": theme,
            "rule_version": RULE_VERSION,
            "eligible_parcels": int(round(r.homes)),
            "data_tier": int(j.loc[r.jurisdiction_geoid, "data_tier"]),
            "denominator_source": "acs_sf_fallback",
            "denominator_quality": "low",
        }
        for theme in themes
        for r in homes.itertuples()
    ]
    return validate(pd.DataFrame(rows), "eligible_parcels")


# ---- `lotline fetch --source eligible` -----------------------------------------------------------------

SOURCE = "eligible"
# ACS, jurisdictions' inputs, and the 2020 code files and housing-unit parts used to split places
MANIFEST_SOURCES = ["census_acs5", "census_bps_place_annual", "census_dec_pl", "census_geo_codes"]


def combine(parcel_rows: pd.DataFrame | None, acs_rows: pd.DataFrame) -> pd.DataFrame:
    """One denominator source per jurisdiction: parcels where a state has them, the ACS fallback elsewhere."""
    if parcel_rows is None or parcel_rows.empty:
        return acs_rows
    covered = set(parcel_rows["jurisdiction_geoid"])
    rest = acs_rows[~acs_rows["jurisdiction_geoid"].isin(covered)]
    return validate(pd.concat([parcel_rows, rest], ignore_index=True), "eligible_parcels")


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    """Build `eligible_parcels` for one state from processed tables (building any that are missing)."""
    from lotline.adapters.national import acs
    from lotline.build import jurisdictions as jur

    def processed_or(table: str, build):
        df = store.read(state, table)
        return df if df is not None else build()

    juris = processed_or("jurisdictions", lambda: jur.load(state, store, refresh=refresh))
    acs_table = processed_or("acs_geo_year", lambda: acs.load(state, store, refresh=refresh))
    parcels = store.read(state, "parcels")
    parcel_rows = from_parcels(parcels, juris) if parcels is not None and len(parcels) else None

    from lotline.adapters.national import geoparts
    from lotline.config import load_state

    cfg = load_state(state)
    places = juris.loc[juris["kind"] == "place", "geoid"].tolist()
    townships = juris.loc[juris["kind"] == "township", "geoid"].tolist()
    c_shares = geoparts.county_shares(cfg.fips, places, store, refresh)
    t_shares = geoparts.township_shares(cfg.fips, places, townships, store, refresh)
    acs_rows = from_acs(acs_table, juris, county_shares=c_shares, township_shares=t_shares)
    return combine(parcel_rows, acs_rows)
