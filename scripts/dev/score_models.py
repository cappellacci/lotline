#!/usr/bin/env python3
"""D-049: held-out log score per place for D-041, D-046, D-047 (approaches 2 and 3) and D-048.

    uv run python scripts/dev/score_models.py --out reports/adu-model-scores [--workers 5]

Each fit place is scored by the fold that left its state out; Raleigh and Durham by each model's full fit.
Fits come from the earlier runs' CSVs; D-041's folds and approach 3 are refitted with the same code.
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_adu as run  # noqa: E402

from lotline.io import DataStore  # noqa: E402
from lotline.model import calibrate_adu as cal  # noqa: E402
from lotline.model import calibrate_shape as shp  # noqa: E402
from lotline.model import score  # noqa: E402
from lotline.model.scenarios import adu  # noqa: E402

REPORTS = Path(__file__).resolve().parents[2] / "reports"
FOLDS = ("",) + run.STATES
MODELS = ("D-041", "D-046", "D-047 approach 2", "D-047 approach 3", "D-048")


def _fold_name(st: str) -> str:
    return "all four states" if st == "" else f"without {st}"


def _refit(args):
    kind, places, st = args
    sub = [pl for pl in places if pl.state != st]
    return kind, st, cal.fit3(sub) if kind == "D-041" else shp.fit_empirical(sub)


def _fit3_row(r) -> cal.Fit3:
    m_o, m_x = float(r["m_owner"]), float(r["m_other"])
    return cal.Fit3(
        float(r["theta"]),
        float(r["low"]),
        float(r["high"]),
        float(r["alpha"]),
        m_o,
        m_x,
        (m_o, m_o),
        (m_x, m_x),
        False,
        False,
        float(r["loglik"]),
        0,
        0,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store, cs = DataStore(), cal.count_settings()
    p = adu.central_params()
    places, test = run.four_state_places(store, cs), run._test_set(store, cs)
    places_d, test_d = run.four_state_places(store, cs, True), run._test_set(store, cs, True)
    print(f"=== D-049: {len(places)} fit places, {len(test)} test places ===", flush=True)

    with ProcessPoolExecutor(a.workers) as pool:
        tasks = [(k, places, st) for k in ("D-041", "D-047 approach 3") for st in FOLDS]
        refits = {(k, st): f for k, st, f in pool.map(_refit, tasks)}

    det = pd.read_csv(REPORTS / "adu-detached" / "fits.csv").set_index("fit")
    a2 = pd.read_csv(REPORTS / "adu-shape" / "approach2_fits.csv").set_index("fit")
    nr = pd.read_csv(REPORTS / "adu-no-ramp" / "fits.csv").set_index("fit")

    def scorer(model: str, st: str):
        """(places to score, function place -> score) for a model's fold."""
        if model == "D-041":
            f = refits[("D-041", st)]
            return places, test, lambda pl: score.place_log_score(pl, f)
        if model == "D-046":
            r = det.loc[_fold_name(st)]
            base = _fit3_row(r)
            md = float(r["m_detached"])
            f = cal.FitD(
                *[getattr(base, fld.name) for fld in base.__dataclass_fields__.values()],
                md,
                (md, md),
                bool(r["detached_estimated"]),
            )
            return places_d, test_d, lambda pl: score.place_log_score(pl, f)
        if model == "D-047 approach 2":
            r = a2.loc[_fold_name(st)]
            f = _fit3_row(r.to_dict() | {"m_owner": shp.SHARES[0], "m_other": shp.SHARES[1]})
            sh = (float(r["ramp_half"]), float(r["equity"]), float(r["size"]))
            return places, test, lambda pl: score.place_log_score(shp.shaped(pl, *sh, p), f)
        if model == "D-047 approach 3":
            f = refits[("D-047 approach 3", st)]
            return places, test, lambda pl: score.empirical_log_score(pl, f)
        r = nr.loc[_fold_name(st)]
        f = _fit3_row(r)
        eq = p["adu_equity_elasticity"]
        return places, test, lambda pl: score.place_log_score(shp.shaped(pl, shp.NO_RAMP, eq, 0.0, p), f)

    rows = []
    for model in MODELS:
        for st in run.STATES:
            pls, _, fn = scorer(model, st)
            for pl in pls:
                if pl.state == st:
                    rows.append(
                        dict(
                            model=model,
                            role="fit",
                            state=st,
                            geoid=pl.geoid,
                            name=pl.name,
                            years=len(pl.y),
                            observed=float(pl.y.sum()),
                            score=fn(pl),
                        )
                    )
        _, tst, fn = scorer(model, "")
        for pl in tst:
            rows.append(
                dict(
                    model=model,
                    role="test",
                    state=pl.state,
                    geoid=pl.geoid,
                    name=pl.name,
                    years=len(pl.y),
                    observed=float(pl.y.sum()),
                    score=fn(pl),
                )
            )
    d = pd.DataFrame(rows)
    d.to_csv(a.out / "place_scores.csv", index=False)

    fit = d[d["role"] == "fit"].pivot(index="geoid", columns="model", values="score")
    states = d[(d["role"] == "fit") & (d["model"] == "D-041")].set_index("geoid")["state"]
    test_tot = d[d["role"] == "test"].groupby("model")["score"].sum()
    out = []
    for m in MODELS:
        delta = fit[m] - fit["D-041"]
        tot, se = score.paired(delta)
        by_state = delta.groupby(states).sum()
        out.append(
            dict(
                model=m,
                total=float(fit[m].sum()),
                per_place_year=float(fit[m].sum() / 296),
                delta_vs_d041=tot,
                paired_se=se,
                **{f"delta_{s}": float(by_state.get(s, 0.0)) for s in run.STATES},
                test_score=float(test_tot[m]),
                test_delta=float(test_tot[m] - test_tot["D-041"]),
            )
        )
    summ = pd.DataFrame(out)
    summ.to_csv(a.out / "summary.csv", index=False)
    pd.set_option("display.width", 220)
    print("\nHeld-out log score (higher is better)\n" + summ.round(2).to_string(index=False))
    cand = summ[summ["model"] != "D-041"].sort_values("total", ascending=False).iloc[0]
    worse_states = sum(cand[f"delta_{s}"] < 0 for s in run.STATES)
    ok = cand["delta_vs_d041"] > 2 * cand["paired_se"] and worse_states <= 1 and cand["test_delta"] >= -2
    print(
        f"\nBest other model: {cand['model']} (Δ {cand['delta_vs_d041']:.2f}, "
        f"2 SE {2 * cand['paired_se']:.2f}, "
        f"worse in {worse_states} states, test Δ {cand['test_delta']:.2f}) -> "
        f"{'propose to Ben for adoption' if ok else 'D-041 stays'}"
    )
    worst = d[d["role"] == "fit"].pivot(index="name", columns="model", values="score")
    worst = worst.assign(d048_minus_d041=worst["D-048"] - worst["D-041"]).sort_values("d048_minus_d041")
    print("\nPlaces where D-048 differs most from D-041\n" + worst.round(2).head(6).to_string())
    print(worst.round(2).tail(6).to_string(header=False))


if __name__ == "__main__":
    main()
