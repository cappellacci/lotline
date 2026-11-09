#!/usr/bin/env python3
"""V5: predict Mecklenburg County's (37119) BPS 2-4 unit buildings in 2023-2025 after Charlotte's UDO, from
the missing-middle fit that never saw Charlotte (analysis plan D-071, `lotline.validation.v5`).

    uv run python scripts/dev/v5_clt_predict.py --out <dir>   # dry run: a prediction, not committed
    uv run python scripts/dev/v5_clt_predict.py --freeze      # results/frozen/V5-NC-CHARLOTTE.json, once

Reads only holdout-filtered inputs dated before 2023-06-01 (annual inputs to 2022); never unblinds. The
freeze refuses to overwrite an existing file. A dry run's output stays outside results/frozen/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lotline.config import load_params
from lotline.io import DataStore
from lotline.validation import v5

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
    print(f"  N1 lots {i['n1_lots']:,}, share {i['share_low']:.3f}-{i['share_high']:.3f}, dose gap "
          f"{i['gap']:.4f}, F ratio {i['f_ratio']:.3f}, B {i['B']:.1f} buildings/yr")  # fmt: skip
    for k, s in payload["prediction"].items():
        t = s["2023-2025"]
        print(
            f"  {k}: 2023-2025 P10 {t['p10']:,.0f}  P50 {t['p50']:,.0f}  P90 {t['p90']:,.0f}"
            f"  mean {t['mean']:,.1f}"
        )


if __name__ == "__main__":
    main()
