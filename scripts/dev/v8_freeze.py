"""V8 Wisconsin: write the frozen prediction, results/frozen/V8-WI-TRANSFER.json (analysis plan D-104).

Runs the standard results bundle for Wisconsin at origin 2019, offline, from the holdout-filtered tables (no
Wisconsin outcome from 2020 on exists in them), and writes the parts that are scored or kept for the record,
with the commit, seed, config hash and a SHA-256 of every input table. The per-draw scenario rows are left
out: they regenerate from the commit and seed.

    uv run python scripts/dev/v8_freeze.py            # writes the file
    uv run python scripts/dev/v8_freeze.py --check    # rebuilds and compares with the committed file

Scoring (D-104, after Ben unblinds): the observed 2021-2025 statewide Census permits (reported units, the
bundle's `basis`) against `prediction.baseline`, all sizes and each size class; a hit is P10 <= observed <=
P90.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from lotline.io import DataStore
from lotline.io.offline import offline_build
from lotline.model import results
from lotline.validation import holdout

TEST_ID = "V8-WI-TRANSFER"
STATE = "WI"
ORIGIN = 2019
YEARS = list(range(2021, 2026))
INPUT_TABLES = ("acs_geo_year", "bps_place_year", "eligible_parcels", "jurisdictions", "market_geo_year")
KEEP = ("meta", "baseline", "totals", "need", "scorecard", "funnel", "observed")
REPO = Path(__file__).resolve().parents[2]


def table_hashes(store: DataStore) -> dict[str, str]:
    out = {}
    for table in INPUT_TABLES:
        h = hashlib.sha256()
        for f in sorted(store.processed(STATE, table).glob("*.parquet")):
            h.update(f.name.encode())
            h.update(f.read_bytes())
        out[table] = h.hexdigest()
    return out


def freeze() -> dict:
    store = DataStore()
    holdout.assert_no_leak(store.read(STATE, "bps_place_year"), "bps_place_year", STATE)
    with offline_build(store):
        bundle = results.build_bundle(STATE, store, origin=ORIGIN)
    meta = bundle["meta"].iloc[0].to_dict()
    parts = {p: json.loads(bundle[p].to_json(orient="records")) for p in KEEP if p in bundle and p != "meta"}
    return {
        "test_id": TEST_ID,
        "method": (
            "D-104: lotline results --state WI --origin 2019, national data only, no Wisconsin-specific code"
        ),
        "commit": meta["commit_sha"],
        "draws": int(meta["n_draws"]),
        "seed": int(meta["seed"]),
        "origin": ORIGIN,
        "years": YEARS,
        "target": "statewide Census permits (reported units) 2021-2025, all sizes and each size class",
        "pass_rule": "observed five-year total inside P10-P90 of prediction.baseline (size_class 'all')",
        "secondary": {
            "size_classes": "each size class's five-year total inside its P10-P90",
            "ratio": "observed / P50, reported",
            "v0": "2010-2019 place sums within 1% of state totals (reports/wi/V0-national.md)",
            "overlap": "share of places outside the calibration range (meta.overlap_flag, overlap_note)",
            "not_scored": (
                "adu, missing_middle and fee rows are reform counterfactuals with no observed outcome"
            ),
        },
        "exposure": (
            "none: Wisconsin permits and ACS stock from 2020 on are dropped at build (holdout V8-WI-TRANSFER)"
        ),
        "inputs": {"tables": list(INPUT_TABLES), "data_tier": int(meta["data_tier"])},
        "params": {},
        "input_table_sha256": table_hashes(store),
        "config_sha256": meta["config_hash"],
        "prediction": {"meta": {k: (None if v != v else v) for k, v in meta.items()}, **parts},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    path = REPO / holdout.FROZEN_DIR / f"{TEST_ID}.json"
    new = freeze()
    if args.check:
        old = json.loads(path.read_text())
        for d in (old, new):
            d["prediction"]["meta"].pop("run_at", None)
            d["prediction"]["meta"].pop("commit_sha", None)
            d.pop("commit", None)
        same = old == new
        print("identical to the frozen file" if same else "DIFFERS from the frozen file")
        return 0 if same else 1
    path.write_text(json.dumps(new, indent=1, sort_keys=True, default=str) + "\n")
    print(f"wrote {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
