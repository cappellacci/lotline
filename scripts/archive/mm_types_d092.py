#!/usr/bin/env python3
"""Missing middle: place types, φ by type (D-092 deviation 2026-11-15 (c)).

    uv run python scripts/archive/mm_types_d092.py --out /tmp/x --dry                     # inputs count only
    uv run python scripts/archive/mm_types_d092.py --out reports/mm-d092/run12-types  # Ben's go-ahead

Types every place each part of the deviation uses, by D-088's rule (`lotline.model.place_types`):
- the fit places (M's 93), the scored test places, test C's places;
- the uncoded places φ is learned from (`mm_kappa_d092.kept_ids`).
Then applies the minimum size rule to the fit places (for a type term on the reform rate) and to the uncoded
places (for φ by type). The dry run reads housing units (ACS through `holdout.apply_acs`), OMB areas and
eligible lots; no permit count is read or printed.

The run compares, on the uncoded places, one φ (Y1) with one φ per type (YT): each fitted on the 2016 origin
and scored, held out, on the 2021 origin (run 8's split, construction C0). YT is adopted only if it beats Y1
by more than 2 paired SE. Then φ per type is re-estimated on both origins (as run 9) and written to
`phi_by_type.json` for `calibrate_mm_d092.py --phi-by-type`. Reported, never selected: each type's 2021
P10-P90 coverage under both candidates, and φ by state and type. Offline: cached tables only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from lotline.io import DataStore
from lotline.model import calibrate_mm as cal
from lotline.model import estimate_mm as mm
from lotline.model import place_types as pt
from lotline.model import rule_tags


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


d092 = _load("d092", "calibrate_mm_d092.py")
K = _load("mm_kappa", "mm_kappa_d092.py")
CH = _load("mm_choice", "mm_baseline_choice_d092.py")
TRAIN, SCORE, SE_MARGIN = 2016, 2021, 2.0


def roles(panel: pd.DataFrame, store: DataStore) -> dict[str, list[str]]:
    """geoids by role, built as `calibrate_mm_d092.main` and `mm_tests_d092` build them."""
    p = d092.params()
    rules = d092.rule_rows(store, d092.STATES)
    classes = d092.bps_classes(store, set(panel["place"]))
    all_events, _ = d092.events_d092(panel, rules)
    usable = {g: e for g, e in all_events.items() if e.classes}
    fit_events = {g: e for g, e in usable.items() if g not in d092.TESTS and g not in d092.EXCLUDE}
    test_events = {g: e for g, e in usable.items() if g in d092.TESTS}
    m_fit, _ = d092.build_m(panel, classes, fit_events, p, p["s_dose"])
    m_test, _ = d092.build_m(panel, classes, test_events, p, p["s_dose"])
    none_ids = set().union(*(rule_tags.none_places(r["raw"]) for r in rules.values()))
    oh = store.read("OH", "bps_place_year")
    franklin = set(oh.loc[oh["county_geoid"].astype(str) == K.FRANKLIN, "geoid"].dropna().astype(str))
    panel_ids = set(panel["place"])
    test_c = sorted(((none_ids | franklin) & panel_ids) - set(d092.TESTS) - set(d092.HOLDOUTS))
    unused, _ = K.kept_ids(panel, store)
    return {
        "fit": [q.geoid for q in m_fit],
        "test": [q.geoid for q in m_test],
        "test_c": test_c,
        "unused (phi)": unused,
    }


def phi_by_type(train, test, type_of: dict[str, str]) -> dict:
    """Y1 against YT on the uncoded places: φ fitted on `train`, per-place held-out scores on `test`."""
    f1 = cal.fit_noise(train, "year")
    s1 = cal.baseline_scores(test, "year", f1.kappa)
    fits = {
        t: cal.fit_noise([q for q in train if type_of[q.geoid] == t], "year")
        for t in sorted(set(type_of.values()))
    }
    sT = np.array([cal.baseline_scores([q], "year", fits[type_of[q.geoid]].kappa)[0] for q in test])
    d = sT - s1
    se = float(d.std(ddof=1) * np.sqrt(len(d)))
    cov = {}
    for t in fits:
        sub = [q for q in test if type_of[q.geoid] == t]
        cov[t] = {"places": len(sub), "Y1": CH.coverage(sub, "year", f1.kappa)[0],
                  "YT": CH.coverage(sub, "year", fits[t].kappa)[0]}  # fmt: skip
    n = sum(c["places"] for c in cov.values())
    cov["all"] = {k: sum(c[k] * c["places"] for c in cov.values()) / n for k in ("Y1", "YT")} | {"places": n}
    return {"Y1_phi": f1.kappa, "YT_phi_train": {t: f.kappa for t, f in fits.items()},
            "heldout_Y1": float(s1.sum()), "heldout_YT": float(sT.sum()), "delta": float(d.sum()),
            "paired_se": se, "adopt_YT": bool(d.sum() > SE_MARGIN * se), "coverage_2021": cov}  # fmt: skip


def main(out: Path, dry: bool) -> None:
    store = DataStore()
    panel = mm.build_panel(store, states=d092.STATES).data
    # D-100: St. Paul is released (D-098); D-092's runs still keep every listed place out
    panel = panel[~panel["place"].isin(d092.HOLDOUTS)]
    types = pt.type_table(store, d092.STATES).set_index("geoid")
    state_of = panel.groupby("place")["state"].first().to_dict()
    rs = roles(panel, store)
    rows = []
    for role, ids in rs.items():
        for g in ids:
            t = types.loc[g] if g in types.index else None
            rows.append({"role": role, "geoid": g, "state": state_of.get(g),
                         "name": None if t is None else t["name"],
                         "type_raw": "untyped" if t is None else t["type_raw"],
                         "units": None if t is None else t["units"],
                         "units_source": "missing" if t is None else t["units_source"],
                         "cbsa_code": None if t is None else t["cbsa_code"]})  # fmt: skip
    df = pd.DataFrame(rows)
    fit = df[df["role"] == "fit"].rename(columns={"type_raw": "type"})
    mapping, notes = pt.merge_small(fit[["state", "type"]])
    df["type"] = df["type_raw"].map(mapping).fillna(df["type_raw"])
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        for role in rs:
            sub = df[df["role"] == role]
            print(f"\n== {role}: {len(sub)} places, raw type by state")
            print(sub.groupby(["state", "type_raw"]).size().unstack(fill_value=0).to_string())
        print("\nminimum size rule on the fit places:", mapping, notes or "no merge")
        print("units source (all roles):", df["units_source"].value_counts().to_dict())
        print("\nfit places' core cities:")
        print(df[(df["role"] == "fit") & (df["type_raw"] == "core")][["state", "name", "units"]].to_string())
    un = df[df["role"] == "unused (phi)"].rename(columns={"type": "fit_type", "type_raw": "type"})
    un_map, un_notes = pt.merge_small(un[["state", "type"]])
    print("minimum size rule on the uncoded places:", un_map, un_notes or "no merge")
    if dry:
        return

    # ================= Not run without Ben's go-ahead (D-092 §9) =================
    p = d092.params()
    type_of = {g: un_map[t] for g, t in zip(un["geoid"], un["type"], strict=True)}
    by_o = {o: K.pseudo_places(panel, list(type_of), o, p) for o in (TRAIN, SCORE)}
    res = phi_by_type(by_o[TRAIN], by_o[SCORE], type_of)
    every = by_o[TRAIN] + by_o[SCORE]
    final = {
        t: cal.fit_noise([q for q in every if type_of[q.geoid] == t], "year") for t in set(type_of.values())
    }
    res["phi_both_origins"] = {t: {"phi": f.kappa, "low": f.low, "high": f.high, "n": f.n_places}
                               for t, f in final.items()}  # fmt: skip
    res["phi_both_origins_one"] = cal.fit_noise(every, "year").kappa
    res["by_state_type"] = {
        f"{st}-{t}": cal.fit_noise(sub, "year").kappa
        for st in K.STATES for t in set(type_of.values())
        if (sub := [q for q in every if type_of[q.geoid] == t and state_of[q.geoid] == st])
    }  # fmt: skip
    print(json.dumps(res, indent=1, default=float))
    out.mkdir(parents=True, exist_ok=True)
    phis = {t: res["phi_both_origins"][un_map[t]]["phi"] for t in pt.TYPES}  # merged types share φ
    (out / "phi_by_type.json").write_text(
        json.dumps({"phi_by_type": phis, "adopted": res["adopt_YT"]}, indent=2, default=float)
    )
    (out / "summary.json").write_text(json.dumps(res | {"uncoded_mapping": un_map}, indent=2, default=float))
    df.to_csv(out / "place_types.csv", index=False)
    summary = {"mapping": mapping, "notes": notes, "uncoded_mapping": un_map, "uncoded_notes": un_notes,
               "counts": {r: df[df["role"] == r].groupby("type").size().to_dict() for r in rs},
               "units_sources": df["units_source"].value_counts().to_dict()}  # fmt: skip
    (out / "types_summary.json").write_text(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dry", action="store_true", help="print the inputs count only; write nothing")
    a = ap.parse_args()
    main(a.out, a.dry)
