#!/usr/bin/env python3
"""Score V9 (analysis plan D-051, D-052) against Oregon's unblinded outcomes.

    uv run python scripts/dev/v9_or_score.py            # writes reports/v9-oregon/

1. Regenerates the frozen draws (same code, inputs and seed as `v9_or_predict.py --freeze`) and stops unless
   their summaries are identical to results/frozen/V9-OR-TRANSFER.json, so scoring uses exactly what was
   frozen. If the code has moved on since the freeze, run this from the freeze commit (the file's `commit`).
2. Unblinds Oregon BPS in memory (`unblind=("V9-OR-TRANSFER",)`; check_unblind needs the freeze on main);
   the processed tables on disk stay blind.
3. Scores each target as D-051 says: randomized P10-P90 coverage (D-003), obs ÷ P50, D-040's verdict
   (useful: inside P10-P90 and P50 within ×2; inside only; missed), for 2018-2025 and 2018-2022; for the
   Oregon totals also the CRPS against a no-reform benchmark, Poisson(B_i) each year.

4. ADU targets (D-051, D-052): ADU permits from the Portland and Bend permit adapters (unblinded in memory),
   counted as D-041 (`calibrate_adu.adu_counts` with `count_settings()`: co-built dropped, issue year), each
   variant scored as above, plus D-052's gain (CRPS of own-history against transfer). Also written, and
   labelled: flagged-permit counts (no co-built rule), and a POST-HOC re-run of the own-history variant on the
   adapters' own 2010-2017 D-041 counts (not pre-registered; a diagnostic only).
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.adapters.national import bps
from lotline.io import DataStore
from lotline.model import calibrate_adu
from lotline.model import estimate_mm as mm
from lotline.model.baseline import crps_from_draws, randomized_coverage
from lotline.validation import v9

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "v9-oregon"
BENCH_SEED = 1
ADU_SOURCES = {"4159000": "portland_permits", "4105800": "bend_permits"}


def regenerate(store: DataStore, frozen: dict) -> dict:
    if v9.table_hashes("OR", store) != frozen["input_table_sha256"]:
        raise SystemExit(
            "input tables differ from the freeze's. Oregon was released on 2026-11-05, so run with "
            "LOTLINE_DATA_DIR=~/lotline-data-v9-blind (the blind copy, checked against the freeze)"
        )
    n, seed = frozen["draws"], frozen["seed"]
    adu_in = v9.adu_inputs("OR", store, list(v9.ADU_TARGETS))
    hist = v9.adu_history("OR", store, list(v9.ADU_TARGETS), v9.load_history(REPO / v9.HISTORY_FILE))
    mm_in = v9.mm_inputs("OR", store)
    a = v9.adu_draws(adu_in, n, seed)
    ah = v9.adu_draws(adu_in, n, seed, history=hist)
    m = v9.mm_draws(mm_in, n, seed)
    pred = v9.prediction(adu_in, a, mm_in, m, adu_hist_d=ah)
    if json.dumps(pred["targets"] + pred["totals"], sort_keys=True) != json.dumps(
        frozen["targets"] + frozen["totals"], sort_keys=True
    ):
        raise SystemExit(f"regenerated draws differ from the freeze; run from commit {frozen['commit']}")
    return {"adu_in": adu_in, "adu": a, "adu_hist": ah, "mm_in": mm_in, "mm": m}


def verdict(ob: float, p10: float, p50: float, p90: float) -> str:
    inside = p10 <= ob <= p90
    ratio = ob / p50 if p50 > 0 else np.inf
    if inside:
        return "useful" if 0.5 <= ratio <= 2 else "inside only"
    return "missed (over)" if ob < p10 else "missed (under)"


def score(label: str, draws: np.ndarray, ob: float, bench: np.ndarray | None = None) -> dict:
    draws = np.asarray(draws, float)
    p10, p50, p90 = np.percentile(draws, [10, 50, 90])
    r = {
        "target": label,
        "observed": ob,
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "mean": draws.mean(),
        "obs_over_p50": ob / p50 if p50 > 0 else np.inf,
        "coverage_rand": float(randomized_coverage(draws[None, :], np.array([ob]), 0.1, 0.9)[0]),
        "verdict": verdict(ob, p10, p50, p90),
    }
    if bench is not None:
        r["crps_model"] = float(crps_from_draws(draws[None, :], np.array([ob]))[0])
        r["crps_no_reform"] = float(crps_from_draws(np.asarray(bench, float)[None, :], np.array([ob]))[0])
        r["no_reform_p50"] = float(np.percentile(bench, 50))
    return r


def adu_counts(store: DataStore, geoid: str) -> tuple[pd.Series, pd.Series]:
    """(D-041 counts, flagged permits) by issue year for one ADU target, outcomes unblinded in memory."""
    from lotline.model.scenarios import adu

    m = importlib.import_module(f"lotline.adapters.states.or.{ADU_SOURCES[geoid]}")
    p = m.load("OR", store, unblind=(v9.TEST_ID,))
    c = calibrate_adu.adu_counts(p, 2010, max(v9.YEARS), calibrate_adu.count_settings())
    flagged = p[adu._is_adu(p) & (p["jurisdiction_geoid"] == geoid)].groupby("issue_year").size()
    return c[c["geoid"] == geoid].set_index("year")["adu_permits"], flagged


def score_adu(store: DataStore, g: dict, frozen: dict) -> list[str]:
    adu_in, years = g["adu_in"], g["adu_in"].years
    periods = {"2018-2025": np.ones(len(years), bool), "2018-2022": years <= v9.SUBTOTAL_LAST}
    rows, yearly, pre = [], [], []
    for i, geo in enumerate(adu_in.geoids):
        d041, flagged = adu_counts(store, geo)
        ob = np.array([float(d041.get(int(y), 0)) for y in years])
        for j, y in enumerate(years):
            yearly.append(
                {"geoid": geo, "year": int(y), "d041": ob[j], "flagged": int(flagged.get(int(y), 0))}
            )
        pre += [
            {"geoid": geo, "year": int(y), "adu_permits": int(v)} for y, v in d041.items() if y < min(years)
        ]
        for variant, key in (("transfer", "adu"), ("own_history", "adu_hist")):
            for per, ym in periods.items():
                x = g[key][:, i, ym].sum(axis=1)
                r = {"geoid": geo, "variant": variant, "period": per}
                r |= score(f"ADU permits, {adu_in.names[i]}", x, ob[ym].sum())
                r["crps_model"] = float(crps_from_draws(x[None, :], np.array([ob[ym].sum()]))[0])
                r["observed_flagged"] = float(sum(int(flagged.get(int(y), 0)) for y in years[ym]))
                rows.append(r)
    t = pd.DataFrame(rows)
    t.round(3).to_csv(OUT / "adu_scores.csv", index=False)
    pd.DataFrame(yearly).to_csv(OUT / "adu_by_year.csv", index=False)
    # POST-HOC diagnostic (not pre-registered): own history from the adapters' 2010-2017 D-041 counts
    pre = pd.DataFrame(pre)
    ok = pre[(pre["geoid"] != "4105800") | (pre["year"] >= 2013)]  # Bend: no ADU code before 2013
    h = v9.adu_history(
        "OR", store, adu_in.geoids, ok.assign(source_url="adapter", source_section="", quote="")
    )
    x = v9.adu_draws(adu_in, frozen["draws"], frozen["seed"], history=h).sum(axis=2)
    post = [
        {"geoid": geo, "label": "POST-HOC: own history on adapter D-041 counts 2010-2017 (Bend 2013-2017)"}
        | dict(zip(("p10", "p50", "p90"), np.percentile(x[:, i], [10, 50, 90]).round(1), strict=True))
        for i, geo in enumerate(adu_in.geoids)
    ]
    pd.DataFrame(post).to_csv(OUT / "adu_posthoc_history.csv", index=False)
    print(t.round(2).to_string(index=False))
    return [
        f"{r.target} {r.variant} {r.period}: obs {r.observed:.0f}, {r.p10:.0f}-{r.p90:.0f}, {r.verdict}"
        for r in t.itertuples()
    ]


def main() -> None:
    store = DataStore()
    frozen = json.loads((REPO / "results" / "frozen" / f"{v9.TEST_ID}.json").read_text())
    g = regenerate(store, frozen)
    mm_in, draws = g["mm_in"], g["mm"]
    years = mm_in.years
    counts = mm.bps_counts(bps.load("OR", store, unblind=(v9.TEST_ID,)))["y_buildings"]
    obs = np.array([[counts.get((p, int(y)), np.nan) for y in years] for p in mm_in.geoids])
    missing = int(np.isnan(obs).sum())  # small places with no BPS row that year: no permits reported
    obs = np.nan_to_num(obs)
    bench = np.random.default_rng(BENCH_SEED).poisson(np.broadcast_to(mm_in.B[None, :, None], draws.shape))
    periods = {"2018-2025": np.ones(len(years), bool), "2018-2022": years <= v9.SUBTOTAL_LAST}
    early = mm_in.T < years.max()
    totals = []
    for name, mask in (("Oregon headline (62 places reached before 2025)", early),
                       ("Oregon, all places reached by 2025", np.ones(len(mm_in.geoids), bool))):  # fmt: skip
        for per, ym in periods.items():
            totals.append(
                score(
                    f"{name}, {per}",
                    draws[:, mask][:, :, ym].sum(axis=(1, 2)),
                    obs[mask][:, ym].sum(),
                    bench[:, mask][:, :, ym].sum(axis=(1, 2)),
                )  # fmt: skip
            )
    places = []
    for i, p in enumerate(mm_in.geoids):
        for per, ym in periods.items():
            r = score(mm_in.names[i], draws[:, i, ym].sum(axis=1), obs[i, ym].sum())
            places.append({"geoid": p, "period": per, "adoption_year": int(mm_in.T[i]),
                           "baseline_per_year": float(mm_in.B[i])} | r)  # fmt: skip
    yearly = []
    dy, oy = draws[:, early].sum(axis=1), obs[early].sum(axis=0)
    for j, y in enumerate(years):
        p10, p50, p90 = np.percentile(dy[:, j], [10, 50, 90])
        yearly.append({"year": int(y), "observed": oy[j], "p10": p10, "p50": p50, "p90": p90,
                       "no_reform_baseline": float(mm_in.B[early].sum())})  # fmt: skip
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(totals).round(3).to_csv(OUT / "mm_totals.csv", index=False)
    pd.DataFrame(places).round(3).to_csv(OUT / "mm_places.csv", index=False)
    pd.DataFrame(yearly).round(1).to_csv(OUT / "mm_headline_by_year.csv", index=False)
    pl = pd.DataFrame(places)
    p8 = pl[pl["period"] == "2018-2025"]
    lines = [
        f"V9 missing-middle score; freeze commit {frozen['commit']}; place-years with no BPS row: {missing}"
    ]
    for lab, m in (
        ("reached before 2025", p8["adoption_year"] < 2025),
        ("2025 tier", p8["adoption_year"] >= 2025),
    ):
        q = p8[m]
        lines.append(
            f"places {lab}: n={len(q)}, mean randomized coverage {q['coverage_rand'].mean():.3f}, "
            f"below P10 {(q['observed'] < q['p10']).mean():.3f}, "
            f"above P90 {(q['observed'] > q['p90']).mean():.3f}, "
            f"verdicts {q['verdict'].value_counts().to_dict()}"
        )
    print(pd.DataFrame(totals).round(2).to_string(index=False))
    lines += score_adu(store, g, frozen)
    (OUT / "run-log.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
