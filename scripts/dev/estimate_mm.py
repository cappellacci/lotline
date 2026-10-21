#!/usr/bin/env python3
"""The D-024 missing-middle estimation: smoke counts, a dry run on a simulated panel, or the one real run.

    uv run python scripts/dev/estimate_mm.py --smoke                 # counts only, no estimate
    uv run python scripts/dev/estimate_mm.py --dry-run --out DIR     # --full pipeline on simulated data
    uv run python scripts/dev/estimate_mm.py --dry-run --fallback --out DIR   # ... through the D-025 fallback
    uv run python scripts/dev/estimate_mm.py --full --out DIR        # the pre-registered run (once)
    uv run python scripts/dev/estimate_mm.py --coverage              # interval coverage on simulated panels

--smoke prints, for the main panel (Census BPS 2-4 unit homes, MN NC OH TX, 2010-2025, places of 10,000+
people plus every place with a coded missing-middle rule) under both comparison rules, for the 50,000+
sample and for the Met Council local check: places, adopters per year, comparisons, places with no 2-4 unit
home in any year and treated place-years per event-time bin.

--full follows D-024 (docs/analysis_plan.md): PPML with place and state × year fixed effects and the
pre-specified fallback (Poisson-gamma place random effects) if PPML fails or drops a treated place; the wild
cluster score bootstrap; randomization inference; the eight checks; the robustness fits; out-of-sample tests
A (North Carolina) and B (Minneapolis). Everything is computed before anything is written; --out then gets
named CSVs (no panel: outcomes stay in the data directory).
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.config import CONFIG_DIR, load_params
from lotline.io import DataStore
from lotline.model import estimate_adu
from lotline.model import estimate_mm as mm

ROOT = CONFIG_DIR.parent
PIPELINE = ROOT / "docs" / "research" / "ordinances" / "batch1-2026-10-20.json"
DURHAM_CITY, DURHAM_COUNTY, RALEIGH, MINNEAPOLIS = "3719000", "37063", "3755000", "2743000"
TRANSPORT = {"A: North Carolina": [DURHAM_CITY, DURHAM_COUNTY, RALEIGH], "B: Minneapolis": [MINNEAPOLIS]}
LOCAL = {  # treated city -> local permit sources for check 8
    MINNEAPOLIS: ("metc_residential_permits", "mpls_ccs_permits"),
    DURHAM_CITY: ("durham_permits",),
    RALEIGH: ("raleigh_permits",),
}
SEED = 20261020


def show(title: str, c: dict) -> None:
    print(f"\n== {title} (comparisons: {c['comparisons']})")
    print(f"  places {c['places']} ({c['by_state']}), place-years with an outcome {c['place_years']}")
    print(
        f"  treated {c['treated']} (adopting inside the panel years: {c['adopted_in_window']}); "
        f"adopters by year {c['adopters_by_year']}"
    )
    print(f"  comparison places {c['comparison_places']}")
    print(
        f"  places with no 2-4 unit home in any year: {c['all_zero_places']} "
        f"(treated {c['all_zero_treated']}, comparisons {c['all_zero_comparisons']}); "
        f"a place fixed-effects Poisson model keeps {c['kept_by_place_fe']}"
    )
    print(f"  share of place-years with zero: {c['zero_share_place_years']:.2f}")
    print(
        f"  treated place-years by event-time bin {c['treated_place_years_by_bin']}; "
        f"treated places per bin {c['treated_places_by_bin']}"
    )


def smoke(store) -> None:
    main = mm.build_panel(store)
    d = main.data
    span = f"{d['year'].min()}-{d['year'].max()}"
    print(f"Main panel: {d['place'].nunique()} places × {d['year'].nunique()} years ({span})")
    for reason, g in main.excluded.items():
        print(f"  excluded, {reason}: {len(g)}")
    print(f"  missing outcome place-years (no BPS row): {int(d['y'].isna().sum())}")
    print(f"  denominators: {d.drop_duplicates('place')['denominator_source'].value_counts().to_dict()}")
    tr = d[d["status"] == "treated"].drop_duplicates("place")
    for r in tr.itertuples():
        print(
            f"  treated: {r.state} {r.place} {r.name}, T = {int(r.T)}, dose in 2025 = "
            f"{d.loc[(d['place'] == r.place) & (d['year'] == d['year'].max()), 'dose'].iloc[0]:.2f}, "
            f"modifiers missing: {[m for m in mm.MODIFIERS if r._asdict()[m] != r._asdict()[m]]}"
        )
    cnt = d.drop_duplicates("place")["status"].value_counts().to_dict()
    print(f"  places by status: {cnt}")
    n_adu = int(d.drop_duplicates("place")["adu_coded"].sum())
    print(f"  ADU rule coded for {n_adu} places (others take the prior)")
    for note in main.notes:
        print("  note:", note)
    show("Main: BPS, 10,000+ people", mm.smoke_counts(d, "uncoded"))
    show("Main: BPS, 10,000+ people", mm.smoke_counts(d, "coded"))
    big = d[(d["pop_2020"] >= 50000) | (d["status"] != "uncoded")]
    show("Robustness: BPS, 50,000+ people", mm.smoke_counts(big, "uncoded"))
    local = mm.build_panel(store, states=("MN",), years=range(2016, 2026), source="metc_residential_permits")
    show("Local check: Met Council 2-4 unit permits, 2016-2025", mm.smoke_counts(local.data, "uncoded"))


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def pipeline_flagged(panel: pd.DataFrame) -> list[str]:
    """Check 7b: comparison places the ordinance pipeline lists with a status other than not_legal (a
    missing-middle ordinance, or unknown), matched to Minnesota places by name ("<City> city")."""
    recs = json.loads(PIPELINE.read_text())
    status = {r["city"]: (r["record"].get("missing_middle_legal") or {}).get("status") for r in recs}
    names = {f"{city} city" for city, st in status.items() if st != "not_legal"}
    comp = panel[(panel["status"] != "treated") & (panel["state"] == "MN")].drop_duplicates("place")
    return sorted(comp.loc[comp["name"].isin(names), "place"])


def term_rows(label: str, s: pd.DataFrame) -> list[dict]:
    keep = [t for t in (*mm.BIN_NAMES, "att") if t in set(s["term"])]
    return [{"fit": label, **s.set_index("term").loc[t, ["estimate", "low", "high"]].to_dict(), "term": t}
            for t in keep]  # fmt: skip


def robust(label, fn, rows, notes):
    """Run one robustness fit; a failure is reported, never raised."""
    try:
        rows += fn()
        log(f"robustness {label}: done")
    except Exception as err:  # noqa: BLE001 (reported, not raised)
        notes.append({"fit": label, "note": f"could not be estimated: {err}"})
        log(f"robustness {label}: could not be estimated: {err}")


def run(
    panel: pd.DataFrame,
    p: dict,
    workers: int,
    local: dict | None = None,
    metc: pd.DataFrame | None = None,
    transport: dict = TRANSPORT,
    flagged: list | None = None,
    durham_pair=(DURHAM_CITY, DURHAM_COUNTY),
    force_fallback: str = "",
) -> dict:
    """The D-024 run on `panel`. Returns named tables; writes nothing. `force_fallback` (dry runs only) takes
    the fallback path as if PPML had failed with that message."""
    draws, perms = int(p["mm_estimation_bootstrap_draws"]), int(p["mm_estimation_permutations"])
    out: dict[str, pd.DataFrame] = {}
    kw = {"modifiers": list(mm.MAIN_MODIFIERS)}
    method, why = "ppml", force_fallback
    try:
        main = mm.estimate(panel, method="ppml", **kw)
        gone = mm.treated_dropped(main)
        if gone and not why:
            why = f"PPML dropped treated places {gone}"
    except (estimate_adu.EstimationError, np.linalg.LinAlgError) as err:
        why = why or f"PPML failed: {err}"
    if why:
        log(f"FALLBACK (pre-specified): {why}; main model is now the negative binomial with place random "
            "effects (Poisson-gamma, Hausman-Hall-Griliches; the 17:06 run's fallback)")  # fmt: skip
        method = "re"
        try:
            main = mm.estimate(panel, method="re", **kw)
        except (estimate_adu.EstimationError, np.linalg.LinAlgError, ValueError) as err:
            log(f"NO ESTIMATE: the fallback could not be estimated either: {err}")
            status = {"model": "none", "ppml": why, "re": str(err)}
            return {"status": pd.DataFrame([status])}
    f = main.fit
    log(
        f"main fit ({method}): {f.iterations} iterations; "
        f"kept {int(f.keep.sum())} of {len(f.keep)} place-years; "
        f"dropped places {len(f.dropped_places)}; dropped columns {f.dropped_columns}; "
        f"separated observations {len(getattr(f, 'separated', []))}"
    )
    s, boot = mm.summary(main, draws=draws, seed=SEED)
    s["proportional_effect"] = np.expm1(s["estimate"])
    log(
        "main estimates (log scale; proportional_effect = e^estimate - 1):\n"
        + s.round(4).to_string(index=False)
    )
    added = mm.added_homes(main, boot)
    log(
        "added 2-4 unit homes in the treated places' post-adoption years:\n"
        + added.round(1).to_string(index=False)
    )
    att, p_ri, dist, failed = mm.randomization_inference(panel, permutations=perms, seed=SEED, method=method,
                                                         workers=workers, **kw)  # fmt: skip
    log(
        f"randomization inference: overall effect {att:.4f}, p = {p_ri:.3f} ({len(dist)} reassignments, "
        f"{failed} could not be fitted)"
    )
    kwm = {"method": method, **kw}
    checks = [
        mm.check_leads(panel, draws=draws, seed=1, **kwm),
        mm.check_placebo_dates(panel, draws=draws, seed=2, **kwm),
        mm.check_outcome(panel, "units_5p", "placebo outcome (5+ unit homes)", draws=draws, seed=3, **kwm),
        mm.check_outcome(
            panel,
            "units_1",
            "substitution (1-unit homes; no pass rule)",
            draws=draws,
            seed=4,
            rule=False,
            **kwm,
        ),
        mm.check_inside(
            panel[~panel["year"].isin([2020, 2021])],
            s,
            "excluding 2020-21",
            terms=(*mm.BIN_NAMES, "att"),
            draws=draws,
            seed=5,
            **kwm,
        ),
    ]
    treated = list(panel.loc[panel["T"].notna(), "place"].unique())
    groups = {pl: [pl] for pl in treated}
    if all(g in treated for g in durham_pair):
        groups["Durham city and county"] = list(durham_pair)
    loo, loo_table = mm.check_leave_one_out(panel, s, groups, method=method, **kw)
    checks.append(loo)
    big = panel[(panel["pop_2020"] >= 50000) | panel["T"].notna()]
    checks.append(
        mm.check_inside(big, s, "contamination (a): 50,000+ people only", draws=draws, seed=6, **kwm)
    )
    flagged = flagged or []
    name_b = "contamination (b): without pipeline-flagged places"
    res_b = mm.check_inside(panel[~panel["place"].isin(flagged)], s, name_b, draws=draws, seed=7, **kwm)
    checks.append({**res_b, "dropped_places": len(flagged)})
    local_rows = []
    for city, entries in (local or {}).items():
        for src, counts in entries:
            local_rows.append(local_check(panel, city, src, counts, s, draws, method, kw))
    checks.append({"check": "local measurement (reported)", "pass": None,
                   "note": "; ".join(f"{r['place']} {r['source']}: post ratio {r['post_ratio']:.2f}"
                                     for r in local_rows) or "skipped (no local data)"})  # fmt: skip
    for c in checks:
        log(f"check: {c}")
    rob, rob_notes = term_rows(f"main ({method})", s), []
    for other in [m for m in ("ppml", "re", "nb") if m != method]:  # nb = D-025's estimator (pooled_adu)
        robust(
            f"model: {other}",
            lambda o=other: term_rows(
                o, mm.summary(mm.estimate(panel, method=o, **kw), draws=draws, seed=8)[0]
            ),
            rob,
            rob_notes,
        )
    robust(
        "Borusyak imputation (point only)",
        lambda: [
            {"fit": "imputation", "term": k, "estimate": v} for k, v in mm.imputation_effects(panel).items()
        ],
        rob,
        rob_notes,
    )
    robust(
        "binary by-right dose",
        lambda: term_rows(
            "binary dose",
            mm.summary(mm.estimate(panel, method=method, binary_dose=True, **kw), draws=draws, seed=9)[0],
        ),
        rob,
        rob_notes,
    )
    robust(
        "all four modifiers",
        lambda: term_rows(
            "four modifiers",
            mm.summary(mm.estimate(panel, method=method, modifiers=list(mm.MODIFIERS)), draws=draws, seed=10)[
                0
            ],
        ),
        rob,
        rob_notes,
    )
    if metc is not None:
        robust(
            "Met Council, Twin Cities alone",
            lambda: term_rows(
                "Met Council alone",
                mm.summary(mm.estimate(metc, method=method, **kw), draws=draws, seed=11)[0],
            ),
            rob,
            rob_notes,
        )
    for r in rob:
        log(f"robustness: {r}")
    preds, verdicts = [], []
    for label, targets in transport.items():
        try:
            fit_t = mm.estimate(panel[~panel["place"].isin(targets)], method=method, **kw)
            _, boot_t = mm.summary(fit_t, draws=draws, seed=12)
            pr = mm.transport_predict(fit_t, boot_t, panel[panel["place"].isin(targets)], seed=SEED,
                                      widening=p["mm_transport_widening"])  # fmt: skip
            v = estimate_adu.transport_verdict(pr)
            preds.append(pr.assign(test=label))
            verdicts.append({"test": label, **v})
            log(f"out-of-sample {label}:\n{pr.round(1).to_string(index=False)}\nverdict {v}")
        except Exception as err:  # noqa: BLE001 (reported, not raised)
            verdicts.append({"test": label, "pass": False, "note": f"could not be estimated: {err}"})
            log(f"out-of-sample {label}: could not be estimated: {err}")
    drops = [{"kind": "place", "what": x} for x in f.dropped_places]
    drops += [{"kind": "column", "what": x} for x in f.dropped_columns]
    drops += [{"kind": "separated place-year", "what": f"{a} {b}"} for a, b in getattr(f, "separated", [])]
    out["estimates"] = s.assign(model=method, fallback_reason=why)
    out["bootstrap_draws"] = boot
    out["added_homes"] = added
    out["randomization"] = pd.DataFrame({"att_permuted": dist}).assign(att=att, p=p_ri, failed=failed)
    out["checks"] = pd.DataFrame(checks)
    out["leave_one_out"] = loo_table
    out["local_measurement"] = pd.DataFrame(local_rows)
    out["robustness"] = pd.concat([pd.DataFrame(rob), pd.DataFrame(rob_notes)], ignore_index=True)
    out["transport"] = pd.concat(preds, ignore_index=True) if preds else pd.DataFrame()
    out["transport_verdict"] = pd.DataFrame(verdicts)
    out["dropped"] = pd.DataFrame(drops, columns=["kind", "what"])
    return out


def local_check(panel, city, src, counts, s, draws, method, kw) -> dict:
    """Check 8: local 2-4 unit homes vs BPS for one treated city over the years the local source covers,
    before and after adoption; if the post-adoption totals differ by more than 25%, the main model is re-fit
    with that city's local counts on the covered years (its other years dropped)."""
    d = panel[panel["place"] == city]
    T = d["T"].iloc[0]
    years = set(counts["covered_years"])
    dd = d[d["year"].isin(years) & d["y"].notna()].set_index("year")
    loc = counts.set_index("year")["y"].reindex(dd.index, fill_value=0.0)
    pre, post = dd.index < T, dd.index >= T
    row = {"place": city, "source": src, "years": f"{min(dd.index)}-{max(dd.index)}" if len(dd) else "",
           "bps_pre": float(dd["y"][pre].sum()), "local_pre": float(loc[pre].sum()),
           "bps_post": float(dd["y"][post].sum()), "local_post": float(loc[post].sum())}  # fmt: skip
    row["post_ratio"] = row["local_post"] / row["bps_post"] if row["bps_post"] > 0 else np.nan
    if not np.isnan(row["post_ratio"]) and abs(row["post_ratio"] - 1) > 0.25:
        q = panel[(panel["place"] != city) | panel["year"].isin(years)].copy()
        on = (q["place"] == city).to_numpy()
        q.loc[on, "y"] = q.loc[on, "year"].map(counts.set_index("year")["y"]).fillna(0.0).to_numpy()
        try:
            ss = mm.summary(mm.estimate(q, method=method, **kw), draws=draws, seed=13)[0].set_index("term")
            row.update({"local_fit_att": ss.loc["att", "estimate"], "local_fit_low": ss.loc["att", "low"],
                        "local_fit_high": ss.loc["att", "high"]})  # fmt: skip
        except Exception as err:  # noqa: BLE001 (reported)
            row["local_fit_note"] = f"could not be estimated: {err}"
    return row


def local_inputs(store) -> dict:
    """Local 2-4 unit counts per treated city and source, with the years the source covers for that city."""
    out = {}
    for city, sources in LOCAL.items():
        state = "MN" if city.startswith("27") else "NC"
        permits = store.read(state, "permits")
        for src in sources:
            rows = permits[(permits["source"] == src) & (permits["jurisdiction_geoid"] == city)]
            if rows.empty:
                continue
            covered = sorted(rows["issue_year"].dropna().astype(int).unique())
            if src == "metc_residential_permits":
                covered = [y for y in covered if y >= 2016]  # Met Council flags 2-4 unit buildings from 2016
            c = mm.local_counts(permits, src)
            c = (
                c.xs(city, level="geoid")["y"]
                if city in c.index.get_level_values(0)
                else pd.Series(dtype=float)
            )
            counts = pd.DataFrame({"year": covered, "y": [float(c.get(y, 0.0)) for y in covered]})
            counts["covered_years"] = counts["year"]
            out.setdefault(city, []).append((src, counts))
    return out


def write(out: dict, path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for name, df in out.items():
        df.to_csv(path / f"{name}.csv", index=False)
    log(f"wrote {len(out)} CSVs to {path}/")


def simulated_panel(seed: int = 0) -> pd.DataFrame:
    """A panel shaped like the real one (four states, 2010-2025, mostly zeros, seven treated places in
    2020/2022/2024) with known effects, for --dry-run only."""
    rng = np.random.default_rng(seed)
    years = np.arange(2010, 2026)
    rate = np.interp(years, [2010, 2020, 2021, 2022, 2025], [4.7, 3.1, 3.0, 5.3, 6.6])
    treated = {"MNT1": ("MN", 2020), "NCT1": ("NC", 2020), "NCT2": ("NC", 2020), "NCT3": ("NC", 2022),
               "TXT1": ("TX", 2024), "TXT2": ("TX", 2024), "OHT1": ("OH", 2024)}  # fmt: skip
    places = list(treated) + [f"{st}C{i:02d}" for st in mm.STATES for i in range(30)]
    rows = []
    for pl in places:
        st, T = treated.get(pl, (pl[:2], np.nan))
        alpha = rng.normal(-7.0, 0.7) if pl in treated else rng.normal(-9.0, 2.0)  # many never permit
        elig, pcr, lv = rng.uniform(5e3, 8e4), rng.normal(1, 0.2), rng.normal(12.5, 0.3)
        dose = rng.choice([1 / 3, 0.5, 1.0]) if pl in treated else 0.0
        pop = 60000.0 if pl in treated else float(rng.choice([20000, 60000]))
        tr = pl in treated
        for y, r in zip(years, rate, strict=True):
            e = y - T
            post = pl in treated and e >= 0
            eff = (0.3 if e <= 1 else 0.6 if e <= 3 else 0.8) * dose if post else 0.0
            adu = float(rng.random() < 0.3 and y >= 2018)
            mu = elig * math.exp(alpha + 0.02 * (y - 2010) + eff - 0.2 * adu)
            rows.append(
                {
                    "state": st, "place": pl, "name": pl, "pop_2020": pop, "band": 2,
                    "status": "treated" if tr else "uncoded", "year": int(y), "y": float(rng.poisson(mu)),
                    "eligible": elig, "T": T, "dose": dose if post else 0.0, "p_by_right": float(post),
                    "adu": adu, "rate": r, "units_1": float(rng.poisson(5 * mu / math.exp(eff))),
                    "units_5p": float(rng.poisson(20)), "pcr": pcr if tr else np.nan,
                    "log_value": lv if tr else np.nan, "pre_permits": 1.0 if tr else np.nan,
                    "hh_growth": rng.normal(0.05, 0.02) if tr else np.nan,
                }
            )  # fmt: skip
    return pd.DataFrame(rows)


def full(store, out_dir: Path, workers: int) -> None:
    p = {k: v.value for k, v in load_params("mm").items()}
    log("building the main panel")
    panel = mm.build_panel(store).data
    log(
        f"panel: {panel['place'].nunique()} places, "
        f"{int(panel['y'].notna().sum())} place-years with an outcome"
    )
    metc = mm.build_panel(
        store, states=("MN",), years=range(2016, 2026), source="metc_residential_permits"
    ).data
    flagged = pipeline_flagged(panel)
    log(f"check 7b drops {len(flagged)} pipeline-flagged comparison places: {flagged}")
    out = run(panel, p, workers, local=local_inputs(store), metc=metc, flagged=flagged)
    write(out, out_dir)


def dry_run(out_dir: Path, workers: int, fallback: bool = False) -> None:
    p = {k: v.value for k, v in load_params("mm").items()}
    p.update(mm_estimation_bootstrap_draws=49, mm_estimation_permutations=16)
    panel = simulated_panel()
    log(f"DRY RUN on a simulated panel ({panel['place'].nunique()} places); not real data")
    sim = panel[(panel["place"] == "MNT1") & (panel["year"] >= 2016)]  # a local source counting 2× from 2016
    local = {
        "MNT1": [
            (
                "simulated_src",
                pd.DataFrame({"year": sim["year"], "y": 2 * sim["y"], "covered_years": sim["year"]}),
            )
        ]
    }
    out = run(panel, p, workers, local=local, transport={"A": ["NCT1", "NCT2", "NCT3"], "B": ["MNT1"]},
              flagged=["MNC00", "MNC01"], durham_pair=("NCT1", "NCT2"),
              force_fallback="forced for the dry run" if fallback else "")  # fmt: skip
    write(out, out_dir)


COVERAGE_TRUTH = {
    "beta_0": 0.3,
    "beta_2": 0.6,
    "beta_4": 0.8,
    "theta_pcr": 0.0,
    "theta_log_value": 0.0,
    "rho": 0.0,
    "delta": -0.2,
}  # fmt: skip  (the effects `simulated_panel` builds in)


def coverage(panels: int = 40, draws: int = 199) -> None:
    """How well the main model's 90% bootstrap intervals cover the truth on panels shaped like the real one
    (`simulated_panel`, seven treated places): coverage, bias and sd of estimates over mean bootstrap SE."""
    rows = []
    for seed in range(100, 100 + panels):
        sm, _ = mm.summary(mm.estimate(simulated_panel(seed), modifiers=list(mm.MAIN_MODIFIERS)), draws=draws,
                           seed=seed)  # fmt: skip
        sm = sm.set_index("term")
        rows.append({**{t: sm.loc[t, "low"] <= v <= sm.loc[t, "high"] for t, v in COVERAGE_TRUTH.items()},
                     **{f"est_{t}": sm.loc[t, "estimate"] for t in COVERAGE_TRUTH},
                     **{f"se_{t}": sm.loc[t, "se"] for t in COVERAGE_TRUTH}})  # fmt: skip
    d = pd.DataFrame(rows)
    t = pd.DataFrame({
        "coverage_90": d[list(COVERAGE_TRUTH)].mean(),
        "bias": pd.Series({k: d[f"est_{k}"].mean() - v for k, v in COVERAGE_TRUTH.items()}),
        "sd_over_se": pd.Series({k: d[f"est_{k}"].std() / d[f"se_{k}"].mean() for k in COVERAGE_TRUTH}),
    })  # fmt: skip
    print(f"{panels} simulated panels, {draws} bootstrap draws each:\n{t.round(3).to_string()}")


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--smoke", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fallback", action="store_true", help="--dry-run only: take the fallback path")
    g.add_argument("--full", action="store_true")
    g.add_argument("--coverage", action="store_true")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.smoke:
        smoke(DataStore())
    elif a.coverage:
        coverage()
    elif a.dry_run:
        dry_run(a.out or Path("dry-run-out"), a.workers, fallback=a.fallback)
    else:
        if a.out is None:
            ap.error("--full needs --out")
        full(DataStore(), a.out, a.workers)


if __name__ == "__main__":
    main()
