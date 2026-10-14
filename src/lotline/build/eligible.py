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


def from_acs(
    acs: pd.DataFrame, jurisdictions: pd.DataFrame, themes: tuple[str, ...] = THEMES
) -> pd.DataFrame:
    """Fallback denominator: ACS one-unit detached homes per place or township, by 5-year end year.

    Counts *homes*, not parcels, and can't see zoning, so it is the same for every theme and always `low`.
    Unincorporated county areas have no ACS geography of their own and get no fallback row.
    """
    # Places and county subdivisions only: an ACS county row would give an unincorporated area the whole
    # county's homes, double-counting every city in it.
    sf = acs[(acs["variable"] == ACS_SF_DETACHED) & acs["geo"].str.match(r"^(place|cousub):")].copy()
    sf["geoid"] = sf["geo"].str.split(":").str[1]
    j = jurisdictions.set_index("geoid")
    sf = sf[sf["geoid"].isin(j.index) & sf["estimate"].notna()]
    rows = [
        {
            "state": j.loc[r.geoid, "state"],
            "jurisdiction_geoid": r.geoid,
            "year": int(r.end_year),
            "theme": theme,
            "rule_version": RULE_VERSION,
            "eligible_parcels": int(round(r.estimate)),
            "data_tier": int(j.loc[r.geoid, "data_tier"]),
            "denominator_source": "acs_sf_fallback",
            "denominator_quality": "low",
        }
        for theme in themes
        for r in sf.itertuples()
    ]
    return validate(pd.DataFrame(rows), "eligible_parcels")
