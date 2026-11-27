"""Missing-middle D-024 panel: places and years in the four reform states, rule dose and adoption year,
BPS and local counts, pre-adoption modifiers, the ADU prior, `build_panel` and the D-024 smoke counts.

Part of `estimate_mm`, split by method step (modularity step 3); `estimate_mm` re-exports every name.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from lotline.calibrate.adu.estimate_adu import nearest_roll
from lotline.model.mm_rates import _mm_coverage, blank_shares, plex_price_to_cost, rule_dose

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
    July; NaN if none by `last_year`. `rows` come through `rule_tags.apply` (as in `build_panel`), so a
    `[predates]` rule gives T = 1990, before any panel year."""
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
    drop_tags: Sequence[str] = (),
    include: Sequence[str] = (),
) -> MMPanel:
    """The D-024 panel from processed, holdout-filtered tables (see the module docstring for columns).

    `source`: 'bps' (main) or a local permit source (e.g. 'metc_residential_permits'), whose places are the
    ones it covers. `reforms`: state -> coded reforms (default: config/reforms); date tags are read by
    `rule_tags` (`[predates]` rules in force before the panel). `drop_tags`: the tag sensitivities
    ('earliest_known', 'unconfirmed') whose in-panel events leave their place out. Excluded places are listed
    by reason in `excluded`: holdout, dropped by a tag sensitivity, under the population floor, no outcome
    rows, no eligible parcels. `include`: holdout places to keep after their test was released (D-100 adds St.
    Paul after D-098); a place whose holdout is still blind is refused.
    """
    from lotline.build import eligible as eligible_rule
    from lotline.calibrate.adu import estimate_adu
    from lotline.config import load_params, load_state
    from lotline.model import hazard, money, rule_tags
    from lotline.model.scenarios import adu
    from lotline.validation import holdout as hold

    include = set(include)
    for st in states:
        blind = {h.geoid for h in hold.still_blind(hold.holdouts_for(st))}
        if include & blind:
            raise ValueError(f"cannot include places whose holdout is still blind: {sorted(include & blind)}")

    pm = {k: v.value for k, v in load_params("mm").items()}
    pa_ = {k: v.value for k, v in load_params("adu").items()}
    years = list(
        range(int(pm["mm_panel_first_year"]), int(pm["mm_panel_last_year"]) + 1) if years is None else years
    )
    min_pop = pm["mm_estimation_min_population"] if min_population is None else min_population
    permit_grade = pm["mm_dose_grade_permit"]
    if reforms is None:
        reforms = {st: adu.load_reforms(st) for st in adu.REFORM_STATES}
    reforms = {st: rule_tags.apply(r) for st, r in reforms.items()}
    every = pd.concat([r.assign(state=st) for st, r in reforms.items()], ignore_index=True)
    blanks = blank_shares(every[every["status"] == "in_force"])
    adu_grades = (pa_["adu_dose_grade_permit"], pa_["adu_dose_grade_owner"], pa_["adu_dose_grade_by_right"])
    fcounts = adu.field_restrict_counts(every, pd.Timestamp(f"{max(years)}-12-31"))
    edges = (pa_["adu_rule_band_small_max_pop"], pa_["adu_rule_band_mid_max_pop"])

    rows, notes = [], []
    excluded: dict[str, list] = {
        "holdout": [],
        "dropped by tag sensitivity": [],
        "small": [],
        "no outcome rows": [],
        "no eligible parcels": [],
    }
    for st in states:
        fips = load_state(st).fips
        ref = reforms.get(st, every.iloc[0:0])
        mm_rows = ref[(ref["theme"] == "missing_middle") & (ref["status"] == "in_force")]
        dropped = rule_tags.dropped_places(mm_rows, years, drop_tags)
        juris = store.read(st, "jurisdictions")
        held = _excluded_holdout(juris) - include
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
            if {g, fips} & dropped:
                excluded["dropped by tag sensitivity"].append(g)
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
