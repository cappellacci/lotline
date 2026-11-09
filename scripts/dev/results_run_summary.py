#!/usr/bin/env python3
"""Summarize a set of results bundles for a run's results page (not part of the app).

    uv run python scripts/dev/results_run_summary.py --out reports/results-run-2026-11-09/summary.json

Reads `reports/results/<st>/bundle.json` for every state given and writes one JSON with, per state: meta,
the baseline's five-year and per-year ranges (all sizes) and by building size, each scenario's five-year
`homes_net_statewide` and `permits_added`, the headline share of need, and the observed BPS units of the
last seven years on the baseline's own basis (reported or with imputation), from the holdout-filtered panel.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lotline.build import eligible, panels
from lotline.io import DataStore
from lotline.model import baseline


def summarize(st: str, store, results_dir: Path) -> dict:
    b = json.loads((results_dir / st.lower() / "bundle.json").read_text())
    base = b["baseline"]
    window = next(r["period"] for r in base if "-" in r["period"])
    reported = base[0]["basis"] == "reported"
    panel = panels.load(st, store, theme="adu", rule_version=eligible.RULE_VERSION)
    cols = [baseline.outcome_column(s, reported) for s in baseline.SIZE_CLASSES]
    origin = int(b["meta"]["origin_year"])
    by_year = panel[panel["year"].between(origin - 6, origin)].groupby("year")[cols].sum().sum(axis=1)
    keep = ("p10", "p50", "p90", "mean")
    return {
        "meta": {
            k: b["meta"][k]
            for k in (
                "state",
                "state_role",
                "data_tier",
                "overlap_flag",
                "commit_sha",
                "run_at",
                "n_draws",
                "origin_year",
            )
        },  # fmt: skip
        "window": window,
        "baseline_window": {r["size_class"]: {k: r[k] for k in keep} for r in base if r["period"] == window},
        "baseline_years": {
            r["period"]: {k: r[k] for k in keep}
            for r in base
            if r["size_class"] == "all" and "-" not in r["period"]
        },  # fmt: skip
        "baseline_places": base[0]["places"],
        "baseline_coverage": base[0]["coverage_share"],
        "basis": base[0]["basis"],
        "observed": {str(int(y)): float(v) for y, v in by_year.items()},
        "scenarios": {
            r["scenario"] + ":" + r["outcome"]: {k: r[k] for k in keep}
            for r in b["totals"]
            if r["period"] == window and r["outcome"] in ("homes_net_statewide", "permits_added")
        },
        "need": [
            {
                k: r[k]
                for k in (
                    "scenario",
                    "denominator_kind",
                    "denominator",
                    "share_p10",
                    "share_p50",
                    "share_p90",
                )
            }
            for r in b["need"]
            if r["is_headline"]
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--states", nargs="+", default=["MN", "NC", "OH", "OR", "TX"])
    ap.add_argument("--results", type=Path, default=Path("reports/results"))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    store = DataStore()
    doc = {st: summarize(st, store, a.results) for st in a.states}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc, indent=1) + "\n")
    print(a.out)


if __name__ == "__main__":
    main()
