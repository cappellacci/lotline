"""Missing-middle estimation panel (analysis plan D-024, pre-registered; this module runs no estimate).

The panel D-024 estimates on: one row per place and year, 2010-2025, for every permit-issuing place in the
four reform states (MN, NC, OH, TX) with at least `mm_estimation_min_population` people, plus every place
with a coded missing-middle rule. Columns:

- **Outcome** `y`: new homes permitted in 2-4 unit buildings. From Census BPS (`units_2 + units_3_4`, the
  same measurement in every state and year; townhouses are 1-unit in BPS and stay out) or, for a local check,
  from a permit source's U2 / U3_4 / DTQ rows. A place-year missing from BPS is missing (NaN), never 0.
  `y_buildings` counts the buildings.
- **Exposure** `eligible`: missing-middle eligible parcels (rule 1.1, D-014: single-family houses and vacant
  single-family-zoned lots), from the nearest roll.
- **Treatment and dose:** from coded `missing_middle` rows in `config/reforms/*.csv` (in force on 1 July):
  dose = units grade × approval grade × coverage (`rule_dose`). Units allowed 2 / 3 / 4+ grade 1/3, 2/3, 1;
  approval by right 1, by permit `mm_dose_grade_permit`; coverage of single-family zones as in D-021. Blank
  fields take coded shares (D-022). Adoption year `T` = the first year a rule with P(by right) >= 0.5 is in
  force on 1 July (NaN if never).
- **Status** of each place: `treated` (has T), `coded_not_treated` (a coded rule, never by right) or `uncoded`
  (no coded rule: unknown under D-022; D-024 asks Ben whether these serve as comparisons).
- **Pre-adoption modifiers** (year T - 1; NaN for places never treated): `pcr` (price-to-cost of a rental
  duplex from the pro forma), `log_value` (log median home value: the existing-use value a teardown must
  beat, C46), `pre_permits` (2-4 unit homes per 1,000 eligible parcels, mean of T - 3 ... T - 1, C06) and
  `hh_growth` (log ACS households T - 1 over T - 6, C04).
- `adu`: P(a by-right ADU rule is in force) that year (the ADU-on-the-same-lot substitution, C47), from the
  place's coded ADU rules; uncoded places take the mean of coded places in their state and size band.
- `rate` (national 30-year mortgage rate), and the placebo / substitution outcomes `units_1` and `units_5p`.

St. Paul (V5 blind test) and Charlotte with every place reporting under Mecklenburg County (holdout from
2023-06-01, D-012) are excluded entirely. Only NumPy and pandas; tests use synthetic tables
(tests/model/test_estimate_mm.py).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from lotline.model.estimate_adu import nearest_roll

ST_PAUL = "2758000"  # V5 blind test: never used
CHARLOTTE = "3712000"  # holdout from 2023-06-01; its reform falls inside the window
MECKLENBURG = "37119"  # reports Charlotte's and the Mecklenburg towns' BPS permits (D-012)
STATES = ("MN", "NC", "OH", "TX")
MODIFIERS = ("pcr", "log_value", "pre_permits", "hh_growth")
EVENT_BINS = ((0, 1), (2, 3), (4, None))  # event-time bins D-024 pools the effect into: k = 0-1, 2-3, 4+
MM_TYPES = ("U2", "U3_4", "DTQ")  # 2-4 unit building types in local permit sources
BPS = "bps"


# ---------------------------------------------------------------------------------------------------------
# Treatment and dose
# ---------------------------------------------------------------------------------------------------------


def units_grade(cap) -> float:
    """Grade of the units a rule allows on a single-family lot: 2 -> 1/3, 3 -> 2/3, 4 or more -> 1, under 2
    -> 0 (equal steps up to the Handbook's fourplex). NaN if the cap is blank."""
    c = pd.to_numeric(cap, errors="coerce")
    if pd.isna(c):
        return np.nan
    return float(np.clip((min(float(c), 4.0) - 1.0) / 3.0, 0.0, 1.0)) if c >= 2 else 0.0


def blank_shares(reforms: pd.DataFrame) -> tuple[float, float]:
    """(P(by right), expected units grade) for blank fields of a coded missing-middle row (D-022): the share
    of coded `by_right` values that are True, and the mean units grade of coded caps, over the coded
    missing-middle rows of every state (0.5 and 1/3 if none is coded). By hand: by_right True, True, blank,
    False and caps 3, 2, blank, 8 -> (2/3, (2/3 + 1/3 + 1) / 3 = 2/3)."""
    mm = reforms[reforms["theme"] == "missing_middle"]
    br = mm["by_right"].dropna().astype(str).str.lower()
    p_br = float((br == "true").mean()) if len(br) else 0.5
    grades = [units_grade(c) for c in mm["unit_cap"]]
    grades = [g for g in grades if not np.isnan(g)]
    return p_br, (float(np.mean(grades)) if grades else 1 / 3)


def rule_dose(row: Mapping, coverage: float, blanks: tuple[float, float], permit_grade: float):
    """(dose, P(by right)) of one coded missing-middle rule.

    dose = units grade × (P(by right) + (1 − P(by right)) × permit grade) × coverage. A blank `by_right` or
    `unit_cap` takes its coded share (`blank_shares`). A rule capped under 2 units is not missing middle: (0,
    0). By hand: cap 3 (2/3), by right blank with share 0.8, permit grade 1/3, coverage 0.5:
    2/3 × (0.8 + 0.2/3) × 0.5 = 0.2889; P(by right) = 0.8.
    """
    p_br_blank, grade_blank = blanks
    g = units_grade(row.get("unit_cap"))
    if g == 0.0:
        return 0.0, 0.0
    g = grade_blank if np.isnan(g) else g
    br = row.get("by_right")
    if br is None or pd.isna(br):
        p_br = p_br_blank
    else:
        p_br = 1.0 if str(br).lower() == "true" else 0.0
    return float(g * (p_br + (1 - p_br) * permit_grade) * coverage), float(p_br)


def rules_by_year(rows: pd.DataFrame, years, coverage: Mapping[str, float], blanks, permit_grade):
    """Per year: (dose, P(by right)) of the strongest of one place's missing-middle rules in force on 1 July
    (`rows`: that place's in-force missing-middle rows)."""
    out = []
    for y in years:
        mid = pd.Timestamp(f"{int(y)}-07-01")
        live = rows[(rows["effective_date"] <= mid) & (rows["end_date"].isna() | (rows["end_date"] > mid))]
        best = (0.0, 0.0)
        for r in live.to_dict("records"):
            d, br = rule_dose(r, coverage.get(r["reform_id"], 1.0), blanks, permit_grade)
            best = (max(best[0], d), max(best[1], br))
        out.append(best)
    return out


def adoption_year(rows: pd.DataFrame, last_year: int, coverage, blanks, permit_grade, first: int = 1990):
    """T: the first year (from `first`) a rule with P(by right) >= 0.5 and a dose above 0 is in force on 1
    July; NaN if none by `last_year`."""
    years = range(first, last_year + 1)
    for y, (d, br) in zip(years, rules_by_year(rows, years, coverage, blanks, permit_grade), strict=True):
        if br >= 0.5 and d > 0:
            return float(y)
    return np.nan


# ---------------------------------------------------------------------------------------------------------
# Outcome, modifiers, ADU substitution
# ---------------------------------------------------------------------------------------------------------


def bps_counts(bps: pd.DataFrame) -> pd.DataFrame:
    """BPS homes and buildings in 2-4 unit buildings, plus the 1-unit and 5+ unit placebo outcomes, by
    (geoid, year). Places that share a GEOID (e.g. a city split across counties) are summed."""
    b = bps[bps["geoid"].notna()].copy()
    b["y"] = b["units_2"].astype(float) + b["units_3_4"].astype(float)
    b["y_buildings"] = b["bldgs_2"].astype(float) + b["bldgs_3_4"].astype(float)
    cols = ["y", "y_buildings", "units_1", "units_5p"]
    return b.groupby(["geoid", "year"])[cols].sum().astype(float)


def local_counts(permits: pd.DataFrame, source: str) -> pd.DataFrame:
    """Homes and buildings in 2-4 unit buildings by (geoid, year) from one local permit source (U2, U3_4,
    DTQ rows; an aggregate row counts `n_buildings` buildings)."""
    p = permits[(permits["source"] == source) & permits["building_type_std"].isin(MM_TYPES)].copy()
    p["y"] = p["units_new"].astype(float).fillna(0.0)
    nb = p["n_buildings"] if "n_buildings" in p else pd.Series(np.nan, index=p.index)
    p["y_buildings"] = nb.astype(float).fillna(1.0)
    g = p.groupby(["jurisdiction_geoid", "issue_year"])[["y", "y_buildings"]].sum()
    g.index = g.index.set_names(["geoid", "year"])
    return g


def plex_price_to_cost(monthly_rent, params: Mapping[str, float] | None = None, cost_index: float = 1.0):
    """Rental duplex value over its cost from the pro forma, for a place's median gross rent per unit (2025
    dollars): value = 12 × rent × units × (1 − vacancy) × (1 − operating costs) / cap rate; cost = hard + soft
    + interest while building, fees and profit left out. `cost_index` scales the hard cost per sq ft to a
    year's real construction cost (`hazard.cost_index_by_year`). Enters D-024 as a z-score, so any constant
    factor (a new unit's rent premium over the median, the prototype's size) cancels."""
    from lotline.model import proforma

    p = proforma.central_params() if params is None else dict(params)
    if cost_index != 1.0:
        p = dict(p, hard_cost_per_sqft_usd=p["hard_cost_per_sqft_usd"] * cost_index)
    one_dollar = proforma.Market(sale_price_per_sqft=0.0, monthly_rent_per_sqft=1.0 / p["plex_unit_sqft"])
    pf = proforma.pro_forma("duplex", "rental", one_dollar, 0.0, p)
    return np.asarray(monthly_rent, dtype=float) * pf.value / (pf.hard_cost + pf.soft_cost + pf.financing)


def pre_permit_rate(y_by_year: Mapping[int, float], eligible_by_year: Mapping[int, float], T: float) -> float:
    """Mean 2-4 unit homes per 1,000 eligible parcels over T − 3 … T − 1 (years with data). By hand: y = 2,
    0, 4 on 1,000, 1,000, 2,000 parcels -> mean(2, 0, 2) = 1.333."""
    rates = []
    for yy in range(int(T) - 3, int(T)):
        y, e = y_by_year.get(yy, np.nan), eligible_by_year.get(yy, np.nan)
        if pd.notna(y) and pd.notna(e) and e > 0:
            rates.append(float(y) / float(e) * 1000)
    return float(np.mean(rates)) if rates else np.nan


def fill_adu_prior(df: pd.DataFrame) -> pd.Series:
    """`adu` for every place-year: its coded value where `adu_coded`, else the mean over coded places in the
    same state, size band and year (falling back to the state-year, then the year). By hand: coded places in
    one state, band and year at 1 and 0 -> an uncoded place there gets 0.5."""
    coded = df[df["adu_coded"]]
    out = df["adu"].where(df["adu_coded"])
    for keys in (["state", "band", "year"], ["state", "year"], ["year"]):
        m = coded.groupby(keys)["adu"].mean().rename("_prior")
        prior = df[keys].merge(m, left_on=keys, right_index=True, how="left")["_prior"]
        out = out.fillna(pd.Series(prior.to_numpy(), index=df.index))
    return out.fillna(0.0)


# ---------------------------------------------------------------------------------------------------------
# The panel
# ---------------------------------------------------------------------------------------------------------


@dataclass
class MMPanel:
    data: pd.DataFrame
    excluded: dict = field(default_factory=dict)  # reason -> list of geoids
    notes: list = field(default_factory=list)


def _excluded_holdout(juris: pd.DataFrame) -> set[str]:
    county = juris["county_geoid"] if "county_geoid" in juris else pd.Series(None, index=juris.index)
    out = set(juris.loc[county == MECKLENBURG, "geoid"])
    return out | ({ST_PAUL, CHARLOTTE, MECKLENBURG} & set(juris["geoid"]))


def build_panel(
    store,
    states: Sequence[str] = STATES,
    years: Sequence[int] | None = None,
    source: str = BPS,
    min_population: float | None = None,
    reforms: Mapping[str, pd.DataFrame] | None = None,
) -> MMPanel:
    """The D-024 panel from processed, holdout-filtered tables (see the module docstring for columns).

    `source`: 'bps' (main) or a local permit source (e.g. 'metc_residential_permits'), whose places are the
    ones it covers. `reforms`: state -> coded reforms (default: config/reforms). Excluded places are listed
    by reason in `excluded`: holdout, under the population floor, no outcome rows, no eligible parcels.
    """
    from lotline.build import eligible as eligible_rule
    from lotline.config import load_params, load_state
    from lotline.model import estimate_adu, hazard, money
    from lotline.model.scenarios import adu

    pm = {k: v.value for k, v in load_params("mm").items()}
    pa_ = {k: v.value for k, v in load_params("adu").items()}
    years = list(
        range(int(pm["mm_panel_first_year"]), int(pm["mm_panel_last_year"]) + 1) if years is None else years
    )
    min_pop = pm["mm_estimation_min_population"] if min_population is None else min_population
    permit_grade = pm["mm_dose_grade_permit"]
    if reforms is None:
        reforms = {st: adu.load_reforms(st) for st in adu.REFORM_STATES}
    every = pd.concat([r.assign(state=st) for st, r in reforms.items()], ignore_index=True)
    blanks = blank_shares(every[every["status"] == "in_force"])
    adu_grades = (pa_["adu_dose_grade_permit"], pa_["adu_dose_grade_owner"], pa_["adu_dose_grade_by_right"])
    fcounts = adu.field_restrict_counts(every, pd.Timestamp(f"{max(years)}-12-31"))
    edges = (pa_["adu_rule_band_small_max_pop"], pa_["adu_rule_band_mid_max_pop"])

    rows, notes = [], []
    excluded: dict[str, list] = {"holdout": [], "small": [], "no outcome rows": [], "no eligible parcels": []}
    for st in states:
        fips = load_state(st).fips
        ref = reforms.get(st, every.iloc[0:0])
        mm_rows = ref[(ref["theme"] == "missing_middle") & (ref["status"] == "in_force")]
        juris = store.read(st, "jurisdictions")
        held = _excluded_holdout(juris)
        juris = juris.set_index("geoid")
        elig = store.read(st, "eligible_parcels")
        elig = elig[
            (elig["theme"] == "missing_middle") & (elig["rule_version"] == eligible_rule.RULE_VERSION)
        ]
        bps = bps_counts(store.read(st, "bps_place_year"))
        if source == BPS:
            outcome, geoids = bps, sorted(bps.index.get_level_values("geoid").unique())
        else:
            permits = store.read(st, "permits")
            if permits is None or not (permits["source"] == source).any():
                continue
            outcome = local_counts(permits, source)
            geoids = sorted(permits.loc[permits["source"] == source, "jurisdiction_geoid"].dropna().unique())
        coded_mm = set(mm_rows["jurisdiction_geoid"])
        market = store.read(st, "market_geo_year")
        cpi = money.index_by_year(market, "cpi_u")
        rate = market[market["geo"] == money.NATIONAL].set_index("year")["mortgage_rate"]
        cost = hazard.cost_index_by_year(market)
        acs = store.read(st, "acs_geo_year")
        hh = acs[acs["variable"] == "B25003_001"].set_index(["geo", "end_year"])["estimate"]
        fp = adu.field_probabilities(fcounts, st, int(pa_["adu_rule_min_coded"]))
        adu_cov = adu.coverage_map(st, store, ref, pa_).set_index("reform_id")["coverage"].to_dict()
        mm_cov = _mm_coverage(st, store, mm_rows, pa_)

        for g in geoids:
            if g in held:
                excluded["holdout"].append(g)
                continue
            pop = (
                pd.to_numeric(juris["pop_2020"].get(g, np.nan), errors="coerce")
                if g in juris.index
                else np.nan
            )
            mine = mm_rows[mm_rows["jurisdiction_geoid"].isin([g])]
            if mine.empty and not (pd.notna(pop) and pop >= min_pop):
                excluded["small"].append(g)
                continue
            e = elig[elig["jurisdiction_geoid"] == g]
            if e.empty:
                excluded["no eligible parcels"].append(g)
                continue
            per_year = rules_by_year(mine, years, mm_cov, blanks, permit_grade)
            T = adoption_year(mine, max(years), mm_cov, blanks, permit_grade)
            status = "treated" if not np.isnan(T) else ("coded_not_treated" if g in coded_mm else "uncoded")
            adu_years, adu_coded = estimate_adu._rules_by_year(
                ref, ref, g, fips, years, adu_cov, fp, adu_grades
            )
            elig_by_year = {y: nearest_roll(e, y) for y in range(min(years) - 3, max(years) + 1)}
            y_by_year = (
                outcome["y"].xs(g, level="geoid").to_dict() if g in outcome.index.get_level_values(0) else {}
            )
            if source == BPS and not y_by_year:
                excluded["no outcome rows"].append(g)
                continue
            kind = juris["kind"].get(g, "place") if g in juris.index else "place"
            geo = f"{adu.ACS_PREFIX.get(kind, 'place')}:{g}"
            mods = {m: np.nan for m in MODIFIERS}
            if not np.isnan(T):
                y0 = int(T) - 1
                v = adu.acs_values(acs, pd.Series([geo]), max(y0, 2010), cpi)
                if not v.empty and v[["rent", "home_value"]].notna().all(axis=None):
                    v = v.iloc[0]
                    ci = cost.get(max(y0, min(cost)), 1.0)
                    mods["pcr"] = float(plex_price_to_cost(v["rent"], cost_index=ci))
                    mods["log_value"] = float(np.log(v["home_value"]))
                bps_y = bps["y"].xs(g, level="geoid").to_dict() if g in bps.index.get_level_values(0) else {}
                mods["pre_permits"] = pre_permit_rate(bps_y, elig_by_year, T)
                a, b = hh.get((geo, max(y0, 2015)), np.nan), hh.get((geo, max(y0, 2015) - 5), np.nan)
                mods["hh_growth"] = (
                    float(np.log(a / b)) if pd.notna(a) and pd.notna(b) and a > 0 and b > 0 else np.nan
                )
            for y, (dose, p_br), (_, adu_br) in zip(years, per_year, adu_years, strict=True):
                if source == BPS:
                    y_val = y_by_year.get(y, np.nan)
                    yb = outcome["y_buildings"].get((g, y), np.nan)
                else:
                    y_val = float(y_by_year.get(y, 0.0))
                    yb = float(outcome["y_buildings"].get((g, y), 0.0))
                rows.append(
                    {
                        "state": st,
                        "place": g,
                        "name": juris["name"].get(g, g) if g in juris.index else g,
                        "pop_2020": pop,
                        "band": int(adu.size_band([pop if pd.notna(pop) else 0], edges)[0]),
                        "status": status,
                        "year": int(y),
                        "y": y_val,
                        "y_buildings": yb,
                        "eligible": elig_by_year[y],
                        "denominator_source": e.sort_values("year")["denominator_source"].iloc[-1],
                        "T": T,
                        "dose": dose,
                        "p_by_right": p_br,
                        "adu": adu_br,
                        "adu_coded": bool(adu_coded),
                        "rate": float(rate.get(int(y), np.nan)),
                        "units_1": bps["units_1"].get((g, y), np.nan),
                        "units_5p": bps["units_5p"].get((g, y), np.nan),
                        **mods,
                    }
                )
        for g in sorted(coded_mm - held - set(geoids)):
            notes.append(f"{st} {g}: coded missing-middle rule but no {source} rows; not in the panel")
    data = pd.DataFrame(rows)
    if not data.empty:
        data["adu"] = fill_adu_prior(data)
    return MMPanel(data, excluded, notes)


def _mm_coverage(state: str, store, mm_rows: pd.DataFrame, params: Mapping[str, float]) -> dict[str, float]:
    """Coverage of each coded missing-middle rule: the D-021 measure (`adu.rule_coverage`) on the place's
    single-family parcels, reused as is (its judgment shares are D-021's)."""
    from lotline.model.scenarios import adu

    needs = mm_rows["coverage_zones"].notna() | (pd.to_numeric(mm_rows["min_lot_sqft"], errors="coerce") > 0)
    parcels = adu._sf_parcels(state, store) if needs.any() else None
    out = {}
    for r in mm_rows.to_dict("records"):
        mine = (
            parcels[parcels["jurisdiction_geoid"] == r["jurisdiction_geoid"]] if parcels is not None else None
        )
        out[r["reform_id"]] = adu.rule_coverage(r, mine, params)[0]
    return out


# ---------------------------------------------------------------------------------------------------------
# Smoke counts (D-024: can the data support the model? counts only, never an estimate)
# ---------------------------------------------------------------------------------------------------------


def event_bin(k: float) -> str | None:
    """The D-024 event-time bin of k = t − T ('k0_1', 'k2_3', 'k4p'); None before adoption or never."""
    if pd.isna(k) or k < 0:
        return None
    for lo, hi in EVENT_BINS:
        if hi is None or k <= hi:
            return f"k{lo}p" if hi is None else f"k{lo}_{hi}"
    return None


def smoke_counts(data: pd.DataFrame, comparisons: str = "uncoded") -> dict:
    """Counts that say whether the panel can support each model, with no outcome effect computed.

    `comparisons`: 'uncoded' (places with no coded rule count as never treated) or 'coded' (only places with
    a coded rule: D-022 strictly). Returns places, place-years with an outcome, treated places by adoption
    year, comparison places, places with no 2-4 unit home in any year (overall / treated / comparisons:
    these drop out of a place fixed-effects Poisson model), the share of zero place-years, and the number of
    treated place-years with an outcome in each event-time bin.
    """
    d = data[data["y"].notna()]
    if comparisons == "coded":
        d = d[d["status"] != "uncoded"]
    places = d.drop_duplicates("place")
    treated = places[places["status"] == "treated"]
    comp = places[places["status"] != "treated"]
    zero = d.groupby("place")["y"].sum() == 0
    bins = d.loc[d["status"] == "treated"].assign(bin=(d["year"] - d["T"]).map(event_bin))
    return {
        "comparisons": comparisons,
        "places": int(len(places)),
        "place_years": int(len(d)),
        "by_state": places["state"].value_counts().sort_index().to_dict(),
        "treated": int(len(treated)),
        "adopters_by_year": treated["T"].astype(int).value_counts().sort_index().to_dict(),
        "adopted_in_window": int(treated["T"].between(d["year"].min(), d["year"].max()).sum()),
        "comparison_places": int(len(comp)),
        "all_zero_places": int(zero.sum()),
        "all_zero_treated": int(zero.reindex(treated["place"]).sum()),
        "all_zero_comparisons": int(zero.reindex(comp["place"]).sum()),
        "zero_share_place_years": float((d["y"] == 0).mean()) if len(d) else np.nan,
        "kept_by_place_fe": int((~zero).sum()),
        "treated_place_years_by_bin": bins["bin"].value_counts().sort_index().to_dict(),
        "treated_places_by_bin": bins.dropna(subset=["bin"]).groupby("bin")["place"].nunique().to_dict(),
    }
