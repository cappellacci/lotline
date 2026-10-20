#!/usr/bin/env python3
"""The D-023 ADU estimation: smoke test of the panel, or the one real run.

    uv run python scripts/dev/estimate_adu.py --smoke      # counts of places and years only, no estimates
    uv run python scripts/dev/estimate_adu.py --full       # the pre-registered run (once, when Ben says so)

The panel: every Twin Cities metro place with Met Council residential permits, 2016-2025 (St. Paul never;
places with no dated ADU rule left out and counted). The full run: PPML with place and year fixed effects and
cohort × event-time effects (`lotline.model.estimate_adu`), the wild cluster score bootstrap (999 draws),
randomization inference (999 permutations of adoption years), the five checks of D-023, and the transport test
for Austin (2016-2023), Raleigh (2021-2025) and Durham (2019-2025). --out is a directory: estimates.csv,
bootstrap_draws.csv, randomization.csv, checks.csv, transport.csv, transport_verdict.csv, dropped.csv and
panel.csv. A numerical failure raises (EstimationError) before anything is written.
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
    """The one pre-registered run. Any numerical failure raises (estimate_adu.EstimationError) before anything
    is written; on success every table is written to the directory `out` as named CSVs."""
    p = {k: v.value for k, v in load_params("adu").items()}
    draws, perms = int(p["adu_estimation_bootstrap_draws"]), int(p["adu_estimation_permutations"])
    kw = {"modifiers": list(est.MODIFIERS)}
    panel = est.build_panel("MN", store, source=SOURCE).data
    # D-023 implementation choice (Ben, 2026-10-20): places that adopted before 2010 have no pre-adoption
    # measurements, so they don't inform the modifier terms (missing -> zero deviation in the design)
    early = panel["T"] < 2010
    panel.loc[early, list(est.MODIFIERS)] = float("nan")
    print(f"modifiers set to missing for {panel.loc[early, 'place'].nunique()} places adopted before 2010")
    fit = est.estimate(panel, **kw)
    f = fit.fit
    print(
        f"PPML converged in {f.iterations} iterations; kept {int(f.keep.sum())} of {len(f.keep)} place-years"
    )
    print(f"dropped places (no ADU permit in any kept year): {len(f.dropped_places)}")
    print(f"dropped columns: {f.dropped_columns}")
    print(f"separated observations dropped: {len(f.separated)}")
    boot = est.score_bootstrap(fit, draws=draws, seed=20261020)
    main = est.summarize(fit, boot)
    print(main.round(4).to_string(index=False))
    att, p_ri, ri_dist = est.randomization_inference(panel, permutations=perms, seed=20261020, **kw)
    print(f"randomization inference: overall effect {att:.4f}, p = {p_ri:.3f}")
    checks = [
        est.check_leads(panel, draws=draws, seed=1, **kw),
        est.check_placebo_dates(panel, draws=draws, seed=2, **kw),
        est.check_placebo_outcome(panel, draws=draws, seed=3, **kw),
        est.check_excluding(panel, main, draws=draws, seed=4, **kw),
        est.check_leave_one_out(panel, main, **kw),
    ]
    for c in checks:
        print(c)
    targets, window = [], {}
    for g, (state, years, scored) in TRANSPORT.items():
        targets.append(est.build_panel(state, store, years=years, geoids=[g]).data)
        window[g] = scored
    pred = est.transport_predict(
        fit,
        boot,
        pd.concat(targets, ignore_index=True),
        seed=20261020,
        widening=p["adu_transport_widening"],
        window=window,
    )
    print(pred.round(1).to_string(index=False))
    verdict = est.transport_verdict(pred)
    print(verdict)
    if out:
        out.mkdir(parents=True, exist_ok=True)
        main.to_csv(out / "estimates.csv", index=False)
        boot.to_csv(out / "bootstrap_draws.csv", index=False)
        pd.DataFrame({"att_permuted": ri_dist}).assign(att=att, p=p_ri).to_csv(
            out / "randomization.csv", index=False
        )
        pd.DataFrame(checks).to_csv(out / "checks.csv", index=False)
        pred.to_csv(out / "transport.csv", index=False)
        pd.DataFrame([verdict]).to_csv(out / "transport_verdict.csv", index=False)
        drops = [{"kind": "place", "what": x} for x in f.dropped_places]
        drops += [{"kind": "column", "what": x} for x in f.dropped_columns]
        drops += [{"kind": "separated place-year", "what": f"{pl} {yr}"} for pl, yr in f.separated]
        pd.DataFrame(drops, columns=["kind", "what"]).to_csv(out / "dropped.csv", index=False)
        panel.to_csv(out / "panel.csv", index=False)
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
