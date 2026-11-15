#!/usr/bin/env python3
"""D-096: run a dev ADU script with `UNKNOWN-PLACEHOLDER` place-years left out of its inputs.

    PYTHONPATH=<checkout with the corrected rows>/src python scripts/dev/adu_refit_fixed_rows.py \
        adu_types_refit.py --out reports/adu-types-fixed-rows --workers 7

The rule rows come from the `config/` next to the `src` on PYTHONPATH (`lotline.config.CONFIG_DIR`). Any ADU
rule row whose `coding_notes` holds `UNKNOWN-PLACEHOLDER` marks its place's years from its effective date to
the day before its end date as unknown; `adu_owner_refit.inputs` (which every D-084 to D-095 script reads its
places from) is wrapped so those years are cut (`joint_refit.subset_years`). The named script is
loaded as a module at the top level (so worker processes, which re-run this file, can unpickle its functions)
and its `main()` runs with the remaining arguments.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pandas as pd

from lotline.config import CONFIG_DIR
from lotline.model import joint_refit as jr
from lotline.model.scenarios import adu

HERE = Path(__file__).resolve().parent
TAG = "UNKNOWN-PLACEHOLDER"
ENV = "LOTLINE_REFIT_TARGET"


def unknown_years() -> dict[str, set[int]]:
    """{geoid: years} under a placeholder row. By hand: effective 2016-01-01, end 2023-01-01 -> 2016-2022."""
    out: dict[str, set[int]] = {}
    for st in adu.REFORM_STATES:
        r = adu.load_reforms(st)
        r = r[(r["theme"] == "adu") & r["coding_notes"].fillna("").str.contains(TAG)]
        for row in r.itertuples():
            y0 = pd.Timestamp(row.effective_date).year
            end = pd.Timestamp(row.end_date) if pd.notna(row.end_date) else pd.Timestamp("2100-01-01")
            y1 = (end - pd.Timedelta(days=1)).year
            out.setdefault(str(row.jurisdiction_geoid), set()).update(range(y0, y1 + 1))
    return out


def _load(name: str, file: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def patch() -> dict[str, set[int]]:
    """Wrap the `adu_owner_refit` module the target script ended up with (each script's loader re-executes
    its helpers, so the wrap is applied after the target is loaded)."""
    drop = unknown_years()
    own = sys.modules["adu_owner_refit"]
    base = own.inputs

    def inputs(store):
        places, new, table = base(store)
        kept = []
        for p in places:
            gone = drop.get(p.geoid)
            if gone:
                p = jr.subset_years(p, [y for y in p.years if int(y) not in gone])
            if p is not None:
                kept.append(p)
        return kept, new, table

    own.inputs = inputs
    return drop


# top level, so worker processes (which re-run this file) load and patch the same way
# worker processes get other arguments, so the target's file name travels in the environment
if len(sys.argv) > 1 and sys.argv[1].endswith(".py"):
    os.environ[ENV] = sys.argv[1]
_name = os.environ.get(ENV)
TARGET = _load(Path(_name).stem, Path(_name).name) if _name else None
DROPPED = patch() if TARGET is not None else {}

if __name__ == "__main__":
    print(
        f"config: {CONFIG_DIR}; unknown place-years left out: { {g: sorted(y) for g, y in DROPPED.items()} }"
    )
    sys.argv = [str(HERE / sys.argv[1]), *sys.argv[2:]]
    TARGET.main()
