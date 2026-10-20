#!/usr/bin/env python3
"""The D-025 ADU estimation (pooled hierarchical negative binomial): smoke test, or the one real run.

    uv run python scripts/dev/estimate_pooled_adu.py --smoke
    uv run python scripts/dev/estimate_pooled_adu.py --full --out reports/adu-d025/

The panel is D-023's (`estimate_adu.build_panel`: Twin Cities places with Met Council permits, 2016-2025; St.
Paul never; places with no dated ADU rule left out; places adopting before 2010 don't inform the modifiers).
The full run: the main model with the wild score bootstrap (999), randomization inference (999), the five
checks, the robustness estimators (fixed-effects PPML, Borusyak imputation, binary dose) and the transport
test for Austin, Raleigh and Durham. --out is a directory; CSVs are written only after every stage succeeds; a
numerical failure raises EstimationError first.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.config import load_params
from lotline.io import DataStore
from lotline.model import estimate_adu as est
from lotline.model import pooled_adu as pa

SOURCE = "metc_residential_permits"
TRANSPORT = {  # place: (state, panel years incl. pre-adoption, scored years)
    "4805000": ("TX", range(2016, 2024), (2016, 2023)),  # Austin
    "3755000": ("NC", range(2019, 2026), (2021, 2025)),  # Raleigh (ADU flags from 2019)
    "3719000": ("NC", range(2016, 2026), (2019, 2025)),  # Durham
}


def load_panel(store) -> pd.DataFrame:
    panel = est.build_panel("MN", store, source=SOURCE).data
    early = panel["T"] < 2010  # D-023 run choice (Ben): early adopters don't inform the modifier terms
    panel.loc[early, list(est.MODIFIERS)] = float("nan")
    return panel


def smoke(store) -> None:
    panel = load_panel(store)
    places = panel.drop_duplicates("place")
    print(
        f"panel: {panel['place'].nunique()} places × {panel['year'].nunique()} years = {len(panel)} "
        f"place-years; "
        f"treated {int(places['T'].notna().sum())}; places with no ADU in any year "
        f"{int((panel.groupby('place')['y'].sum() == 0).sum())}"
    )


def full(store, out: Path | None) -> None:
    p = {k: v.value for k, v in load_params("adu").items()}
    draws, perms = int(p["adu_estimation_bootstrap_draws"]), int(p["adu_estimation_permutations"])
    kw = {"modifiers": list(est.MODIFIERS)}
    panel = load_panel(store)
    places = panel.drop_duplicates("place")
    print(
        f"panel: {panel['place'].nunique()} places, {len(panel)} place-years, "
        f"treated {int(places['T'].notna().sum())}, "
        f"places with no ADU in any year {int((panel.groupby('place')['y'].sum() == 0).sum())}"
    )

    fit = pa.estimate_pooled(panel, **kw)
    d = fit.design
    print(
        f"main model converged; dropped {d.dropped}; separated rows {len(d.separated)}; "
        f"at bound {fit.at_bound}"
    )
    boot = pa.score_bootstrap(fit, draws=draws, seed=20261020)
    main = pa.summarize_main(fit, boot)
    print(main.round(4).to_string(index=False))

    obs, p_ri, ri_dist = pa.randomization_inference(panel, permutations=perms, seed=20261020, **kw)
    print(f"randomization inference: overall {obs:.4f}, p = {p_ri:.3f}")

    checks = [
        pa.check_leads(panel, draws=draws, seed=1, **kw),
        pa.check_placebo_dates(panel, draws=draws, seed=2, **kw),
        pa.check_placebo_outcome(panel, draws=draws, seed=3, **kw),
        pa.check_excluding(panel, main, draws=draws, seed=4, **kw),
        pa.check_leave_one_out(panel, main, **kw),
    ]
    for c in checks:
        print(c)

    fe = pa.fe_ppml_pooled(panel, **kw)
    print("robustness, fixed-effects PPML:", fe)
    imp = pa.imputation_effects(panel)
    imp_boot = pa.imputation_bootstrap(panel, draws=draws, seed=5)
    imp_rows = []
    for name in [*pa.BAND_NAMES, "overall"]:
        v = imp[name]
        dist = imp_boot[name].replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        lo, hi = np.quantile(dist - v, [0.05, 0.95]) if np.isfinite(v) and len(dist) else (np.nan, np.nan)
        imp_rows.append(
            {"term": name, "estimate": v, "low": v - hi, "high": v - lo, "finite_draws": len(dist)}
        )
    imp_tab = pd.DataFrame(imp_rows)
    print(
        "robustness, imputation:",
        imp_tab.round(4).to_string(index=False),
        f"(imputed rows {imp['imputed_rows']}, not imputable {imp['not_imputable_rows']})",
    )
    bin_fit = pa.estimate_pooled(panel, binary_dose=True, **kw)
    bin_main = pa.summarize_main(bin_fit, pa.score_bootstrap(bin_fit, draws=draws, seed=6))
    print("robustness, binary dose:\n", bin_main.round(4).to_string(index=False))

    targets, window = [], {}
    for g, (state, years, scored) in TRANSPORT.items():
        targets.append(est.build_panel(state, store, years=years, geoids=[g]).data)
        window[g] = scored
    pred = pa.transport_predict(
        fit,
        boot,
        panel,
        pd.concat(targets, ignore_index=True),
        seed=20261020,
        widening=p["adu_transport_widening"],
        window=window,
    )
    print(pred.round(1).to_string(index=False))
    verdict = est.transport_verdict(pred)
    print(verdict)

    effects = pa.place_effects(fit.log_params, d)
    if out:
        out.mkdir(parents=True, exist_ok=True)
        main.to_csv(out / "estimates.csv", index=False)
        boot.to_csv(out / "bootstrap_draws.csv", index=False)
        pd.DataFrame({"overall_permuted": ri_dist}).assign(overall=obs, p=p_ri).to_csv(
            out / "randomization.csv", index=False
        )
        pd.DataFrame(checks).to_csv(out / "checks.csv", index=False)
        pd.DataFrame([fe]).to_csv(out / "robust_fe_ppml.csv", index=False)
        imp_tab.to_csv(out / "robust_imputation.csv", index=False)
        bin_main.to_csv(out / "robust_binary_dose.csv", index=False)
        pred.to_csv(out / "transport.csv", index=False)
        pd.DataFrame([verdict]).to_csv(out / "transport_verdict.csv", index=False)
        pd.DataFrame({"place": d.places, "random_effect": effects}).to_csv(
            out / "place_effects.csv", index=False
        )
        drops = [{"kind": "column", "what": x} for x in d.dropped]
        drops += [{"kind": "separated place-year", "what": f"{pl} {yr}"} for pl, yr in d.separated]
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
