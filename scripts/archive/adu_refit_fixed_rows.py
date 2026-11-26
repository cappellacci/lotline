#!/usr/bin/env python3
"""D-096: run a dev ADU script with `UNKNOWN-PLACEHOLDER` place-years left out of its inputs.

    PYTHONPATH=<checkout with the corrected rows>/src python scripts/archive/adu_refit_fixed_rows.py \
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

from lotline.config import CONFIG_DIR
from lotline.model import adu_fit_set as fs

HERE = Path(__file__).resolve().parent
ENV = "LOTLINE_REFIT_TARGET"


def unknown_years() -> dict[str, set[int]]:
    """{geoid: years} under a placeholder row (`adu_fit_set.unknown_years`)."""
    return fs.unknown_years()


def _load(name: str, file: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _cut(p, drop):
    return fs.limit_years(p, drop) if p is not None and p.geoid in drop else p


def patch() -> dict[str, set[int]]:
    """Cut the unknown years in whichever place builders the target script ended up with:
    `adu_owner_refit.inputs` (D-084 to D-095) and `adu_joint_refit`'s `fit_set`, `all_places` and
    `limit_years` (D-079's fit set), which now pass the years to the library builders
    (`lotline.model.adu_fit_set`). The calibration scripts (`adu_mx_grid`, `adu_config_fit`,
    `adu_types_slopes`, `adu_reference --fit-set`, `adu_new_rule`) cut them through the library and no
    longer need this wrapper."""
    gone = unknown_years()
    own = sys.modules.get("adu_owner_refit")
    if own is not None:
        base_inputs = own.inputs

        def inputs(store):
            places, new, table = base_inputs(store)
            return [q for q in (_cut(p, gone) for p in places) if q is not None], new, table

        own.inputs = inputs
    jrm = sys.modules.get("adu_joint_refit")
    if jrm is not None:

        def fit_set(st, store, undercount="table", drop=()):
            return fs.fit_set(st, store, undercount, drop, unknown=gone)

        def all_places(store, undercount="table", drop=()):
            return fs.all_places(store, undercount, drop, unknown=gone)

        def limit_years(pl):
            return fs.limit_years(pl, gone)

        jrm.fit_set, jrm.all_places, jrm.limit_years = fit_set, all_places, limit_years
    return gone


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
