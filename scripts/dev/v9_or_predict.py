#!/usr/bin/env python3
"""V9: predict Oregon's 2018-2025 ADU permits and 2-4 unit buildings from the four-state fit (D-046), with
the ADU targets also updated on their own pre-2018 permits (D-049, config/validation/or_adu_history.csv).

    uv run python scripts/dev/v9_or_predict.py --out <dir>   # dry run: a prediction, not committed
    uv run python scripts/dev/v9_or_predict.py --freeze      # results/frozen/V9-OR-TRANSFER.json, once

Reads only holdout-filtered inputs; never passes --unblind. The freeze refuses to overwrite an existing file.
A dry run's output is a prediction (no Oregon outcome is read) and stays outside results/frozen/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lotline.io import DataStore
from lotline.model.scenarios import adu
from lotline.validation import v9

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, help="dry run: write prediction.json here")
    ap.add_argument("--freeze", action="store_true", help="write the one-time freeze file")
    ap.add_argument("--draws", type=int)
    a = ap.parse_args()
    if bool(a.out) == a.freeze:
        ap.error("pass exactly one of --out or --freeze")
    store = DataStore()
    central = adu.central_params()
    draws = int(a.draws or central["adu_simulation_draws"])
    seed = int(central["adu_simulation_seed"])
    adu_in = v9.adu_inputs("OR", store, list(v9.ADU_TARGETS))
    counts = v9.load_history(REPO / v9.HISTORY_FILE)
    history = v9.adu_history("OR", store, list(v9.ADU_TARGETS), counts)
    mm_in = v9.mm_inputs("OR", store)
    pred = v9.prediction(
        adu_in,
        v9.adu_draws(adu_in, draws, seed),
        mm_in,
        v9.mm_draws(mm_in, draws, seed),
        adu_hist_d=v9.adu_draws(adu_in, draws, seed, history=history),
    )
    payload = v9.freeze_payload(pred, v9.table_hashes("OR", store), draws, seed, REPO)
    if a.freeze:
        print(f"frozen: {v9.write_freeze(payload, REPO)}")
    else:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "prediction.json").write_text(json.dumps(payload, indent=2) + "\n")
        print(f"dry run: {a.out / 'prediction.json'}")
    for t in pred["targets"][: 2 * len(adu_in.geoids)] + pred["totals"]:
        s = t["by_period"]["2018-2025"]
        print(f"  {t['target']}: 2018-2025 P10 {s['p10']:,.0f}  P50 {s['p50']:,.0f}  P90 {s['p90']:,.0f}")
    print(f"  missing-middle places: {pred['n_mm_places']} ({pred['n_mm_places_before_2025']} before 2025)")


if __name__ == "__main__":
    main()
