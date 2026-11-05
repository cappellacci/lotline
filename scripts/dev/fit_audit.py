#!/usr/bin/env python3
"""D-045: residual audit of the ADU fit (D-041 count rules, four states).

    uv run python scripts/dev/fit_audit.py --out reports/adu-fit-audit [--workers 5]

Writes places.csv (item 1), groups.csv (2), shape.csv (3), sources.csv (4), noise.csv (5). No parameter
changes. Reads D-041's fit set and the Raleigh/Durham test set through the holdout-filtered store.
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_adu as run  # noqa: E402

from lotline.config import load_state  # noqa: E402
from lotline.io import DataStore  # noqa: E402
from lotline.model import calibrate_adu as cal  # noqa: E402
from lotline.model import fit_audit as fa  # noqa: E402
from lotline.model import hazard  # noqa: E402
from lotline.model.scenarios import adu  # noqa: E402

BOOT = 2000


def _fit_task(args):
    places, test, st = args
    if st == "":
        return st, cal.fit3(places), {}
    return run._leave_state((places, test, st))


def _sources(store, state: str, geoids, first: int, last: int, cs: dict) -> pd.DataFrame:
    """ADU permits per place, year and source: all ADUs and co-built ones (D-041's rule)."""
    permits = store.read(state, "permits")
    flagging = permits.loc[adu._is_adu(permits), "source"].unique()
    p = permits[permits["source"].isin(flagging) & permits["jurisdiction_geoid"].isin(geoids)]
    p = p[(p["issue_year"] >= first) & (p["issue_year"] <= last)]
    is_adu = adu._is_adu(p)
    co = cal.cobuilt(p, cs["window"])
    p = p.assign(adu=is_adu, cobuilt=is_adu & co)
    g = p.groupby(["jurisdiction_geoid", "issue_year", "source"])[["adu", "cobuilt"]].sum().reset_index()
    g = g.rename(columns={"jurisdiction_geoid": "geoid", "issue_year": "year"})
    return g.assign(state=state, kept=g["adu"] - g["cobuilt"], survey=g["source"].isin(cal.SURVEY_SOURCES))


def _rule_age(state: str, geoid: str, years) -> float:
    """Mean over the years of the age (at 1 July) of the oldest ADU rule in force, local or state law."""
    reforms = adu.load_reforms(state)
    reforms = reforms[(reforms["theme"] == "adu") & (reforms["status"] == "in_force")]
    fips = load_state(state).fips
    mine = reforms[reforms["jurisdiction_geoid"].isin([geoid, fips])]
    ages = []
    for y in years:
        mid = pd.Timestamp(f"{int(y)}-07-01")
        live = mine[(mine["effective_date"] <= mid) & (mine["end_date"].isna() | (mine["end_date"] > mid))]
        if len(live):
            ages.append((mid - live["effective_date"].min()).days / 365.25)
    return float(np.mean(ages)) if ages else float("nan")


def place_table(store, places, test, full, loso, cs) -> tuple[pd.DataFrame, pd.DataFrame]:
    central = adu.central_params()
    rows, src = [], []
    for pl in places + test:
        yrs = [int(y) for y in pl.years]
        py = cal.place_years(pl.state, store, [pl.geoid], yrs, counts=cs).set_index("year").loc[yrs]
        s = _sources(store, pl.state, [pl.geoid], min(yrs), max(yrs), cs)
        src.append(s)
        kept = s.sort_values(["kept", "survey"], ascending=[False, True]).groupby("year").head(1)
        elig = store.read(pl.state, "eligible_parcels")
        elig = elig[(elig["jurisdiction_geoid"] == pl.geoid) & (elig["theme"] == "adu")]
        elig = elig.sort_values("year").tail(1)
        e_in = fa.expected_by_year(pl, full).sum()
        fit_out = loso.get(pl.state)
        e_out = fa.expected_by_year(pl, fit_out).sum() if fit_out is not None else np.nan
        y = float(pl.y.sum())
        pcr = hazard.adu_price_to_cost(py["rent"], params=central)
        rows.append(
            dict(
                state=pl.state,
                geoid=pl.geoid,
                name=pl.name,
                role="test" if any(pl is t for t in test) else "fit",
                first_year=min(yrs),
                last_year=max(yrs),
                years=len(yrs),
                observed=y,
                expected=e_in,
                expected_out=e_out,
                log_ratio=float(fa.log_ratio(y, e_in)),
                log_ratio_out=float(fa.log_ratio(y, e_out)) if fit_out is not None else np.nan,
                u_posterior=float(fa.posterior_u(y, e_in, full.alpha)),
                per_1000_parcels=1000 * y / py["eligible_parcels"].sum(),
                count_source="+".join(sorted(kept["source"].unique())),
                survey_share=float(kept["survey"].mean()) if len(kept) else np.nan,
                cobuilt_share=float(s["cobuilt"].sum() / s["adu"].sum()) if s["adu"].sum() else np.nan,
                eligible_parcels=float(py["eligible_parcels"].mean()),
                denominator_source=elig["denominator_source"].iloc[0] if len(elig) else None,
                denominator_quality=elig["denominator_quality"].iloc[0] if len(elig) else None,
                data_tier=elig["data_tier"].iloc[0] if len(elig) else None,
                rent=float(py["rent"].mean()),
                home_value=float(py["home_value"].mean()),
                price_to_cost=float(np.mean(pcr)),
                h1=float(py["h1"].mean()),
                rule_age=_rule_age(pl.state, pl.geoid, yrs),
                partial_share=float(((py["ramp_partial"] > 0) & (py["ramp_handbook"] == 0)).mean()),
            )
        )
    return pd.DataFrame(rows), pd.concat(src, ignore_index=True)


def groups_table(pt: pd.DataFrame, yearly: pd.DataFrame) -> pd.DataFrame:
    fit = pt[pt["role"] == "fit"].copy()
    fit["rule_age_band"] = pd.cut(fit["rule_age"], [-np.inf, 2, 5, np.inf], right=False,
                                  labels=["< 2", "2-5", ">= 5"]).astype(str)  # fmt: skip
    fit["pcr_tertile"] = pd.qcut(fit["price_to_cost"], 3, labels=["low", "mid", "high"]).astype(str)
    fit["survey"] = np.where(fit["survey_share"] > 0.5, "survey", "city records")
    out = []
    for by in ("state", "count_source", "survey", "denominator_source", "rule_age_band", "pcr_tertile"):
        for kind, exp in (("in-sample", "expected"), ("out-of-state", "expected_out")):
            for st, d in [("all", fit)] + list(fit.groupby("state")):
                g = fa.group_ratios(d, by, exp=exp).rename(columns={by: "group"})
                out.append(g.assign(by=by, fit=kind, within=st))
    yr = fa.group_ratios(yearly, "year").rename(columns={"year": "group"})
    out.append(yr.assign(by="year", fit="in-sample", within="all"))
    cols = ["by", "fit", "within", "group", "places", "observed", "expected", "ratio"]
    return pd.concat(out, ignore_index=True)[cols]


def shape_table(pt: pd.DataFrame, alpha: float) -> pd.DataFrame:
    fit = pt[pt["role"] == "fit"]
    w = fit["expected"] / (1 + alpha * fit["expected"])
    covs = {
        "log rent": np.log(fit["rent"]),
        "log home value": np.log(fit["home_value"]),
        "log price-to-cost": np.log(fit["price_to_cost"]),
        "rule age": fit["rule_age"],
        "log eligible parcels": np.log(fit["eligible_parcels"]),
    }
    rows = []
    for name, x in covs.items():
        est, lo, hi = fa.bootstrap_slope(fit["log_ratio"], x, fit["state"], w, n=BOOT, seed=45)
        eff = [fa.iqr_effect(b, x) for b in (est, lo, hi)]
        rows.append(
            dict(
                covariate=name,
                slope=est,
                slope_p5=lo,
                slope_p95=hi,
                iqr_effect=eff[0],
                iqr_effect_p5=eff[1],
                iqr_effect_p95=eff[2],
                shape_signal=bool((eff[0] >= 1.5 or eff[0] <= 1 / 1.5) and not lo <= 0 <= hi),
            )
        )
    return pd.DataFrame(rows)


def noise_table(draws: dict, places, test) -> pd.DataFrame:
    rows = []
    for name, pls in run._groups(places, test, True).items():
        tot = sum(draws[pl.geoid].sum(axis=1) for pl in pls)
        obs = float(sum(pl.y.sum() for pl in pls))
        useful, rms = fa.noise_floor(tot)
        p50 = float(np.median(tot))
        rows.append(dict(group=name, observed=obs, p50=p50, obs_over_p50=obs / p50 if p50 else np.nan,
                         observed_log_error=float(fa.log_ratio(obs, p50)),
                         p_useful_if_model_right=useful, k1_if_model_right=rms))  # fmt: skip
    df = pd.DataFrame(rows)
    four = df[df["group"].isin(run.STATES)]
    k1 = float(np.sqrt(np.mean(four["observed_log_error"] ** 2)))
    k1_right = float(np.sqrt(np.mean(four["k1_if_model_right"] ** 2)))
    return pd.concat([df, pd.DataFrame([dict(group="four states: K1", observed_log_error=k1,
                                             k1_if_model_right=k1_right)])], ignore_index=True)  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store, cs = DataStore(), cal.count_settings()
    places, test = (
        run.four_state_places(store, cs, params=run.pre_d048()),
        run._test_set(store, cs, params=run.pre_d048()),
    )
    print(f"=== D-045 audit: {len(places)} fit places, {len(test)} test places, counts {cs} ===", flush=True)
    with ProcessPoolExecutor(a.workers) as pool:
        res = list(pool.map(_fit_task, [(places, test, st) for st in ("",) + run.STATES]))
    full = next(f for st, f, _ in res if st == "")
    loso = {st: f for st, f, _ in res if st}
    draws = {k: v for st, _, d in res if st for k, v in d.items()}
    print(f"full fit: theta {full.theta * 1000:.3f} per 1,000, alpha {full.alpha:.3f}, "
          f"rule shares {full.m_owner}, {full.m_other}")  # fmt: skip
    for st, f in loso.items():
        print(f"  without {st}: theta {f.theta * 1000:.3f}, alpha {f.alpha:.3f}")
    pt, src = place_table(store, places, test, full, loso, cs)
    yearly = pd.DataFrame([dict(year=int(y), observed=v, expected=e)
                           for pl in places for y, v, e in zip(pl.years, pl.y, fa.expected_by_year(pl, full),
                                                               strict=True)])  # fmt: skip
    gt = groups_table(pt, yearly)
    st = shape_table(pt, full.alpha)
    multi = src.groupby(["state", "geoid", "year"]).filter(lambda d: (d["adu"] > 0).sum() >= 2)
    nt = noise_table(draws, places, test)
    pt.to_csv(a.out / "places.csv", index=False)
    gt.to_csv(a.out / "groups.csv", index=False)
    st.to_csv(a.out / "shape.csv", index=False)
    multi.to_csv(a.out / "sources.csv", index=False)
    nt.to_csv(a.out / "noise.csv", index=False)
    pd.set_option("display.width", 200)
    show = ["state", "name", "years", "observed", "expected", "expected_out", "u_posterior",
            "per_1000_parcels", "count_source", "survey_share", "cobuilt_share", "denominator_source",
            "rule_age", "price_to_cost"]  # fmt: skip
    print("\n1. Places\n" + pt[show].round(2).to_string(index=False))
    print("\n2. Groups\n" + gt.round(2).to_string(index=False))
    print("\n3. Shape\n" + st.round(3).to_string(index=False))
    print("\n4. Place-years with two or more ADU-flagging sources\n" + multi.to_string(index=False))
    print("\n5. Noise floor\n" + nt.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
