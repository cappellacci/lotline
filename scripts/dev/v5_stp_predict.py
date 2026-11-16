#!/usr/bin/env python3
"""V5: predict St. Paul's (2758000) BPS 2-4 unit buildings in 2024-2026 after its H1/H2 reform, with C4 (the
missing-middle fit that never saw St. Paul; analysis plan D-098, `lotline.validation.v5_stpaul`).

    uv run python scripts/dev/v5_stp_predict.py --out <dir>   # dry run: a prediction, not committed
    uv run python scripts/dev/v5_stp_predict.py --freeze      # results/frozen/V5-MN-STPAUL.json, once

Reads only holdout-filtered inputs dated before 2024 (annual inputs to 2023); never unblinds. The freeze
refuses to overwrite an existing file. A dry run's output stays outside results/frozen/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lotline.config import load_params
from lotline.io import DataStore
from lotline.validation import v5_stpaul as v5

REPO = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, help="dry run: write prediction.json here")
    ap.add_argument("--freeze", action="store_true", help="write the one-time freeze file")
    a = ap.parse_args()
    if bool(a.out) == a.freeze:
        ap.error("pass exactly one of --out or --freeze")
    store = DataStore()
    mm = load_params("mm")
    n, seed = int(mm["mm_scenario_draws"].value), int(mm["mm_scenario_seed"].value)
    inp = v5.inputs(store)
    d = v5.draws(inp, n, seed)
    payload = v5.freeze_payload(inp, d, n, seed, store, REPO)
    if a.freeze:
        print(f"frozen: {v5.write_freeze(payload, REPO)}")
    else:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "prediction.json").write_text(json.dumps(payload, indent=2, default=str) + "\n")
        print(f"dry run: {a.out / 'prediction.json'}")
    i = payload["inputs"]
    print(f"  eligible H1/H2 lots {i['eligible']:,}, dose gap {i['gap']:.3f}, F ratio {i['f_ratio']:.3f}, "
          f"B {i['B']:.2f} buildings/yr")  # fmt: skip
    for k, s in payload["prediction"].items():
        for span in ("2024-2025", "2024-2026"):
            t = s[span]
            print(f"  {k} {span}: P10 {t['p10']:,.0f}  P50 {t['p50']:,.0f}  P90 {t['p90']:,.0f}  "
                  f"mean {t['mean']:,.1f}")  # fmt: skip


if __name__ == "__main__":
    main()
