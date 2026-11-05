#!/usr/bin/env python3
"""D-047: approach 2 (shape terms on the mechanism) and approach 3 (empirical benchmark), each with the
leave-one-state-out backtest, next to D-041.

    uv run python scripts/dev/calibrate_shape.py --out reports/adu-shape [--workers 8]
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

from lotline.io import DataStore  # noqa: E402
from lotline.model import calibrate_adu as cal  # noqa: E402
from lotline.model import calibrate_shape as shp  # noqa: E402
from lotline.model.scenarios import adu  # noqa: E402

K1_D041 = 0.791


def _k1(t: pd.DataFrame) -> tuple[float, int, float]:
    four = t[t["group"].isin(run.STATES)]
    k1 = float(np.sqrt(np.mean(np.log(four["observed"] / four["p50"]) ** 2)))
    return k1, int((four["verdict"] == "missed").sum()), float(four["p90_over_p10"].median())


def _half(v: float) -> str:
    return "no ramp" if v == shp.NO_RAMP else f"{v:g} years"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store, cs = DataStore(), cal.count_settings()
    places, test = run.four_state_places(store, cs), run._test_set(store, cs)
    p = adu.central_params()
    print(f"=== D-047: {len(places)} fit places, {len(test)} test places, counts {cs} ===", flush=True)
    portland = run._portland_paths(store, places + test, cs)
    groups = run._groups(places, test, True)

    # Approach 2
    sfits = {}
    with ProcessPoolExecutor(a.workers) as pool:
        for st in ("",) + run.STATES:
            sub = [pl for pl in places if pl.state != st]
            f = shp.fit_shape(sub, p, map_fn=lambda fn, it: pool.map(fn, it, chunksize=2))
            sfits[st] = f
            name = "all four states" if st == "" else f"without {st}"
            print(
                f"[2] {name}: theta {f.theta * 1000:.3f} per 1,000 ({f.low * 1000:.3f}-{f.high * 1000:.3f}), "
                f"alpha {f.alpha:.3f}, ramp {_half(f.half)} {f.half_interval}, equity {f.equity} "
                f"{f.equity_interval}, size {f.size} {f.size_interval}, loglik {f.loglik:.3f}",
                flush=True,
            )
    full2 = sfits[""]
    gain = full2.loglik - run.D041_LOGLIK
    draws2 = {}
    for st in run.STATES:
        pred = [pl for pl in places + test if pl.state == st]
        draws2 |= cal.predict_places(sfits[st].apply(pred, p), sfits[st].as_fit3(), seed=run.SEED)
    t2 = run.state_totals("D-047 approach 2: leave one state out", groups, draws2, portland)
    tt2 = run.state_totals(
        "Approach 2: test set from the full fit",
        {"Raleigh and Durham": test},
        cal.predict_places(full2.apply(test, p), full2.as_fit3(), seed=run.SEED),
        portland,
    )

    # Approach 3
    efits = {}
    for st in ("",) + run.STATES:
        efits[st] = shp.fit_empirical([pl for pl in places if pl.state != st])
        f = efits[st]
        name = "all four states" if st == "" else f"without {st}"
        print(f"[3] {name}: alpha {f.alpha:.3f}, loglik {f.loglik:.3f}", flush=True)
    full3 = efits[""]
    se = np.sqrt(np.diag(full3.cov))[:-1]
    coef = pd.DataFrame(
        {"term": shp.NAMES, "estimate": full3.beta, "se": se, "ratio_per_unit": np.exp(full3.beta)}
    )
    print("\nApproach 3, full fit coefficients\n" + coef.round(3).to_string(index=False))
    draws3 = {}
    for st in run.STATES:
        draws3 |= shp.predict_empirical(
            [pl for pl in places + test if pl.state == st], efits[st], seed=run.SEED
        )
    t3 = run.state_totals("D-047 approach 3: leave one state out", groups, draws3, portland)
    tt3 = run.state_totals(
        "Approach 3: test set from the full fit",
        {"Raleigh and Durham": test},
        shp.predict_empirical(test, full3, seed=run.SEED),
        portland,
    )

    # Comparison
    d041 = pd.read_csv(run.D041)
    d041 = d041[d041["test"] == "main: leave one state out"]
    k2, m2, w2 = _k1(t2)
    k3, m3, w3 = _k1(t3)
    k1, m1, w1 = _k1(d041)
    summary = pd.DataFrame(
        [
            dict(
                model="D-041 (today)",
                params=4,
                loglik=run.D041_LOGLIK,
                alpha=2.284,
                k1=k1,
                missed=m1,
                median_p90_p10=w1,
            ),
            dict(
                model="Approach 2: shape terms",
                params=7,
                loglik=full2.loglik,
                alpha=full2.alpha,
                k1=k2,
                missed=m2,
                median_p90_p10=w2,
            ),
            dict(
                model="Approach 3: empirical",
                params=9,
                loglik=full3.loglik,
                alpha=full3.alpha,
                k1=k3,
                missed=m3,
                median_p90_p10=w3,
            ),
        ]
    )
    summary["aic"] = 2 * summary["params"] - 2 * summary["loglik"]
    print(
        "\nComparison (leave one state out over MN, NC, OH, TX)\n" + summary.round(3).to_string(index=False)
    )
    adopt2 = gain >= cal.CHI2_90_3 / 2 and m2 == 0 and k2 < K1_D041
    print(
        f"\nApproach 2 adoption: gain {gain:.3f} (needs >= {cal.CHI2_90_3 / 2:.3f}), missed {m2}, "
        f"K1 {k2:.3f} "
        f"(needs < {K1_D041}) -> {'ADOPT' if adopt2 else 'not adopted'}"
    )
    beats = m3 == 0 and k3 < k2 - 0.10
    print(
        f"Approach 3 reading: K1 {k3:.3f} vs approach 2 {k2:.3f}; missed {m3} -> "
        f"{'mechanism not earning its keep: revisit D-037' if beats else 'mechanism stays'}"
    )

    fits = pd.DataFrame(
        [
            dict(
                fit="all four states" if st == "" else f"without {st}",
                theta=f.theta,
                low=f.low,
                high=f.high,
                alpha=f.alpha,
                ramp_half=f.half,
                equity=f.equity,
                size=f.size,
                half_low=f.half_interval[0],
                half_high=f.half_interval[1],
                equity_low=f.equity_interval[0],
                equity_high=f.equity_interval[1],
                size_low=f.size_interval[0],
                size_high=f.size_interval[1],
                loglik=f.loglik,
            )
            for st, f in sfits.items()
        ]
    )
    fits.to_csv(a.out / "approach2_fits.csv", index=False)
    pd.DataFrame(
        [
            dict(
                fit="all four states" if st == "" else f"without {st}",
                alpha=f.alpha,
                loglik=f.loglik,
                **{n: b for n, b in zip(shp.NAMES, f.beta, strict=True)},
            )
            for st, f in efits.items()
        ]
    ).to_csv(a.out / "approach3_fits.csv", index=False)
    coef.to_csv(a.out / "approach3_coefficients.csv", index=False)
    pd.concat(
        [
            t2.assign(model="approach 2"),
            tt2.assign(model="approach 2"),
            t3.assign(model="approach 3"),
            tt3.assign(model="approach 3"),
        ]
    ).to_csv(a.out / "statewide.csv", index=False)
    summary.to_csv(a.out / "comparison.csv", index=False)


if __name__ == "__main__":
    main()
