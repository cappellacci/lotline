"""Eligible-parcel rule: the denominator for every rate (BUILD_PLAN §5.3, protocol §5.1-5.2 and §6).

One versioned rule, applied the same way to every state and comparable place. A parcel is eligible for:

- **adu**: an existing single-family house (`land_use_std == SF_DETACHED`), at most one unit where the
  roll records units, lot at least `min_lot_sqft_adu`, not excluded (HOA, floodplain, historic district,
  where known). Handbook: "one ADU per parcel with an existing single-family building".
- **missing_middle**: a lot zoned single-family-only (`sf_only_zoned`) that holds an existing single-family
  house (at most one unit where known) **or is vacant residential land** (`VACANT_RESIDENTIAL`), lot at least
  `min_lot_sqft_missing_middle`, not excluded. Handbook: "2-6 units on single-family-only parcels"; unlike
  ADUs, it does not require an existing building (analysis plan D-014; rule 1.1). The ACS fallback has no
  vacant land, so where it is used the missing-middle denominator excludes vacant lots (flagged as `low`).

Unknown is never silently dropped or counted as known. A parcel whose zoning is unknown counts as
single-family-only (WS-NC brief: "assume SF-only unless known"), a missing lot size passes the floor only
while the floor is 0, and an unknown exclusion flag keeps the parcel. Each such parcel is an *assumption*,
and the share of eligible parcels resting on one sets `denominator_quality`.

Where a state has no usable parcels, `from_acs` falls back to ACS one-unit detached homes (B25024_002),
always quality `low` (protocol §6: "fall back to ACS SF units"). Every number comes from
config/params/eligibility.yaml.

A jurisdiction counted from parcels has a real count only in its roll year(s). `scale_history` fills its other
ACS years from its own ACS series scaled to the roll(s), flagged `parcels_scaled_acs` (#208), so engines that
need the 2010-2024 level window have a denominator in every year.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from lotline.config import Parameter, load_params
from lotline.io import DataStore
from lotline.schemas import columns, validate

RULE_VERSION = "1.1"  # 1.1: vacant SF-zoned lots count for missing middle (D-014)
THEMES = ("adu", "missing_middle")
PARCEL_SOURCES = ("parcels", "parcels_scaled_acs")  # counted from a roll, or scaled to one (#208)
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
    house = sf_house & one_unit
    assumed = units.isna() | lot.isna()

    if theme == "adu":
        eligible = house & lot_ok & ~excluded  # an ADU needs an existing single-family building
    else:  # missing middle: an existing house or a vacant residential lot, on single-family-only zoning
        vacant = parcels["land_use_std"] == "VACANT_RESIDENTIAL"
        zoning = _col(parcels, "sf_only_zoned")
        eligible = (house | vacant) & lot_ok & ~excluded & zoning.fillna(True).astype(bool)
        # unknown zoning: assumed SF-only, and flagged as an assumption
        assumed = (assumed & ~vacant) | (lot.isna() & vacant) | zoning.isna()

    return pd.DataFrame({"eligible": eligible.astype(bool), "assumed": (eligible & assumed).astype(bool)})


def quality(assumed_share: float, params: dict[str, Parameter]) -> str:
    if assumed_share >= params["quality_low_min_unknown_share"].value:
        return "low"
    if assumed_share > params["quality_medium_max_unknown_share"].value:
        return "medium"
    return "high"


def usable_rolls(parcels: pd.DataFrame, min_known: float | None = None) -> pd.Series:
    """True for parcels in a jurisdiction-roll whose land use is known often enough to count from.

    A roll with land use known for fewer than `tier2_min_land_use_share` of its parcels (the tier 2 threshold,
    D-016; config/params/tiers.yaml) would undercount: parcels of UNKNOWN use are never eligible. Such
    jurisdiction-rolls are left out, so the ACS fallback is used for them (Summit County, Ohio, sends no land
    use at all: Akron would otherwise have 0 eligible parcels).
    """
    if min_known is None:
        min_known = load_params("tiers")["tier2_min_land_use_share"].value
    known = (
        (parcels["land_use_std"] != "UNKNOWN")
        .groupby([parcels["jurisdiction_geoid"], parcels["vintage"]])
        .transform("mean")
    )
    return known >= min_known


def from_parcels(
    parcels: pd.DataFrame,
    jurisdictions: pd.DataFrame,
    themes: tuple[str, ...] = THEMES,
    params: dict[str, Parameter] | None = None,
) -> pd.DataFrame:
    """Count eligible parcels per jurisdiction, roll vintage and theme -> the `eligible_parcels` table."""
    p = params or load_params("eligibility")
    tiers = jurisdictions.set_index("geoid")["data_tier"]
    parcels = parcels[usable_rolls(parcels)]  # the rest fall back to the ACS denominator (combine)
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
    # County remainders subtract only BPS-universe jurisdictions: BPS files a local-only township's permits in
    # its county's row, so its homes must stay in that county's denominator too.
    in_bps = j["in_bps"].fillna(True).astype(bool) if "in_bps" in j else pd.Series(True, index=j.index)
    bps_members = set(j.index[in_bps])
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
            if p in bps_members:
                in_county[c] = in_county.get(c, 0.0) + homes.get(p, 0.0) * s
        for t in townships:
            if t in homes and t in bps_members:
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


def single_source(parcels: pd.DataFrame, choice: dict[str, str]) -> pd.DataFrame:
    """Keep one parcels source per jurisdiction, so no parcel is counted twice (#147).

    `choice` is the state config's `parcel_sources` (GEOID -> source, `"*"` for the rest). Without one, a
    jurisdiction covered by two sources, in the same roll year or in different ones, raises instead of being
    double-counted or switching source between years (Durham: a 2023 Wake roll holding only its 363 Wake
    County parcels next to its 2026 OneMap roll, so every origin before 2026 saw 5 eligible parcels).
    """
    if parcels.empty:
        return parcels
    if choice:
        wanted = parcels["jurisdiction_geoid"].astype(str).map(choice).fillna(choice.get("*", ""))
        return parcels[parcels["source"] == wanted]
    n = parcels.groupby("jurisdiction_geoid")["source"].nunique()
    overlap = n[n > 1]
    if len(overlap):
        sources = sorted(parcels["source"].unique())
        raise ValueError(
            f"{len(overlap)} jurisdictions are covered by more than one parcels source ({sources}), "
            f"e.g. {list(overlap.index[:3])}: set `parcel_sources` in the state config to pick one per "
            "jurisdiction"
        )
    return parcels


def _nearest_acs_year(year: int, acs_years: list[int], max_gap: float) -> int | None:
    """The ACS end year closest to a roll year (the later on a tie), or None if none is within `max_gap`."""
    best = min(acs_years, key=lambda a: (abs(a - year), -a), default=None)
    return best if best is not None and abs(best - year) <= max_gap else None


def scale_history(
    parcel_rows: pd.DataFrame,
    acs_rows: pd.DataFrame,
    params: dict[str, Parameter] | None = None,
) -> pd.DataFrame:
    """Years without a roll for parcel-counted jurisdictions: their ACS series scaled to the roll(s) (#208).

    A jurisdiction counted from a parcel roll has a real count only in its roll year(s); the ACS fallback has
    one in every ACS end year. For each jurisdiction and theme:

    1. Each roll year r is an **anchor**: scale factor f_r = parcels_r / ACS_a, where a is the ACS end year
       nearest r (r itself if released; the later on a tie), at most `scale_max_year_gap` years away. An
       anchor whose ACS count is 0 or missing is skipped.
    2. For every ACS end year t that has no roll: f(t) is f_r at a single anchor; with two or more, linear
       in t between neighbouring anchors and held at the first / last anchor's value outside them.
    3. The filled count is round(ACS_t · f(t)), `denominator_source = "parcels_scaled_acs"`, with the
       `denominator_quality` of the nearest anchor (the earlier on a tie).

    A real roll year always keeps its real count. Jurisdictions with no usable anchor get no filled rows.
    By hand: rolls 2019 (90 parcels, ACS 100 -> f 0.9) and 2023 (110, ACS 100 -> f 1.1); ACS 2021 = 200 ->
    f 1.0, 200; ACS 2010 = 50 -> f 0.9, 45; ACS 2024 = 120 -> f 1.1, 132.
    Returns only the filled rows, in the `eligible_parcels` schema.
    """
    p = params or load_params("eligibility")
    max_gap = p["scale_max_year_gap"].value
    acs = {
        key: g.set_index("year")["eligible_parcels"].astype(float)
        for key, g in acs_rows.groupby(["jurisdiction_geoid", "theme"])
    }
    rows = []
    for (geoid, theme), g in parcel_rows.groupby(["jurisdiction_geoid", "theme"], sort=True):
        if (geoid, theme) not in acs:
            continue
        series = acs[(geoid, theme)]
        acs_years = sorted(int(y) for y in series.index)
        anchors = []  # (roll year, factor, quality)
        for r in g.sort_values("year").itertuples():
            a = _nearest_acs_year(int(r.year), acs_years, max_gap)
            if a is None or not series[a] > 0:
                continue
            anchors.append((int(r.year), float(r.eligible_parcels) / float(series[a]), r.denominator_quality))
        if not anchors:
            continue
        xs = np.array([a[0] for a in anchors], dtype=float)
        fs = np.array([a[1] for a in anchors], dtype=float)
        first = g.iloc[0]
        real = set(g["year"].astype(int))
        for t in acs_years:
            if t in real:
                continue
            factor = float(np.interp(t, xs, fs))  # flat beyond the first and last anchor
            nearest = min(anchors, key=lambda a: (abs(a[0] - t), a[0]))
            rows.append(
                {
                    "state": first["state"],
                    "jurisdiction_geoid": geoid,
                    "year": t,
                    "theme": theme,
                    "rule_version": first["rule_version"],
                    "eligible_parcels": int(round(series[t] * factor)),
                    "data_tier": int(first["data_tier"]),
                    "denominator_source": "parcels_scaled_acs",
                    "denominator_quality": nearest[2],
                }
            )
    return validate(pd.DataFrame(rows, columns=columns("eligible_parcels")), "eligible_parcels")


def combine(parcel_rows: pd.DataFrame | None, acs_rows: pd.DataFrame) -> pd.DataFrame:
    """One denominator source per jurisdiction: parcels where a state has them (real roll years, the rest
    filled by `scale_history`), the ACS fallback elsewhere."""
    if parcel_rows is None or parcel_rows.empty:
        return acs_rows
    covered = set(parcel_rows["jurisdiction_geoid"])
    rest = acs_rows[~acs_rows["jurisdiction_geoid"].isin(covered)]
    filled = scale_history(parcel_rows, acs_rows)
    parts = [df for df in (parcel_rows, filled, rest) if len(df)]
    return validate(pd.concat(parts, ignore_index=True), "eligible_parcels")


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    """Build `eligible_parcels` for one state from processed tables (building any that are missing)."""
    from lotline.adapters.national import acs
    from lotline.build import jurisdictions as jur

    def processed_or(table: str, build):
        df = store.read(state, table)
        return df if df is not None else build()

    juris = processed_or("jurisdictions", lambda: jur.load(state, store, refresh=refresh))
    acs_table = processed_or("acs_geo_year", lambda: acs.load(state, store, refresh=refresh))
    from lotline.adapters.national import geoparts
    from lotline.config import load_state

    cfg = load_state(state)
    parcels = store.read(state, "parcels")
    if parcels is not None and len(parcels):
        parcels = single_source(parcels, cfg.parcel_sources)
    parcel_rows = from_parcels(parcels, juris) if parcels is not None and len(parcels) else None
    places = juris.loc[juris["kind"] == "place", "geoid"].tolist()
    townships = juris.loc[juris["kind"] == "township", "geoid"].tolist()
    c_shares = geoparts.county_shares(cfg.fips, places, store, refresh)
    t_shares = geoparts.township_shares(cfg.fips, places, townships, store, refresh)
    acs_rows = from_acs(acs_table, juris, county_shares=c_shares, township_shares=t_shares)
    return combine(parcel_rows, acs_rows)
