"""D-083: screen the D-079 Form A place effects against place factors the fit does not use.

Usage: uv run python scripts/dev/adu_covariate_screen.py --out reports/adu-covariate-screen

Offline: every table comes from the cache and nothing is downloaded. The fit set is the D-079 refit's
(`adu_joint_refit.all_places`), so St. Paul is out. ACS stock tables go through `holdout.apply_acs` and BPS
through `holdout.apply`. Parcel rolls dated inside a still-blind statewide holdout window are not used.
Nothing is written to config.
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

from lotline.build import eligible as eligible_rule
from lotline.config import load_params
from lotline.io import DataStore, offline
from lotline.model import adu_screen as scr
from lotline.model import calibrate_adu as cal
from lotline.validation import holdout

HERE = Path(__file__).resolve().parent
ACS_END = 2015  # D-083: the ACS 5-year 2011-15 vintage, before the 2016 window
BPS_YEARS = (2013, 2014, 2015)
OLD_HOMES = ("1950 to 1959", "1940 to 1949", "1939 or earlier")
M_OWNER, M_OTHER = 1.0, 0.4  # D-079 refit, Form A as kept (reports/adu-joint-refit-2026-11)

FACTORS = {
    "X1": "Owner-occupied share (ACS B25003)",
    "X2": "Share of homes built before 1960 (ACS B25034)",
    "X3": "Detached single-family share of homes (ACS B25024)",
    "X4": "New houses per 1,000 eligible lots, 2013-15 (BPS)",
    "X5": "Median eligible lot size, log (parcel rolls)",
    "X6": "HOA share of eligible lots (parcel rolls)",
    "X7": "Homestead share of eligible lots (parcel rolls)",
    "R1": "Place size: log eligible lots (reference)",
    "R2": "Home value: log median, ACS B25077 (reference)",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_refit():
    spec = importlib.util.spec_from_file_location("adu_joint_refit", HERE / "adu_joint_refit.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["adu_joint_refit"] = mod
    spec.loader.exec_module(mod)
    return mod


def _share(df: pd.DataFrame, table: str, num) -> pd.Series:
    t = df[df["table_id"] == table]
    lab = t["label"].astype(str).str.replace(":", "", regex=False).str.strip().str.lower()
    total = t[lab.isin(["total", "estimate!!total"])].groupby("geoid")["estimate"].sum()
    part = t[lab.map(num)].groupby("geoid")["estimate"].sum()
    return (part / total.replace(0, np.nan)).dropna()


def acs_factors(store, st: str) -> pd.DataFrame:
    a = store.read(st, "acs_geo_year")
    a = holdout.apply_acs(a, st)
    a = a[(a["end_year"] == ACS_END) & a["geo"].astype(str).str.startswith("place:")].copy()
    a["geoid"] = a["geo"].astype(str).str.split(":", n=1).str[1]
    out = pd.DataFrame(
        {
            "X1": _share(a, "B25003", lambda s: s.endswith("owner occupied")),
            "X2": _share(a, "B25034", lambda s: any(k in s for k in OLD_HOMES)),
            "X3": _share(a, "B25024", lambda s: s.endswith("1, detached")),
        }
    )
    v = a[a["table_id"] == "B25077"].groupby("geoid")["estimate"].first()
    out["R2"] = np.log(v[v > 0])
    return out


def eligible_lots(store, st: str) -> pd.Series:
    e = store.read(st, "eligible_parcels")
    e = e[e["theme"] == "adu"]
    # the window's first year (2016) where present, else the place's earliest year
    e16 = e[e["year"] == 2016].groupby("jurisdiction_geoid")["eligible_parcels"].sum()
    first = e.groupby("jurisdiction_geoid")["year"].transform("min")
    rest = e[e["year"] == first].groupby("jurisdiction_geoid")["eligible_parcels"].sum()
    return e16.combine_first(rest).astype(float)


def bps_factor(store, st: str, lots: pd.Series) -> pd.Series:
    b = store.read(st, "bps_place_year")
    b = holdout.apply(b, st, geoid_col="geoid", year_col="year")
    b = b[b["year"].isin(BPS_YEARS)].dropna(subset=["geoid"])
    mean = b.groupby(b["geoid"].astype(str))["bldgs_1"].mean()
    n = b.groupby(b["geoid"].astype(str))["year"].nunique()
    mean = mean[n == len(BPS_YEARS)]
    return (1000 * mean / lots.reindex(mean.index)).replace([np.inf, -np.inf], np.nan).dropna()


def parcel_factors(store, st: str, geoids: set[str], fill_min: float) -> tuple[pd.DataFrame, list[dict]]:
    """X5-X7 from each place's earliest roll. Rolls inside a still-blind holdout window are left out
    (`holdout.apply`, snapshot rule)."""
    notes = []
    try:
        p = store.read(st, "parcels")
    except Exception as e:  # noqa: BLE001
        return pd.DataFrame(), [{"state": st, "note": f"no parcel table ({e.__class__.__name__})"}]
    p = p[p["jurisdiction_geoid"].astype(str).isin(geoids)]
    before = set(p["jurisdiction_geoid"].astype(str))
    p = holdout.apply(
        p, st, geoid_col="jurisdiction_geoid", date_col="vintage_date", year_col="vintage", snapshot=True
    )
    for g in sorted(before - set(p["jurisdiction_geoid"].astype(str))):
        notes.append(
            {"state": st, "geoid": g, "note": "every roll is inside a blind holdout window: not used"}
        )
    rows = {}
    for g, q in p.groupby(p["jurisdiction_geoid"].astype(str)):
        first = q["vintage"].min()
        q = q[q["vintage"] == first]
        el = eligible_rule.classify(q, "adu")["eligible"].to_numpy()
        houses = (q["land_use_std"] == "SF_DETACHED").to_numpy()
        row = {"roll": str(first)}
        lot = pd.to_numeric(q["lot_sqft"], errors="coerce")
        if houses.sum() and lot[houses].notna().mean() >= fill_min and el.sum():
            row["X5"] = math.log(float(lot[el].median()))
        for key, col in (("X6", "hoa"), ("X7", "homestead")):
            if col in q and el.sum():
                v = q.loc[el, col]
                if v.notna().mean() >= fill_min:
                    row[key] = float(v.astype("boolean").fillna(False).astype(bool).mean())
        rows[g] = row
    return pd.DataFrame.from_dict(rows, orient="index"), notes


def main() -> None:
    global M_OWNER, M_OTHER
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument(
        "--influence", action="store_true", help="D-083 addition: leave-one-place-out on candidates"
    )
    ap.add_argument("--m-owner", type=float, default=M_OWNER, help="Form A owner multiplier (default D-079)")
    ap.add_argument("--m-other", type=float, default=M_OTHER, help="Form A other-rule multiplier (default D-079)")
    a = ap.parse_args()
    M_OWNER, M_OTHER = a.m_owner, a.m_other
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        if a.influence:
            influence(a.out, store)
        else:
            run(a.out, store)


def influence(out: Path, store) -> None:
    """D-083 addition: drop each screened place in turn and refit β for the within-state candidates."""
    pm = {k: v.value for k, v in load_params("adu_screen").items()}
    res = pd.read_csv(out / "screen.csv")
    cands = res[(res["version"] == "within") & (res["verdict"] == "candidate")]
    fac = pd.read_csv(out / "factors.csv", dtype={"geoid": str}).set_index("geoid")
    jr = load_refit()
    places, _ = jr.all_places(store)
    prep = scr.prepare(places, cal._cvals(M_OWNER, M_OTHER))
    name_of = {pl.geoid: pl.name for pl in places}
    fac = fac.reindex(list(prep.geoids))
    summary, frames = {}, []
    for r in cands.itertuples():
        keep = fac[r.factor].notna().to_numpy()
        sub = prep.subset(keep)
        z = scr.standardize(fac.loc[keep, r.factor]).to_numpy()
        d = scr.drop_one(sub, z, within=True).assign(factor=r.factor)
        d["name"] = d["dropped"].map(name_of)
        d["shift"] = d["beta"] - r.beta
        frames.append(d)
        top = d.reindex(d["shift"].abs().sort_values(ascending=False).index).head(5)
        summary[r.factor] = {
            "beta_full": r.beta,
            "beta_min": float(d["beta"].min()),
            "beta_max": float(d["beta"].max()),
            "sign_kept": int((np.sign(d["beta"]) == np.sign(r.beta)).sum()),
            "p_below": int((d["p"] < pm["adu_screen_p_max"]).sum()),
            "drops": len(d),
            "largest_shifts": top[["name", "state", "beta", "p"]].to_dict("records"),
            "reading": scr.influence_reading(r.beta, d, pm["adu_screen_p_max"]),
        }
        lo, hi = d["beta"].min(), d["beta"].max()
        log(f"{r.factor}: {summary[r.factor]['reading']}; beta {lo:+.3f} to {hi:+.3f}")
    pd.concat(frames).to_csv(out / "influence.csv", index=False)
    (out / "influence.json").write_text(json.dumps(summary, indent=1, default=str))


def run(out: Path, store) -> None:
    t0 = time.time()
    pm = {k: v.value for k, v in load_params("adu_screen").items()}
    jr = load_refit()
    places, _ = jr.all_places(store)
    log(f"fit set: {len(places)} places, {sum(len(pl.y) for pl in places)} place-years")
    prep = scr.prepare(places, cal._cvals(M_OWNER, M_OTHER))
    geoids = list(prep.geoids)
    state_of = dict(zip(prep.geoids, prep.states, strict=True))
    name_of = {pl.geoid: pl.name for pl in places}

    frames, notes = [], []
    for st in sorted(set(prep.states)):
        mine = {g for g in geoids if state_of[g] == st}
        lots = eligible_lots(store, st)
        f = acs_factors(store, st)
        f["X4"] = bps_factor(store, st, lots)
        f["R1"] = np.log(lots[lots > 0])
        pf, pn = parcel_factors(store, st, mine, pm["adu_screen_min_field_fill"])
        notes += pn
        f = f.join(pf, how="outer") if len(pf) else f
        frames.append(f.reindex(sorted(mine)))
        log(f"{st}: factors for {len(mine)} places")
    fac = pd.concat(frames).reindex(geoids)
    for k in FACTORS:
        if k not in fac:
            fac[k] = np.nan
    fac.insert(0, "state", [state_of[g] for g in fac.index])
    fac.insert(1, "name", [name_of[g] for g in fac.index])
    fac.index.name = "geoid"
    fac.to_csv(out / "factors.csv")

    n_fit = len(geoids)
    avail = {}
    for k in FACTORS:
        n = int(fac[k].notna().sum())
        ok = n >= pm["adu_screen_min_share"] * n_fit and n >= pm["adu_screen_min_places"]
        avail[k] = {"places": n, "share": n / n_fit, "screened": bool(ok)}
    log("availability: " + ", ".join(f"{k} {v['places']}" for k, v in avail.items()))

    rows = []
    for version, within in (("within", True), ("pooled", False)):
        for k in FACTORS:
            if not avail[k]["screened"]:
                continue
            keep = fac[k].notna().to_numpy()
            sub = prep.subset(keep)
            z = scr.standardize(fac.loc[keep, k]).to_numpy()
            r = scr.screen_one(sub, z, within, loso_min=int(pm["adu_screen_loso_min_places"]))
            null = scr.fit(sub, z, within, beta=0.0)
            rate = np.array([null.theta["all" if not within else s] for s in sub.states])
            post = scr.posterior_mean(sub, rate, null.alpha)
            rho = float(pd.Series(post).rank().corr(pd.Series(z).rank()))
            rows.append({"factor": k, "label": FACTORS[k], "version": version, "spearman_u": rho}
                        | {kk: vv for kk, vv in r.items() if kk != "loso_signs"}
                        | {"loso_signs": json.dumps(r["loso_signs"])})  # fmt: skip
            log(f"{version} {k}: beta {r['beta']:+.3f} ({r['beta_low']:+.2f}, {r['beta_high']:+.2f}), "
                f"p {r['p']:.4f}, alpha {r['alpha_null']:.3f} -> {r['alpha']:.3f}")  # fmt: skip
    res = pd.DataFrame(rows)
    for version in ("within", "pooled"):
        m = res["version"] == version
        adj = scr.holm(dict(zip(res.loc[m, "factor"], res.loc[m, "p"], strict=True)))
        res.loc[m, "p_holm"] = res.loc[m, "factor"].map(adj)
    res["verdict"] = [
        scr.verdict(r, pm["adu_screen_alpha_drop"], pm["adu_screen_p_max"])
        if r["version"] == "within"
        else ""
        for r in res.to_dict("records")
    ]
    res.to_csv(out / "screen.csv", index=False)

    cands = res[(res["version"] == "within") & (res["verdict"] == "candidate")]["factor"].tolist()
    joint = None
    if len(cands) >= 2:
        keep = fac[cands].notna().all(axis=1).to_numpy()
        joint = {"factors": cands, "places": int(keep.sum()),
                 "correlations": fac.loc[keep, cands].corr().round(3).to_dict()}  # fmt: skip
    summary = {
        "entry": "D-083 (accepted by Ben 2026-11-13)",
        "model": {"form": "Form A", "m_owner": M_OWNER, "m_other": M_OTHER},
        "fit_set": {"places": n_fit, "place_years": int(sum(len(pl.y) for pl in places))},
        "availability": avail,
        "notes": notes,
        "candidates": cands,
        "joint_descriptive": joint,
        "params": pm,
        "seconds": round(time.time() - t0),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"done: candidates {cands}")


if __name__ == "__main__":
    main()
