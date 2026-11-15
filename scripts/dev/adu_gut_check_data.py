#!/usr/bin/env python3
"""The counted ADUs per place and year behind the fit (for the gut-check page), from the D-096 inputs.

    PYTHONPATH=<checkout with the corrected rows>/src python scripts/dev/adu_refit_fixed_rows.py \
        adu_gut_check_data.py --out reports/adu-gut-check

Writes `place_years.csv`: state, geoid, name, year, ADUs counted (undercount-scaled, as fitted) and the
base exposure (eligible lots). Offline; St. Paul is out (adu_joint_refit). Nothing is fitted.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import pandas as pd

from lotline.io import DataStore, offline

HERE = Path(__file__).resolve().parent


def _load(name: str, file: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


TYP = _load("adu_types_refit", "adu_types_refit.py")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    store = DataStore()
    with offline.offline_build(store):
        places, _new, _own = TYP.OWN.inputs(store)
    rows = [
        {
            "state": p.state,
            "geoid": p.geoid,
            "name": p.name,
            "year": int(y),
            "adus": float(v),
            "eligible": float(b),
        }
        for p in places
        for y, v, b in zip(p.years, p.y, p.base, strict=True)
    ]
    pd.DataFrame(rows).to_csv(a.out / "place_years.csv", index=False)
    print(pd.DataFrame(rows).groupby(["state", "year"])["adus"].sum().unstack(0).round(0).to_string())


if __name__ == "__main__":
    main()
