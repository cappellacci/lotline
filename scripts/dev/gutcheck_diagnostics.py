#!/usr/bin/env python3
"""Gut-check diagnostics for a state's ADU forecast (WS-NC-GUTCHECK tasks 1-3; not part of the app).

    uv run python scripts/dev/gutcheck_diagnostics.py NC [--draws 1000] [--out reports/diagnostics/nc]

Writes, under --out (CSV and PNG are gitignored; the README is written by hand from them):

- `adu_two_worlds.csv`: statewide gross ADU permits per window year and over five years, P10/P50/P90, under
  current rules (the no-reform world), under the Handbook rule (with reform) and added (the difference). The
  same three on the places whose local permits flag ADUs, next to their observed counts.
- `adu_funnel.csv`: each funnel stage with P10/P50/P90 over the draws: eligible parcels -> newly legal
  (eligible x (1 - c)) -> newly legal that pencil out -> ADU permits added -> completed -> new homes
  (net-new share, formalization) -> net new statewide (displacement). Each stage is a percentile of the
  draws' own values, so stages do not multiply exactly at P10/P90.
- `baseline_total.csv`: the all-units no-reform baseline per year (`results.baseline_table`) next to observed
  BPS units 2019-2025 on the same basis.
- `adu_history.png`, `baseline_history.png`: observed vs forecast.

Reads only the holdout-filtered store. Places with a holdout (config/states/<st>.yaml) are left out of the
observed-vs-forecast comparison on both sides, because their outcome years are missing from the store.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from lotline.build import eligible, panels  # noqa: E402
from lotline.config import load_params, load_state  # noqa: E402
from lotline.io import DataStore  # noqa: E402
from lotline.model import aggregate, baseline, results  # noqa: E402
from lotline.model.scenarios import adu  # noqa: E402

OBS_FIRST, OBS_LAST = 2019, 2025


def pct(a) -> dict[str, float]:
    p10, p50, p90 = np.percentile(np.asarray(a, dtype=float), [10, 50, 90])
    return {"p10": p10, "p50": p50, "p90": p90, "mean": float(np.mean(a))}


def holdout_geoids(state: str) -> set[str]:
    out = set()
    for h in load_state(state).holdouts:
        out.add(h.geoid)
        out |= set(getattr(h, "reporting_geoids", None) or [])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("state")
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--origin", type=int, default=2025)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    st = a.state.upper()
    out = a.out or Path("reports/diagnostics") / st.lower()
    out.mkdir(parents=True, exist_ok=True)
    store = DataStore()

    places = adu.places_from_store(st, store, a.origin)
    places = places[places["rent"].notna() & places["home_value"].notna()].reset_index(drop=True)
    places["state"] = st
    tier3 = bool(results.proxy.proxy_states(places))
    _, _, rd = adu.run(places, a.origin, draws=a.draws, eligible_proxy=tier3, return_draws=True)
    _, horizon, first = baseline.window(a.origin)
    years = [first + k for k in range(horizon)]
    cur, added = np.asarray(rd["current"]), np.asarray(rd["added"])  # draws x places x years
    hb = cur + added

    # ---- two worlds, statewide and on the places that report ADUs ----
    held = holdout_geoids(st)
    counts = adu.observed_adu_counts(store.read(st, "permits"), OBS_FIRST, OBS_LAST)
    counts = counts[~counts["geoid"].isin(held)]
    obs_geoids = set(counts["geoid"])
    on_obs = places["geoid"].isin(obs_geoids).to_numpy()
    rows = []
    for scope, mask in (("statewide", np.ones(len(places), bool)), ("reporting_places", on_obs)):
        for world, arr in (("current_rules", cur), ("with_reform", hb), ("added", added)):
            s = arr[:, mask, :].sum(axis=1)  # draws x years
            rows.append(
                {"scope": scope, "world": world, "period": f"{years[0]}-{years[-1]}", **pct(s.sum(1))}
            )
            for k, y in enumerate(years):
                rows.append({"scope": scope, "world": world, "period": str(y), **pct(s[:, k])})
    two = pd.DataFrame(rows)
    two.to_csv(out / "adu_two_worlds.csv", index=False)
    obs_by_year = (
        counts.groupby("year")["adu_permits"].sum().reindex(range(OBS_FIRST, OBS_LAST + 1), fill_value=0)
    )
    obs_by_year.rename("observed_adu_permits").to_csv(out / "adu_observed.csv")

    # ---- funnel ----
    sets = rd["params"]
    e = np.asarray(rd["eligible"], dtype=float)
    c = np.asarray(rd["rule_share"], dtype=float)
    newly = e * (1 - c)
    pencil = np.asarray(rd["pencil"], dtype=float)
    agg = load_params("aggregate")
    rng = np.random.default_rng(int(agg["results_seed"].value))
    completion = results.triangular("completion_factor_single_family", len(sets), rng)
    net_new = np.array([p["adu_net_new_share"] * (1 - p["adu_formalization_share"]) for p in sets])
    displacement = results.triangular("displacement_share", len(sets), rng)
    permits_added = added.sum(axis=(1, 2))
    stages = [
        ("eligible parcels", "parcels", e.sum(1)),
        ("newly legal: eligible x (1 - c)", "parcels", newly.sum(1)),
        ("newly legal that pencil out", "parcels", (newly * pencil).sum(1)),
        ("ADU permits added, 5 years", "permits", permits_added),
        ("completed", "homes", permits_added * completion),
        ("new homes (net-new share x (1 - formalization))", "homes", permits_added * completion * net_new),
        (
            "net new statewide (x (1 - displacement))",
            "homes",
            permits_added * completion * net_new * (1 - displacement),
        ),
        ("no-reform ADU permits, 5 years (current rules)", "permits", cur.sum(axis=(1, 2))),
        ("with-reform ADU permits, 5 years", "permits", hb.sum(axis=(1, 2))),
    ]
    funnel = pd.DataFrame([{"stage": s, "unit": u, **pct(x)} for s, u, x in stages])
    funnel["share_of_parcels_newly_legal"] = (newly.sum(1) / e.sum(1)).mean()
    funnel.to_csv(out / "adu_funnel.csv", index=False)
    rate_hb = np.median(permits_added / np.maximum((newly * pencil).sum(1), 1))
    print(f"median 5-year uptake among newly legal parcels that pencil out: {rate_hb:.4%}")
    # the bundle's own arithmetic, as a check that this funnel matches it
    d = results.adu_draws(places, rd, np.random.default_rng(int(agg["results_seed"].value)))
    print(
        "bundle homes_net_statewide:",
        {k: round(v) for k, v in pct(aggregate.homes_from_draws(d)["homes_net_statewide"]).items()},
    )

    # ---- all-units baseline vs history ----
    panel = panels.load(st, store, theme="adu", rule_version=eligible.RULE_VERSION)
    base = results.baseline_table(panel, st, a.origin)
    reported = bool(load_params("baseline")["use_reported_only"].value)
    cols = [baseline.outcome_column(s, reported) for s in baseline.SIZE_CLASSES]
    obs_units = panel[panel["year"].between(OBS_FIRST, OBS_LAST)].groupby("year")[cols].sum().sum(axis=1)
    base_all = base[(base["size_class"] == "all") & ~base["period"].str.contains("-")]
    pd.concat(
        [base_all.assign(kind="forecast"), obs_units.rename("p50").reset_index().assign(kind="observed")]
    ).to_csv(out / "baseline_total.csv", index=False)

    # ---- plots ----
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(
        obs_by_year.index, obs_by_year.values, color="#888", label="observed ADU permits (reporting places)"
    )
    for world, colr in (("current_rules", "#3b6ea5"), ("with_reform", "#c4572e")):
        g = two[
            (two["scope"] == "reporting_places") & (two["world"] == world) & ~two["period"].str.contains("-")
        ]
        x = g["period"].astype(int)
        ax.plot(x, g["p50"], color=colr, marker="o", label=f"{world.replace('_', ' ')} (median)")
        ax.fill_between(x, g["p10"], g["p90"], color=colr, alpha=0.15)
    ax.set_title(f"{st}: ADU permits per year, places whose permits flag ADUs (holdouts left out)")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "adu_history.png", dpi=150)

    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(obs_units.index, obs_units.values, color="#888", label="observed units (BPS)")
    x = base_all["period"].astype(int)
    ax.plot(x, base_all["p50"], color="#3b6ea5", marker="o", label="no-reform baseline (median)")
    ax.fill_between(x, base_all["p10"], base_all["p90"], color="#3b6ea5", alpha=0.15, label="P10-P90")
    ax.set_title(f"{st}: all housing units permitted per year")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(out / "baseline_history.png", dpi=150)

    pd.set_option("display.width", 200)
    print(two[two["period"].str.contains("-")].round(1).to_string(index=False))
    print(
        two[(two["scope"] == "reporting_places") & ~two["period"].str.contains("-")]
        .round(1)
        .to_string(index=False)
    )
    print("observed ADU permits, reporting places:", obs_by_year.to_dict(), "places:", len(obs_geoids))
    print(funnel.round(4).to_string(index=False))
    print(base_all[["period", "p10", "p50", "p90"]].round(0).to_string(index=False))
    print("observed units:", obs_units.round(0).to_dict())


if __name__ == "__main__":
    main()
