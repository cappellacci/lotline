#!/usr/bin/env python3
"""The A + place types fit the ADU config holds, on the rule rows in `config/reforms/` (D-096 inputs).

    PYTHONPATH=src python scripts/dev/adu_refit_fixed_rows.py adu_config_fit.py --out reports/adu-final-config

Builds the D-096 inputs (St. Paul out; `UNKNOWN-PLACEHOLDER` place-years cut by the wrapper) and fits Form
A + P with `adu_types.fit3_types` (θ and its 90% profile interval, α, m_o and m_x on the 0.1 grid with their
intervals, β_core with its interval). Writes `fit.json`. Offline; nothing is written to config.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from lotline.io import DataStore, offline
from lotline.model import adu_types as ty

HERE = Path(__file__).resolve().parent


def _load(name: str, file: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


GRID = _load("adu_mx_grid", "adu_mx_grid.py")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        pz = GRID.places(store)
    f = ty.fit3_types(pz, estimate_beta=False)
    out = {
        "places": len(pz),
        "place_years": int(sum(len(p.y) for p in pz)),
        "theta": f.theta,
        "theta_low": f.low,
        "theta_high": f.high,
        "alpha": f.alpha,
        "m_owner": f.m_owner,
        "m_owner_interval": list(f.owner_interval),
        "m_other": f.m_other,
        "m_other_interval": list(f.other_interval),
        "core": f.type_beta[0],
        "core_low": f.type_low[0],
        "core_high": f.type_high[0],
        "loglik": f.loglik,
    }
    (a.out / "fit.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
