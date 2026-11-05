#!/usr/bin/env python3
"""D-045 follow-up: are the MN suburbs with no ADU permits true zeros or survey reporting gaps?

    uv run python scripts/dev/fit_audit_zeros.py --out reports/adu-fit-audit

Reads reports/adu-fit-audit/places.csv (the D-045 run) and the holdout-filtered store. Writes:
- zeros_by_detached.csv: observed and expected (D-041 full fit) by whether the rules in force that year allow
  detached ADUs (any rule allows / only rules that forbid / blank), by state and for MN by count source;
- zeros_assessor.csv: for metro parcels in counties that record unit counts, single-family parcels built
  before 2020 whose unit count goes from 1 (2021 roll) to 2 (2025 roll) with the year built unchanged, next to
  the Met Council survey's ADU permits for 2021-2024. An independent check that misses some ADUs (an assessor
  need not update the unit count for an ADU), so it can confirm a near-zero but not size a count.
No fit and no parameter changes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_adu as run  # noqa: E402

from lotline.config import load_state  # noqa: E402
from lotline.io import DataStore  # noqa: E402
from lotline.model import calibrate_adu as cal  # noqa: E402
from lotline.model import fit_audit as fa  # noqa: E402
from lotline.model.scenarios import adu  # noqa: E402

MINNEAPOLIS = "2743000"


def detached_class(live: pd.DataFrame) -> str:
    """'detached allowed' if any rule in force allows detached ADUs, 'attached only' if a rule in force
    forbids them and none allows them, else 'blank'."""
    v = live["adu_detached_allowed"].dropna().map(lambda x: x is True or str(x).lower() == "true")
    return "detached allowed" if v.any() else "attached only" if len(v) else "blank"


def by_detached(store, cs, places=None, full=None) -> pd.DataFrame:
    """Observed and expected by detached rule; `places` and `full` default to D-041's places and fit 3."""
    if places is None:
        places = run.four_state_places(store, cs, params=run.pre_d048()) + run._test_set(
            store, cs, params=run.pre_d048()
        )
    if full is None:
        full = cal.fit3([p for p in places if p.geoid not in (run.RALEIGH, run.DURHAM)])
    rows = []
    for pl in places:
        ref = adu.load_reforms(pl.state)
        ref = ref[(ref["theme"] == "adu") & (ref["status"] == "in_force")]
        mine = ref[ref["jurisdiction_geoid"].isin([pl.geoid, load_state(pl.state).fips])]
        for y, o, x in zip(pl.years, pl.y, fa.expected_by_year(pl, full), strict=True):
            mid = pd.Timestamp(f"{int(y)}-07-01")
            live = mine[
                (mine["effective_date"] <= mid) & (mine["end_date"].isna() | (mine["end_date"] > mid))
            ]
            src = "survey" if pl.state == "MN" and pl.geoid != MINNEAPOLIS else "city records"
            rows.append(dict(state=pl.state, name=pl.name, year=int(y), observed=o, expected=x,
                             detached=detached_class(live), count_source=src))  # fmt: skip
    d = pd.DataFrame(rows)
    out = []
    for keys in (["detached"], ["state", "detached"], ["state", "count_source", "detached"]):
        g = d.groupby(keys).agg(places=("name", "nunique"), observed=("observed", "sum"),
                                expected=("expected", "sum")).reset_index()  # fmt: skip
        out.append(g.assign(ratio=g["observed"] / g["expected"], by="+".join(keys)))
    return pd.concat(out, ignore_index=True)


def assessor(store, mn_places: pd.DataFrame) -> pd.DataFrame:
    cols = ["parcel_id", "vintage", "jurisdiction_geoid", "units", "year_built", "source"]
    p = store.read("MN", "parcels")[cols]
    p = p[p["source"] == "metc_parcels"]
    a, b = (p[p["vintage"] == v].drop_duplicates("parcel_id").set_index("parcel_id") for v in (2021, 2025))
    j = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
    keep = j["units_a"].notna() & j["units_b"].notna() & (j["year_built_a"] < 2020)
    keep &= j["year_built_a"] == j["year_built_b"]
    sf = j[keep & (j["units_a"] == 1)]
    gain = sf[sf["units_b"] == 2].groupby("jurisdiction_geoid_a").size().rename("units_1_to_2")
    base = sf.groupby("jurisdiction_geoid_a").size().rename("single_family_known")
    pm = store.read("MN", "permits")
    m = pm[(pm["source"] == "metc_residential_permits") & pm["issue_year"].between(2021, 2024)]
    survey = m[adu._is_adu(m)].groupby("jurisdiction_geoid").size().rename("survey_adus_2021_24")
    t = pd.concat([gain, base, survey], axis=1).fillna(0)
    t = t[t.index.isin(mn_places["geoid"]) & (t["single_family_known"] > 0)]
    t = t.rename_axis("geoid").reset_index()
    t["name"] = t["geoid"].map(mn_places.set_index("geoid")["name"])
    t["per_1000"] = 1000 * t["units_1_to_2"] / t["single_family_known"]
    return t.sort_values("single_family_known", ascending=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    store, cs = DataStore(), cal.count_settings()
    pt = pd.read_csv(a.out / "places.csv", dtype={"geoid": str})
    det = by_detached(store, cs)
    ass = assessor(store, pt[pt["state"] == "MN"])
    det.to_csv(a.out / "zeros_by_detached.csv", index=False)
    ass.to_csv(a.out / "zeros_assessor.csv", index=False)
    pd.set_option("display.width", 200)
    print(
        "Observed and expected by whether detached ADUs are allowed\n" + det.round(2).to_string(index=False)
    )
    print(
        "\nAssessor unit changes 2021 -> 2025 (counties that record units)\n"
        + ass.round(2).to_string(index=False)
    )
    print(f"\nTotal: {int(ass['units_1_to_2'].sum())} parcels 1 -> 2 units of "
          f"{int(ass['single_family_known'].sum()):,}; survey ADUs 2021-24 in the same places "
          f"{int(ass['survey_adus_2021_24'].sum())}")  # fmt: skip


if __name__ == "__main__":
    main()
