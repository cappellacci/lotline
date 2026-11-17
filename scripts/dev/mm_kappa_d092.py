#!/usr/bin/env python3
"""Missing middle: estimate κ, the variance of the place-level rate multiplier w (D-092 deviation 2026-11-15).

    uv run python scripts/dev/mm_kappa_d092.py --out /tmp/x --dry          # structure only: places per origin
    uv run python scripts/dev/mm_kappa_d092.py --out reports/mm-d092/run7-kappa   # ONLY with Ben's go-ahead

κ is learned from places that neither the fit nor any §7 test uses, before any refit:
- "uncoded" places in MN, NC, OH and TX (Oregon left out: HB 2001 reaches most places; D-037);
- minus every place with a D-092 event, the fit set, the scored test places, test C's places (coded "none" and
  Franklin County), the always-allowed level set, Lubbock and Richfield, and the holdouts (St. Paul, Ramsey
  County, Charlotte, Mecklenburg; asserted absent from the panel).
Each kept place gets test C's baseline construction (own growth, 3 pre-years, zero floor) at two origins, 2016
(scored 2016-2020) and 2021 (scored 2021-2025), with no reform term; `calibrate_mm.fit_kappa` then maximizes
Σ log ∫ Π_t Poisson(y_t; w B_t) dGamma(w; mean 1, variance κ), one w per (place, origin).

Reported, never selected: κ on the 2021 origin only, and κ per state. Offline: cached tables only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path

import pandas as pd

from lotline.io import DataStore
from lotline.model import calibrate_mm as cal
from lotline.model import estimate_mm as mm
from lotline.model import rule_tags

_spec = importlib.util.spec_from_file_location("d092", Path(__file__).with_name("calibrate_mm_d092.py"))
d092 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d092)

STATES = ("MN", "NC", "OH", "TX")
ORIGINS = (2016, 2021)
HORIZON = 5
FRANKLIN = "39049"  # test C's Franklin County places (as mm_tests_d092.py)


def kept_ids(panel: pd.DataFrame, store: DataStore) -> tuple[list[str], dict]:
    """The uncoded places κ is learned from, and what was removed (counts by reason)."""
    rules = d092.rule_rows(store, d092.STATES)
    all_events, _ = d092.events_d092(panel, rules)
    none_ids = set().union(*(rule_tags.none_places(r["raw"]) for r in rules.values()))
    always = set().union(*(rule_tags.always_allowed_places(r["raw"]) for r in rules.values()))
    oh_bps = store.read("OH", "bps_place_year")
    franklin = set(oh_bps.loc[oh_bps["county_geoid"].astype(str) == FRANKLIN, "geoid"].dropna().astype(str))
    max_dose = panel.groupby("place")["dose"].max().fillna(0.0)
    status = panel.groupby("place")["status"].first()
    state = panel.groupby("place")["state"].first()
    pool = sorted(g for g in status.index if status[g] == "uncoded" and state[g] in STATES)
    drop = {
        "event": set(all_events),
        "dose": {g for g in pool if max_dose.get(g, 0.0) > 0},
        "tests": set(d092.TESTS),
        "test_c": none_ids | franklin,
        "level_set": always,
        "excluded": set(d092.EXCLUDE),
        "holdouts": set(d092.HOLDOUTS),
    }
    removed = {k: len(set(pool) & v) for k, v in drop.items()}
    keep = [g for g in pool if not any(g in v for v in drop.values())]
    return keep, removed


def pseudo_places(panel: pd.DataFrame, ids: list[str], origin: int, p: dict) -> list[cal.Place]:
    """Test C's no-reform baseline at `origin`, scored over origin … origin + 4."""
    sub = panel[panel["place"].isin(ids)].copy()
    sub["T"], sub["dose"] = float(origin), 0.0
    sub["eligible"] = sub["eligible"].where(sub["eligible"] > 0, 1.0)
    out = cal.place_inputs(sub, ids, p["margin"], p["sigma"], growth="own", zero_floor=True)
    return [q for q in (q.upto(origin + HORIZON - 1) for q in out) if len(q.years)]


def row(f: cal.KappaFit) -> dict:
    return {"kappa": f.kappa, "low": f.low, "high": f.high, "loglik": f.loglik,
            "loglik_poisson": f.loglik_poisson, "places": f.n_places, "place_years": f.n_years}  # fmt: skip


def main(out: Path, dry: bool, form: str = "w") -> None:
    t0 = time.time()
    p = d092.params()
    store = DataStore()
    panel = mm.build_panel(store, states=d092.STATES).data
    leaked = sorted(set(panel["place"]) & set(d092.HOLDOUTS))
    assert not leaked, f"holdout places in the panel: {leaked}"
    keep, removed = kept_ids(panel, store)
    state = panel.groupby("place")["state"].first().to_dict()
    print(f"uncoded places kept: {len(keep)}; removed by reason (overlapping): {removed}", flush=True)
    by_origin = {o: pseudo_places(panel, keep, o, p) for o in ORIGINS}
    for o, ps in by_origin.items():
        per = pd.Series([state[q.geoid] for q in ps]).value_counts().to_dict()
        print(f"origin {o}: {len(ps)} places {per}", flush=True)
    if dry:
        return

    # ================= Not run without Ben's go-ahead (D-092 §9) =================
    every = [q for ps in by_origin.values() for q in ps]
    main_fit = cal.fit_noise(every, form)
    res = {"main": row(main_fit), "origin_2021_only": row(cal.fit_noise(by_origin[2021], form))}
    res["by_state"] = {s: row(cal.fit_noise([q for q in every if state[q.geoid] == s], form)) for s in STATES}
    rows = [{"geoid": q.geoid, "name": q.name, "state": state[q.geoid], "origin": q.T, "years": len(q.years),
             "observed": float(q.y.sum()), "baseline": float(q.B.sum())} for q in every]  # fmt: skip
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "places.csv", index=False)
    summary = {"form": form, "kappa" if form == "w" else "phi": res, "kept_places": len(keep),
               "removed": removed, "origins": list(ORIGINS), "horizon": HORIZON,
               "seconds": round(time.time() - t0)}  # fmt: skip
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=1, default=float))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry", action="store_true", help="structure only: places per origin, no outcome read")
    ap.add_argument("--form", choices=("w", "year"), default="w",
                    help="w: place multiplier κ (run 7); year: per-year NB φ (deviation (b))")  # fmt: skip
    a = ap.parse_args()
    main(a.out, a.dry, a.form)
