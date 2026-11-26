#!/usr/bin/env python3
"""Missing-middle gut check, numbers: reports/mm-gut-check/summary.json.

    uv run lotline results --all            # writes reports/results/<st>/bundle.json (gitignored)
    uv run python scripts/archive/mm_gut_check_data.py [--results reports/results]

Report only (no model run): reads each state's results bundle and compares the missing-middle scenario
with Census BPS homes in 2-4 unit buildings for 2019-2025 (the bundle's `observed` rows). Per state:
- history: observed 2-4 unit homes by year, the 2019-2025 mean and the 2023-2025 mean ("recent pace");
- baseline: no-reform 2-4 unit homes, 2027-2031 total (P10/P50/P90, mean) and its yearly P50s and means;
- added: the scenario's permits_added, homes_in_place and homes_net_statewide, 2027-2031 and by year;
- floor: the bundle's `historical_floor:missing_middle` scorecard value (with-reform median a year
  divided by the 2023-2025 observed mean);
- funnel: P10/P50/P90 across draws of each stage of `aggregate.homes_from_draws`.

By hand (MN): recent pace (461 + 656 + 567) / 3 = 561.3 a year, 2,807 over five years; added permits
P50 2,934 -> 1.05 times the recent five-year pace.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.model import aggregate

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "mm-gut-check"
STATES = ("mn", "nc", "oh", "tx", "or")
WINDOW = "2027-2031"
OUTCOMES = ("permits_added", "homes_in_place", "homes_net_statewide")


def q(a) -> list[float]:
    return [float(np.percentile(np.asarray(a, dtype=float), p)) for p in (10, 50, 90)]


def state_summary(b: dict) -> dict:
    meta = b["meta"]
    obs = {int(r["year"]): r["value"] for r in b["observed"] if r["measure"] == "homes_2_4"}
    base = {r["period"]: r for r in b["baseline"] if r["size_class"] == "2_4"}
    tot = {(r["outcome"], r["period"]): r for r in b["totals"] if r["scenario"] == "missing_middle"}
    years = [str(y) for y in range(meta["origin_year"] + 2, meta["origin_year"] + 2 + meta["horizon_years"])]
    d = pd.DataFrame(b["draws"])
    d = d[d["scenario"] == "missing_middle"]
    h = aggregate.homes_from_draws(d)
    recent = float(np.mean([obs[y] for y in (2023, 2024, 2025)]))
    floor = next(r for r in b["scorecard"] if r["check_id"] == "historical_floor:missing_middle")
    pct = lambda r: [r["p10"], r["p50"], r["p90"]]  # noqa: E731
    return {
        "state": meta["state"],
        "commit_sha": meta["commit_sha"],
        "schemas_version": meta["schemas_version"],
        "n_draws": meta["n_draws"],
        "history": {str(y): v for y, v in sorted(obs.items())},
        "history_mean": float(np.mean(list(obs.values()))),
        "recent_pace": recent,
        "baseline": pct(base[WINDOW]) + [base[WINDOW]["mean"]],
        "baseline_coverage": base[WINDOW]["coverage_share"],
        "baseline_by_year_p50": [base[y]["p50"] for y in years],
        "baseline_by_year_mean": [base[y]["mean"] for y in years],
        "added": {o: pct(tot[(o, WINDOW)]) for o in OUTCOMES},
        "added_by_year_p50": [tot[("permits_added", y)]["p50"] for y in years],
        "net_by_year_p50": [tot[("homes_net_statewide", y)]["p50"] for y in years],
        "floor": floor["value"],
        "floor_verdict": floor["verdict"],
        "funnel": {
            "legal": q(h["legal"]),
            "pencil_out_share": q(d["pencil_out_share"]),
            "pencils": q(h["pencils"]),
            "theta_per_1000": q(d["theta"] * 1000),
            "permits_added": q(h["permits_added"]),
            "completion": q(d["completion_factor"]),
            "net_new_share": q(d["net_new_share"]),
            "homes_in_place": q(h["homes_in_place"]),
            "displacement": q(d["displacement_share"]),
            "homes_net_statewide": q(h["homes_net_statewide"]),
        },
        "years": years,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, default=REPO / "reports" / "results")
    args = ap.parse_args()
    load = lambda st: json.loads((args.results / st / "bundle.json").read_text())  # noqa: E731
    out = {st.upper(): state_summary(load(st)) for st in STATES}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
    for st, s in out.items():
        five = 5 * s["recent_pace"]
        print(
            f"{st}: recent {s['recent_pace']:,.0f}/yr | baseline P50 {s['baseline'][1]:,.0f} "
            f"({s['baseline'][1] / five:.0%} of 5x recent) | added P50 {s['added']['permits_added'][1]:,.0f} "
            f"({s['added']['permits_added'][1] / five:.2f}x) | floor {s['floor']:.2f} {s['floor_verdict']}"
        )
    print(f"wrote {OUT / 'summary.json'}")


if __name__ == "__main__":
    main()
