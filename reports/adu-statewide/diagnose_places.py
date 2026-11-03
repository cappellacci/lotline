"""Exploratory diagnosis of the D-039/D-040 misses: per-place inputs vs observed. Read-only; no fit.

uv run python reports/adu-statewide/diagnose_places.py <out.csv>
"""

import importlib.util
import sys
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.model import calibrate_adu as cal

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("cal_script", ROOT / "scripts/dev/calibrate_adu.py")
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)


def main(out: str) -> None:
    store = DataStore()
    places = script.four_state_places(store) + script._test_set(store)
    f = pd.read_csv(ROOT / "reports" / "adu-anchor-4state" / "fit.csv").iloc[0]
    theta, alpha, cv = f.theta, f.alpha, cal._cvals(f.m_owner, f.m_other)
    recs = []
    for pl in places:
        rows = cal.place_years(pl.state, store, [pl.geoid], pl.years)
        big_k = float((pl.w / pl.w.sum()) @ pl.k(cv).sum(axis=1))
        y = float(pl.y.sum())
        ramp = rows[["ramp_handbook", "ramp_partial", "ramp_blank"]].max(axis=1)
        recs.append(dict(state=pl.state, name=pl.name, geoid=pl.geoid, n=len(pl.y), observed=int(y),
                         parcels=rows.eligible_parcels.mean(), rent=rows.rent.mean(),
                         value=rows.home_value.mean(), h1=rows.h1.mean(), ramp=ramp.mean(),
                         partial=(rows.ramp_partial > rows.ramp_handbook).mean(), q_blank=rows.q_blank.mean(),
                         expected=theta * big_k, rate_per_1000=y / rows.eligible_parcels.sum() * 1000,
                         u_post=(y + 1 / alpha) / (theta * big_k + 1 / alpha)))  # fmt: skip
    df = pd.DataFrame(recs).assign(obs_over_exp=lambda d: d.observed / d.expected)
    df.to_csv(out, index=False)
    print(df.drop(columns=["geoid"]).round(3).sort_values("obs_over_exp").to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
