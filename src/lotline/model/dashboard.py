"""The engine results dashboard: one self-contained HTML page that shows and compares runs.

`render(runs)` takes runs as `runs.load_run` returns them and fills `dashboard.html` (next to this file): the
page embeds the runs as JSON and draws every chart in the browser with plain SVG, so it needs no server, no
network and no extra dependency. Pick up to three runs to compare; for each it shows the method, data scope,
configuration and reading from the run's manifest, then the overall effect, the effect terms, the checks,
the robustness fits, randomization inference, leave one out, the out-of-sample tests and the added homes.
Calibration runs (D-038 to D-041) show instead: the uptake-rate fits, held-out state totals and their
verdicts, observed against predicted by place, the test places, and the counts and market-term check.

    uv run python scripts/dev/results_dashboard.py            # every run under reports/
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

TEMPLATE = Path(__file__).with_name("dashboard.html")


def render(runs: list[dict], generated: str | None = None) -> str:
    """The page for `runs` (oldest first). `generated` labels the page (default: now)."""
    if not runs:
        raise ValueError("no runs to show")
    ids = [r["id"] for r in runs]
    if len(set(ids)) != len(ids):
        raise ValueError(f"run ids must be unique: {ids}")
    data = json.dumps(runs, allow_nan=False, default=str).replace("</", "<\\/")
    stamp = generated or datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    return TEMPLATE.read_text().replace("__GENERATED__", stamp).replace("__RUNS_JSON__", data)
