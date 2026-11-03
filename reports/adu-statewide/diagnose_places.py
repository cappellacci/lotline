"""Exploratory diagnosis of D-039/D-040 misses: per-place inputs vs observed. Read-only; no fit."""
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd
from lotline.io import DataStore
from lotline.model import calibrate_adu as cal
root = Path("/Users/bencappellacci/Engineering/lotline-engine14")
spec = importlib.util.spec_from_file_location("s", root / "scripts/dev/calibrate_adu.py")
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
store = DataStore()
places = s.four_state_places(store) + s._test_set(store)
f = pd.read_csv(root / "reports/adu-anchor-4state/fit.csv").iloc[0]
theta, alpha, cv = f.theta, f.alpha, cal._cvals(f.m_owner, f.m_other)
recs = []
for pl in places:
    rows = cal.place_years(pl.state, store, [pl.geoid], pl.years)
    K = float((pl.w / pl.w.sum()) @ pl.k(cv).sum(axis=1))
    Y = float(pl.y.sum())
    recs.append(dict(state=pl.state, name=pl.name, geoid=pl.geoid, years=f"{pl.years.min()}-{pl.years.max()}",
        n=len(pl.y), observed=int(Y), parcels=rows.eligible_parcels.mean(), rent=rows.rent.mean(),
        value=rows.home_value.mean(), h1=rows.h1.mean(), ramp=rows[["ramp_handbook","ramp_partial","ramp_blank"]].max(axis=1).mean(),
        partial=(rows.ramp_partial > rows.ramp_handbook).mean(), q_blank=rows.q_blank.mean(),
        expected=theta * K, rate_per_1000=Y / rows.eligible_parcels.sum() * 1000,
        u_post=(Y + 1 / alpha) / (theta * K + 1 / alpha)))
df = pd.DataFrame(recs)
df["obs_over_exp"] = df.observed / df.expected
df.to_csv(sys.argv[1], index=False)
pd.set_option("display.width", 250)
print(df.drop(columns=["geoid"]).round(3).sort_values("obs_over_exp").to_string(index=False))
