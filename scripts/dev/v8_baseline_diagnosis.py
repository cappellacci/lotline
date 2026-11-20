"""V8 diagnosis (D-106): why Wisconsin's frozen baseline starts below its 2019 permits.

    uv run python scripts/dev/v8_baseline_diagnosis.py     # prints the step-by-step totals

Reads only the blind processed tables (no outcome after 2019 is needed), offline. For each BPS size class it
follows the baseline's steps (`model.baseline`) for the places it forecasts at origin 2019 and prints the
statewide yearly total after each step:
  2019 observed -> 2015-2019 average -> own recent rate at 2019 lots (step 1) -> after Fay-Herriot shrinkage
  (step 2) -> cycle start (D-029) -> simulated mean for 2021.
It then prints the same shrinkage step for the other states, and Wisconsin's places that lose most to it.
"""

from __future__ import annotations

from lotline.build import eligible, panels
from lotline.config import load_params
from lotline.io import DataStore
from lotline.io.offline import offline_build
from lotline.model import baseline as bl

ORIGIN = 2019
STATES = ("WI", "MN", "NC", "OH", "OR", "TX")


def panel_for(store: DataStore, state: str):
    with offline_build(store):
        panel = panels.load(state, store, theme="adu", rule_version=eligible.RULE_VERSION)
    return panel[panel["state"] == state]


def levels(panel, col: str, p):
    return bl.level_estimates(
        panel[panel["year"] <= ORIGIN],
        col,
        ORIGIN,
        level_years=int(p["level_years"].value),
        min_group_places=int(p["min_group_places"].value),
        use_direct_variance=bool(p["use_direct_variance"].value),
        detrend=bool(p["detrend_dispersion"].value),
    )


def steps(store: DataStore) -> None:
    p = load_params("baseline")
    panel = panel_for(store, "WI")
    names = store.read("WI", "jurisdictions").set_index("geoid")["name"]
    print("size | 2019 obs | 2015-19 avg | own rate | shrunk | cycle start | 2021 mean")
    for size in bl.SIZE_CLASSES:
        col = bl.outcome_column(size, True)
        lv = levels(panel, col, p)
        by = panel[panel["geoid"].isin(set(lv["geoid"]))].groupby("year")[col].sum()
        tab, _ = bl.forecast_draws(panel, col, ORIGIN, params=p)
        own = (lv["direct"] * lv["parcels_origin"] / 1000).sum()
        shrunk = (lv["level"] * lv["parcels_origin"] / 1000).sum()
        print(
            f"{size} | {by[ORIGIN]:,.0f} | {by.loc[ORIGIN - 4 : ORIGIN].mean():,.0f} | {own:,.0f} | "
            f"{shrunk:,.0f} | x{tab['momentum'].iloc[0]:.3f} | {tab[tab['year'] == 2021]['mean'].sum():,.0f}"
        )
        if size == "5p":
            loss = (lv["direct"] - lv["level"]) * lv["parcels_origin"] / 1000
            lv = lv.assign(loss=loss).sort_values("loss", ascending=False)
            for _, r in lv.head(6).iterrows():
                own_r, sh_r = (r[c] * r["parcels_origin"] / 1000 for c in ("direct", "level"))
                name = names.get(r["geoid"], r["geoid"])
                print(f"    5+ {name}: own {own_r:,.0f}/yr -> shrunk {sh_r:,.0f} (B {r['b']:.2f})")
            up, down = loss[loss < 0], loss[loss > 0]
            print(f"    pulled down: {len(down)} places, {down.sum():,.0f}/yr;", end=" ")
            print(f"up: {len(up)}, {-up.sum():,.0f}/yr")
    print("\nshrinkage step, total after / before, by state and size class (origin 2019)")
    for st in STATES:
        panel = panel_for(store, st)
        out = []
        for size in bl.SIZE_CLASSES:
            lv = levels(panel, bl.outcome_column(size, True), p)
            own = (lv["direct"] * lv["parcels_origin"]).sum()
            out.append(f"{size} {(lv['level'] * lv['parcels_origin']).sum() / own - 1:+.0%}")
        print(st, " | ".join(out))


if __name__ == "__main__":
    steps(DataStore())
