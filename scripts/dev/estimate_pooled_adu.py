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


WORKERS = 1  # processes for the independent refits (--workers); results are those of the serial run


def stages(
    store, panel, fit, boot, main, out: Path | None, log_note: str = "", skip_ri: str | None = None
) -> None:
    """Randomization inference, the five checks, robustness and transport, all under the D-025 convergence
    rule; CSVs written to `out` at the end (with convergence counts). With WORKERS > 1 the refits of
    randomization inference and leave-one-out, and the four single-refit checks, run in parallel processes
    with the serial result (D-025 implementation note, 2026-10-22); refit times are printed."""
    p = {k: v.value for k, v in load_params("adu").items()}
    draws, perms = int(p["adu_estimation_bootstrap_draws"]), int(p["adu_estimation_permutations"])
    kw = {"modifiers": list(est.MODIFIERS)}
    logs = []

    try:
        if skip_ri:
            raise pa.StageFailed(skip_ri)
        obs, p_ri, ri_dist, ri_log = pa.randomization_inference(
            panel, perms, fit, seed=20261020, workers=WORKERS, **kw
        )
        logs.append(ri_log.summary)
        print(ri_log.timing, flush=True)
        print(f"randomization inference: overall {obs:.4f}, p = {p_ri:.3f} over {len(ri_dist)}", flush=True)
    except pa.StageFailed as err:  # D-025 rule: the stage is reported as not computed; the run continues
        obs, p_ri, ri_dist = pa.overall_effect(fit), float("nan"), np.array([])
        logs.append(f"randomization inference NOT COMPUTED: {err}")
    print(logs[-1], flush=True)

    checks = pa.run_parallel(
        [
            (pa.check_leads, (panel, fit), {"draws": draws, "seed": 1, **kw}),
            (pa.check_placebo_dates, (panel, fit), {"draws": draws, "seed": 2, **kw}),
            (pa.check_placebo_outcome, (panel, fit), {"draws": draws, "seed": 3, **kw}),
            (pa.check_excluding, (panel, fit, main), {"draws": draws, "seed": 4, **kw}),
        ],
        WORKERS,
    )
    checks.append(pa.check_leave_one_out(panel, fit, main, workers=WORKERS, **kw))
    for c in checks:
        print({k: v for k, v in c.items() if k not in ("effects", "timing")})
        print("  ", c.get("timing", ""))
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
        print({k: v for k, v in c.items() if k not in ("dropped", "timing")})
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
        pd.DataFrame([{k: v for k, v in c.items() if k not in ("effects", "timing")} for c in checks]).to_csv(
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
        pd.DataFrame(sens).drop(columns="timing", errors="ignore").to_csv(
            out / "sensitivity.csv", index=False
        )
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


def changed_growth(store, panel) -> None:
    """Places whose household-growth modifier differs between the as-run and corrected panels (D-031 (b))."""
    other = "as_run" if HH_GROWTH == "corrected" else "corrected"
    alt = est.build_panel("MN", store, source=SOURCE, hh_growth=other).data
    alt.loc[alt["T"] < 2010, list(est.MODIFIERS)] = float("nan")
    a = panel.drop_duplicates("place").set_index("place")[["name", "T", "hh_growth"]]
    b = alt.drop_duplicates("place").set_index("place")["hh_growth"].rename(f"hh_growth_{other}")
    d = a.join(b)
    diff = d[~((d["hh_growth"] == d[b.name]) | (d["hh_growth"].isna() & d[b.name].isna()))]
    print(f"household growth differs ({HH_GROWTH} vs {other}) for {len(diff)} places:")
    print(diff.to_string())


def full(store, out: Path | None) -> None:
    panel, fit, boot, main = main_model(store)
    changed_growth(store, panel)
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


def band_inputs(fit, boot, panel, band: int):
    """θ_b (mean of β_band × dose over the band's treated place-years), per draw, and ω restricted to the
    band's event times (renormalised), for `pa.honest_set` on one band (D-031 HonestDiD plan)."""
    post = panel[panel["T"].notna() & (panel["year"] >= panel["T"])]
    k = (post["year"] - post["T"]).to_numpy(dtype=int)
    on = pa._band_of(k) == band
    omega = np.bincount(k[on], minlength=k.max() + 1) / on.sum()
    mean_dose = float(post["dose"].to_numpy(dtype=float)[on].mean())
    name = pa.BAND_NAMES[band]
    est_ = dict(zip(fit.names, fit.log_params, strict=True))
    theta = float(est_.get(name, 0.0)) * mean_dose
    draws = boot[name].to_numpy() * mean_dose if name in boot else np.zeros(len(boot))
    return theta, draws, omega


def honest(store, out: Path | None, first_log: Path) -> None:
    """HonestDiD bounds (D-025 choices, D-031 run plan) for one main model: reproduce it (checked against
    its log), refit the pre-trend-leads model as check 1 did, then `pa.honest_bounds` and `pa.rm_breakdown`
    for the pooled effect and each band."""
    p = {k: v.value for k, v in load_params("adu").items()}
    draws = int(p["adu_estimation_bootstrap_draws"])
    kw = {"modifiers": list(est.MODIFIERS)}
    panel, fit, boot, main = main_model(store)
    check_matches(main, first_log)
    log = pa.RefitLog("pre-trend leads (HonestDiD)")
    lfit = pa.refit(panel, fit, log, leads=(-3, -2, -1), **kw)
    if lfit is None:
        raise SystemExit(f"the leads refit did not converge after a retry: {log.summary}")
    lboot = pa.score_bootstrap(lfit, draws=draws, seed=1, log=log)
    print(log.summary)
    es = pa.summarize(lfit, lboot).set_index("term")
    terms = [("lead_3", "−3"), ("lead_2", "−2"), ("lead_1", "−1")]
    terms += [(b, lab) for b, lab in zip(pa.BAND_NAMES, ("0–1", "2–3", "4+"), strict=True)]
    event = pd.DataFrame(
        [
            {"term": t, "k_label": lab, **es.loc[t, ["estimate", "low", "high"]].to_dict()}
            for t, lab in terms
            if t in es.index
        ]
    )
    print("event study (leads refit):\n", event.round(4).to_string(index=False))
    try:
        theta, leads, theta_d, lead_d, omega = pa.event_study_inputs(lfit, lboot, panel)
    except est.EstimationError as err:  # a dropped lead or band: the bounds are not identified (D-031 note)
        print(f"HonestDiD NOT COMPUTED: {err}")
        if out:
            out.mkdir(parents=True, exist_ok=True)
            event.to_csv(out / "event_study.csv", index=False)
        return
    targets = {"pooled": (theta, theta_d, omega)}
    for b, name in enumerate(pa.BAND_NAMES):
        if name in lfit.names:
            targets[name] = band_inputs(lfit, lboot, panel, b)
    rows = []
    for target, (th, th_d, om) in targets.items():
        tab = pa.honest_bounds(th, leads, th_d, lead_d, om)
        brk = pa.rm_breakdown(th_d, lead_d, om)
        q = np.quantile(th_d - th, [0.05, 0.95])
        orig = {
            "restriction": "original",
            "m": np.nan,
            "set_low": th,
            "set_high": th,
            "ci_low": th - q[1],
            "ci_high": th - q[0],
            "ci_includes_0": bool(th - q[1] <= 0 <= th - q[0]),
        }
        both = pd.concat([pd.DataFrame([orig]), tab], ignore_index=True)
        rows.append(both.assign(target=target, breakdown=brk))
        print(f"{target}: θ {th:.4f}, breakdown M̄ {brk}")
    res = pd.concat(rows, ignore_index=True)
    lead_names = ("δ_−3", "δ_−2", "δ_−1")
    print("leads:", dict(zip(lead_names, np.round(leads, 4), strict=True)))
    print("ω_k:", np.round(omega, 3).tolist())
    print(res.round(4).to_string(index=False))
    if out:
        out.mkdir(parents=True, exist_ok=True)
        event.to_csv(out / "event_study.csv", index=False)
        res.to_csv(out / "honest_bounds.csv", index=False)
        print(f"wrote event_study.csv and honest_bounds.csv to {out}/")


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
        "--honest",
        type=Path,
        metavar="MAIN_RUN_LOG",
        help="HonestDiD bounds for the main model logged in MAIN_RUN_LOG (reproduced and checked first)",
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
    ap.add_argument(
        "--workers",
        type=int,
        default=1,
        help="processes for the independent refits (same results as 1, the serial run)",
    )
    a = ap.parse_args()
    global HH_GROWTH, WORKERS
    HH_GROWTH = a.hh_growth
    WORKERS = a.workers
    print(f"household growth: {HH_GROWTH}")
    store = DataStore()
    if a.smoke:
        smoke(store)
    elif a.honest:
        honest(store, a.out, a.honest)
    elif a.transport_only:
        transport_only(store, a.out, a.transport_only)
    elif a.remaining:
        remaining(store, a.out, a.remaining, a.skip_ri)
    else:
        full(store, a.out)


if __name__ == "__main__":
    main()
