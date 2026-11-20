"""Score V8, the Wisconsin unseen-state test, against the Census permits (analysis plan D-104, D-105).

    uv run python scripts/dev/v8_score.py      # writes reports/wi/V8-score.json and reports/wi/V8-score.md

1. Rebuilds the frozen baseline from the blind tables (offline, same code path, seed and draws as
   `v8_freeze.py`) and stops unless it equals `prediction.baseline` in results/frozen/V8-WI-TRANSFER.json,
   so the draws used for ranks are the frozen ones. The P10/P50/P90 scored are read from the frozen file.
2. Unblinds Wisconsin's Census place permits **in memory** (`bps.load(..., unblind=("V8-WI-TRANSFER",))`;
   `check_unblind` requires the freeze on main). The processed tables on disk stay blind.
3. Scores what D-104 pre-registered, with no parameter or model change:
   - statewide reported units 2021-2025, all sizes (the pass rule) and each size class, inside P10-P90;
   - observed / P50, and the observed value's rank in the frozen draws (share of draws at or below it);
   - each year against its yearly band;
   - the overlap: the share of places (and of eligible lots) outside the calibration range.
   "Statewide" is every Wisconsin place in the permit survey. The baseline forecasts 1,131 of them (98% of
   2019 homes), so the same-places sum is reported too, as a like-for-like check.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from lotline.adapters.national import bps
from lotline.build import eligible, panels
from lotline.io import DataStore
from lotline.io.offline import offline_build
from lotline.model import baseline, results
from lotline.model import eligible_proxy as proxy
from lotline.model.scenarios import adu
from lotline.validation import holdout

TEST_ID = "V8-WI-TRANSFER"
STATE = "WI"
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "reports" / "wi"
SIZES = ("all", "1", "2", "3_4", "5p", "2_4")


def verdict(ob: float, p10: float, p50: float, p90: float) -> str:
    """D-040's reading (as V9): useful = inside P10-P90 with P50 within x2; inside only; missed. "over" means
    the model predicted more than was built."""
    if p10 <= ob <= p90:
        return "useful" if p50 > 0 and 0.5 <= ob / p50 <= 2 else "inside only"
    return "missed (over)" if ob < p10 else "missed (under)"


def observed_by_class(df: pd.DataFrame, years: list[int], places: set[str] | None = None) -> dict:
    """{size: {period: reported units}} over `years`, every place or only `places`."""
    d = df[df["year"].isin(years) & df["geoid"].astype("string").str.startswith(holdout_geoid())]
    if places is not None:
        d = d[d["geoid"].isin(places)]
    col = {s: baseline.outcome_column(s, True) for s in baseline.SIZE_CLASSES}
    per_year = {s: d.groupby("year")[c].sum().reindex(years, fill_value=0) for s, c in col.items()}
    per_year["all"] = sum(per_year[s] for s in baseline.SIZE_CLASSES)
    per_year["2_4"] = per_year["2"] + per_year["3_4"]
    out = {}
    for s, y in per_year.items():
        out[s] = {f"{years[0]}-{years[-1]}": float(y.sum())} | {str(k): float(v) for k, v in y.items()}
    return out


def holdout_geoid() -> str:
    (h,) = [h for h in holdout.holdouts_for(STATE) if h.test_id == TEST_ID]
    return h.geoid


def rebuild(store: DataStore, frozen: dict):
    """The frozen baseline's draws and modelled places, and the overlap, from the blind tables."""
    origin = frozen["origin"]
    with offline_build(store):
        panel = panels.load(STATE, store, theme="adu", rule_version=eligible.RULE_VERSION)
        class_draws = results.baseline_class_draws(panel, STATE, origin)
        base = results.baseline_table(panel, STATE, origin, class_draws=class_draws)
        places = adu.places_from_store(STATE, store, origin)
        places = places[places["rent"].notna() & places["home_value"].notna()].reset_index(drop=True)
        places["state"] = STATE
        _, per_place, _ = adu.run(
            places,
            origin,
            draws=frozen["draws"],
            eligible_proxy=bool(proxy.proxy_states(places)),
            return_draws=True,
        )
    if json.loads(base.to_json(orient="records")) != frozen["prediction"]["baseline"]:
        raise SystemExit("rebuilt baseline differs from the frozen file; score from the freeze commit")
    flag, median = results.overlap_flag(places["eligible_parcels"], per_place["calibration_distance"])
    meta = frozen["prediction"]["meta"]
    if flag != meta["overlap_flag"] or f"{median:.2f}" not in meta["overlap_note"]:
        raise SystemExit("rebuilt overlap differs from the frozen meta")
    outside = per_place["calibration_distance"].to_numpy() > 0
    e = places["eligible_parcels"].to_numpy(float)
    overlap = {
        "flag": flag,
        "median_calibration_distance": round(float(median), 4),
        "places": int(len(places)),
        "places_outside_range": int(outside.sum()),
        "share_places_outside_range": round(float(outside.mean()), 4),
        "share_eligible_lots_outside_range": round(float(e[outside].sum() / e.sum()), 4),
        "flagged_in_bundle": "every place: overlap_flag and calibration_distance are computed for all",
    }
    by_class, modelled = class_draws
    by_class = {**by_class, "2_4": by_class["2"] + by_class["3_4"]}
    return by_class, modelled, overlap


def score(frozen: dict, by_class: dict, obs: dict, obs_same: dict) -> list[dict]:
    years = frozen["years"]
    bands = {(r["size_class"], r["period"]): r for r in frozen["prediction"]["baseline"]}
    rows = []
    for s in SIZES:
        a = by_class[s]  # (years, draws)
        periods = [(f"{years[0]}-{years[-1]}", a.sum(axis=0))] + [(str(y), a[k]) for k, y in enumerate(years)]
        for period, draws in periods:
            b = bands[(s, period)]
            ob = obs[s][period]
            rows.append(
                {
                    "size_class": s,
                    "period": period,
                    "observed": ob,
                    "observed_same_places": obs_same[s][period],
                    "p10": b["p10"],
                    "p50": b["p50"],
                    "p90": b["p90"],
                    "inside_p10_p90": bool(b["p10"] <= ob <= b["p90"]),
                    "inside_same_places": bool(b["p10"] <= obs_same[s][period] <= b["p90"]),
                    "ratio_obs_p50": round(ob / b["p50"], 4) if b["p50"] > 0 else None,
                    "rank_in_draws": round(float((draws <= ob).mean()), 4),
                    "verdict": verdict(ob, b["p10"], b["p50"], b["p90"]),
                }
            )
    return rows


def markdown(doc: dict) -> str:
    lines = [
        "# V8 Wisconsin: frozen prediction vs Census permits (D-104, D-105)",
        "",
        f"Frozen at commit `{doc['frozen_commit'][:10]}`; unblinded in memory on {doc['scored_on']} at Ben's "
        "request. Reported units, every Wisconsin place in the permit survey. "
        "Rank = share of the 1,000 frozen draws at or below the observed value.",
        "",
        f"**Pass rule (statewide 2021-2025, all sizes): {doc['pass_rule_result']}.**",
        "",
        "| Size | Period | Observed | P10 | P50 | P90 | Obs / P50 | Rank | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in doc["rows"]:
        lines.append(
            f"| {r['size_class']} | {r['period']} | {r['observed']:,.0f} | {r['p10']:,.0f} | {r['p50']:,.0f} "
            f"| {r['p90']:,.0f} | {r['ratio_obs_p50']} | {r['rank_in_draws']:.2f} | {r['verdict']} |"
        )
    o = doc["overlap"]
    lines += [
        "",
        f"Overlap: {o['flag']} (median calibration distance {o['median_calibration_distance']}); "
        f"{o['places_outside_range']} of {o['places']} places ({o['share_places_outside_range']:.0%}) and "
        f"{o['share_eligible_lots_outside_range']:.0%} of eligible lots sit outside the calibration range.",
        "",
        "Same-places check (the 1,131 places the baseline forecasts): see `observed_same_places` in "
        "`V8-score.json`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    frozen = json.loads(holdout.frozen_path(TEST_ID).read_text())
    store = DataStore()
    by_class, modelled, overlap = rebuild(store, frozen)
    with offline_build(store):
        seen = bps.load(STATE, store, unblind=(TEST_ID,))  # in memory only; nothing is written
    obs = observed_by_class(seen, frozen["years"])
    obs_same = observed_by_class(seen, frozen["years"], set(modelled))
    rows = score(frozen, by_class, obs, obs_same)
    head = next(r for r in rows if r["size_class"] == "all" and "-" in r["period"])
    doc = {
        "test_id": TEST_ID,
        "method": "D-104 reading rules, scored by scripts/dev/v8_score.py (D-105)",
        "frozen_commit": frozen["commit"],
        "scored_on": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"),
        "basis": "Census BPS reported units, every Wisconsin place (bps_place_year, unblinded in memory)",
        "pass_rule": frozen["pass_rule"],
        "pass_rule_result": "pass" if head["inside_p10_p90"] else "fail",
        "coverage_share": frozen["prediction"]["baseline"][0]["coverage_share"],
        "places_forecast": len(modelled),
        "overlap": overlap,
        "rows": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "V8-score.json").write_text(json.dumps(doc, indent=1) + "\n")
    (OUT / "V8-score.md").write_text(markdown(doc))
    print(markdown(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
