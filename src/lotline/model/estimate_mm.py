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

import math
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


# ---------------------------------------------------------------------------------------------------------
# Estimation (D-024): design, PPML with place and state × year effects, and the pre-specified fallback
# ---------------------------------------------------------------------------------------------------------

MAIN_MODIFIERS = ("pcr", "log_value")
BIN_NAMES = ("beta_0", "beta_2", "beta_4")  # k = 0-1, 2-3, 4+ (the number is the bin's first year)
LEADS = (-3, -2, -1)


def year_code(panel: pd.DataFrame) -> np.ndarray:
    """State × year group as one integer (state's position in STATES × 10,000 + year), so the year effects
    γ_st are one fixed effect per state and year. By hand: NC 2020 -> 12020."""
    s = panel["state"].map({st: i for i, st in enumerate(STATES)}).to_numpy(dtype=int)
    return s * 10_000 + panel["year"].to_numpy(dtype=int)


def build_design(
    panel: pd.DataFrame,
    modifiers: Sequence[str] = MAIN_MODIFIERS,
    leads: Sequence[int] = (),
    binary_dose: bool = False,
    use_rate: bool = True,
    use_adu: bool = True,
    scale_from: pd.DataFrame | None = None,
):
    """Regressors of the D-024 model from a panel (place, state, year, T, dose, rate, adu, modifiers).

    - β_b: dose × 1[t − T in bin b], b = 0-1, 2-3, 4+ (`binary_dose`: 1 instead of the dose);
    - leads: 1[t − T = k] for k < 0 (pre-trend check);
    - θ_m: z-score of the modifier over the treated places (of `scale_from`, default the panel) × post;
    - ρ: (rate − panel mean rate) × post; δ: adu.
    Returns an `estimate_adu.Design` whose bin columns are named beta_0 / beta_2 / beta_4, so the D-023
    aggregation (`estimate_adu.aggregate`) weights them by counterfactual expected homes.
    """
    from lotline.model.estimate_adu import Design, modifier_scale

    e = panel["year"].to_numpy(dtype=float) - panel["T"].to_numpy(dtype=float)
    post = np.nan_to_num((e >= 0).astype(float) * ~np.isnan(e))
    dose = panel["dose"].to_numpy(dtype=float)
    if binary_dose:
        dose = (dose > 0).astype(float)
    cols, names, cells = [], [], []
    for (lo, hi), name in zip(EVENT_BINS, BIN_NAMES, strict=True):
        ind = (e >= lo) & (e <= (np.inf if hi is None else hi))
        if ind.any():
            cols.append(dose * ind)
            names.append(name)
            cells.append((-1, lo))
    n_cells = len(cols)
    for k in leads:
        cols.append((e == k).astype(float))
        names.append(f"lead_{-k}")
    ref = panel if scale_from is None else scale_from
    treated = ref.loc[ref["T"].notna()].drop_duplicates("place")
    for m in modifiers:
        centre, sd = modifier_scale(treated, m)
        cols.append(np.nan_to_num((panel[m].to_numpy(dtype=float) - centre) / sd) * post)
        names.append(f"theta_{m}")
    if use_rate:
        r = panel["rate"].to_numpy(dtype=float)
        cols.append((r - float(ref["rate"].mean())) * post)
        names.append("rho")
    if use_adu:
        cols.append(panel["adu"].to_numpy(dtype=float))
        names.append("delta")
    X = np.column_stack(cols) if cols else np.zeros((len(panel), 0))
    return Design(X, names, cells, n_cells)


def estimate(panel: pd.DataFrame, method: str = "ppml", **design_kw):
    """Fit the D-024 model on the place-years with an outcome. `method`: 'ppml' (main: place and state ×
    year fixed effects, `estimate_adu.ppml` with its separation removal and guards), 'nb' (the pre-specified
    fallback: D-025's negative binomial with normal place random effects, `fit_nb`) or 're' (Poisson-gamma
    place random effects, `fit_re`; a robustness model). Returns an `estimate_adu.Estimate`."""
    from lotline.model.estimate_adu import Estimate, ppml

    p = panel[panel["y"].notna()].reset_index(drop=True)
    d = build_design(p, **design_kw)
    off = np.log(p["eligible"].to_numpy(dtype=float))
    if method == "ppml":
        fit = ppml(p["y"], d.X, off, p["place"], year_code(p), d.names)
    elif method == "re":
        fit = fit_re(p["y"], d.X, off, p["place"], year_code(p), d.names)
    elif method == "nb":
        fit = fit_nb(p, d, **design_kw)
    else:
        raise ValueError(f"unknown method {method!r}")
    return Estimate(fit, d, p)


NB_NAMES = {"beta_0_1": "beta_0", "beta_2_3": "beta_2", "beta_4p": "beta_4"}  # D-025 bands -> D-024 bins


@dataclass
class NBFit:
    """A D-025 negative-binomial fit (`pooled_adu.fit_pooled`) seen through D-024's names, with the attributes
    `estimate_adu.aggregate` / `summarize` and `transport_predict` use."""

    names: list
    coef: np.ndarray
    mu: np.ndarray  # fitted means at each place's posterior-mode random effect
    keep: np.ndarray
    y: np.ndarray
    cluster: np.ndarray
    alpha: np.ndarray  # intercept + random effect, per place
    gamma: np.ndarray  # state-year effects (reference = 0)
    years: np.ndarray
    pooled: object
    iterations: int = 0
    converged: bool = True
    dropped_places: list = field(default_factory=list)
    dropped_columns: list = field(default_factory=list)
    separated: list = field(default_factory=list)

    def coef_of(self, name: str) -> float:
        return float(self.coef[self.names.index(name)])


NB_MAX_ITER = 3000  # BFGS iterations for the D-025 fit: dozens of state-year dummies need more than its 500


def poisson_start(X: np.ndarray, y: np.ndarray, offset: np.ndarray, iters: int = 25) -> np.ndarray:
    """Start values for the D-025 fit: a pooled Poisson regression (no place effects) on the same fixed
    design, by IRLS. Only where BFGS starts; the estimate is D-025's maximum. By hand: intercept only, y = (2,
    6), offset 0 -> log 4."""
    b = np.zeros(X.shape[1])
    b[0] = math.log(max(y.sum(), 1e-9) / np.exp(offset).sum())
    for _ in range(iters):
        eta = np.clip(offset + X @ b, -50, 50)
        mu = np.exp(eta)
        w = np.sqrt(mu)
        z = eta - offset + (y - mu) / mu
        b_new = np.linalg.lstsq(X * w[:, None], z * w, rcond=None)[0]
        if np.max(np.abs(b_new - b)) < 1e-8:
            return np.clip(b_new, -15, 15)
        b = b_new
    return np.clip(b, -15, 15)


def pooled_panel(p: pd.DataFrame) -> pd.DataFrame:
    """The D-024 panel relabelled for D-025's design builder, which is used unchanged: `year` becomes the
    state × year code (`year_code`), so its year dummies are D-024's state × year effects; `T` is shifted by
    the same state offset, so event time t − T is unchanged; `mm` (D-025's δ column) carries D-024's ADU
    term. By hand: NC 2021 with T = 2020 -> year 12021, T 12020, event time 1."""
    shift = p["state"].map({st: i for i, st in enumerate(STATES)}).to_numpy(dtype=float) * 10_000
    return p.assign(year=year_code(p), T=p["T"].to_numpy(dtype=float) + shift, mm=p["adu"])


def fit_nb(p: pd.DataFrame, d, modifiers=MAIN_MODIFIERS, leads=(), binary_dose=False, use_rate=True,
           use_adu=True, scale_from=None) -> NBFit:  # fmt: skip
    """D-025's estimator (`pooled_adu.build_pooled_design` and `fit_pooled`, unchanged) on the D-024 panel
    (`pooled_panel`); its guards raise `EstimationError`. `d` is the D-024 design of the same rows."""
    from lotline.model import pooled_adu as pa

    if scale_from is not None:
        raise ValueError("the D-025 design scales modifiers on its own panel")
    pp = pooled_panel(p)
    pd_ = pa.build_pooled_design(pp, modifiers=modifiers, leads=leads, use_rate=use_rate, use_mm=use_adu,
                                 binary_dose=binary_dose)  # fmt: skip
    k = pd_.X.shape[1]
    start = np.r_[poisson_start(pd_.X, pd_.y, pd_.offset), 0.0, math.log(0.5)]  # σ = 1, κ = 0.5 as in D-025
    pf = pa.fit_pooled(pd_, start=start, max_iter=NB_MAX_ITER)
    lp = pf.log_params
    u = pa.place_effects(lp, pd_)
    mu = np.exp(pd_.offset + pd_.X @ lp[:k] + u[pd_.place_idx])
    sep = set(getattr(pd_, "separated", []))
    keep = np.array([(pl, int(c)) not in sep for pl, c in zip(p["place"], pp["year"], strict=True)])
    names, coef = [], []
    for j, n in enumerate(pd_.names):
        if n == "intercept" or n.startswith("year_"):
            continue
        names.append(NB_NAMES.get(n, n))
        coef.append(lp[j])
    gam = {int(n.split("_", 1)[1]): lp[j] for j, n in enumerate(pd_.names) if n.startswith("year_")}
    years = np.asarray(pd_.years)
    a0 = lp[pd_.names.index("intercept")] if "intercept" in pd_.names else 0.0
    fit = NBFit(
        names=names, coef=np.asarray(coef), mu=mu, keep=keep, y=pd_.y, cluster=pd_.places[pd_.place_idx],
        alpha=a0 + u, gamma=np.array([gam.get(int(c), 0.0) for c in years]), years=years, pooled=pf,
        dropped_columns=list(pd_.dropped), separated=sorted(sep),
    )  # fmt: skip
    fit.at_bound = getattr(pf, "at_bound", [])
    fit.sigma, fit.kappa = math.exp(lp[k]), math.exp(lp[k + 1])
    return fit


def treated_dropped(est_) -> list:
    """Treated places the fit dropped (all their rows removed): D-024's trigger for the fallback."""
    p = est_.panel
    treated = set(p.loc[p["T"].notna(), "place"])
    kept = set(p.loc[est_.fit.keep, "place"])
    return sorted(treated - kept)


@dataclass
class REFit:
    """A Poisson-gamma random-effects fit, with the attributes `estimate_adu.aggregate` / `summarize` use."""

    names: list
    coef: np.ndarray
    params: np.ndarray  # [regressors | intercept | state-year effects (drop first) | log a]
    info: np.ndarray  # minus the Hessian of the log likelihood
    scores: np.ndarray  # clusters × params
    mu: np.ndarray  # fitted means, including each place's posterior multiplier
    keep: np.ndarray
    y: np.ndarray
    cluster: np.ndarray
    alpha: np.ndarray  # intercept + log posterior multiplier, per place
    gamma: np.ndarray  # state-year effects (first = 0)
    years: np.ndarray
    a: float  # gamma shape: var(u) = 1 / a
    iterations: int = 0
    converged: bool = True
    dropped_places: list = field(default_factory=list)
    dropped_columns: list = field(default_factory=list)
    separated: list = field(default_factory=list)

    def coef_of(self, name: str) -> float:
        return float(self.coef[self.names.index(name)])


def _re_parts(theta, Z, y, off, cl, n_cl):
    """Log likelihood, per-cluster scores and the pieces of the Poisson-gamma random-effects model.

    u_i ~ Gamma(a, 1/a) (mean 1, variance 1/a), y_it | u_i ~ Poisson(u_i μ_it), μ = exp(off + Z b). With
    Y_i = Σ_t y_it, M_i = Σ_t μ_it: ll_i = Σ_t [y log μ − log y!] + lgamma(Y_i + a) − lgamma(a) + a log a −
    (Y_i + a) log(M_i + a). Scores: ∂/∂b = Σ_t y z − (Y + a)/(M + a) Σ_t μ z;
    ∂/∂log a = a [ψ(Y + a) − ψ(a) + log a + 1 − log(M + a) − (Y + a)/(M + a)].
    """
    import math

    b, la = theta[:-1], theta[-1]
    if not np.isfinite(la) or abs(la) > 50:
        raise ValueError("diverged")
    a = math.exp(la)
    eta = off + Z @ b
    if np.max(np.abs(eta - off)) > 30:
        raise ValueError("diverged")
    mu = np.exp(eta)
    Y = np.bincount(cl, weights=y, minlength=n_cl)
    M = np.bincount(cl, weights=mu, minlength=n_cl)
    ratio = (Y + a) / (M + a)
    lg = np.array([math.lgamma(v + a) for v in Y]) - math.lgamma(a)
    ll = float(np.sum(y * eta) + lg.sum() + n_cl * a * la - np.sum((Y + a) * np.log(M + a)))
    sz = np.zeros((n_cl, Z.shape[1]))
    np.add.at(sz, cl, Z * (y - ratio[cl] * mu)[:, None])
    psi = np.array([np.sum(1.0 / (a + np.arange(int(round(v))))) for v in Y])  # ψ(Y + a) − ψ(a)
    sa = a * (psi + la + 1 - np.log(M + a) - ratio)
    return ll, np.hstack([sz, sa[:, None]]), mu, ratio


def _damped_newton_step(theta, g, H, ll_old, loglik, max_damping: int = 20):
    """(step, step length, new log likelihood) for a safeguarded Newton ascent: solve (−H + λI) step = g with
    λ = 0 first and then rising (Levenberg damping, scaled by the largest |H_jj|), accepting the first
    direction that goes uphill (g·step > 0) and, after halving the step at most 30 times, raises the log
    likelihood. Returns (None, 0, ll_old) if no damping finds an increase. By hand: ll = −(x − 1)², x = 0,
    g = 2, H = −2: the plain Newton step 1 lands on the maximum."""
    scale = max(1.0, float(np.max(np.abs(np.diag(H)))))
    n = len(theta)
    for i in range(max_damping):
        lam = 0.0 if i == 0 else scale * 10.0 ** (i - 8)
        step = np.linalg.lstsq(-H + lam * np.eye(n), g, rcond=None)[0]
        if not np.all(np.isfinite(step)) or float(g @ step) <= 0:
            continue
        s = 1.0
        for _ in range(30):
            try:
                ll_new = loglik(theta + s * step)
            except ValueError:
                ll_new = -np.inf
            if ll_new > ll_old:
                return step, s, ll_new
            s /= 2
    return None, 0.0, ll_old


LOG_A_BOUND = 15.0  # log of the gamma shape: var(u) = e^-15 is no place heterogeneity (held at the bound)


def fit_re(y, X, offset, place, year, names, tol: float = 1e-9, max_iter: int = 100) -> REFit:
    """Poisson-gamma place random effects with state × year fixed effects (the negative binomial panel model
    of Hausman, Hall & Griliches 1984; D-024's fallback, protocol §5.7), by Newton's method on the closed-
    form marginal likelihood (`_re_parts`) with a finite-difference Hessian of the analytic score. Keeps
    places whose counts are all zero (they inform a and the year effects). Regressors collinear with the
    year effects and intercept are dropped. log a is held at `LOG_A_BOUND` when the data show no place
    heterogeneity (Poisson counts), and left out of the step test there. Fails loudly (`EstimationError`) on
    non-convergence or a coefficient beyond ±20."""
    from lotline.model.estimate_adu import COEF_BOUND, EstimationError, _independent_columns

    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float).reshape(len(y), -1)
    off = np.asarray(offset, dtype=float)
    places, cl = np.unique(np.asarray(place), return_inverse=True)
    years, yi = np.unique(np.asarray(year), return_inverse=True)
    G = np.eye(len(years))[yi][:, 1:]
    base = np.hstack([np.ones((len(y), 1)), G])
    names = list(names)
    Z = np.hstack([X, base])
    dropped = []
    if np.linalg.matrix_rank(Z) < Z.shape[1]:
        keep_cols = _independent_columns(Z, len(names))
        dropped = [f"{n} (collinear with year effects)" for i, n in enumerate(names) if i not in keep_cols]
        names = [names[i] for i in keep_cols]
        Z = np.hstack([X[:, keep_cols], base])
    k = len(names)
    theta = np.zeros(Z.shape[1] + 1)
    theta[k] = np.log(max(y.sum(), 1e-8) / np.exp(off).sum())
    n_cl = len(places)

    def grad(t):
        return _re_parts(t, Z, y, off, cl, n_cl)[1].sum(axis=0)

    ll, converged, it = -np.inf, False, 0
    for it in range(1, max_iter + 1):  # noqa: B007 (reported on the fit)
        try:
            g = grad(theta)
        except ValueError as err:  # |η − offset| > 30 at the current step
            raise EstimationError(f"random-effects fit diverged at iteration {it}") from err
        H = np.empty((len(theta), len(theta)))
        for j in range(len(theta)):
            h = 1e-5 * max(1.0, abs(theta[j]))
            tp, tm = theta.copy(), theta.copy()
            tp[j] += h
            tm[j] -= h
            try:
                H[:, j] = (grad(tp) - grad(tm)) / (2 * h)
            except ValueError as err:
                raise EstimationError(f"random-effects fit diverged at iteration {it}") from err
        H = (H + H.T) / 2
        ll_old = _re_parts(theta, Z, y, off, cl, n_cl)[0]
        step, s, ll_new = _damped_newton_step(
            theta, g, H, ll_old, lambda t: _re_parts(t, Z, y, off, cl, n_cl)[0]
        )
        if step is None:  # no direction raises the likelihood: at a maximum to numerical precision
            converged = abs(float(g @ np.linalg.pinv(-H) @ g)) < 1e-6 * (abs(ll_old) + 1)
            ll = ll_old
            break
        theta = theta + s * step
        at_bound = theta[-1] >= LOG_A_BOUND  # no place heterogeneity left (Poisson counts): hold log a there
        theta[-1] = min(theta[-1], LOG_A_BOUND)
        ll = _re_parts(theta, Z, y, off, cl, n_cl)[0] if at_bound else ll_new
        moved = np.abs(s * step)[:-1] if at_bound else np.abs(s * step)
        if np.max(moved) < tol * 1e3 or abs(ll - ll_old) < tol * (abs(ll) + 1):
            converged = True
            break
    if not converged:
        raise EstimationError(f"random-effects fit did not converge in {it} iterations")
    _, S, mu, ratio = _re_parts(theta, Z, y, off, cl, n_cl)
    info = -H
    coef = theta[:k]
    if not np.all(np.isfinite(theta)) or np.max(np.abs(coef), initial=0) > COEF_BOUND:
        raise EstimationError(f"random-effects coefficients beyond ±{COEF_BOUND} or non-finite")
    return REFit(
        names=names,
        coef=coef,
        params=theta,
        info=info,
        scores=S,
        mu=mu * ratio[cl],
        keep=np.ones(len(y), dtype=bool),
        y=y,
        cluster=np.asarray(place),
        alpha=theta[k] + np.log(ratio),
        gamma=np.r_[0.0, theta[k + 1 : -1]],
        years=years,
        a=float(np.exp(theta[-1])),
        iterations=it,
        converged=True,
        dropped_columns=dropped,
    )


def bootstrap(est_, draws: int = 999, seed: int = 0) -> pd.DataFrame:
    """Wild cluster score bootstrap by place (Webb weights): `estimate_adu.score_bootstrap` for PPML (CR2
    scores), the same one-step draw b* = b̂ + I⁻¹ Σ_g w_g S_g with the random-effects scores otherwise."""
    from lotline.model.estimate_adu import COEF_BOUND, WEBB, EstimationError, aggregate, score_bootstrap

    fit = est_.fit
    if isinstance(fit, NBFit):
        from lotline.model import pooled_adu as pa

        raw = pa.score_bootstrap(fit.pooled, draws=draws, seed=seed).rename(columns=NB_NAMES)
        rows = []
        for _, r in raw.iterrows():
            coef = r[fit.names].to_numpy(dtype=float)
            rows.append({**dict(zip(fit.names, coef, strict=True)), **aggregate(est_, coef)})
        return pd.DataFrame(rows)
    if not isinstance(fit, REFit):
        return score_bootstrap(est_, draws=draws, seed=seed)
    rng = np.random.default_rng(seed)
    I_inv = np.linalg.pinv(fit.info)
    k = len(fit.names)
    rows = []
    for _ in range(draws):
        b = fit.params + I_inv @ (rng.choice(WEBB, size=fit.scores.shape[0]) @ fit.scores)
        coef = b[:k]
        if not np.all(np.isfinite(coef)) or np.max(np.abs(coef), initial=0) > COEF_BOUND:
            raise EstimationError("bootstrap draw diverged (non-finite or beyond the coefficient bound)")
        rows.append({**dict(zip(fit.names, coef, strict=True)), **aggregate(est_, coef)})
    return pd.DataFrame(rows)


def summary(est_, draws: int = 999, seed: int = 0, level: float = 0.90) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(summary table with 90% basic bootstrap intervals, bootstrap draws) for one fit."""
    from lotline.model.estimate_adu import summarize

    boot = bootstrap(est_, draws=draws, seed=seed)
    return summarize(est_, boot, level=level), boot


def overall(est_) -> float:
    from lotline.model.estimate_adu import aggregate

    return aggregate(est_).get("att", np.nan)


# ---------------------------------------------------------------------------------------------------------
# Randomization inference (D-024): treatment packages reassigned within state and size band
# ---------------------------------------------------------------------------------------------------------

PACKAGE = ("T", "dose", "p_by_right", *MODIFIERS)


def reassign(panel: pd.DataFrame, rng: np.random.Generator, pool: set | None = None) -> pd.DataFrame:
    """One reassignment: each treated place's package (adoption year, its calendar-year dose path and its
    modifiers) moves to a place drawn without replacement from the treated and untreated places in the same
    state and size band (`pool`: the places eligible to receive one, default all). Places not drawn get no
    treatment."""
    p = panel.copy()
    places = p.drop_duplicates("place")[["place", "state", "band", "T"]]
    if pool is not None:
        places = places[places["place"].isin(pool) | places["T"].notna()]
    treated = places[places["T"].notna()]
    target: dict = {}
    for (st, band), grp in treated.groupby(["state", "band"]):
        cands = places[(places["state"] == st) & (places["band"] == band)]["place"].to_numpy()
        chosen = rng.choice(cands, size=len(grp), replace=False)
        for src, dst in zip(rng.permutation(grp["place"].to_numpy()), chosen, strict=True):
            target[dst] = src
    by_place_year = panel.set_index(["place", "year"])[list(PACKAGE)]
    for c in PACKAGE:
        p[c] = np.nan if c != "dose" else 0.0
    p["p_by_right"] = 0.0
    for dst, src in target.items():
        rows = p["place"] == dst
        vals = by_place_year.loc[src].reindex(p.loc[rows, "year"].to_numpy())
        for c in PACKAGE:
            p.loc[rows, c] = vals[c].to_numpy()
    return p


def _ri_one(args):
    panel, seed, i, pool, method, kw = args
    from lotline.model.estimate_adu import EstimationError

    try:
        return overall(
            estimate(reassign(panel, np.random.default_rng([seed, i]), pool=pool), method=method, **kw)
        )
    except (EstimationError, np.linalg.LinAlgError, ValueError):  # a fit that cannot be estimated
        return None


def randomization_inference(panel, permutations=999, seed=0, method="ppml", workers=1, **kw):
    """(overall effect, p, permuted effects, failed): p = share of reassignments (`reassign`; receiving places
    are those with any 2-4 unit home, so a fixed-effects fit can see them) whose |overall effect| is at least
    the observed one. Reassignment i uses its own generator (seed, i), so results don't depend on `workers`
    (processes). A reassignment the fit cannot estimate is skipped and counted in `failed`."""
    att = overall(estimate(panel, method=method, **kw))
    pos = set(panel.loc[panel["y"].fillna(0) > 0, "place"])
    jobs = [(panel, seed, i, pos, method, kw) for i in range(permutations)]
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=workers) as ex:
            res = list(ex.map(_ri_one, jobs, chunksize=max(1, permutations // (4 * workers))))
    else:
        res = [_ri_one(j) for j in jobs]
    failed = sum(r is None for r in res)
    dist = np.array([r for r in res if r is not None], dtype=float)
    dist = dist[~np.isnan(dist)]
    p = float(np.mean(np.abs(dist) >= abs(att))) if len(dist) else np.nan
    return att, p, dist, failed


def added_homes(est_, boot: pd.DataFrame | None = None, level: float = 0.90) -> pd.DataFrame:
    """Homes the rules added in the treated places' post-adoption years: fitted mean minus the mean with the
    treatment terms (β, θ, ρ) switched off, per place, and per 1,000 eligible parcels a year. Interval:
    each bootstrap draw's treatment terms applied to the untreated means, μ0 (e^(X b*) − 1), with place and
    year effects held at the estimate. Columns: place, name, years, added, low, high,
    per_1000_parcels_year."""
    fit, d, p = est_.fit, est_.design, est_.panel
    X = d.X[fit.keep][:, [d.names.index(n) for n in fit.names]]
    treat = [i for i, n in enumerate(fit.names) if n.startswith(("beta_", "theta_", "rho"))]
    kp = p[fit.keep].reset_index(drop=True)
    post = (kp["T"].notna() & (kp["year"] >= kp["T"])).to_numpy()
    lin = X[:, treat] @ fit.coef[treat]
    mu0 = fit.mu * np.exp(-lin)
    rows = []
    a = (1 - level) / 2
    draws = None
    if boot is not None:
        B = boot[[fit.names[i] for i in treat]].to_numpy()
        draws = mu0[None, :] * (np.exp(B @ X[:, treat].T) - 1.0)
    for place, g in kp[post].groupby("place"):
        on = post & (kp["place"] == place).to_numpy()
        add = float(np.sum(fit.mu[on] - mu0[on]))
        lo = hi = np.nan
        if draws is not None:
            tot = draws[:, on].sum(axis=1)
            dev_lo, dev_hi = np.quantile(tot - add, [a, 1 - a])
            lo, hi = add - dev_hi, add - dev_lo
        n = int(on.sum())
        name = g["name"].iloc[0] if "name" in g else place
        per = add / float(g["eligible"].mean()) / n * 1000
        rows.append({"place": place, "name": name, "years": n, "added": add, "low": lo, "high": hi,
                     "per_1000_parcels_year": per})  # fmt: skip
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Checks (D-024, all reported; pass rules fixed in the entry)
# ---------------------------------------------------------------------------------------------------------


def _interval(est_, draws, seed, term="att"):
    s, _ = summary(est_, draws=draws, seed=seed)
    s = s.set_index("term")
    return s.loc[term, "estimate"], s.loc[term, "low"], s.loc[term, "high"]


def _safe(name, fn):
    """Run one check; a fit that fails becomes a failed check with the reason, never a crash."""
    from lotline.model.estimate_adu import EstimationError

    try:
        return fn()
    except (EstimationError, np.linalg.LinAlgError, KeyError, ValueError) as err:
        return {"check": name, "pass": False, "note": f"could not be estimated: {err}"}


def check_leads(panel, draws=999, seed=0, method="ppml", **kw) -> dict:
    """1. Leads k = −3…−1 jointly 0 at the 10% level (pass: bootstrap Wald p >= 0.10)."""
    from lotline.model.estimate_adu import joint_wald

    def run():
        e = estimate(panel, method=method, leads=LEADS, **kw)
        W, p = joint_wald(bootstrap(e, draws=draws, seed=seed), e, [f"lead_{-k}" for k in LEADS])
        return {"check": "pre-trend leads", "statistic": W, "p": p, "pass": bool(p >= 0.10)}

    return _safe("pre-trend leads", run)


def check_placebo_dates(panel, shift=2, draws=999, seed=0, method="ppml", **kw) -> dict:
    """2. Adoption moved `shift` years early, pre-adoption years only, full dose: 90% interval contains 0."""
    name = f"placebo dates (−{shift} years)"

    def run():
        p = panel[panel["T"].isna() | (panel["year"] < panel["T"])].copy()
        p["T"] = p["T"] - shift
        p.loc[p["T"].notna(), "dose"] = 1.0
        est_, lo, hi = _interval(estimate(p, method=method, **kw), draws, seed)
        return {"check": name, "estimate": est_, "low": lo, "high": hi, "pass": bool(lo <= 0 <= hi)}

    return _safe(name, run)


def check_outcome(panel, column, name, draws=999, seed=0, rule=True, method="ppml", **kw) -> dict:
    """3./4. Another outcome (5+ unit homes: placebo, pass if the 90% interval contains 0; 1-unit homes:
    substitution, reported with no pass rule)."""

    def run():
        p = panel.assign(y=panel[column].round())
        est_, lo, hi = _interval(estimate(p, method=method, **kw), draws, seed)
        return {
            "check": name,
            "estimate": est_,
            "low": lo,
            "high": hi,
            "pass": bool(lo <= 0 <= hi) if rule else None,
        }

    return _safe(name, run)


def check_inside(panel, main: pd.DataFrame, name, terms=("att",), draws=999, seed=0, method="ppml", **kw):
    """5./7. A re-fit on `panel` (a subsample): every listed term's estimate inside the main 90% interval."""

    def run():
        s, _ = summary(estimate(panel, method=method, **kw), draws=draws, seed=seed)
        s, m = s.set_index("term"), main.set_index("term")
        got = {t: float(s.loc[t, "estimate"]) for t in terms if t in s.index}
        outside = [
            t for t, v in got.items() if t in m.index and not (m.loc[t, "low"] <= v <= m.loc[t, "high"])
        ]
        return {
            "check": name,
            **{f"estimate_{t}": v for t, v in got.items()},
            "outside": outside,
            "pass": not outside,
        }

    return _safe(name, run)


def check_leave_one_out(panel, main: pd.DataFrame, groups: Mapping[str, Sequence[str]], method="ppml", **kw):
    """6. Leaving out each treated place (and each named group): the overall effect stays inside the main
    90% interval."""
    m = main.set_index("term").loc["att"]
    moved, rows = [], []
    for label, places in groups.items():
        try:
            att = overall(estimate(panel[~panel["place"].isin(places)], method=method, **kw))
        except Exception as err:  # noqa: BLE001 (reported, not raised)
            att = np.nan
            rows.append({"left_out": label, "att": np.nan, "note": str(err)})
            moved.append(label)
            continue
        rows.append({"left_out": label, "att": att})
        if not (m["low"] <= att <= m["high"]):
            moved.append(label)
    return {"check": "leave one treated place out", "moved": moved, "pass": not moved}, pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------
# Out-of-sample tests (D-024 A and B)
# ---------------------------------------------------------------------------------------------------------


def transport_predict(est_, boot, target: pd.DataFrame, draws=4000, seed=0, widening=1.0) -> pd.DataFrame:
    """Predicted 2-4 unit homes per post-adoption year for treated places left out of the fit.

    Per target place and draw: η_t = α + γ_{s,t} + log(eligible) + β_b(t) × dose + Σ θ_m z_m + ρ (r − r̄) +
    δ adu, with coefficient draws from the bootstrap, γ from the fit (the target's state keeps its year
    effects from its comparison places), z_m on the fit's treated-place scale, and α from the place's own
    pre-adoption years given γ and the offset, with its sampling error (variance ≈ (1 + κ·mean) / pre-period
    homes); a place with none draws α from the fitted places. Places outside the fitted modifier range get
    log-normal noise with sd = `widening` × summed log distance outside the range. Counts are Poisson-gamma
    with the fit's overdispersion κ. Returns place, name, year, observed, mean, p05, p10, p90, p95,
    outside_range, with a 'total' row per place.
    """
    from lotline.model.estimate_adu import MAX_YEARLY_RATE, EstimationError, modifier_scale, overdispersion

    rng = np.random.default_rng(seed)
    f, fp = est_.fit, est_.panel
    gam = dict(zip(f.years, f.gamma, strict=True))
    kappa = overdispersion(est_)
    treated = fp[fp["T"].notna()].drop_duplicates("place")
    mods = [n.replace("theta_", "") for n in f.names if n.startswith("theta_")]
    scale = {m: modifier_scale(treated, m) for m in mods}
    span = {m: (float(treated[m].min()), float(treated[m].max())) for m in mods}
    rate_ref = float(fp["rate"].mean())
    coefs = {n: boot[n].to_numpy() for n in boot.columns}
    idx = rng.integers(0, len(boot), size=draws)
    out = []
    for place, d in target[target["y"].notna()].groupby("place", sort=False):
        d = d.sort_values("year").reset_index(drop=True)
        T = d["T"].iloc[0]
        e = d["year"].to_numpy() - T
        post = e >= 0
        g = np.array([gam.get(c, np.nan) for c in year_code(d)])
        if np.isnan(g).any():
            raise EstimationError(f"transport for {place}: no year effect for some of its state-years")
        off = np.log(d["eligible"].to_numpy(dtype=float))
        dist = 0.0
        for m in mods:
            x, (lo, hi) = d[m].iloc[0], span[m]
            if np.isnan(x):
                continue
            xv, lov, hiv = (
                (x, lo, hi)
                if m == "log_value"
                else (np.log(max(x, 1e-12)), np.log(max(lo, 1e-12)), np.log(max(hi, 1e-12)))
            )
            dist += max(0.0, lov - xv, xv - hiv)
        pre = ~post
        y_pre = float(d.loc[pre, "y"].sum())
        if y_pre > 0:
            a_hat = np.log(y_pre / np.sum(np.exp(off[pre] + g[pre] + _delta(coefs, None, d.loc[pre, "adu"]))))
            a_draw = a_hat + rng.normal(0.0, np.sqrt((1 + kappa * y_pre / pre.sum()) / y_pre), size=draws)
        else:
            a_draw = rng.choice(np.asarray(f.alpha), size=draws)
        eta = a_draw[:, None] + g[None, :] + off[None, :]
        for (lo, hi), name in zip(EVENT_BINS, BIN_NAMES, strict=True):
            on = post & (e >= lo) & (e <= (np.inf if hi is None else hi))
            if name in coefs:
                eta[:, on] += coefs[name][idx][:, None] * d.loc[on, "dose"].to_numpy()[None, :]
        for m in mods:
            c, sd = scale[m]
            z = 0.0 if np.isnan(d[m].iloc[0]) else (d[m].iloc[0] - c) / sd
            eta[:, post] += coefs[f"theta_{m}"][idx][:, None] * z
        if "rho" in coefs:
            eta[:, post] += coefs["rho"][idx][:, None] * (d.loc[post, "rate"].to_numpy() - rate_ref)[None, :]
        eta += _delta(coefs, idx, d["adu"])
        if not np.all(np.isfinite(eta)) or np.max(eta - off[None, :]) > np.log(MAX_YEARLY_RATE):
            raise EstimationError(
                f"transport for {place}: predicted rate beyond {MAX_YEARLY_RATE:.0%} a year"
            )
        s = widening * dist
        mu = np.exp(eta + s * rng.standard_normal((draws, 1)) - s**2 / 2)
        lam = rng.gamma(1 / kappa, mu * kappa) if kappa > 0 else mu
        sims = rng.poisson(lam)[:, post]
        dpost = d[post]
        for t, r in enumerate(dpost.itertuples()):
            col = sims[:, t]
            out.append(_pred_row(place, r.name, int(r.year), float(r.y), col, dist))
        out.append(
            _pred_row(place, d["name"].iloc[0], "total", float(dpost["y"].sum()), sims.sum(axis=1), dist)
        )
    return pd.DataFrame(out)


def _delta(coefs, idx, adu: pd.Series):
    if "delta" not in coefs:
        return 0.0
    v = adu.to_numpy(dtype=float)
    if idx is None:
        return float(np.median(coefs["delta"])) * v
    return coefs["delta"][idx][:, None] * v[None, :]


def _pred_row(place, name, year, observed, col, dist) -> dict:
    q = np.quantile(col, [0.05, 0.10, 0.90, 0.95])
    return {"place": place, "name": name, "year": year, "observed": observed, "mean": float(col.mean()),
            "p05": q[0], "p10": q[1], "p90": q[2], "p95": q[3], "outside_range": dist}  # fmt: skip


# ---------------------------------------------------------------------------------------------------------
# Robustness: the Borusyak imputation estimator
# ---------------------------------------------------------------------------------------------------------


def imputation_effects(panel: pd.DataFrame) -> dict[str, float]:
    """Borusyak, Jaravel & Spiess (2024) imputation, in Poisson form: fit place and state × year effects (and
    δ) on untreated place-years only (never treated, or before adoption), impute each treated place-year's
    untreated mean μ0, and report log(Σ y / Σ μ0) per event-time bin and overall (same scale as β and att;
    the dose is not used). Treated places without untreated years with homes are left out."""
    from lotline.model.estimate_adu import ppml

    p = panel[panel["y"].notna()].reset_index(drop=True)
    e = p["year"] - p["T"]
    untreated = (p["T"].isna() | (e < 0)).to_numpy()
    codes = year_code(p)
    adu_x = p[["adu"]].to_numpy(dtype=float)
    off = np.log(p["eligible"].to_numpy(dtype=float))
    fit = ppml(p.loc[untreated, "y"], adu_x[untreated], off[untreated], p.loc[untreated, "place"],
               codes[untreated], ["delta"])  # fmt: skip
    alpha = dict(zip(np.unique(p.loc[untreated, "place"][fit.keep]), fit.alpha, strict=True))
    gam = dict(zip(fit.years, fit.gamma, strict=True))
    d = fit.coef_of("delta") if "delta" in fit.names else 0.0
    tr = p[~untreated].copy()
    tr["a"] = tr["place"].map(alpha)
    tr["g"] = [gam.get(c, np.nan) for c in codes[~untreated]]
    tr = tr.dropna(subset=["a", "g"])
    tr["mu0"] = np.exp(np.log(tr["eligible"]) + tr["a"] + tr["g"] + d * tr["adu"])
    tr["bin"] = (tr["year"] - tr["T"]).map(event_bin)
    bin_name = dict(zip(("k0_1", "k2_3", "k4p"), BIN_NAMES, strict=True))
    out = {bin_name[b]: float(np.log(g["y"].sum() / g["mu0"].sum())) for b, g in tr.groupby("bin")}
    out["att"] = float(np.log(tr["y"].sum() / tr["mu0"].sum())) if len(tr) else np.nan
    out["places"] = int(tr["place"].nunique())
    return out
