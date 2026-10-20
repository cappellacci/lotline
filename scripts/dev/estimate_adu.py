#!/usr/bin/env python3
"""The ADU estimation (D-026 imputation; D-023's estimator is a robustness run): smoke test of the panel, or
the one real run.

    uv run python scripts/dev/estimate_adu.py --smoke      # counts of places and years only, no estimates
    uv run python scripts/dev/estimate_adu.py --full       # the one run, after Ben approves D-026

The panel: every Twin Cities metro place with Met Council residential permits, 2016-2025 (St. Paul never;
places with no dated ADU rule left out and counted). The full run (D-026): the imputation estimator with
place and year effects fitted on untreated place-years (`lotline.model.estimate_adu.impute`), exclusions
listed, randomization inference that moves each dose path with its adoption year (primary), the stratified
place bootstrap (range), the seven D-026 checks, heterogeneity described per place, the robustness estimates,
and the transport test for Austin (2016-2023), Raleigh (2021-2025) and Durham (2019-2025). --out is a
directory: estimates.csv, bootstrap_draws.csv, randomization.csv, checks.csv, heterogeneity.csv,
robustness.csv, transport.csv, transport_verdict.csv, dropped.csv and panel.csv. A numerical failure
raises (EstimationError) before anything is written.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore
from lotline.model import estimate_adu as est

SOURCE = "metc_residential_permits"
TRANSPORT = {  # place: (state, panel years incl. pre-adoption, scored years)
    "4805000": ("TX", range(2016, 2024), (2016, 2023)),  # Austin
    "3755000": ("NC", range(2019, 2026), (2021, 2025)),  # Raleigh (ADU flags from 2019)
    "3719000": ("NC", range(2016, 2026), (2019, 2025)),  # Durham
}


def smoke(store) -> None:
    panel = est.build_panel("MN", store, source=SOURCE)
    d = panel.data
    places = d.drop_duplicates("place")
    treated = places["T"].notna()
    in_window = treated & (places["T"] >= 2016)
    print(
        f"Twin Cities panel: {d['place'].nunique()} places × {d['year'].nunique()} years "
        f"({d['year'].min()}-{d['year'].max()}) = {len(d)} place-years"
    )
    print(f"  left out, no dated ADU rule: {len(panel.excluded_no_rule)} places")
    print(f"  left out, holdout (St. Paul): {len(panel.excluded_holdout)}")
    print(
        f"  treated (a by-right rule at some point): {int(treated.sum())}, of which adopting in 2016-2025: "
        f"{int(in_window.sum())}; never treated in the window: {int((~treated).sum())}"
    )
    first = d["year"].min()
    print(f"  D-026 exclusions: treated in or before {first}: {int((places['T'] <= first).sum())}")
    pre = d[d["T"].notna() & (d["T"] > first) & (d["year"] < d["T"])]
    n_zero = int((pre.groupby("place")["y"].sum() == 0).sum())
    print(f"  treated in the window with no ADU before adoption: {n_zero}")
    print(
        f"  places with no ADU permit in any year (dropped by PPML): "
        f"{int((d.groupby('place')['y'].sum() == 0).sum())}"
    )
    n_mm = int(d.groupby("place")["mm"].max().sum())
    print(f"  places with a missing-middle rule in force in some year: {n_mm}")
    print(
        f"  place-years with missing modifiers among treated places: "
        f"{int(places.loc[treated, list(est.MODIFIERS)].isna().any(axis=1).sum())} places"
    )
    for note in panel.notes:
        print("  note:", note)


def full(store, out: Path | None) -> None:
    """The one pre-registered D-026 run (only after Ben approves D-026). Any numerical failure raises
    (estimate_adu.EstimationError) before anything is written; on success every table is written to the
    directory `out` as named CSVs."""
    p = {k: v.value for k, v in load_params("adu").items()}
    draws, perms = int(p["adu_estimation_bootstrap_draws"]), int(p["adu_estimation_permutations"])
    panel = est.build_panel("MN", store, source=SOURCE).data
    res = est.impute(panel)
    f = res.fit
    print(f"untreated PPML converged in {f.iterations} iterations; kept {int(f.keep.sum())} untreated rows")
    print(f"dropped columns: {f.dropped_columns}; separated rows: {len(f.separated)}")
    print("excluded places:")
    print(res.excluded.to_string(index=False))
    print(f"contributing treated places: {len(res.contributing)} (floor {est.MIN_CONTRIBUTING})")
    if not res.estimable:
        print("D-026: fewer contributing treated places than the floor; the ATT is not estimable. Stopping.")
        return
    boot = est.place_bootstrap(panel, draws=draws, seed=20261020)
    ri = est.randomization_inference(panel, permutations=perms, seed=20261020)
    main = est.summarize_att(res, boot, ri)
    print(main.round(4).to_string(index=False))
    print(
        f"randomization inference: ATT {ri.att:.4f} per 1,000 parcels a year, p = {ri.p:.3f} "
        f"({ri.n_assignments} assignments, {'all enumerated' if ri.enumerated else 'drawn'}; "
        f"smallest attainable p {ri.p_min:.3f})"
    )
    if len(res.contributing) < 10:
        print(
            "range: fewer than 10 contributing treated places, so the bootstrap range is probably too narrow"
        )
    checks = [
        est.check_pretrends(panel, draws=draws, seed=1),
        est.check_anticipation(panel, main, draws=draws, seed=2),
        est.check_placebo_dates(panel, draws=draws, seed=3),
        est.check_placebo_outcome(panel, draws=draws, seed=4),
        est.check_excluding(panel, main),
        est.check_leave_one_out(panel, main),
        est.check_first_ring(panel, main, neighbors=None),  # adjacency dataset not built yet (D-026)
    ]
    for c in checks:
        print(c)
    # heterogeneity, described only (D-026: θ is not identified)
    mods = panel.drop_duplicates("place").set_index("place")[list(est.MODIFIERS)]
    het = res.per_place.join(mods, on="place")
    print(het.round(3).to_string(index=False))
    print("Spearman rank correlations with ATT_i (description, no test):")
    print(het[["att_i", *est.MODIFIERS]].corr(method="spearman")["att_i"].round(2).to_string())
    u = res.rows[res.rows["used"]]
    dose_att = 1000 * (u["y"] - u["mu0"]).sum() / (u["eligible"] * u["dose"]).sum()
    pooled = est.estimate(panel[panel["place"].isin(res.rows["place"])], cohort_cells=False, use_rate=False)
    robust = {
        "dose_weighted_att": dose_att,
        **{f"d023_pooled_{k}": v for k, v in est.aggregate(pooled).items()},
    }
    print("robustness:", robust)
    targets, window = [], {}
    for g, (state, years, scored) in TRANSPORT.items():
        targets.append(est.build_panel(state, store, years=years, geoids=[g]).data)
        window[g] = scored
    pred = est.transport_predict(
        res, boot, pd.concat(targets, ignore_index=True), seed=20261020, window=window
    )
    print(pred.round(1).to_string(index=False))
    verdict = est.transport_verdict(pred)
    print(verdict)
    if out:
        out.mkdir(parents=True, exist_ok=True)
        main.to_csv(out / "estimates.csv", index=False)
        boot.to_csv(out / "bootstrap_draws.csv", index=False)
        pd.DataFrame({"att_permuted": ri.dist}).assign(att=ri.att, p=ri.p).to_csv(
            out / "randomization.csv", index=False
        )
        pd.DataFrame(checks).to_csv(out / "checks.csv", index=False)
        het.to_csv(out / "heterogeneity.csv", index=False)
        pd.DataFrame([robust]).to_csv(out / "robustness.csv", index=False)
        pred.to_csv(out / "transport.csv", index=False)
        pd.DataFrame([verdict]).to_csv(out / "transport_verdict.csv", index=False)
        drops = [{"kind": "place", "what": f"{r.place}: {r.reason}"} for r in res.excluded.itertuples()]
        drops += [{"kind": "column", "what": x} for x in f.dropped_columns]
        drops += [{"kind": "separated place-year", "what": f"{pl} {yr}"} for pl, yr in f.separated]
        pd.DataFrame(drops, columns=["kind", "what"]).to_csv(out / "dropped.csv", index=False)
        res.rows.to_csv(out / "panel.csv", index=False)
        print(f"wrote CSVs to {out}/")


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--smoke", action="store_true")
    g.add_argument("--full", action="store_true")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    store = DataStore()
    smoke(store) if a.smoke else full(store, a.out)


if __name__ == "__main__":
    main()
