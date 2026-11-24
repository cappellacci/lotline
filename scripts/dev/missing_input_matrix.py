"""WS-SCALE task 9: how far a state's results move when one input drops to its fallback.

Runs `lotline results` for one state four times in this process, offline, with the same seed:
- `base`: as is;
- `no_parcels`: the state's parcels hidden, so `jurisdictions` and `eligible_parcels` are rebuilt in memory
  from the ACS (tier 3, D-056 scaling);
- `no_zoning`: the state's coded reform rows emptied, so every place takes the borrowed rule priors;
- `no_permits`: the state's permit table hidden (no observed ADU floor).

Nothing is written to the data directory: tables are hidden by a `DataStore` subclass and rebuilt ones live
in memory. Holdout filters stay in force (no unblinding). Writes each run's meta, totals and need parts to OUT
as parquet, and the five-year statewide table to OUT/matrix.csv.

    uv run python scripts/dev/missing_input_matrix.py --state NC --out /tmp/missing
"""

import argparse
import time
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.io.offline import offline_build
from lotline.model import results
from lotline.model.scenarios import adu

VARIANTS = ("base", "no_parcels", "no_zoning", "no_permits")


class HidingStore(DataStore):
    """Hides some of one state's tables and serves rebuilt ones; everything else is read as usual."""

    def __init__(self, state: str, hide=(), replace=None):
        super().__init__()
        self.state, self.hide, self.replace = state, set(hide), dict(replace or {})

    def read(self, state, table):
        if state.upper() == self.state and table in self.hide:
            return None
        if state.upper() == self.state and table in self.replace:
            return self.replace[table].copy()
        return super().read(state, table)


def store_for(variant: str, st: str) -> DataStore:
    if variant == "no_parcels":
        from lotline.build import eligible
        from lotline.build import jurisdictions as jur

        s = HidingStore(st, hide={"parcels"})
        s.replace["jurisdictions"] = jur.load(st, s)  # tiers with no parcels
        s.replace["eligible_parcels"] = eligible.load(st, s)  # ACS rows only
        return s
    if variant == "no_permits":
        return HidingStore(st, hide={"permits"})
    return HidingStore(st)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    st, out = args.state.upper(), args.out
    out.mkdir(parents=True, exist_ok=True)
    real = adu.load_reforms

    def without_state(state, config_dir=None):
        df = real(state) if config_dir is None else real(state, config_dir)
        return df.iloc[0:0] if state.upper() == st else df

    rows = []
    for v in VARIANTS:
        t = time.time()
        with offline_build(DataStore()):
            store = store_for(v, st)
            adu.load_reforms = without_state if v == "no_zoning" else real
            try:
                b = results.build_bundle(st, store)
            finally:
                adu.load_reforms = real
        for part in ("meta", "totals", "need"):
            b[part].to_parquet(out / f"{v}_{part}.parquet")
        tot = b["totals"]
        tot = tot[(tot["outcome"] == "homes_net_statewide") & tot["period"].str.contains("-")]
        rows += [dict(variant=v, **r) for r in tot[["scenario", "p10", "p50", "p90"]].to_dict("records")]
        print(f"{v}: {time.time() - t:.0f}s", flush=True)
    d = pd.DataFrame(rows)
    base = d[d["variant"] == "base"].set_index("scenario")
    d["median_change_pct"] = 100 * (d["p50"] / d["scenario"].map(base["p50"]) - 1)
    d["range_ratio"] = (d["p90"] - d["p10"]) / d["scenario"].map(base["p90"] - base["p10"])
    d.to_csv(out / "matrix.csv", index=False)
    print(d.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
