#!/usr/bin/env python3
"""The D-025 ADU estimation (pooled hierarchical negative binomial): smoke test, or the one real run.

    uv run python scripts/dev/estimate_pooled_adu.py --smoke
    uv run python scripts/dev/estimate_pooled_adu.py --full --out reports/adu-d025/

The panel is D-023's (`estimate_adu.build_panel`: Twin Cities places with Met Council permits, 2016-2025; St.
Paul never; places with no dated ADU rule left out; places adopting before 2010 don't inform the modifiers).
The full run: the main model with the wild score bootstrap (999), randomization inference (999), the five
checks, the robustness estimators (fixed-effects PPML, Borusyak imputation, binary dose, D-031 additive
imputation), the D-031 sensitivity runs and the transport test for Austin, Raleigh and Durham. --out is a
directory; CSVs are written only after every stage succeeds; a numerical failure raises EstimationError first.
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


HH_GROWTH = "corrected"  # D-031 (b); "as_run" reproduces the panel the first D-025 main model used


def load_panel(store) -> pd.DataFrame:
    panel = est.build_panel("MN", store, source=SOURCE, hh_growth=HH_GROWTH).data
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


def logged_estimates(log_path: Path) -> dict[str, float]:
    """The main-model estimates printed by the first run (term -> estimate), parsed from its log."""
    out, on = {}, False
    for line in log_path.read_text().splitlines():
        parts = line.split()
        if parts[:2] == ["term", "estimate"]:
            on = True
            continue
        if on:
            if len(parts) < 7:
                break
            try:
                out[parts[0]] = float(parts[1])
            except ValueError:
                break
    return out


def stages(
    store, panel, fit, boot, main, out: Path | None, log_note: str = "", skip_ri: str | None = None
) -> None:
    """Randomization inference, the five checks, robustness and transport, all under the D-025 convergence
    rule; CSVs written to `out` at the end (with convergence counts)."""
    p = {k: v.value for k, v in load_params("adu").items()}
    draws, perms = int(p["adu_estimation_bootstrap_draws"]), int(p["adu_estimation_permutations"])
    kw = {"modifiers": list(est.MODIFIERS)}
    logs = []

    try:
        if skip_ri:
            raise pa.StageFailed(skip_ri)
        obs, p_ri, ri_dist, ri_log = pa.randomization_inference(panel, perms, fit, seed=20261020, **kw)
        logs.append(ri_log.summary)
        print(f"randomization inference: overall {obs:.4f}, p = {p_ri:.3f} over {len(ri_dist)}", flush=True)
    except pa.StageFailed as err:  # D-025 rule: the stage is reported as not computed; the run continues
        obs, p_ri, ri_dist = pa.overall_effect(fit), float("nan"), np.array([])
        logs.append(f"randomization inference NOT COMPUTED: {err}")
    print(logs[-1], flush=True)

    checks = [
        pa.check_leads(panel, fit, draws=draws, seed=1, **kw),
        pa.check_placebo_dates(panel, fit, draws=draws, seed=2, **kw),
        pa.check_placebo_outcome(panel, fit, draws=draws, seed=3, **kw),
        pa.check_excluding(panel, fit, main, draws=draws, seed=4, **kw),
        pa.check_leave_one_out(panel, fit, main, **kw),
    ]
    for c in checks:
        print({k: v for k, v in c.items() if k != "effects"})
        logs.append(c.get("convergence", ""))

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
        "robustness, imputation:\n",
        imp_tab.round(4).to_string(index=False),
        f"\n(imputed rows {imp['imputed_rows']}, not imputable {imp['not_imputable_rows']})",
    )
    bin_log = pa.RefitLog("binary dose")
    bin_fit = pa.refit(panel, fit, bin_log, binary_dose=True, **kw)
    if bin_fit is None:
        bin_main = pd.DataFrame([{"term": "not computed", "estimate": np.nan}])
    else:
        bin_main = pa.summarize_main(bin_fit, pa.score_bootstrap(bin_fit, draws=draws, seed=6, log=bin_log))
    logs.append(bin_log.summary)
    print("robustness, binary dose:\n", bin_main.round(4).to_string(index=False), "\n", bin_log.summary)

    # D-031: additive imputation (robustness) and the pre-declared sensitivity runs of the D-025 model
    add = est.impute(panel)
    add_main = est.summarize_att(add, est.place_bootstrap(panel, draws=draws, seed=7))
    print("robustness, additive imputation (D-031), per 1,000 eligible parcels a year:")
    print(add.excluded.to_string(index=False))
    if add.estimable:
        print(add_main.round(4).to_string(index=False))
    else:
        n = len(add.contributing)
        print(f"not estimable: {n} contributing treated places (floor {est.MIN_CONTRIBUTING})")
    sens = pa.sensitivity_runs(panel, fit, main, draws=draws, seed=8, **kw)
    for c in sens:
        print({k: v for k, v in c.items() if k != "dropped"})
        logs.append(c.get("convergence", ""))

    pred, verdict = transport_stage(store, panel, fit, boot, p, logs)
    print("convergence:", *logs, sep="\n  ")

    if out:
        d = fit.design
        out.mkdir(parents=True, exist_ok=True)
        main.to_csv(out / "estimates.csv", index=False)
        boot.to_csv(out / "bootstrap_draws.csv", index=False)
        pd.DataFrame({"overall_permuted": ri_dist}).assign(overall=obs, p=p_ri, kept=len(ri_dist)).to_csv(
            out / "randomization.csv", index=False
        )
        pd.DataFrame([{k: v for k, v in c.items() if k != "effects"} for c in checks]).to_csv(
            out / "checks.csv", index=False
        )
        loo = checks[-1].get("effects", {})
        pd.DataFrame({"place": list(loo), "overall_without": list(loo.values())}).to_csv(
            out / "leave_one_out.csv", index=False
        )
        pd.DataFrame([fe]).to_csv(out / "robust_fe_ppml.csv", index=False)
        imp_tab.to_csv(out / "robust_imputation.csv", index=False)
        bin_main.to_csv(out / "robust_binary_dose.csv", index=False)
        add_main.assign(estimable=add.estimable).to_csv(out / "robust_additive_imputation.csv", index=False)
        add.excluded.to_csv(out / "robust_additive_imputation_excluded.csv", index=False)
        pd.DataFrame(sens).to_csv(out / "sensitivity.csv", index=False)
        pred.to_csv(out / "transport.csv", index=False)
        pd.DataFrame([verdict]).to_csv(out / "transport_verdict.csv", index=False)
        pd.DataFrame({"place": d.places, "random_effect": pa.place_effects(fit.log_params, d)}).to_csv(
            out / "place_effects.csv", index=False
        )
        pd.DataFrame({"stage": logs}).to_csv(out / "convergence.csv", index=False)
        drops = [{"kind": "column", "what": x} for x in d.dropped]
        drops += [{"kind": "separated place-year", "what": f"{pl} {yr}"} for pl, yr in d.separated]
        pd.DataFrame(drops, columns=["kind", "what"]).to_csv(out / "dropped.csv", index=False)
        panel.to_csv(out / "panel.csv", index=False)
        print(f"wrote CSVs to {out}/ {log_note}")


def main_model(store):
    p = {k: v.value for k, v in load_params("adu").items()}
    draws = int(p["adu_estimation_bootstrap_draws"])
    panel = load_panel(store)
    fit = pa.estimate_pooled(panel, modifiers=list(est.MODIFIERS))
    boot_log = pa.RefitLog("main bootstrap")
    boot = pa.score_bootstrap(fit, draws=draws, seed=20261020, log=boot_log)
    print(boot_log.summary)
    return panel, fit, boot, pa.summarize_main(fit, boot)


def full(store, out: Path | None) -> None:
    panel, fit, boot, main = main_model(store)
    print(main.round(4).to_string(index=False))
    stages(store, panel, fit, boot, main, out)


def transport_stage(store, panel, fit, boot, p, logs):
    """The D-025 transport test (Austin, Raleigh, Durham); a numerical failure is reported, not raised."""
    targets, window = [], {}
    for g, (state, years, scored) in TRANSPORT.items():
        targets.append(est.build_panel(state, store, years=years, geoids=[g], hh_growth=HH_GROWTH).data)
        window[g] = scored
    try:
        pred = pa.transport_predict(
            fit,
            boot,
            panel,
            pd.concat(targets, ignore_index=True),
            seed=20261020,
            widening=p["adu_transport_widening"],
            window=window,
        )
        print(pred.round(2).to_string(index=False))
        verdict = est.transport_verdict(pred)
    except est.EstimationError as err:  # D-025 rule: report the stage as not computed and carry on
        pred = pd.DataFrame()
        verdict = {"pass": None, "note": f"not computed: {err}"}
        logs.append(f"transport NOT COMPUTED: {err}")
    print(verdict, flush=True)
    return pred, verdict


def transport_only(store, out: Path | None, first_log: Path) -> None:
    """Only the transport test, reusing the main model (checked against the first run's log to 1e-4)."""
    panel, fit, boot, main = main_model(store)
    check_matches(main, first_log)
    p = {k: v.value for k, v in load_params("adu").items()}
    logs: list[str] = []
    pred, verdict = transport_stage(store, panel, fit, boot, p, logs)
    print("convergence:", *(logs or ["transport computed"]), sep="\n  ")
    if out:
        out.mkdir(parents=True, exist_ok=True)
        pred.to_csv(out / "transport.csv", index=False)
        pd.DataFrame([verdict]).to_csv(out / "transport_verdict.csv", index=False)


def check_matches(main, first_log: Path) -> None:
    logged = logged_estimates(first_log)
    now = main.set_index("term")["estimate"].to_dict()
    diffs = {t: (v, now.get(t)) for t, v in logged.items() if t not in now or abs(now[t] - v) > 1e-4}
    if not logged or diffs:
        raise SystemExit(f"main model does not match the first run's log: {diffs or 'nothing parsed'}")
    print(f"main model matches the first run's {len(logged)} logged estimates (to 1e-4); reusing it")


def remaining(store, out: Path | None, first_log: Path, skip_ri: str | None = None) -> None:
    """The stages after the main model, reusing it: the fit is recomputed deterministically (to recover its
    Hessian and place scores) and must match the estimates logged by the first run to 1e-4."""
    panel, fit, boot, main = main_model(store)
    check_matches(main, first_log)
    stages(store, panel, fit, boot, main, out, log_note="(main model reused)", skip_ri=skip_ri)


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--smoke", action="store_true")
    g.add_argument("--full", action="store_true")
    g.add_argument(
        "--remaining",
        type=Path,
        metavar="FIRST_RUN_LOG",
        help="run the stages after the main model, reusing it (checked against the first run's log)",
    )
    g.add_argument(
        "--transport-only",
        type=Path,
        metavar="FIRST_RUN_LOG",
        help="run only the transport test, reusing the main model (checked against the first run's log)",
    )
    ap.add_argument("--out", type=Path)
    ap.add_argument(
        "--hh-growth",
        choices=["corrected", "as_run"],
        default="corrected",
        help="household-growth modifier: corrected (D-031 b, default) or as_run (the first main model's)",
    )
    ap.add_argument(
        "--skip-ri", metavar="REASON", help="don't attempt randomization inference; report REASON"
    )
    a = ap.parse_args()
    global HH_GROWTH
    HH_GROWTH = a.hh_growth
    print(f"household growth: {HH_GROWTH}")
    store = DataStore()
    if a.smoke:
        smoke(store)
    elif a.transport_only:
        transport_only(store, a.out, a.transport_only)
    elif a.remaining:
        remaining(store, a.out, a.remaining, a.skip_ri)
    else:
        full(store, a.out)


if __name__ == "__main__":
    main()
