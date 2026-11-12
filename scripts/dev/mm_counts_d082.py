"""Inputs and runs for the D-082 missing-middle counts (`lotline.model.mm_counts`).

    uv run python scripts/dev/mm_counts_d082.py --dry                                  # structure only
    uv run python scripts/dev/mm_counts_d082.py --coverage --out reports/mm-d082/run1-coverage   # run 1

`--dry` reads each candidate permit source, parcel roll and BPS table through `mm_counts.blind` (St. Paul and
Ramsey County dropped outright, then `holdout.apply`) and prints **structure only**.

`--coverage` is D-082 §9 run 1 (approved by Ben 2026-11-12; go-ahead "Yes, start run 1"). Since the
2026-11-12 deviation ("Per-permit split rule") the main collapse is the per-permit split; the pre-registered
collapse is kept as `prereg_*`. For each candidate permit source it reports the building collapse, k_src
against BPS over each place's own pre-event years, its 90% interval, and the four strong-source tests. It
writes `coverage.csv` and `coverage_by_year.csv` to `--out`. Nothing is fitted and nothing is written to
config. Runs 2-6 are not here: each needs its own go-ahead.

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
from lotline.validation.undercount import wilson

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
            # Main: the per-permit split (D-082 deviation 2026-11-12). Pre-registered rule kept as `prereg_*`.
            bld = mc.collapse_buildings(df, split_merged=True)
            bld0 = mc.collapse_buildings(df)
            rep = mc.collapse_report(bld)
            geoids = sorted(set(df["jurisdiction_geoid"].astype(str)))
            area = [g for g in geoids if g in bps_geoids]
            left_out = [g for g in geoids if g not in bps_geoids]
            ev = {g: events[g].year for g in area if g in events}
            first_event = min(ev.values()) if ev else None
            res = {}
            for label, start, b in (("", WINDOW_FIRST, bld), ("long_", BPS_FIRST, bld),
                                    ("prereg_", WINDOW_FIRST, bld0)):  # fmt: skip
                win = {g: (max(y0, start), min(y1, ev[g] - 1) if g in ev else y1) for g in area}
                k = mc.area_coverage(b, bps, win)
                cols = ("permit_buildings", "bps_buildings", "k", "k_lo", "k_hi", "enters", "years")
                res |= {f"{label}{c}": k[c] for c in cols}
                if label == "":
                    okb = mc.ok(bld)
                    for g, (a, b_) in win.items():
                        for yr in range(a, b_ + 1):
                            n_p = int(((okb["jurisdiction_geoid"] == g) & (okb["issue_year"] == yr)).sum())
                            n_b = mc.bps_buildings_24(bps, [g], [yr])
                            by_year.append({"state": state, "source": place, "geoid": g, "year": yr,
                                            "permit_buildings": n_p, "bps_buildings": n_b})  # fmt: skip
            # Sensitivity (run 1's bound): under the pre-registered collapse, a "building" summing to 5+ units
            # is likely several 2-4 buildings on one parcel in one year (no address, #406). Count it as
            # ceil(u / 4) (fewest) to floor(u / 2) (most) buildings and recompute k.
            multi = bld0.loc[(bld0["status"] == "units_out_of_range") & (bld0["units"] >= 5).fillna(False)]
            for side, f in (("lo", lambda u: -(-u // 4)), ("hi", lambda u: u // 2)):
                extra = 0
                for g, (a, b_) in {g: (max(y0, WINDOW_FIRST), min(y1, ev[g] - 1) if g in ev else y1)
                                   for g in area}.items():  # fmt: skip
                    m = multi.loc[(multi["jurisdiction_geoid"] == g) & multi["issue_year"].between(a, b_)]
                    extra += int(sum(f(int(u)) for u in m["units"]))
                n_b = res["prereg_bps_buildings"]
                k_b = (res["prereg_permit_buildings"] + extra) / n_b if n_b else float("nan")
                res[f"split_{side}_k"] = k_b
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


# --------------------------------------------------------------------------- parcel keys for the roll joins


def franklin_key(parcel: pd.Series) -> pd.Series:
    """Columbus permit parcel ('010052628', '010-052628', '010-052628-00') -> the Ohio roll's Franklin parcel
    ID '39049010-052628' (county FIPS + auditor number without the split suffix); else missing."""
    d = parcel.astype("string").str.replace(r"\D", "", regex=True)
    d = d.where(d.str.len().isin([9, 11]))
    d = d.str[:9]
    return ("39049" + d.str[:3] + "-" + d.str[3:]).astype("string")


def wake_crosswalk(card_frames) -> pd.Series:
    """Raw Wake card rows (`REAL_ESTATE_ID`, `Parcel_Identification`) -> Series indexed by the roll's
    `parcel_id` ('37183' + REID) with Raleigh's 10-digit PIN (`wake_roll_diff.pin10`) as values."""
    from lotline.adapters.states.nc import wake_roll_diff as wd

    cards = pd.concat(card_frames, ignore_index=True)
    reid = cards["REAL_ESTATE_ID"].astype("string").str.strip()
    pin = wd.pin10(cards["Parcel_Identification"])
    xw = pd.DataFrame({"pid": "37183" + reid, "pin": pin}).dropna().drop_duplicates("pid")
    return xw.set_index("pid")["pin"].rename(None).rename_axis(None)


def _wake_cards(store: DataStore, name: str) -> pd.DataFrame:
    """REID and PIN columns of one registered Wake roll (raw spreadsheet, offline; no personal column)."""
    from lotline.adapters.states.nc import wake_realestate as wr

    entry = wr.roll_entries(store, name)[-1]
    if store.is_stale(entry):
        raise FileNotFoundError(f"registered Wake roll missing or changed: {entry.path}")
    cols = ["REAL_ESTATE_ID", "Parcel_Identification"]
    return pd.read_excel(store.root / entry.path, usecols=cols, dtype=str, engine="openpyxl")


# ------------------------------------------------------------------------------------------ run 2: ratios

RATIO_FIRST, RATIO_LAST = 2016, 2025  # D-082 §3
SPLIT_STRONG = ("Raleigh", "Durham", "Columbus", "College Station", "Bend")  # run 1, per-permit split
PREREG_STRONG = ("Raleigh", "Austin", "Bend")  # run 1, pre-registered collapse
SIDE = ("Minneapolis",)  # not strong; r56 is defined there only, so it is shown as a side figure
# s_td's prior roll (#408 choice 9): Wake for Raleigh, Franklin for Columbus; others demolition-only.
STD_ROLLS = {"Raleigh": ("NC", "wake_realestate"), "Columbus": ("OH", "oh_parcels")}


def _source_lookup() -> dict[str, tuple[str, str]]:
    return {place: (st, src) for st, srcs in PERMIT_SOURCES.items() for place, src in srcs}


def _roll(store: DataStore, state: str, source: str) -> pd.DataFrame | None:
    raw = _read(store, state, "parcels", source)
    if raw is None:
        return None
    date_col = "vintage_date" if "vintage_date" in raw else None
    df = mc.blind(raw, state, date_col=date_col, year_col="vintage", snapshot=True)
    cols = ("parcel_id", "vintage", "land_use_std", "sf_only_zoned", "jurisdiction_geoid")
    return df[[c for c in cols if c in df]]


def ratios(store: DataStore, out) -> dict:
    from pathlib import Path

    from lotline.build import permit_theme

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    look = _source_lookup()
    per, shares, notes = [], [], {}
    for place in dict.fromkeys(SPLIT_STRONG + PREREG_STRONG + SIDE):
        state, source = look[place]
        raw = _read(store, state, "permits", source)
        if raw is None:
            notes[place] = "not built"
            continue
        df = mc.blind(raw, state, date_col="issue_date", year_col="issue_year")
        themes = permit_theme.permit_theme(df)
        shares.append({"source": place} | mc.two_unit_adu_share(df, themes, RATIO_FIRST, RATIO_LAST))
        dft = mc.apply_themes(df, themes)
        rolls = None
        roll_note = "demolition-only (no prior roll)"
        if place in STD_ROLLS:
            rolls = _roll(store, *STD_ROLLS[place])
            if rolls is not None and place == "Columbus":
                dft = dft.assign(parcel_id=franklin_key(dft["parcel_id"]))
            if rolls is not None and place == "Raleigh":
                from lotline.adapters.states.nc import wake_realestate as wr

                xw = wake_crosswalk([_wake_cards(store, n) for n in wr.ROLLS])
                rolls = rolls.assign(parcel_id=rolls["parcel_id"].astype("string").map(xw))
                rolls = rolls.loc[rolls["parcel_id"].notna()]
            if rolls is None:
                roll_note = "roll not built: demolition-only"
            else:
                pids = set(dft["parcel_id"].dropna().astype(str).str.strip())
                hit = int(rolls["parcel_id"].astype("string").str.strip().isin(pids).sum())
                vint = sorted(int(v) for v in pd.to_numeric(rolls["vintage"]).dropna().unique())
                roll_note = (
                    f"prior roll {STD_ROLLS[place][1]} (vintages {vint}, {hit:,} roll rows on permit parcels)"
                )
        notes[place] = roll_note
        for collapse, split in (("split", True), ("prereg", False)):
            r = mc.source_ratios(
                dft,
                rolls,
                first_year=RATIO_FIRST,
                last_year=RATIO_LAST,
                r56_measured=place == "Minneapolis",
                split_merged=split,
            )
            r["source"] = place
            r["collapse"] = collapse
            # Broad rCV (run 2 choice): conversion-themed permits of any type adding 1-3 homes.
            n_cv = mc.conversion_buildings(df, themes, RATIO_FIRST, RATIO_LAST)
            den = int(r.loc[r["ratio"] == "rCV", "denominator"].iloc[0])
            r["rCV_broad_numerator"] = n_cv
            r["rCV_broad"] = n_cv / den if den else float("nan")
            r["recoded_rows"] = int(dft["theme_recoded"].sum())
            per.append(r)
    per = pd.concat(per, ignore_index=True)
    pooled = []
    sets = (("split_strong", SPLIT_STRONG, "split"), ("prereg_strong", PREREG_STRONG, "prereg"))
    for set_name, members, collapse in sets:
        r = per.loc[per["source"].isin(members) & (per["collapse"] == collapse)]
        pooled.append(mc.pool_ratios(r).assign(source_set=set_name, collapse=collapse))
        # Broad rCV is kept per source as a diagnostic only, never pooled: Bend flags remodels of houses as
        # conversions (thousands of 1-unit 'RE|SFD' rows), so the broad count is not comparable.
    pooled = pd.concat(pooled, ignore_index=True)
    per.to_csv(out / "ratios_by_source.csv", index=False)
    pooled.to_csv(out / "ratios_pooled.csv", index=False)
    pd.DataFrame(shares).to_csv(out / "two_unit_adu_share.csv", index=False)
    (out / "notes.txt").write_text("\n".join(f"{k}: {v}" for k, v in notes.items()) + "\n")
    return {"per": per, "pooled": pooled, "shares": pd.DataFrame(shares), "notes": notes}


# ------------------------------------------------------------------------------------------- run 3: rolls

FRANKLIN_BEFORE, FRANKLIN_AFTER = "2016-12-22", "2024-12-30"  # the cached pair with dwelling cards
FRANKLIN_VACANT = ("500",)  # LUC 500 residential vacant land
ROLL_PAIRS = (  # area, state, processed source, roll 1 vintage, roll 2 vintage
    ("Wake", "NC", "wake_realestate", 2019, 2023),
    # Minneapolis: 2017 -> 2024, the last vintage with unit counts (2025-26 have them on about 1% of houses).
    ("Minneapolis", "MN", "mpls_assessor_parcels", 2017, 2024),
    ("Met Council", "MN", "metc_parcels", 2021, 2025),
)
IMPUTE = {"Met Council"}  # units on about a third of parcels: read missing counts from land use (main)


def _franklin_cards(store: DataStore, date: str) -> pd.DataFrame:
    from lotline.adapters.states.oh import franklin_roll_diff as fr

    base = store.raw("franklin_auditor", date)
    cols = {
        "Dwelling": ["PARCEL ID", "CARD", "LIVUNITS", "YRBLT", "SFLA"],
        "Parcel": ["PARCEL ID", "LUC", "ACRES"],
    }
    frames = {}
    for name, sub in (("Dwelling", "appraisal"), ("Parcel", "")):
        path = base / sub / f"{name}.xlsx"
        if not path.exists():
            raise FileNotFoundError(f"not cached: {path}")
        df = pd.read_excel(path, dtype=str, usecols=lambda c, n=name: c.strip() in cols[n])
        df.columns = [c.strip() for c in df.columns]
        frames[name] = df
    return fr.summarize(frames["Dwelling"], frames["Parcel"])


def rolls(store: DataStore, out) -> pd.DataFrame:
    from pathlib import Path

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    sums, meta = [], []
    for area, state, source, v1, v2 in ROLL_PAIRS:
        raw = _read(store, state, "parcels", source)
        if raw is None:
            meta.append({"area": area, "result": "not built"})
            continue
        date_col = "vintage_date" if "vintage_date" in raw else None
        df = mc.blind(raw, state, date_col=date_col, year_col="vintage", snapshot=True)
        p1 = df.loc[pd.to_numeric(df["vintage"]) == v1]
        p2 = df.loc[pd.to_numeric(df["vintage"]) == v2]
        reads = [("main", area in IMPUTE)] + ([("units_as_coded", False)] if area in IMPUTE else [])
        for read, imp in reads:
            d = mc.diff_rolls_24(
                mc.roll_from_parcels(p1, impute_units=imp), mc.roll_from_parcels(p2, impute_units=imp)
            )
            sums.append(mc.roll_diff_summary(d).assign(area=area, roll_1=v1, roll_2=v2, read=read))
        u2 = df.loc[pd.to_numeric(df["vintage"]) == v2, "units"] if "units" in df else pd.Series(dtype=float)
        fill = float(pd.to_numeric(u2).notna().mean()) if len(u2) else float("nan")
        meta.append({"area": area, "result": "diffed", "roll_1": v1, "roll_2": v2, "units_fill_roll_2": fill,
                     "blinded_rows": int(len(raw) - len(df))})  # fmt: skip
    # Franklin: dwelling cards from the cached auditor spreadsheets (oh_parcels has no units).
    try:
        b = _franklin_cards(store, FRANKLIN_BEFORE)
        a = _franklin_cards(store, FRANKLIN_AFTER)
        oh = _read(store, "OH", "parcels", "oh_parcels")
        oh = mc.blind(oh, "OH", date_col="vintage_date", year_col="vintage", snapshot=True)
        # Place of each Franklin parcel from every vintage of the Ohio roll (only 2023 carries Columbus); a
        # place GEOID (7 digits) wins over the county code.
        oh = oh.loc[oh["county_geoid"] == "39049", ["parcel_id", "jurisdiction_geoid"]].drop_duplicates()
        oh = oh.assign(place=oh["jurisdiction_geoid"].astype("string").str.len() == 7)
        geo = oh.sort_values("place").drop_duplicates("parcel_id", keep="last").set_index("parcel_id")
        geo = geo["jurisdiction_geoid"]
        for x in (b, a):
            key = "39049" + x.index.astype("string").str[:10]
            x["jurisdiction_geoid"] = pd.Series(key, index=x.index).map(geo).fillna("39049").values
        d = mc.diff_rolls_24(mc.roll_from_cards(b, vacant_uses=FRANKLIN_VACANT),
                             mc.roll_from_cards(a, vacant_uses=FRANKLIN_VACANT))  # fmt: skip
        s = mc.roll_diff_summary(d).assign(
            area="Franklin", roll_1=FRANKLIN_BEFORE, roll_2=FRANKLIN_AFTER, read="main"
        )
        sums.append(s)
        matched = float(pd.Series("39049" + b.index.astype("string").str[:10]).isin(geo.index).mean())
        meta.append({"area": "Franklin", "result": "diffed", "roll_1": FRANKLIN_BEFORE,
                     "roll_2": FRANKLIN_AFTER, "jurisdiction_matched": matched})  # fmt: skip
    except FileNotFoundError as e:
        meta.append({"area": "Franklin", "result": f"not built: {e}"})
    table = pd.concat(sums, ignore_index=True) if sums else pd.DataFrame()
    lead = ["area", "read", "roll_1", "roll_2"]
    table = table[lead + [c for c in table.columns if c not in lead]]
    count_cols = [
        "lots",
        "single",
        "vacant",
        "gained_24",
        "merge",
        "split",
        "none",
        "merge_looked_gained",
        "counted",
    ]
    totals = table.groupby(["area", "read"], sort=False)[count_cols].sum().reset_index()
    totals["share"] = totals["gained_24"] / totals["counted"]
    w = [wilson(int(k), int(n), 1.96) for k, n in zip(totals["gained_24"], totals["counted"], strict=True)]
    totals["share_lo"], totals["share_hi"] = [x[0] for x in w], [x[1] for x in w]
    table.to_csv(out / "roll_gains_by_place.csv", index=False)
    totals.to_csv(out / "roll_gains_by_area.csv", index=False)
    pd.DataFrame(meta).to_csv(out / "rolls_meta.csv", index=False)
    return table


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true", help="print input structure only (no counts)")
    ap.add_argument("--coverage", action="store_true", help="D-082 run 1: coverage, k_src, strong tests")
    ap.add_argument("--ratios", action="store_true", help="D-082 run 2: uplift ratios r56, rTH, rCV, s_td")
    ap.add_argument("--rolls", action="store_true", help="D-082 run 3: 2-4 roll diffs (test B, observed)")
    ap.add_argument("--out", help="output directory")
    args = ap.parse_args()
    if args.dry:
        dry(DataStore())
        return 0
    if args.coverage and args.out:
        t = coverage(DataStore(), args.out)
        with pd.option_context("display.width", 250, "display.max_columns", 60):
            print(t.to_string(index=False))
        return 0
    if args.ratios and args.out:
        r = ratios(DataStore(), args.out)
        with pd.option_context("display.width", 250, "display.max_columns", 60, "display.max_rows", 200):
            print(r["per"].to_string(index=False))
            print(r["pooled"].to_string(index=False))
            print(r["shares"].to_string(index=False))
            print(r["notes"])
        return 0
    if args.rolls and args.out:
        t = rolls(DataStore(), args.out)
        with pd.option_context("display.width", 250, "display.max_columns", 60, "display.max_rows", 300):
            print(t.to_string(index=False))
        return 0
    print("Choose --dry, or --coverage --out DIR (D-082 run 1). Runs 2-6 need their own go-ahead.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
