"""Inputs and runs for the D-082 missing-middle counts (`lotline.model.mm_counts`).

    uv run python scripts/dev/mm_counts_d082.py --dry                                  # structure only
    uv run python scripts/dev/mm_counts_d082.py --coverage --out reports/mm-d082/run1-coverage   # run 1

`--dry` reads each candidate permit source, parcel roll and BPS table through `mm_counts.blind` (St. Paul and
Ramsey County dropped outright, then `holdout.apply`) and prints **structure only**.

`--coverage` is D-082 §9 run 1 (approved by Ben 2026-11-12; go-ahead "Yes, start run 1"): for each candidate
permit source, the building collapse report, k_src against BPS over each place's own pre-event years, its 90%
interval, and the four strong-source tests. It writes `coverage.csv`, `coverage_by_year.csv` and
`README.md` to `--out`. Nothing is fitted and nothing is written to config. Runs 2–6 are not here: each needs
its own go-ahead.

Run-1 choices (stated in the report):
- Event years: D-082's event rule (`calibrate_mm_d082.events_d082`, the accepted rule rows). A place with no
  event is pre-event through the source's last full year.
- Window: from 2013 (D-042's first event year) or the source's first full year, whichever is later, to the
  year before the place's event. The long window (back to BPS's first year, 1992) is a sensitivity.
- Full years only: a source's first year counts if its first permit is on or before 15 January, its last if
  its last permit is on or after 15 December; never past 2025, BPS's last year.
- Places in a source with no BPS place row are left out of the area and reported.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from lotline.io import DataStore
from lotline.model import mm_counts as mc

# D-082 §2: the strong permit candidates (review §2), by state and processed file name
# (processed/<st>/permits/<name>.parquet).
PERMIT_SOURCES = {
    "MN": [("Minneapolis", "mpls_permits")],
    "NC": [("Mecklenburg", "meck_permits"), ("Raleigh", "raleigh_permits"), ("Durham", "durham_permits")],
    "OH": [("Columbus", "columbus_permits"), ("Cincinnati", "cincy_permits")],
    "TX": [("Austin", "austin_permits"), ("College Station", "cstx_permits")],
    "OR": [("Portland", "portland_permits"), ("Bend", "bend_permits"), ("Medford", "medford_permits")],
}
# D-082 §2 test B rolls (Wake 2019→2023, Franklin 2016→2025, Minneapolis 2017→2026, Met Council 2021→2025).
ROLL_SOURCES = {
    "NC": [("Wake", "wake_realestate")],
    "OH": [("Franklin", "oh_parcels")],
    "MN": [("Minneapolis", "mpls_assessor_parcels"), ("Met Council", "metc_parcels")],
}
PERMIT_COLUMNS = ("parcel_id", "units_new", "building_type_std", "is_conversion", "is_demolition", "address",
                  "issue_date", "n_buildings")  # fmt: skip
ROLL_COLUMNS = (
    "parcel_id",
    "units",
    "lot_sqft",
    "land_use_std",
    "sf_only_zoned",
    "year_built",
    "vintage_date",
)
BPS_COLUMNS = ("geoid", "year", "bldgs_2", "bldgs_3_4")


def _read(store: DataStore, state: str, table: str, source: str) -> pd.DataFrame | None:
    path = store.processed(state, table, source)
    return pd.read_parquet(path) if path.exists() else None


def _fill(s: pd.Series) -> float:
    t = s.astype("string").str.strip()
    return float((t.notna() & (t != "")).mean()) if len(s) else float("nan")


def _present(df: pd.DataFrame, cols: tuple[str, ...]) -> str:
    return " ".join(f"{c}={'y' if c in df else 'n'}" for c in cols)


def dry(store: DataStore) -> None:
    print("D-082 inputs, structure only (no counts of 2-4 unit buildings, no ratios)\n")
    print("Permit sources")
    for state, sources in PERMIT_SOURCES.items():
        for place, source in sources:
            raw = _read(store, state, "permits", source)
            if raw is None:
                print(f"  {state} {place:16} {source:22} not built")
                continue
            df = mc.blind(raw, state, date_col="issue_date", year_col="issue_year")
            years = pd.to_numeric(df["issue_year"])
            fill = _fill(df["parcel_id"]) if "parcel_id" in df else float("nan")
            print(
                f"  {state} {place:16} {source:22} rows={len(df):>8,} (blinded {len(raw) - len(df):,}) "
                f"years={int(years.min())}-{int(years.max())} parcel_fill={fill:.3f}"
            )
            print(f"      {_present(df, PERMIT_COLUMNS)}")
    print("\nParcel rolls")
    for state, sources in ROLL_SOURCES.items():
        for place, source in sources:
            raw = _read(store, state, "parcels", source)
            if raw is None:
                print(f"  {state} {place:16} {source:22} not built")
                continue
            date_col = "vintage_date" if "vintage_date" in raw else None
            df = mc.blind(raw, state, date_col=date_col, year_col="vintage", snapshot=True)
            vint = sorted(pd.to_numeric(df["vintage"]).dropna().astype(int).unique().tolist())
            print(
                f"  {state} {place:16} {source:22} rows={len(df):>9,} (blinded {len(raw) - len(df):,}) "
                f"vintages={vint} parcel_fill={_fill(df['parcel_id']):.3f}"
            )
            print(f"      {_present(df, ROLL_COLUMNS)}")
    print("\nBPS place-year tables")
    for state in PERMIT_SOURCES:
        raw = store.read(state, "bps_place_year")
        if raw is None:
            print(f"  {state} not built")
            continue
        df = mc.blind(raw, state, geoid_col="geoid", year_col="year")
        years = pd.to_numeric(df["year"])
        span = f"{int(years.min())}-{int(years.max())}"
        print(f"  {state} rows={len(df):>7,} years={span} {_present(df, BPS_COLUMNS)}")


# ------------------------------------------------------------------------------------------ run 1: coverage

WINDOW_FIRST = 2013  # D-042's first event year (calibrate_mm_d082.FIRST)
BPS_LAST = 2025
BPS_FIRST = 1992
NOT_SCREENED = {  # source -> reason (no k is computed)
    "meck_permits": "BPS has no place rows for Charlotte or the Mecklenburg towns (Mecklenburg is kept out "
    "of the D-082 panel); a county-only k would cover about 6% of the source's rows",
}


def _d082():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("d082", Path(__file__).with_name("calibrate_mm_d082.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def full_years(df: pd.DataFrame) -> tuple[int, int]:
    d = pd.to_datetime(df["issue_date"], errors="coerce").dropna()
    y0, y1 = int(d.min().year), int(d.max().year)
    if d.min() > pd.Timestamp(f"{y0}-01-15"):
        y0 += 1
    if d.max() < pd.Timestamp(f"{y1}-12-15"):
        y1 -= 1
    return y0, min(y1, BPS_LAST)


def coverage(store: DataStore, out) -> pd.DataFrame:
    from pathlib import Path

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    d082 = _d082()
    from lotline.model import estimate_mm as mm

    panel = mm.build_panel(store, states=d082.STATES).data
    events, _ = d082.events_d082(panel, d082.rule_rows(store, d082.STATES))
    names = panel.groupby("place")["name"].first().to_dict()
    rows, by_year = [], []
    for state, sources in PERMIT_SOURCES.items():
        bps = mc.blind(store.read(state, "bps_place_year"), state, geoid_col="geoid", year_col="year")
        bps_geoids = set(bps["geoid"].astype(str))
        for place, source in sources:
            base = {"state": state, "source": place, "file": source}
            raw = _read(store, state, "permits", source)
            if raw is None:
                rows.append(base | {"result": "not built"})
                continue
            if source in NOT_SCREENED:
                rows.append(base | {"result": "not screened", "note": NOT_SCREENED[source]})
                continue
            df = mc.blind(raw, state, date_col="issue_date", year_col="issue_year")
            y0, y1 = full_years(df)
            df = df.loc[pd.to_numeric(df["issue_year"]).between(y0, y1)]
            bld = mc.collapse_buildings(df)
            rep = mc.collapse_report(bld)
            geoids = sorted(set(df["jurisdiction_geoid"].astype(str)))
            area = [g for g in geoids if g in bps_geoids]
            left_out = [g for g in geoids if g not in bps_geoids]
            ev = {g: events[g].year for g in area if g in events}
            first_event = min(ev.values()) if ev else None
            res = {}
            for label, start in (("", WINDOW_FIRST), ("long_", BPS_FIRST)):
                win = {g: (max(y0, start), min(y1, ev[g] - 1) if g in ev else y1) for g in area}
                k = mc.area_coverage(bld, bps, win)
                cols = ("permit_buildings", "bps_buildings", "k", "k_lo", "k_hi", "enters", "years")
                res |= {f"{label}{c}": k[c] for c in cols}
                if not label:
                    okb = mc.ok(bld)
                    for g, (a, b_) in win.items():
                        for yr in range(a, b_ + 1):
                            n_p = int(((okb["jurisdiction_geoid"] == g) & (okb["issue_year"] == yr)).sum())
                            n_b = mc.bps_buildings_24(bps, [g], [yr])
                            by_year.append({"state": state, "source": place, "geoid": g, "year": yr,
                                            "permit_buildings": n_p, "bps_buildings": n_b})  # fmt: skip
            # Sensitivity, not the entry rule: a collapsed "building" summing to 5+ units is likely several
            # 2-4 buildings on one parcel in one year (no address to tell them apart, #406). Count it as
            # ceil(u / 4) (fewest) to floor(u / 2) (most) buildings and recompute k.
            multi = bld.loc[(bld["status"] == "units_out_of_range") & (bld["units"] >= 5)]
            for side, f in (("lo", lambda u: -(-u // 4)), ("hi", lambda u: u // 2)):
                extra = 0
                for g, (a, b_) in {g: (max(y0, WINDOW_FIRST), min(y1, ev[g] - 1) if g in ev else y1)
                                   for g in area}.items():  # fmt: skip
                    m = multi.loc[(multi["jurisdiction_geoid"] == g) & multi["issue_year"].between(a, b_)]
                    extra += int(sum(f(int(u)) for u in m["units"]))
                n_b = res["bps_buildings"]
                res[f"split_{side}_k"] = (res["permit_buildings"] + extra) / n_b if n_b else float("nan")
            strong = mc.strong_source(df, {"enters": res["enters"]}, first_event_year=first_event or (y1 + 1))
            rows.append(
                base
                | {"result": "screened", "full_years": f"{y0}-{y1}", "area": ";".join(area),
                   "area_names": ";".join(names.get(g, g) for g in area), "left_out": ";".join(left_out),
                   "events": ";".join(f"{names.get(g, g)} {e}" for g, e in ev.items()) or "none in 2013-2025"}
                | res
                | {f"collapse_{c}": v for c, v in rep.items()}
                | strong
            )  # fmt: skip
    table = pd.DataFrame(rows)
    table.to_csv(out / "coverage.csv", index=False)
    pd.DataFrame(by_year).to_csv(out / "coverage_by_year.csv", index=False)
    return table


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true", help="print input structure only (no counts)")
    ap.add_argument("--coverage", action="store_true", help="D-082 run 1: coverage, k_src, strong tests")
    ap.add_argument("--out", help="output directory for --coverage")
    args = ap.parse_args()
    if args.dry:
        dry(DataStore())
        return 0
    if args.coverage and args.out:
        t = coverage(DataStore(), args.out)
        with pd.option_context("display.width", 250, "display.max_columns", 60):
            print(t.to_string(index=False))
        return 0
    print("Choose --dry, or --coverage --out DIR (D-082 run 1). Runs 2-6 need their own go-ahead.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
