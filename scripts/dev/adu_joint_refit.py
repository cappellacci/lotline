#!/usr/bin/env python3
"""The five-state ADU joint refit, run once as D-079 pre-registers it (D-074, D-075, D-078, D-080, D-081).

    uv run python scripts/dev/adu_joint_refit.py --inputs-only --out reports/adu-joint-refit-2026-11
    uv run python scripts/dev/adu_joint_refit.py --out reports/adu-joint-refit-2026-11 --workers 6

`--inputs-only` builds the fit set and writes it with the in-window event list (D-079: "the event list is
written to the report before the fit is run"); it fits nothing. Without it the script runs everything once:

1. **Fit set** (`fit_set`): every place with a coded ADU rule in force, eligible lots and ADU-flagged permits,
   2016-2025 (D-079's window; Austin to 2023 and San Antonio from 2021, the years its permit file covers, as
   in D-039 to D-053). A place new since D-053 enters only if one record-level permit source holds 1,000+ of
   its permits (D-074 step 2). St. Paul never enters (V5 is blind; the store's holdout filter also hides it).
   Counts are each source's ADU permits × its central k (D-078, D-081), D-041's count rules, county
   remainders on permit-level lots (#375), 37119 on its parcel roll (D-080), legalizations already out of
   the counts (D-080 item 2, the parser since #376), sources marked `fit: false` dropped (Dallas, D-081 4).
2. **Both forms** on all five states: Form A (D-048, `calibrate_adu.fit3`) and Form B (`joint_refit`), with
   g estimated only if `joint_refit.g_identified` holds for the event list.
3. **Data-tier test** (D-075 §5, D-079): each state held out, both forms refitted on the other four, the
   held-out state's fit places predicted 2021-2024 at tiers 0, 1 and 2, leaving out the tier-2 city at every
   tier. Tier 0: ACS lots, every local rule borrowed by size band from the other four states' coded places,
   the state's own ADU law rows, the state effect from its prior. Tier 1: the 20 largest places' own coded
   local rules. Tier 2: the largest fit place's counts update the state effect. Scores: inside P10-P90,
   observed ÷ P50, CRPS, log score, and each tier's gain; D-075's claim rule per form.
4. **Tests A-C** (D-074 §3, state by state): A, each new place predicted 2021-2024 from a fit without it; B,
   the roll check (Wake towns without Raleigh, 2020-2023; Franklin County towns, 2020-2024); C, the scenario's
   no-reform median a year against counted ADUs a year 2023-2025 in every counted place (Form A: the only form
   with a scenario engine; C is reported and left out of both forms' counts in the decision rule).
5. **D-079's decision rule**, the tier-1 held-out log score per place (D-049) as the tie-breaker.
6. **Sensitivities** (reported, never used to choose): the field rows' k at their 5th and 95th percentiles
   (one shared z, D-078 §5), and the low-recall rows left out (D-078 §3; Asheville before 2022). Fort Worth's
   no-kitchen count (D-081 item 2) is reported beside its central count.

Reads the holdout-filtered processed tables only. The whole run sits inside `offline_build`, which refuses
every network request, so nothing is downloaded (cached Census shares and Fort Worth's raw snapshot are read
from the data directory). Writes only to `--out`.
"""

from __future__ import annotations

import argparse
import dataclasses
import functools
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.build import eligible as eligible_rule
from lotline.config import load_params, load_state
from lotline.io import DataStore, offline
from lotline.model import calibrate_adu as cal
from lotline.model import estimate_adu
from lotline.model import joint_refit as jr
from lotline.model import score as sc
from lotline.model import undercount as uc
from lotline.model.scenarios import adu

STATES = ("MN", "NC", "OH", "TX", "OR")
WINDOW = range(2016, 2026)
TARGET_YEARS = range(2021, 2025)  # D-075: ADU permits a year over 2021-2024
TIER2_LAST = 2024  # the tier-2 city's counts used to update: its fit years through the target window
ST_PAUL, ROCHESTER = "2758000", "2754880"
MIN_PERMITS = 1000  # D-074 step 2
TOP_PLACES = 20  # D-075 tier 1
SEED = 20261111
DRAWS = 20_000
Z_FIELD = 1.645  # the field rows' 5th and 95th percentiles (D-079)
YEAR_LIMITS = {
    "4805000": (2016, 2023),
    "4865000": (2021, 2025),
}  # Austin's R-102 flag stops; SA's file starts
# D-053's fit set (D-039's four states plus Portland and Bend): the places that are not "new" for test A.
D053 = {
    "TX": {"4805000", "4865000"},
    "NC": {"3743480", "3741960", "3714700", "3733120", "3728000", "37063"},
    "OH": {"3915000"},
    "OR": {"4159000", "4105800"},
}
ROLLS = Path(__file__).resolve().parents[2] / "config" / "validation" / "adu_roll_counts.csv"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------------------------------------
# The fit set
# ---------------------------------------------------------------------------------------------------------


def state_law(rows: pd.DataFrame) -> pd.Series:
    """True for a state ADU law's own rows: NC's S.L. 2026-59 rows and Oregon's SB 1051 / HB 2001 rows
    (generated per city, D-068). Every other ADU row is a local rule."""
    comp = rows["component"].fillna("").astype(str)
    return rows["reform_id"].astype(str).str.startswith("NC-SL") | comp.str.match(r"^(SB 1051|HB 2001)")


def d053_places(st: str) -> set[str]:
    if st == "MN":  # every coded MN place but St. Paul (D-039's MN set) ...
        r = adu.load_reforms("MN")
        # ... less Rochester, whose permit source came after D-053 (#367): D-053's MN fit held 42 places
        # (reports/adu-d053-fit/run-2026-11-06-log.txt), and Rochester is the 43rd
        return set(r.loc[r["theme"] == "adu", "jurisdiction_geoid"]) - {ST_PAUL, ROCHESTER}
    return D053.get(st, set())


def candidates(st: str, store) -> tuple[list[str], set[str]]:
    """(candidate GEOIDs, D-053 places): D-053's places plus every place with 1,000+ permits in one
    ADU-flagging, fit-eligible permit source."""
    p = cal.drop_sources(store.read(st, "permits"), [(s, None, None) for s in uc.out_of_fit()])
    flagging = p.loc[adu._is_adu(p), "source"].unique()
    q = p[p["source"].isin(flagging) & p["jurisdiction_geoid"].notna()]
    n = q.groupby(["jurisdiction_geoid", "source"]).size()
    big = {g for (g, _), v in n.items() if v >= MIN_PERMITS}
    old = d053_places(st)
    return sorted((big | old) - {ST_PAUL}), old


def limit_years(pl: cal.PlaceData) -> cal.PlaceData | None:
    lo, hi = YEAR_LIMITS.get(pl.geoid, (min(WINDOW), max(WINDOW)))
    return jr.subset_years(pl, range(lo, hi + 1))


def fit_set(st: str, store, undercount="table", drop=()) -> tuple[list[cal.PlaceData], set[str]]:
    geoids, old = candidates(st, store)
    pls = cal.place_data(
        st, store, geoids, WINDOW, counts=cal.count_settings(), undercount=undercount, drop=drop
    )
    pls = [q for q in (limit_years(pl) for pl in pls) if q is not None and q.geoid != ST_PAUL]
    return pls, {pl.geoid for pl in pls if pl.geoid not in old}


def all_places(store, undercount="table", drop=()) -> tuple[list[cal.PlaceData], set[str]]:
    out, new = [], set()
    for st in STATES:
        pls, nw = fit_set(st, store, undercount, drop)
        out += pls
        new |= nw
    return out, new


# ---------------------------------------------------------------------------------------------------------
# Tier inputs
# ---------------------------------------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _central() -> dict:
    return {k: v.value for k, v in load_params("adu").items()}


@functools.lru_cache(maxsize=1)
def _field_counts() -> pd.DataFrame:
    every = pd.concat([_reforms(s) for s in adu.REFORM_STATES], ignore_index=True)
    return adu.field_restrict_counts(every, pd.Timestamp.today().normalize())  # as place_years


def acs_lots(st: str, store, pl: cal.PlaceData) -> np.ndarray:
    """Tier 0's lots: ACS one-unit detached homes (`eligible.from_acs`, remainders permit-level) each year,
    the newest vintage <= the year, else the earliest later one (as `place_years`)."""
    juris = store.read(st, "jurisdictions")
    rows = estimate_adu.permit_acs_rows(st, store, juris)
    rows = rows[(rows["theme"] == "adu") & (rows["jurisdiction_geoid"] == pl.geoid)]
    if rows.empty:
        raise ValueError(f"{pl.name}: no ACS lots")
    out = []
    for y in pl.years:
        r = rows.assign(after=rows["year"] > y, gap=(rows["year"] - y).abs()).sort_values(["after", "gap"])
        out.append(float(r["eligible_parcels"].iloc[0]))
    return np.asarray(out)


@functools.cache
def _reforms(st: str) -> pd.DataFrame:
    return adu.load_reforms(st).assign(state=st)


def _rules_on(st: str, store, rows: pd.DataFrame, geoids, date: pd.Timestamp) -> pd.DataFrame:
    """`current_rules` for `geoids` from `rows` on `date`, (state field probabilities, coverage)."""
    fp = adu.field_probabilities(_field_counts(), st, int(_central()["adu_rule_min_coded"]))
    cm = _coverage(st, store)
    return adu.current_rules(rows, list(geoids), load_state(st).fips, date, fp, cm)


_COV: dict[str, dict] = {}


def _coverage(st: str, store) -> dict:
    if st not in _COV:
        cm = adu.coverage_map(st, store, _reforms(st), _central())
        _COV[st] = dict(zip(cm.reform_id, cm.coverage, strict=True))
    return _COV[st]


def donors(held: str, store, year: int) -> pd.DataFrame:
    """The other four states' coded places on 1 July of `year`: their local rules' type probabilities
    (coverage in), population and rule age (D-068's coded places, state laws left out)."""
    out = []
    for st in STATES:
        if st == held:
            continue
        r = _reforms(st)
        r = r[r["theme"] == "adu"]
        local = r[~state_law(r)]
        geoids = sorted(g for g in local["jurisdiction_geoid"].unique() if len(g) > 2)
        cr = _rules_on(st, store, local, geoids, pd.Timestamp(f"{year}-07-01"))
        cr = cr[cr["rule_class"] != "unknown"]
        pop = store.read(st, "jurisdictions").set_index("geoid")["pop_2020"]
        out.append(cr.assign(state=st, population=cr["geoid"].map(pop).astype(float)))
    return pd.concat(out, ignore_index=True).dropna(subset=["population"])


def tier_inputs(held: str, store, places: list[cal.PlaceData]) -> dict:
    """For each held-out place: tier-0 and tier-1 versions, the 20 largest places, and the tier-2 city."""
    c = _central()
    edges = (c["adu_rule_band_small_max_pop"], c["adu_rule_band_mid_max_pop"])
    min_count = int(c["adu_rule_min_coded"])
    years = sorted({int(y) for pl in places for y in pl.years})
    bands = {y: jr.borrowed_by_band(donors(held, store, y), edges, min_count) for y in years}
    r = _reforms(held)
    r = r[r["theme"] == "adu"]
    law_rows, local_rows = r[state_law(r)], r[~state_law(r)]
    pop = store.read(held, "jurisdictions").set_index("geoid")["pop_2020"]
    elig = store.read(held, "eligible_parcels")
    elig = elig[(elig["theme"] == "adu") & (elig["rule_version"] == eligible_rule.RULE_VERSION)]
    elig = elig[elig["year"] <= TIER2_LAST].sort_values("year").groupby("jurisdiction_geoid").last()
    top = list(elig["eligible_parcels"].sort_values(ascending=False).index[:TOP_PLACES])
    coded_local = set(local_rows["jurisdiction_geoid"])
    out = {"top20": top, "t0": {}, "t1": {}}
    for pl in places:
        lots = acs_lots(held, store, pl)
        band = int(
            adu.size_band(pd.to_numeric(pd.Series([pop.get(pl.geoid)]), errors="coerce").fillna(0), edges)[0]
        )  # as apply_priors
        p_local = np.array(
            [[bands[int(y)].set_index("band").loc[band, col] for col in adu.P_COLS] for y in pl.years]
        )
        age = np.array([bands[int(y)].set_index("band").loc[band, "rule_age"] for y in pl.years])
        law = np.full((len(pl.years), len(adu.TYPES)), np.nan)
        law_age = np.full(len(pl.years), np.nan)
        if not law_rows.empty:
            for t, y in enumerate(pl.years):
                cr = _rules_on(held, store, law_rows, [pl.geoid], pd.Timestamp(f"{int(y)}-07-01")).iloc[0]
                if cr["rule_class"] != "unknown":
                    law[t] = [cr[col] for col in adu.P_COLS]
                    law_age[t] = cr["rule_age"]
        t0 = jr.with_borrowed_rules(jr.with_lots(pl, lots), p_local, age, law, law_age)
        out["t0"][pl.geoid] = t0
        own = pl.geoid in top and pl.geoid in coded_local
        out["t1"][pl.geoid] = jr.with_lots(pl, lots) if own else t0
    lots_now = {pl.geoid: float(np.nanmax(pl.extra["parcels"])) for pl in places}
    out["city"] = max(lots_now, key=lots_now.get)
    return out


# ---------------------------------------------------------------------------------------------------------
# Fits (top level, for worker processes)
# ---------------------------------------------------------------------------------------------------------


def fit_a_task(args):
    key, places = args
    t0 = time.time()
    return key, cal.fit3(places), time.time() - t0


def fit_b_task(args):
    key, places, with_dose = args
    t0 = time.time()
    return key, jr.fit_form_b(places, with_dose), time.time() - t0


def tau_task(args):
    key, places, m_o, m_x = args
    ll = cal.tau_profile(places, m_o, m_x)
    return key, ll


def run_fits(pool, a_jobs: dict, b_jobs: dict, with_dose: bool, tau_for: set) -> tuple[dict, dict, dict]:
    """Form A and B fits for every job {key: places}; τ's profile for the A fits in `tau_for`."""
    fa = {k: pool.submit(fit_a_task, (k, v)) for k, v in a_jobs.items()}
    fb = {k: pool.submit(fit_b_task, (k, v, with_dose)) for k, v in b_jobs.items()}
    a, b = {}, {}
    for k, f in fb.items():
        _, fit, sec = f.result()
        b[k] = fit
        log(f"  Form B {k}: loglik {fit.fit.loglik:.2f}, alpha {fit.fit.alpha:.3f} ({sec:.0f}s)")
    for k, f in fa.items():
        _, fit, sec = f.result()
        a[k] = fit
        log(
            f"  Form A {k}: theta {fit.theta * 1000:.4f}/1,000 ({fit.low * 1000:.4f}-{fit.high * 1000:.4f}), "
            f"alpha {fit.alpha:.3f}, m_o {fit.m_owner}, m_x {fit.m_other}, loglik {fit.loglik:.2f} "
            f"({sec:.0f}s)"
        )
    ft = {k: pool.submit(tau_task, (k, a_jobs[k], a[k].m_owner, a[k].m_other)) for k in tau_for}
    taus = {k: f.result()[1] for k, f in ft.items()}
    return a, b, taus


def fit_row(variant: str, fold: str, form: str, fit) -> dict:
    if form == "A":
        return {
            "variant": variant,
            "fold": fold,
            "form": "A",
            "theta": fit.theta,
            "theta_low": fit.low,
            "theta_high": fit.high,
            "alpha": fit.alpha,
            "m_owner": fit.m_owner,
            "m_other": fit.m_other,
            "owner_estimated": fit.owner_estimated,
            "other_estimated": fit.other_estimated,
            "loglik": fit.loglik,
            "places": fit.n_places,
            "place_years": fit.n_years,
        }
    names = jr.NAMES_B if fit.with_dose else jr.NAMES_B[:-2]
    se = np.sqrt(np.clip(np.diag(fit.fit.cov)[: len(fit.fit.beta)], 0, None))
    row = {
        "variant": variant,
        "fold": fold,
        "form": "B",
        "alpha": fit.fit.alpha,
        "loglik": fit.fit.loglik,
        "places": fit.fit.n_places,
        "with_dose": fit.with_dose,
    }
    for n, b, s in zip(names, fit.fit.beta, se, strict=True):
        row[f"b[{n}]"], row[f"se[{n}]"] = b, s
    return row


# ---------------------------------------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------------------------------------


def target_cols(pl: cal.PlaceData) -> np.ndarray:
    return np.isin(pl.years, list(TARGET_YEARS))


def tiers_for_state(
    held, inputs, places_held, fit_a, taus, fit_b, s_b, seed
) -> tuple[list[dict], list[dict]]:
    """Scores per form and tier for one held-out state, and the tier-1 held-out log score per place."""
    city = inputs["city"]
    targets = [pl for pl in places_held if pl.geoid != city and target_cols(pl).any()]
    if not targets:  # every fit place but the tier-2 city is outside 2021-2024: nothing to score
        none = {
            "observed": np.nan,
            "p10": np.nan,
            "p50": np.nan,
            "p90": np.nan,
            "inside": False,
            "obs_over_p50": np.nan,
            "within_2x": False,
            "useful": False,
            "percentile": np.nan,
            "crps": np.nan,
            "log_score": np.nan,
        }
        return [
            {
                "held_out": held,
                "form": f,
                "tier": t,
                "targets": 0,
                "tier2_city": city,
                "ess": np.nan,
                "note": "no place to score besides the tier-2 city",
            }
            | none
            for f in ("A", "B")
            for t in (0, 1, 2)
        ], []
    obs = float(sum(pl.y[target_cols(pl)].sum() for pl in targets))
    rng = np.random.default_rng([seed, 1])
    tau_draws = cal.draw_tau(cal.TAU_GRID, cal.tau_probabilities(taus), DRAWS, rng)
    g0 = {"A": jr.globals_a(fit_a, tau_draws, DRAWS, seed), "B": jr.globals_b(fit_b, s_b, DRAWS, seed + 1)}
    rows, ls_rows = [], []
    for form, g in g0.items():
        city_t1 = jr.subset_years(inputs["t1"][city], range(min(WINDOW), TIER2_LAST + 1))
        g2, ess = jr.update(g, city_t1, seed + 2)
        for tier, (key, gg) in enumerate([("t0", g), ("t1", g), ("t1", g2)]):
            pls = [inputs[key][pl.geoid] for pl in targets]
            d = jr.predict(pls, gg, seed + 3)
            tot = sum(d[pl.geoid][:, target_cols(pl)].sum(axis=1) for pl in pls)
            rows.append(
                {
                    "held_out": held,
                    "form": form,
                    "tier": tier,
                    "targets": len(pls),
                    "tier2_city": city,
                    "ess": ess if tier == 2 else np.nan,
                }
                | jr.score(obs, tot)
            )
        for pl in targets:
            t1 = jr.subset_years(inputs["t1"][pl.geoid], TARGET_YEARS)
            ls_rows.append(
                {
                    "held_out": held,
                    "form": form,
                    "geoid": pl.geoid,
                    "name": pl.name,
                    "log_score_tier1": jr.held_out_log_score(t1, g),
                }
            )
    return rows, ls_rows


def tier_gains(t: pd.DataFrame) -> pd.DataFrame:
    t = t.sort_values(["form", "held_out", "tier"]).copy()
    grp = t.groupby(["form", "held_out"])
    t["crps_gain"] = -grp["crps"].diff()  # lower CRPS is better: gain = previous - this
    t["log_gain"] = grp["log_score"].diff()
    return t


def test_a_rows(new_places, fits_a, fits_b, seed) -> list[dict]:
    rows = []
    for pl in new_places:
        cols = target_cols(pl)
        if not cols.any():
            continue
        obs = float(pl.y[cols].sum())
        for form, fit in (("A", fits_a[pl.geoid]), ("B", fits_b[pl.geoid])):
            g = jr.globals_a(fit, 0.0, DRAWS, seed) if form == "A" else jr.globals_b(fit, 0.0, DRAWS, seed)
            d = jr.predict([pl], g, seed + 1)[pl.geoid][:, cols].sum(axis=1)
            rows.append(
                {
                    "form": form,
                    "state": pl.state,
                    "geoid": pl.geoid,
                    "name": pl.name,
                    "years": int(cols.sum()),
                }
                | jr.score(obs, d)
            )
    return rows


def test_b_rows(store, fit_a, fit_b, seed) -> tuple[list[dict], list[dict]]:
    """D-074 test B: towns with an accepted ADU rule in a roll comparison, the k-setting city left out."""
    rolls = pd.read_csv(ROLLS, dtype={"geoid": str})
    per, tot = [], []
    for st, r in rolls.groupby("state"):
        r = r[~r["sets_k"]]
        y0, y1 = int(r["first_year"].min()), int(r["last_year"].max())
        pls = cal.place_data(
            st, store, list(r["geoid"]), range(y0, y1 + 1), counts=cal.count_settings(), require_counts=False
        )
        if not pls:
            continue
        gained = r.set_index("geoid")["gained"]
        for form, g in (
            ("A", jr.globals_a(fit_a, 0.0, DRAWS, seed)),
            ("B", jr.globals_b(fit_b, 0.0, DRAWS, seed)),
        ):
            d = jr.predict(pls, g, seed + 1)
            total = sum(d[pl.geoid].sum(axis=1) for pl in pls)
            obs = float(sum(gained[pl.geoid] for pl in pls))
            tot.append(
                {"form": form, "state": st, "towns": len(pls), "years": f"{y0}-{y1}"}
                | jr.score(obs, total)
                | {"pass": jr.test_b_pass(obs, total)}
            )
            for pl in pls:
                per.append(
                    {
                        "form": form,
                        "state": st,
                        "geoid": pl.geoid,
                        "name": pl.name,
                        "rule_years": int(len(pl.years)),
                        "in_fit": bool(np.isfinite(pl.y).all()),
                    }
                    | jr.score(float(gained[pl.geoid]), d[pl.geoid].sum(axis=1))
                )
    return tot, per


def test_c_rows(store, fit_a, draws: int = 2000) -> list[dict]:
    """D-074 test C with Form A's refit values in the scenario engine: per counted place, the no-reform
    (current-rules) median a year over the window against counted ADUs a year 2023-2025 (central k, sources
    out of the fit dropped). θ, α, m_o and m_x are held at the refit's values in every draw."""
    origin = 2025
    params = {
        "adu_mature_hazard_ref": fit_a.theta,
        "adu_place_effect_variance": fit_a.alpha,
        "adu_owner_occupancy_share": fit_a.m_owner,
        "adu_partial_rule_share": fit_a.m_other,
    }
    rows = []
    for st in STATES:
        places = adu.places_from_store(st, store, origin)
        _, _, rd = adu.run(places, origin, draws=draws, params=params, return_draws=True)
        permits = cal.drop_sources(store.read(st, "permits"), [(s, None, None) for s in uc.out_of_fit()])
        counts = adu.observed_adu_counts(permits, 2023, 2025, uc.central())
        stops = adu.holdout_stops(load_state(st).holdouts)
        counts = counts[~counts["geoid"].isin(stops)]
        per = counts.groupby("geoid")["adu_permits"].sum() / 3.0
        cur = np.asarray(rd["current"], dtype=float)
        for i, g in enumerate(places["geoid"]):
            if g not in per.index or per[g] <= 0:
                continue
            med = float(np.median(cur[:, i, :].mean(axis=1)))
            rows.append(
                {
                    "state": st,
                    "geoid": g,
                    "name": places["name"].iloc[i],
                    "counted_a_year": float(per[g]),
                    "no_reform_median_a_year": med,
                    "ratio": med / float(per[g]),
                }
            )
    return rows


def event_check(places, ev: pd.DataFrame, fit_a) -> list[dict]:
    """D-079: per event, Form A's predicted step (mean expected count after ÷ before, θ and the place effect
    cancel) against the observed step. Reported, not used to choose."""
    by = {pl.geoid: pl for pl in places}
    cv = cal._cvals(fit_a.m_owner, fit_a.m_other)
    rows = []
    for e in ev.itertuples():
        pl = by[e.geoid]
        k = (pl.w[:, None] * pl.k(cv)).sum(axis=0) / pl.w.sum()
        after = pl.years >= e.year
        pred = k[after].mean() / k[~after].mean() if k[~after].mean() > 0 else math.inf
        o_b, o_a = pl.y[~after].mean(), pl.y[after].mean()
        rows.append(
            {
                "state": e.state,
                "geoid": e.geoid,
                "name": e.name,
                "year": e.year,
                "dose": f"{e.dose_before:.2f} -> {e.dose_after:.2f}",
                "predicted_step": pred,
                "observed_step": o_a / o_b if o_b > 0 else math.inf,
                "observed_before_a_year": o_b,
                "observed_after_a_year": o_a,
            }
        )
    return rows


def fw_no_kitchen(store) -> dict:
    """Fort Worth's ADU permits with the kitchen rule (central) and without it (D-081 item 2's named
    sensitivity): an in-memory rebuild from the cached raw snapshot, network refused, nothing written."""
    from lotline.adapters.states.tx import fw_permits as fw
    from lotline.parse import permit_text

    with offline.offline_build(store):
        raw = fw.download(store)
    out = {}
    original = fw.parse_description
    try:
        for name, needs in (("central", True), ("no_kitchen", False)):
            fw.parse_description = functools.partial(
                permit_text.parse_description, in_law_suite_needs_kitchen=needs
            )
            b = fw.build(raw)
            a = b[adu._is_adu(b)]
            out[name] = {
                "2015_2026": int(a["issue_year"].between(2015, 2026).sum()),
                "2023_2025": int(a["issue_year"].between(2023, 2025).sum()),
            }
    finally:
        fw.parse_description = original
    return out


# ---------------------------------------------------------------------------------------------------------
# One variant: fits, tiers and tests
# ---------------------------------------------------------------------------------------------------------


def run_variant(name, pool, store, places, new, with_dose, seed, tests: bool) -> dict:
    log(f"=== variant {name}: {len(places)} places, {sum(len(p.y) for p in places)} place-years ===")
    a_jobs = {"all": places} | {f"without {st}": [p for p in places if p.state != st] for st in STATES}
    if tests:
        a_jobs |= {f"without place {g}": [p for p in places if p.geoid != g] for g in sorted(new)}
    loso = {f"without {st}" for st in STATES}
    fa, fb, taus = run_fits(pool, a_jobs, dict(a_jobs), with_dose, loso)
    fits = [fit_row(name, k, "A", v) for k, v in fa.items()] + [
        fit_row(name, k, "B", v) for k, v in fb.items()
    ]
    tier_rows, ls_rows = [], []
    for st in STATES:
        held = [p for p in places if p.state == st]
        others = [p for p in places if p.state != st]
        shifts = [
            jr.state_shift([p for p in others if p.state == s], fb[f"without {st}"])
            for s in STATES
            if s != st
        ]
        s_b = jr.shift_spread(shifts)
        inputs = tier_inputs(st, store, held)
        log(f"  {st}: tier-2 city {inputs['city']}, s_B {s_b:.3f}, top-20 {len(inputs['top20'])}")
        r, ls = tiers_for_state(
            st, inputs, held, fa[f"without {st}"], taus[f"without {st}"], fb[f"without {st}"], s_b, seed
        )
        tier_rows += r
        ls_rows += ls
    tiers = tier_gains(pd.DataFrame(tier_rows)).assign(variant=name)
    lsd = pd.DataFrame(ls_rows).assign(variant=name)
    out = {"fits": fits, "tiers": tiers, "logscores": lsd, "fit_a": fa["all"], "fit_b": fb["all"]}
    if tests:
        out["test_a"] = pd.DataFrame(
            test_a_rows(
                [p for p in places if p.geoid in new],
                {g: fa[f"without place {g}"] for g in new},
                {g: fb[f"without place {g}"] for g in new},
                seed,
            )
        ).assign(variant=name)
        tb, tbp = test_b_rows(store, fa["all"], fb["all"], seed)
        out["test_b"], out["test_b_towns"] = pd.DataFrame(tb).assign(variant=name), pd.DataFrame(tbp)
    return out


def verdicts(v: dict) -> dict:
    """Claim tiers, tests A-B pass state by state, the tier-1 log-score gain and the decision."""
    t = v["tiers"]
    claim = {f: jr.claim_tier(t[t["form"] == f]) for f in ("A", "B")}
    passes = {}
    for f in ("A", "B"):
        ta = v["test_a"][v["test_a"]["form"] == f]
        tb = v["test_b"][v["test_b"]["form"] == f]
        passes[f] = {
            "A": {st: jr.test_a_pass(ta[ta["state"] == st]) for st in STATES},
            "B": {
                st: (bool(tb.loc[tb["state"] == st, "pass"].iloc[0]) if (tb["state"] == st).any() else None)
                for st in STATES
            },
        }
    ls = v["logscores"].pivot_table(index="geoid", columns="form", values="log_score_tier1")
    gain, se = sc.paired((ls["B"] - ls["A"]).dropna()) if len(ls) > 1 else (0.0, math.inf)
    dec = jr.decide(
        claim["A"], claim["B"], gain, se, jr.tests_passed(passes["A"]), jr.tests_passed(passes["B"])
    )
    return {
        "claim_tier": claim,
        "tests": passes,
        "tests_passed": {f: jr.tests_passed(passes[f]) for f in passes},
        "log_gain_b_over_a": gain,
        "log_gain_se": se,
        "decision": dataclasses.asdict(dec),
    }


def place_table(places, new, inputs_city: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "state": p.state,
                "geoid": p.geoid,
                "name": p.name,
                "first": int(p.years.min()),
                "last": int(p.years.max()),
                "place_years": len(p.y),
                "adu_permits_k": float(p.y.sum()),
                "lots_max": float(np.nanmax(p.extra["parcels"])),
                "new_since_d053": p.geoid in new,
                "tier2_city": inputs_city.get(p.state) == p.geoid,
            }
            for p in places
        ]
    )


def tier2_cities(places) -> dict:
    out = {}
    for st in STATES:
        held = [p for p in places if p.state == st]
        if held:
            out[st] = max(held, key=lambda p: float(np.nanmax(p.extra["parcels"]))).geoid
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument(
        "--inputs-only", action="store_true", help="write the fit set and event list; fit nothing"
    )
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):  # nothing is downloaded: every request is refused, caches are read
        run(a, store)


def run(a, store) -> None:
    log(f"undercount table: {len(uc.resolve())} rows; out of the fit: {sorted(uc.out_of_fit())}")
    places, new = all_places(store)
    cities = tier2_cities(places)
    pt = place_table(places, new, cities)
    pt.to_csv(a.out / "fit_set.csv", index=False)
    ev = jr.events(places)
    ev.to_csv(a.out / "events.csv", index=False)
    identified = jr.g_identified(ev)
    log(
        f"fit set: {len(places)} places, {int(pt['place_years'].sum())} place-years, "
        f"{len(new)} new since D-053"
    )
    log(
        f"events: {len(ev)} in {ev['state'].nunique()} states -> g "
        f"{'estimated' if identified else 'held at 0'}"
    )
    if a.inputs_only:
        return
    summary: dict = {
        "fit_set": {
            "places": len(places),
            "place_years": int(pt["place_years"].sum()),
            "new": sorted(new),
            "tier2_city": cities,
        },
        "events": {"n": len(ev), "states": int(ev["state"].nunique()), "g_identified": identified},
    }
    results = {}
    with ProcessPoolExecutor(a.workers) as pool:
        results["central"] = run_variant("central", pool, store, places, new, identified, SEED, tests=True)
        summary["central"] = verdicts(results["central"])
        log(f"decision: {summary['central']['decision']}")
        for z, name in ((-Z_FIELD, "field k 5th pct"), (Z_FIELD, "field k 95th pct")):
            pz, _ = all_places(store, undercount=uc.at_field_z(z))
            results[name] = run_variant(name, pool, store, pz, new, identified, SEED, tests=False)
            t = results[name]["tiers"]
            summary[name] = {"claim_tier": {f: jr.claim_tier(t[t["form"] == f]) for f in ("A", "B")}}
        drop = [(s, f, last) for s, f, last in uc.low_recall_rows()]
        pw, new_w = all_places(store, drop=drop)
        results["without low-recall rows"] = run_variant(
            "without low-recall rows", pool, store, pw, new_w, identified, SEED, tests=True
        )
        summary["without low-recall rows"] = verdicts(results["without low-recall rows"])
    fit_a = results["central"]["fit_a"]
    pd.DataFrame([r for v in results.values() for r in v["fits"]]).to_csv(a.out / "fits.csv", index=False)
    pd.concat([v["tiers"] for v in results.values()]).to_csv(a.out / "tiers.csv", index=False)
    pd.concat([v["logscores"] for v in results.values()]).to_csv(a.out / "logscores_tier1.csv", index=False)
    pd.concat([v["test_a"] for v in results.values() if "test_a" in v]).to_csv(
        a.out / "test_a.csv", index=False
    )
    pd.concat([v["test_b"] for v in results.values() if "test_b" in v]).to_csv(
        a.out / "test_b.csv", index=False
    )
    results["central"]["test_b_towns"].to_csv(a.out / "test_b_towns.csv", index=False)
    pd.DataFrame(event_check(places, ev, fit_a)).to_csv(a.out / "event_check.csv", index=False)
    log("test C: the scenario engine with Form A's refit values")
    tc = pd.DataFrame(test_c_rows(store, fit_a))
    tc.to_csv(a.out / "test_c.csv", index=False)
    summary["central"]["test_c_form_a"] = {
        st: jr.test_c_pass(tc.loc[tc["state"] == st, "ratio"]) for st in STATES
    }
    summary["fort_worth_no_kitchen"] = fw_no_kitchen(store)
    summary["low_recall_rows"] = uc.low_recall_rows()
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    log("done")


if __name__ == "__main__":
    sys.exit(main())
