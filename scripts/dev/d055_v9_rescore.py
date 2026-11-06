#!/usr/bin/env python3
"""D-055: re-score V9 Oregon's missing-middle targets with D-054's refit (not blind; written before the run).

    LOTLINE_DATA_DIR=~/lotline-data-v9-blind uv run python scripts/dev/d055_v9_rescore.py

Same inputs, code, draws and seed as the V9 freeze (`validation.v9.mm_inputs`, D-051's model), two parameter
sets: D-038's (regenerated and checked against results/frozen/V9-OR-TRANSFER.json) and D-054's refit (b).
Oregon BPS is unblinded in memory only, as `v9_or_score.py` does. Results to reports/v9-oregon-d055/.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from lotline.adapters.national import bps
from lotline.io import DataStore
from lotline.model import estimate_mm as mm
from lotline.validation import v9

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "v9-oregon-d055"
_spec = importlib.util.spec_from_file_location("v9s", Path(__file__).with_name("v9_or_score.py"))
v9s = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(v9s)

SLOPE = 0.75
FROZEN_HEADLINE_P50 = 2658.0  # reports/v9-oregon/mm_totals.csv, headline 2018-2025 (D-051 results)
SETS = {  # value, low, high (D-055)
    "D-038 (frozen)": {"theta": (0.001076, 0.000362, 0.005347), "alpha": (7.29, 3.18, 19.78), "half": 2.0},
    "D-054 refit": {"theta": (0.0001235, 0.0000325, 0.001006), "alpha": (8.415, 2.80, 32.4), "half": 0.5},
}


def draws_for(inp, n: int, seed: int, ps: dict) -> np.ndarray:
    """`v9.mm_draws` with the parameter set given here instead of read from config (same random stream)."""
    rng = np.random.default_rng(seed + 7)
    theta = v9._lognormal(
        SimpleNamespace(value=ps["theta"][0], low=ps["theta"][1], high=ps["theta"][2]), n, rng
    )
    alpha = v9._lognormal(
        SimpleNamespace(value=ps["alpha"][0], low=ps["alpha"][1], high=ps["alpha"][2]), n, rng
    )
    k = v9.mm_k(inp, ps["half"], SLOPE)
    out = np.zeros((n, len(inp.geoids), len(inp.years)))
    for d in range(n):
        a = alpha[d]
        u = rng.gamma(1 / a, a, size=len(inp.geoids)) if a > 1e-9 else np.ones(len(inp.geoids))
        out[d] = rng.poisson(inp.B[:, None] + theta[d] * u[:, None] * k)
    return out


def main() -> None:
    store = DataStore()
    frozen = json.loads((REPO / "results" / "frozen" / f"{v9.TEST_ID}.json").read_text())
    if v9.table_hashes("OR", store) != frozen["input_table_sha256"]:
        raise SystemExit(
            "input tables differ from the freeze's: set LOTLINE_DATA_DIR=~/lotline-data-v9-blind"
        )
    n, seed = frozen["draws"], frozen["seed"]
    inp = v9.mm_inputs("OR", store)
    years = inp.years
    obs_store = DataStore(
        Path.home() / "lotline-data"
    )  # outcomes: the main store (the blind copy's raw is a link)
    counts = mm.bps_counts(bps.load("OR", obs_store, unblind=(v9.TEST_ID,)))["y_buildings"]
    obs = np.nan_to_num(np.array([[counts.get((p, int(y)), np.nan) for y in years] for p in inp.geoids]))
    bench = np.random.default_rng(v9s.BENCH_SEED).poisson(
        np.broadcast_to(inp.B[None, :, None], (n, len(inp.geoids), len(years)))
    )
    early = inp.T < years.max()
    periods = {"2018-2025": np.ones(len(years), bool), "2018-2022": years <= v9.SUBTOTAL_LAST}
    totals, yearly, places = [], [], []
    for label, ps in SETS.items():
        d = draws_for(inp, n, seed, ps)
        if label.startswith("D-038"):  # same stream as the freeze: identical draws, and the frozen headline
            assert np.array_equal(d, v9.mm_draws(inp, n, seed)), "D-038 draws differ from v9.mm_draws"
            p50 = float(np.percentile(d[:, early].sum(axis=(1, 2)), 50))
            assert math.isclose(p50, FROZEN_HEADLINE_P50), (
                f"headline P50 {p50} is not the frozen {FROZEN_HEADLINE_P50}"
            )
        for name, mask in (("headline (62 places)", early), ("all places", np.ones(len(inp.geoids), bool))):
            for per, ym in periods.items():
                r = v9s.score(
                    f"{name}, {per}",
                    d[:, mask][:, :, ym].sum(axis=(1, 2)),
                    obs[mask][:, ym].sum(),
                    bench[:, mask][:, :, ym].sum(axis=(1, 2)),
                )
                totals.append({"params": label} | r)
        dy = d[:, early].sum(axis=1)
        for j, y in enumerate(years):
            p10, p50, p90 = np.percentile(dy[:, j], [10, 50, 90])
            yearly.append(
                {"params": label, "year": int(y), "observed": obs[early][:, j].sum(), "p10": p10, "p50": p50,
                 "p90": p90, "no_reform_baseline": float(inp.B[early].sum())}
            )  # fmt: skip
        for i in np.where(early)[0]:
            r = v9s.score(inp.names[i], d[:, i].sum(axis=1), obs[i].sum())
            places.append({"params": label, "geoid": inp.geoids[i]} | r)
    OUT.mkdir(parents=True, exist_ok=True)
    t = pd.DataFrame(totals)
    t.round(3).to_csv(OUT / "mm_totals.csv", index=False)
    pd.DataFrame(yearly).round(1).to_csv(OUT / "mm_headline_by_year.csv", index=False)
    pl = pd.DataFrame(places)
    pl.round(3).to_csv(OUT / "mm_places.csv", index=False)
    summ = (
        pl.assign(below=pl["observed"] < pl["p10"], above=pl["observed"] > pl["p90"])
        .groupby("params")[["coverage_rand", "below", "above"]]
        .mean()
    )
    summ.round(3).to_csv(OUT / "mm_places_summary.csv")
    print(t[["params", "target", "observed", "p10", "p50", "p90", "verdict", "crps_model", "crps_no_reform"]]
          .round(1).to_string(index=False))  # fmt: skip
    print(summ.round(3).to_string())
    print(pd.DataFrame(yearly).round(0).to_string(index=False))


if __name__ == "__main__":
    main()
