#!/usr/bin/env python3
"""D-082 run 5: the missing-middle accuracy tests of §7, scored on run 4's fits.

    uv run python scripts/dev/mm_tests_d082.py \
        --run4 reports/mm-d082/run4-refit --out reports/mm-d082/run5-tests

Ben's go-ahead: "Can we get close to having a finalized model over night?" (2026-11-12), which covers runs
2–6 in order. Pass rules are `lotline.model.mm_tests` (fixed in code before this script was first run), and
their thresholds are in `config/params/mm.yaml`.

What it scores, for M and challengers C1, C3 and C4:
- **Leave one state out:** each held-out state's fit places are predicted from run 4's
  `<model>_without_<state>` fit (`fits.csv`), with joint draws (`calibrate_mm.predict_places`), and get
  D-040's verdict.
- **Test A, new places:** non-Oregon fit places that were not in D-059's fit set or whose event changed
  (year, or the standards class S), each predicted over its
  post-years (5-year horizon) from the fit that leaves its whole state out. That is stricter than leaving out
  one place, and it needs no new fit.
- **Test C, no-reform floor:** coded "none" places and Franklin County places with no event and zero dose
  throughout. Each gets M's baseline (own growth, 3 pre-years, zero floor) with T = 2021 and no effect, scored
  over 2021–25. The no-reform forecast is the same for every model (C3 and C4 only change the effect), so all
  of them get the same verdict.
- **Placebo:** M's places with events moved 3 years early and pre-years only (`place_inputs(shift=3)`). One
  r5 profile is fitted, and its 90% upper bound must be below run 4's main r5.
- **Place coverage:** randomized P10–P90 coverage over every place scored above (`mm_tests.randomized_pit`).
- **Test B (roll check):** with `--run3`, each roll area's places (panel places only) are predicted over the
  permit years matched to the roll pair (`B_AREAS`) from each model's full fit: post-event years from the
  place's own Place, every other year from a no-effect baseline. The prediction is 2-4 unit buildings and the
  observation is lots gaining one; pass if Wake, Franklin and Minneapolis are each inside P10-P90.
- **Data tier:** not run here (see the README).
- **Selection (§5):** `calibrate_mm.select_model` on run 4's `place_scores.csv`, with the A–C pass counts.

Holdouts: the same panel as run 4 (St. Paul, Ramsey, Charlotte and Mecklenburg asserted absent). No
unblinding, no download, nothing written to config.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.io import DataStore
from lotline.model import calibrate_mm as cal
from lotline.model import estimate_mm as mm
from lotline.model import mm_tests as mt
from lotline.model import rule_tags

HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("d082", HERE / "calibrate_mm_d082.py")
d082 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d082)
d054, d042 = d082.d054, d082.d042

MODELS = ("M", "C1", "C3", "C4")
DRAWS, SEED = 20_000, 20261112
FRANKLIN = "39049"
D059_SCORES = Path("reports/mm-d059/place_scores.csv")
# Test B: permit years matched to each roll pair (a building permitted in year t is on the roll about a year
# later): Wake 2019-11 -> 2023-12, Franklin 2016-12 -> 2024-12, Minneapolis 2017 -> 2024,
# Met Council 2021 -> 2025.
B_AREAS = {
    "Wake": (2019, 2022),
    "Franklin": (2016, 2023),
    "Minneapolis": (2017, 2023),
    "Met Council": (2021, 2024),
}
B_PASS_AREAS = ("Wake", "Franklin", "Minneapolis")  # D-082 §7 test B; Met Council is reported only


def fold_fits(run4: Path) -> dict[str, dict]:
    f = pd.read_csv(run4 / "fits.csv")
    out = {}
    for r in f.itertuples():
        out[r.fit] = {"theta": r.per_1000 / 1000, "log_se": r.log_se, "alpha": r.alpha, "half": r.half,
                      "b": getattr(r, "b", 0.0) if pd.notna(getattr(r, "b", 0.0)) else 0.0}  # fmt: skip
    return out


def summarize(draws: np.ndarray, observed: float) -> dict:
    p10, p50, p90 = np.percentile(draws, [10, 50, 90])
    return {"observed": float(observed), "p10": float(p10), "p50": float(p50), "p90": float(p90)}


def main(run4: Path, out: Path, run3: Path | None) -> None:
    t0 = time.time()

    def tick(msg):
        print(f"[{time.time() - t0:5.0f}s] {msg}", flush=True)

    rng = np.random.default_rng(SEED)
    p = d082.params()
    pm = {k: mt._p(k) for k in ("mm_placebo_shift_years", "mm_test_c_first_year")}
    store = DataStore()
    panel = mm.build_panel(store, states=d082.STATES).data
    assert not set(panel["place"]) & set(d082.HOLDOUTS), "holdout places in the panel"
    state_of = panel.groupby("place")["state"].first().to_dict()
    name_of = panel.groupby("place")["name"].first().to_dict()
    rules = d082.rule_rows(store, d082.STATES)
    classes = d082.bps_classes(store, set(panel["place"]))
    all_events, _ = d082.events_d082(panel, rules)
    usable = {g: e for g, e in all_events.items() if e.classes}
    fit_events = {g: e for g, e in usable.items() if g not in d082.TESTS and g not in d082.EXCLUDE}
    test_events = {g: e for g, e in usable.items() if g in d082.TESTS}
    m_fit, rp = d082.build_m(panel, classes, fit_events, p, p["s_dose"])
    fit_ids = [q.geoid for q in m_fit]
    targets = {q.geoid: q for q in d054.horizon(m_fit)}
    c1_targets = {q.geoid: q for q in d054.horizon(d082.build_c1(panel, classes, fit_events, all_events, p,
                                                                 p["s_dose"]))}  # fmt: skip
    pace = d042.capacity(
        classes, rp, {g: (e.year, e.prior_cap) for g, e in {**fit_events, **test_events}.items()}
    )
    fits = fold_fits(run4)
    tick(f"setup: {len(fit_ids)} fit places")

    def target_for(model, g, z):
        q = c1_targets.get(g, targets[g]) if model == "C1" else targets[g]
        return replace(q, z=float(z.get(g, 0.0))) if model == "C3" else q

    pits = {k: [] for k in MODELS}
    # ---- leave one state out + test A (fold = without the place's state) ----
    # "Newly entering" (§7 A: from step 1 or method changes): a non-Oregon fit place that was not in D-059's
    # fit set, or whose D-082 event differs from D-059's (another year, or the standards class S).
    d059 = pd.read_csv(D059_SCORES, dtype={"geoid": str})
    d059_T = dict(
        zip(d059.loc[~d059["test_place"], "geoid"], d059.loc[~d059["test_place"], "T"], strict=True)
    )
    new_ids = [g for g in fit_ids if state_of[g] != "OR"
               and (g not in d059_T or int(d059_T[g]) != int(fit_events[g].year)
                    or fit_events[g].dose_class == "S")]  # fmt: skip

    def why(g):
        if g not in d059_T:
            return "not in D-059"
        e = fit_events[g]
        return f"D-059 T {int(d059_T[g])} -> D-082 {e.year} {e.dose_class}"

    new_why = {name_of[g]: why(g) for g in new_ids}
    same = {name_of[g]: fit_events[g].year for g in fit_ids if state_of[g] != "OR" and g not in new_ids}
    loso_rows, a_rows = [], []
    for s in d082.STATES:
        held = [g for g in fit_ids if state_of[g] == s]
        if not held:
            continue
        keep = [g for g in fit_ids if state_of[g] != s]
        z = cal.conditional_z(pace, keep)
        for k in MODELS:
            f = fits.get(f"{k}_without_{s}")
            if f is None:
                continue
            qs = [target_for(k, g, z) for g in held]
            dr = cal.predict_places(qs, f["theta"], f["log_se"], f["alpha"], f["half"],
                                    b=f["b"] if k == "C3" else 0.0, draws=DRAWS, seed=SEED)  # fmt: skip
            tot = cal.state_total(dr, held)
            obs = float(sum(q.y.sum() for q in qs))
            loso_rows.append({"model": k, "state": s, "fit_places": len(held)} | summarize(tot, obs))
            for q in qs:
                pits[k].append(mt.randomized_pit(dr[q.geoid].sum(axis=1), float(q.y.sum()), rng))
                if q.geoid in new_ids:
                    a_rows.append({"model": k, "geoid": q.geoid, "name": q.name, "state": s, "T": q.T}
                                  | summarize(dr[q.geoid].sum(axis=1), float(q.y.sum())))  # fmt: skip
        tick(f"LOSO {s}: {len(held)} places")
    loso_df, a_df = pd.DataFrame(loso_rows), pd.DataFrame(a_rows)

    # ---- test C: no-reform floor ----
    none_ids = set().union(*(rule_tags.none_places(r["raw"]) for r in rules.values()))
    oh_bps = store.read("OH", "bps_place_year")
    franklin = set(oh_bps.loc[oh_bps["county_geoid"].astype(str) == FRANKLIN, "geoid"].dropna().astype(str))
    max_dose = panel.groupby("place")["dose"].max().fillna(0.0)
    c_ids = sorted(g for g in (none_ids | franklin) & set(panel["place"])
                   if g not in all_events and max_dose.get(g, 0.0) <= 0 and g not in d082.TESTS)  # fmt: skip
    first = int(pm["mm_test_c_first_year"])
    sub = panel[panel["place"].isin(c_ids)].copy()
    sub["T"] = float(first)
    sub["dose"] = 0.0
    sub["eligible"] = sub["eligible"].where(sub["eligible"] > 0, 1.0)
    c_places = [q.upto(first + 4) for q in cal.place_inputs(sub, c_ids, p["margin"], p["sigma"], growth="own",
                                                            zero_floor=True)]  # fmt: skip
    c_rows, c_pits = [], []
    c_draws = cal.benchmark_places(c_places, 0.0, 1.0, draws=DRAWS, seed=SEED)
    for q in c_places:
        tot = c_draws[q.geoid].sum(axis=1)
        c_rows.append({"geoid": q.geoid, "name": q.name, "state": state_of[q.geoid],
                       "franklin": q.geoid in franklin, "none_coded": q.geoid in none_ids}
                      | summarize(tot, float(q.y.sum())))  # fmt: skip
        c_pits.append(mt.randomized_pit(tot, float(q.y.sum()), rng))
    c_df = pd.DataFrame(c_rows)
    c_state = []
    for s, g in c_df.groupby("state"):
        ids = g["geoid"].tolist()
        c_state.append({"state": s, "places": len(ids)}
                       | summarize(cal.state_total(c_draws, ids), float(g["observed"].sum())))  # fmt: skip
    c_state = pd.DataFrame(c_state)
    test_c = mt.test_c(c_df, c_state)
    tick(f"test C: {len(c_df)} places")

    # ---- placebo ----
    shift = int(pm["mm_placebo_shift_years"])
    plac = cal.place_inputs(rp, fit_ids, p["margin"], p["sigma"], growth="own", zero_floor=True, shift=shift)
    pr5 = cal.five_year_profile(plac)
    run4_summary = json.loads((run4 / "summary.json").read_text())
    main_r5 = float(run4_summary["r5_M"]["r5"])
    placebo = mt.placebo(pr5.high, main_r5) | {"placebo_r5": pr5.r5, "placebo_low": pr5.low,
                                               "placebo_places": len(plac)}  # fmt: skip
    tick(f"placebo r5 {pr5.r5:.5f} ({pr5.low:.5f}-{pr5.high:.5f}) vs main {main_r5:.5f}")

    # ---- test B (roll check; run 3's lots gaining a 2-4 building) ----
    test_b = {k: {"pass": None, "status": "pending: no run-3 roll gains"} for k in MODELS}
    b_rows = []
    gains_path = run3 / "roll_gains_by_place.csv" if run3 is not None else None
    if gains_path is not None and gains_path.exists():
        gains = pd.read_csv(gains_path, dtype={"jurisdiction_geoid": str})
        gains = gains[gains["read"] == "main"]
        m_test, _ = d082.build_m(panel, classes, test_events, p, p["s_dose"])
        all_places = {q.geoid: q for q in m_fit + m_test}
        z_full = cal.conditional_z(pace, fit_ids)
        for area, (y0, y1) in B_AREAS.items():
            g_area = gains[gains["area"] == area]
            ids = [g for g in g_area["jurisdiction_geoid"] if g in set(panel["place"])]
            obs_all = int(g_area["gained_24"].sum())
            obs = int(g_area.loc[g_area["jurisdiction_geoid"].isin(ids), "gained_24"].sum())
            years = list(range(y0, y1 + 1))
            # Baseline for every place-year not covered by a post-event Place: a no-effect place with T = y0.
            base = panel[panel["place"].isin(ids)].copy()
            base["T"], base["dose"] = float(y0), 0.0
            base["eligible"] = base["eligible"].where(base["eligible"] > 0, 1.0)
            bq = {q.geoid: q for q in cal.place_inputs(base, ids, p["margin"], p["sigma"], growth="own",
                                                       zero_floor=True)}  # fmt: skip
            for k in MODELS:
                f = fits.get(f"{k}_full")
                if f is None:
                    continue
                tot = np.zeros(DRAWS)
                for g in ids:
                    q = all_places.get(g)
                    post = [] if q is None else [y for y in years if y in set(q.years)]
                    if post:
                        # the full post-event Place (all years, not the 5-year horizon); C1 differs from M
                        # only in Oregon, so these non-Oregon areas use M's Place for every model.
                        qq = replace(q, z=float(z_full.get(g, 0.0))) if k == "C3" else q
                        dr = cal.predict_places(
                            [qq],
                            f["theta"],
                            f["log_se"],
                            f["alpha"],
                            f["half"],
                            b=f["b"] if k == "C3" else 0.0,
                            draws=DRAWS,
                            seed=SEED,
                        )[g]
                        cols = [i for i, y in enumerate(qq.years) if y in post]
                        tot += dr[:, cols].sum(axis=1)
                    pre = [y for y in years if y not in post]
                    if pre and g in bq:
                        b = bq[g]
                        cols = [i for i, y in enumerate(b.years) if y in pre]
                        if cols:
                            tot += cal.benchmark_places([b], 0.0, 1.0, draws=DRAWS, seed=SEED)[g][
                                :, cols
                            ].sum(axis=1)
                b_rows.append({"model": k, "area": area, "permit_years": f"{y0}-{y1}", "places": len(ids),
                               "observed_all_places": obs_all} | summarize(tot, obs))  # fmt: skip
        b_df = pd.DataFrame(b_rows)
        for k in MODELS:
            r = b_df[(b_df["model"] == k) & b_df["area"].isin(B_PASS_AREAS)]
            cols = zip(r["area"], r["observed"], r["p10"], r["p90"], strict=True)
            ins = {a: mt.inside(o, lo, hi) for a, o, lo, hi in cols}
            test_b[k] = {"areas_inside": ins, "pass": bool(ins) and all(ins.values())}
        out.mkdir(parents=True, exist_ok=True)
        b_df.to_csv(out / "test_b_areas.csv", index=False)
        tick(
            "test B: "
            + ", ".join(
                f"{a} obs {o} P10-P90 {lo:.0f}-{hi:.0f}"
                for a, o, lo, hi in zip(
                    b_df[b_df["model"] == "M"]["area"],
                    b_df[b_df["model"] == "M"]["observed"],
                    b_df[b_df["model"] == "M"]["p10"],
                    b_df[b_df["model"] == "M"]["p90"],
                    strict=True,
                )
            )
        )

    # ---- per model ----
    res = {}
    for k in MODELS:
        a = mt.test_a(a_df[a_df["model"] == k]) if len(a_df) else mt.test_a(pd.DataFrame())
        lo = mt.loso(loso_df[loso_df["model"] == k]) if len(loso_df) else {"pass": None}
        cov = mt.place_coverage(pits[k] + c_pits)
        passed = sum(bool(x) for x in (a["pass"], test_b[k]["pass"], test_c["pass"]))
        res[k] = {"test_a": a, "test_c": test_c, "test_b": test_b[k], "loso": lo, "place_coverage": cov,
                  "tests_a_c_passed": passed}  # fmt: skip
    passed = {k: v["tests_a_c_passed"] for k, v in res.items()}
    scores = pd.read_csv(run4 / "place_scores.csv", dtype={"geoid": str})
    fs = scores[~scores["test_place"]]
    sel = cal.select_model(fs, passed, "M", d082.CHALLENGERS, p["se_margin"])

    out.mkdir(parents=True, exist_ok=True)
    loso_df.to_csv(out / "loso_states.csv", index=False)
    a_df.to_csv(out / "test_a_places.csv", index=False)
    c_df.to_csv(out / "test_c_places.csv", index=False)
    c_state.to_csv(out / "test_c_states.csv", index=False)
    summary = {
        "models": res,
        "placebo": placebo,
        "tests_passed": passed,
        "selection": {"chosen": sel["chosen"], "table": sel["table"].to_dict("records")},
        "new_places_test_a": new_why,
        "unchanged_non_oregon_places": same,
        "test_c_places": len(c_df),
        "data_tier": "not run (see README)",
        "seed": SEED,
        "draws": DRAWS,
        "seconds": round(time.time() - t0),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run4", type=Path, required=True)
    ap.add_argument("--run3", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    main(a.run4, a.out, a.run3)
