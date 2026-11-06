#!/usr/bin/env python3
"""D-053: Portland's and Bend's yearly ADU counts against each fit's predictive (θ and the place effect drawn,
as for any place), five-state fit next to the four-state D-048 fit.

    LOTLINE_FIT_WITH_OR=1 uv run python scripts/dev/d053_or_insample.py --out reports/adu-d053-fit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_adu as run  # noqa: E402

from lotline.io import DataStore  # noqa: E402
from lotline.model import calibrate_adu as cal  # noqa: E402
from lotline.model import calibrate_shape as shp  # noqa: E402
from lotline.model.scenarios import adu  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if not run.WITH_OR:
        raise SystemExit("set LOTLINE_FIT_WITH_OR=1")
    store, counts = DataStore(), cal.count_settings()
    places = run.four_state_places(store, counts, params=run.pre_d048())
    p = adu.central_params()
    flat = [shp.shaped(pl, shp.NO_RAMP, p["adu_equity_elasticity"], 0.0, p) for pl in places]
    four = [f for f in flat if f.state != "OR"]
    fits = {"five states": cal.fit3(flat), "four states (D-048)": cal.fit3(four)}
    oregon = [f for f in flat if f.state == "OR"]
    rows = []
    for name, fit in fits.items():
        draws = cal.predict_places(oregon, fit, seed=run.SEED)
        for pl in oregon:
            d = np.asarray(draws[pl.geoid])
            for j, yr in enumerate(pl.years):
                col = d[:, j]
                rows.append(dict(fit=name, place=pl.name, geoid=pl.geoid, year=int(yr),
                                 observed=float(pl.y[j]), p10=np.percentile(col, 10),
                                 p50=np.percentile(col, 50), p90=np.percentile(col, 90)))  # fmt: skip
    out = pd.DataFrame(rows)
    out.to_csv(a.out / "or_insample.csv", index=False)
    print(out.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
