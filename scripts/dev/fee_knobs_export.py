#!/usr/bin/env python3
"""Export the fee slider's grid for the results page (D-077): statewide five-year units added for each fee
change and home type, in every draw, plus the central path (development run; not a published result).

    uv run python scripts/dev/fee_knobs_export.py [--origin 2025] [--state MN NC OH TX]
        [--out reports/fees-knobs/grid.json]

Places and inputs are the statewide run's (`fee_dev_run.statewide_places`, D-076). For each slider stop
(`SHARES`: a change of −s × each place's real local fee, from a rise of half to abolishing fees) it runs
`fees.change_grid` (the same draws as `fees.run`) and `fees.central_path`, and writes one JSON file the page
reads: per state and size class, the draws at every stop (rounded to 0.1 home), the central value and the
baseline. The page adds the classes a user switches on, draw by draw, and reads P10/P50/P90 off the sums.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import numpy as np

from lotline.io import DataStore
from lotline.model.scenarios import fees

_spec = importlib.util.spec_from_file_location("fee_dev_run", Path(__file__).with_name("fee_dev_run.py"))
dev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dev)

SHARES = [round(s, 1) for s in np.arange(-0.5, 1.01, 0.1)]  # -0.5 = fees up by half; 1.0 = no fees
SIZES = tuple(fees.SIZE_TYPES)  # "1", "2", "3_4"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--origin", type=int, default=2025)
    ap.add_argument("--state", nargs="+", default=["MN", "NC", "OH", "TX"])
    ap.add_argument("--out", type=Path, default=Path("reports/fees-knobs/grid.json"))
    ap.add_argument("--page", type=Path, help="results page whose GRID block to rewrite with the grid")
    ap.add_argument("--from-json", action="store_true", help="skip the run: put --out's grid into --page")
    a = ap.parse_args()
    if a.from_json:
        write_page(a.page, a.out.read_text())
        return
    store = DataStore()
    out = {
        "note": "Development run (D-077): five-year (2027-2031) homes added vs the baseline, by size class.",
        "shares": SHARES,
        "sizes": list(SIZES),
        "states": {},
    }
    for state in a.state:
        t0 = time.time()
        places = dev.statewide_places(state, store, a.origin)
        ok = places["home_value"].notna() & places.filter(like="baseline_y").notna().all(axis=1)
        places = places[ok].reset_index(drop=True)
        grid = fees.change_grid(places, a.origin, SHARES)
        central = {
            s: fees.central_path(places, "local_half", {"handbook_fee_cut_share": s})["added_by_size"]
            for s in SHARES
        }
        _, horizon, _ = fees.baseline_model.window(a.origin)
        by = fees._by_size(places, horizon)
        rec = {
            "places": len(places),
            "coded_places": int((places["fee_source"] == "local").sum()),
            "baseline": {c: round(float(v.sum())) for c, v in by.items()},
            "draws": {},
            "central": {},
        }
        for c in SIZES:
            g = grid[grid["size"] == c]
            rec["draws"][c] = [
                np.round(g.loc[g["share"] == s, "units_added"].to_numpy(), 1).tolist() for s in SHARES
            ]
            rec["central"][c] = [round(float(central[s][c].sum()), 1) for s in SHARES]
        out["states"][state] = rec
        half = SHARES.index(0.5)
        tot = sum(np.array(rec["draws"][c][half]) for c in SIZES)
        print(
            f"{state}: {len(places)} places, {time.time() - t0:.0f}s; at a cut of half: central "
            f"{sum(rec['central'][c][half] for c in SIZES):,.0f}, P10/P50/P90 "
            + " / ".join(f"{np.percentile(tot, q):,.0f}" for q in (10, 50, 90))
        )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {a.out} ({a.out.stat().st_size / 1e6:.1f} MB)")
    if a.page:
        write_page(a.page, a.out.read_text())


def write_page(page: Path, grid: str) -> None:
    """Replace the page's GRID block (between the GRID markers) with the grid's JSON."""
    text = page.read_text()
    start = text.index('<script id="grid" type="application/json">')
    end = text.index("</script>", start)
    head = '<script id="grid" type="application/json">'
    page.write_text(text[:start] + head + grid.replace("</", "<\\/") + text[end:])
    print(f"wrote the grid into {page}")


if __name__ == "__main__":
    main()
