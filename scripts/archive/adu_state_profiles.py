#!/usr/bin/env python3
"""D-089: a profile of each state's places by type, the share of each state outside the fit's evidence, and
statewide 5-year ADU totals under Form A + place types with and without the town prior.

    uv run python scripts/archive/adu_state_profiles.py --out reports/adu-state-profiles

Inputs, for every jurisdiction in the five states (national data only):
- type: D-088's rule (`adu_types_refit.type_table`);
- population: `jurisdictions.pop_2020`;
- eligible lots: ACS one-unit detached homes (`estimate_adu.permit_acs_rows`, as tier 0), vintage 2011-15;
- home value and rent: ACS B25077 / B25064, newest vintage ending 2015 or earlier, 2025 dollars
  (`scenarios.adu.acs_values`); unincorporated county areas read their county's medians (flagged);
- owner share: B25003, as D-084 (`adu_owner_refit.owner_rows`).
All ACS reads go through `holdout.apply_acs`. No ADU count is read for Parts 1-2.

Part 4 builds each state's scenario inputs (`scenarios.adu.places_from_store`, origin 2025, as a forward run:
holdout-filtered tables only, observed floor included) and draws Form A + P's θ, core term and place effects,
with towns as suburbs and with the town prior. St. Paul is left out of the totals. Writes only to `--out`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.io import DataStore, offline
from lotline.model import adu_profiles as pr
from lotline.model import baseline, estimate_adu, hazard, money
from lotline.model import calibrate_adu as cal
from lotline.model.scenarios import adu
from lotline.validation import holdout

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
D088 = REPO / "reports/adu-place-types"
STATES = ("MN", "NC", "OH", "TX", "OR")
ST_PAUL = "2758000"
VINTAGE = 2015
ORIGIN = 2025
DRAWS = 20_000
SEED = 20261111
MEASURES = ("home_value", "rent", "owner", "lots")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TY = _load("adu_types_refit", "adu_types_refit.py")
OWN = TY.OWN


def jurisdiction_table(store) -> pd.DataFrame:
    tt = TY.type_table(store)
    tt["type"] = tt["type_raw"].replace({"town": "town"})  # no merge for profiles: towns stay towns
    out = []
    for st in STATES:
        s = st.lower()
        juris = store.read(s, "jurisdictions")
        juris = juris.assign(geoid=juris["geoid"].astype(str))
        acs = holdout.apply_acs(store.read(s, "acs_geo_year"), s)
        lots = estimate_adu.permit_acs_rows(s, store, juris)
        lots = lots[(lots["theme"] == "adu") & (lots["year"] <= VINTAGE)]
        lots = lots.sort_values("year").groupby("jurisdiction_geoid")["eligible_parcels"].last()
        cpi = money.index_by_year(store.read(s, "market_geo_year"), "cpi_u")
        geo = (
            juris["kind"].map(adu.ACS_PREFIX)
            + ":"
            + juris["geoid"].where(
                juris["kind"] != "county_unincorporated", juris["county_geoid"].astype(str)
            )
        )
        vals = adu.acs_values(acs, geo, VINTAGE, cpi)
        own = OWN.b25003(store, s)
        rows = []
        for r, g in zip(juris.itertuples(), geo, strict=True):
            try:
                by_year, _ = OWN.owner_rows(s, r.geoid, r.kind, str(r.county_geoid), own, juris)
            except ValueError:  # a county remainder whose places lack ACS rows: owner share left missing
                by_year = {}
            share, _ = OWN.ao.vintage_share(by_year, VINTAGE)
            rows.append(
                {
                    "state": st,
                    "geoid": r.geoid,
                    "name": r.name,
                    "kind": r.kind,
                    "pop": float(r.pop_2020) if pd.notna(r.pop_2020) else 0.0,
                    "lots": float(lots.get(r.geoid, 0.0)),
                    "home_value": float(vals["home_value"].get(g, np.nan)) if g in vals.index else np.nan,
                    "rent": float(vals["rent"].get(g, np.nan)) if g in vals.index else np.nan,
                    "owner": np.nan if share is None else share,
                    "value_from_county": r.kind == "county_unincorporated",
                }
            )
        out.append(pd.DataFrame(rows))
    j = pd.concat(out, ignore_index=True)
    return j.merge(tt[["geoid", "type", "cbsa_code", "cbsa_type"]], on="geoid", how="left")


def a_p_fit() -> dict:
    f = pd.read_csv(D088 / "fits.csv")
    r = f[(f.variant == "central") & (f.fold == "all") & (f.form == "A+P")].iloc[0]
    return {
        "theta": float(r.theta),
        "log_se": (math.log(r.high) - math.log(r.low)) / (2 * cal.Z_95),
        "alpha": float(r.alpha),
        "b_core": float(r.b_core),
        "core_se": (float(r.b_core_high) - float(r.b_core_low)) / (2 * pr.Z_90),
        "m_owner": float(r.m_owner),
        "m_other": float(r.m_other),
    }


def state_totals(store, st: str, jt: pd.DataFrame, fit: dict, s_town: float) -> tuple[dict, pd.DataFrame]:
    p = adu.central_params() | {
        "adu_owner_occupancy_share": fit["m_owner"],
        "adu_partial_rule_share": fit["m_other"],
    }
    places = adu.places_from_store(st, store, ORIGIN)
    places = places[places["geoid"].astype(str) != ST_PAUL].reset_index(drop=True)
    places = adu.with_rule_probs(places, p)
    c = adu.expected_rule_share(places, p)
    rate = np.full(len(places), p["mortgage_rate_forecast"])
    unit = 1e-6
    h1 = hazard.adu_mature_hazard(
        places["rent"], places["home_value"], rate, p | {"adu_mature_hazard_ref": unit}
    )
    h1 = np.nan_to_num(np.asarray(h1, dtype=float) / unit, nan=0.0)
    info = jt.set_index("geoid")
    geo = places["geoid"].astype(str)
    typ = geo.map(info["type"]).fillna("town").to_numpy()
    outside = geo.map(info["outside"]).fillna(True).to_numpy(dtype=bool)
    core, town = (typ == "core").astype(float), (typ == "town").astype(float)
    lead, horizon, first = baseline.window(ORIGIN)
    rng = np.random.default_rng([SEED, 89, STATES.index(st)])
    n = DRAWS
    theta = np.exp(rng.normal(math.log(fit["theta"]), fit["log_se"], size=n))
    b_core = rng.normal(fit["b_core"], fit["core_se"], size=n)
    b_town = rng.normal(0.0, s_town, size=n)
    r = 1.0 / fit["alpha"]
    out = {}
    for variant, bt in (("towns as suburbs", np.zeros(n)), ("town prior", b_town)):
        tot = np.zeros(n)
        part = {"towns": np.zeros(n), "outside": np.zeros(n)}
        for lo in range(0, n, 2000):  # chunks keep the draws × places arrays small
            sl = slice(lo, min(lo + 2000, n))
            m = len(theta[sl])
            u = rng.gamma(r, 1.0 / r, size=(m, len(places)))
            mult = np.exp(b_core[sl, None] * core[None, :] + bt[sl, None] * town[None, :])
            hm = theta[sl, None] * h1[None, :] * mult * u
            args = (places["observed_rate"], places["rule_age"], p, horizon, lead)
            e = places["eligible_parcels"].to_numpy(dtype=float)
            tot[sl] = pr.current_totals(e, hm, c, *args)
            for key, mask in (("towns", typ == "town"), ("outside", outside)):
                if mask.any():
                    a2 = (places["observed_rate"][mask], places["rule_age"][mask], p, horizon, lead)
                    part[key][sl] = pr.current_totals(e[mask], hm[:, mask], c[mask], *a2)
        q = np.percentile(tot, [10, 50, 90])
        out[variant] = {
            "p10": float(q[0]),
            "p50": float(q[1]),
            "p90": float(q[2]),
            "p90_over_p10": float(q[2] / q[0]) if q[0] > 0 else None,
            "share_from_towns": float(part["towns"].mean() / tot.mean()),
            "share_from_outside": float(part["outside"].mean() / tot.mean()),
        }
        log(f"  {st} {variant}: P10 {q[0]:,.0f}, P50 {q[1]:,.0f}, P90 {q[2]:,.0f}")
    out["window"] = f"{first}-{first + horizon - 1}"
    out["places"] = len(places)
    out["lots_in_scenario"] = float(places["eligible_parcels"].sum())
    return out, places.assign(type=typ, outside=outside)[
        ["geoid", "name", "eligible_parcels", "type", "outside"]
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--profiles-only", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        run(a, store)


def run(a, store) -> None:
    log("jurisdiction table")
    jt = jurisdiction_table(store)
    fit_ids = set(pd.read_csv(D088 / "place_types.csv", dtype={"geoid": str})["geoid"])
    jt["in_fit"] = jt["geoid"].isin(fit_ids)
    fit = jt[jt["in_fit"]]
    ranges = pr.fit_ranges(fit, MEASURES)
    flags = pr.outside_evidence(jt, ranges, MEASURES)
    jt = pd.concat([jt.reset_index(drop=True), flags], axis=1)
    jt.to_csv(a.out / "jurisdictions.csv", index=False)

    prof = pr.profile(jt[jt["lots"] > 0])
    fit_prof = pr.profile(fit.assign(state="fit set"))
    pd.concat([prof, fit_prof]).to_csv(a.out / "profiles.csv", index=False)
    ev = []
    for st, g in jt.groupby("state"):
        lots = g["lots"].sum()
        sh = {k: float(g.loc[g[k], "lots"].sum() / lots) for k in ("is_town", "beyond_range", "outside")}
        ev.append({"state": st, "lots": lots} | sh | {"labeled": pr.label(sh["outside"])})
    ev = pd.DataFrame(ev)
    ev.to_csv(a.out / "evidence.csv", index=False)
    summary = {
        "jurisdictions": len(jt),
        "fit_places": int(jt["in_fit"].sum()),
        "fit_ranges": ranges,
        "evidence": ev.set_index("state").to_dict(orient="index"),
        "missing": {m: int(jt[m].isna().sum()) for m in MEASURES},
        "value_from_county": int(jt["value_from_county"].sum()),
    }
    drivers = {}
    for st, g in jt[(jt["lots"] > 0) & (~jt["is_town"])].groupby("state"):
        tot = g["lots"].sum()
        drivers[st] = {}
        for m in MEASURES:
            lo_hi = g["type"].map(lambda t, m=m: ranges.get(t, {}).get(m, (np.nan, np.nan)))
            lo = lo_hi.map(lambda x: x[0])
            hi = lo_hi.map(lambda x: x[1])
            beyond = g[m].notna() & ((g[m] < lo) | (g[m] > hi))
            drivers[st][m] = float(g.loc[beyond, "lots"].sum() / tot)
    summary["beyond_range_by_measure_non_town_lot_share"] = drivers
    log(ev.to_string())
    log(prof.to_string())
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    if a.profiles_only:
        return

    fitp = a_p_fit()
    s_town = pr.town_sd(fitp["b_core"])
    summary["a_p_fit"] = fitp
    summary["town_prior_sd"] = s_town
    log(f"town prior sd {s_town:.3f}")
    totals, scen = {}, []
    for st in STATES:
        log(f"part 4: {st}")
        totals[st], pl = state_totals(store, st, jt, fitp, s_town)
        scen.append(pl.assign(state=st))
    pd.concat(scen).to_csv(a.out / "scenario_places.csv", index=False)
    summary["totals"] = totals
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    log("done")


if __name__ == "__main__":
    sys.exit(main())
