"""Missing-middle permit and roll counts pre-registered by D-082 (proposed) §2–§3. Code only: nothing here has
been run on real data, and every run waits for Ben's go-ahead.

D-082 keeps Census BPS as the fitted outcome everywhere and adds record-level permit counts from the strong
sources (numeric unit counts, parcel IDs) for three things: measured uplift ratios (§3), test B (the roll
diff) and challenger 2. This module holds the counting rules, so they are committed and tested before any
count:

- **Building collapse** (§2), `collapse_buildings`: permit rows → buildings. One building = one parcel × one
  issue year × one street address, among rows with `building_type_std` in {U2, U3_4}, units summed across the
  permits. A building whose summed units fall outside 2–4, or whose units are unknown, is reported (`status`)
  and left out of every count.
- **Coverage screen** (§2), `coverage_k` / `coverage_screen` / `strong_source`: k_src = permit buildings ÷ BPS
  2–4 unit buildings over the same area and the years before the source's events; the source enters if
  0.8 ≤ k_src ≤ 1.25. k_src is kept per source and never pooled (D-078).
- **Uplift ratios** (§3), `source_ratios` / `pool_ratios`: r56, rTH, rCV and s_td per source, pooled as a
  building-weighted mean with a min–max range over sources on at least 50 buildings.
- **Roll diff for 2–4** (§2, test B), `roll_from_parcels` / `diff_rolls_24` / `roll_diff_summary`: a lot
  that was a single dwelling (or vacant) in roll 1 and holds 2–4 units in one building in roll 2. Merges (lot
  area up more than 20%) and splits (parcel ID retired) are reported and left out, as in `wake_roll_diff.py`
  §1.
- **Holdouts**, `blind`: every table that enters goes through `holdout.apply`, after St. Paul and all of
  Ramsey County are dropped outright (D-082 §1: "St. Paul and Ramsey are never read"). The counting functions
  refuse (raise `NeverReadError`) a table that still carries one of those GEOIDs, so a caller that skipped
  `blind` fails loudly instead of counting the holdout.

Every threshold is read from `config/params/mm.yaml` (the `mm_*` keys under "D-082 counting protocol"); the
functions take them as arguments with those values as defaults, so tests can pass hand-worked values.
No data is read here: `scripts/dev/mm_counts_d082.py` builds the inputs through `DataStore`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from functools import cache

import pandas as pd

from lotline.config import load_params
from lotline.validation import holdout
from lotline.validation.undercount import wilson

# ---------------------------------------------------------------------------------------------- parameters

MM_TYPES = ("U2", "U3_4")  # D-082 §2: the 2–4 unit classes
HOUSE_USES = frozenset({"SF_DETACHED"})  # "held a house" in the prior roll (s_td)
VACANT_USES = frozenset({"VACANT_RESIDENTIAL"})
ONE_BUILDING_24_USES = frozenset({"DUPLEX", "TRI_QUAD"})
IMPUTED_UNITS = {
    "SF_DETACHED": 1,
    "DUPLEX": 2,
    "TRI_QUAD": 3,
}  # roll_from_parcels(impute_units=True)  # roll land uses read as one 2–4 unit building

# D-082 §1: St. Paul and Ramsey County are never read (V5 blind test). Not parameters: fixed identifiers.
NEVER_READ_PLACES = frozenset({"2758000"})  # St. Paul city
NEVER_READ_COUNTIES = ("27123",)  # Ramsey County: any GEOID or MN parcel ID that starts with it


@cache
def params() -> dict[str, float]:
    """The D-082 counting thresholds from config/params/mm.yaml."""
    p = load_params("mm")
    keys = (
        "mm_strong_parcel_fill",
        "mm_strong_min_pre_years",
        "mm_coverage_k_low",
        "mm_coverage_k_high",
        "mm_collapse_min_units",
        "mm_collapse_max_units",
        "mm_ratio_min_buildings",
        "mm_teardown_demolition_window",
        "mm_roll_merge_growth",
        "mm_coverage_interval_z",
    )
    return {k: p[k].value for k in keys}


def _p(name: str) -> float:
    return params()[name]


# ------------------------------------------------------------------------------------------------ holdouts


class NeverReadError(RuntimeError):
    """Raised when a St. Paul or Ramsey County row reaches a counting function."""


def never_read_mask(df: pd.DataFrame) -> pd.Series:
    """True for rows of St. Paul or Ramsey County, judged on every GEOID-like column present
    (`jurisdiction_geoid`, `geoid`, `county_geoid`, `ctu_geoid`) and on `parcel_id`, whose MN form starts with
    the county FIPS. A missing value is not a match: those rows are left to `holdout.apply`."""
    mask = pd.Series(False, index=df.index)
    for col in ("jurisdiction_geoid", "geoid", "county_geoid", "ctu_geoid", "parcel_id"):
        if col not in df:
            continue
        s = df[col].astype("string").str.strip()
        hit = s.isin(NEVER_READ_PLACES)
        for county in NEVER_READ_COUNTIES:
            hit |= s.str.startswith(county)
        mask |= hit.fillna(False).astype(bool)
    return mask


def refuse_never_read(df: pd.DataFrame, what: str) -> None:
    """Raise if `df` still holds a St. Paul or Ramsey row (the caller skipped `blind`)."""
    n = int(never_read_mask(df).sum())
    if n:
        raise NeverReadError(
            f"{what}: {n} St. Paul / Ramsey County rows reached a count; pass them through blind()"
        )


def blind(
    df: pd.DataFrame,
    state: str,
    *,
    geoid_col: str = "jurisdiction_geoid",
    date_col: str | None = None,
    year_col: str | None = None,
    snapshot: bool = False,
    holdouts=None,
) -> pd.DataFrame:
    """The one door every table goes through: drop St. Paul / Ramsey rows outright, then `holdout.apply`.

    Permits: `date_col="issue_date", year_col="issue_year"`. Rolls: `year_col="vintage"` (and
    `date_col="vintage_date"` when present) with `snapshot=True`. BPS: `geoid_col="geoid", year_col="year"`.
    No test is ever unblinded here. `holdouts` overrides the registry (tests only)."""
    out = df.loc[~never_read_mask(df)]
    return holdout.apply(
        out,
        state,
        holdouts=holdouts,
        geoid_col=geoid_col,
        date_col=date_col,
        year_col=year_col,
        snapshot=snapshot,
    )


# --------------------------------------------------------------------------------------- building collapse

COLLAPSE_STATUS = ("ok", "units_missing", "units_out_of_range")


def _address(s: pd.Series) -> pd.Series:
    """Street address → a comparison key: upper case, punctuation dropped, spaces collapsed; missing → ""."""
    a = s.astype("string").str.upper().str.replace(r"[^A-Z0-9 ]", " ", regex=True)
    return a.str.replace(r"\s+", " ", regex=True).str.strip().fillna("")


def collapse_buildings(
    permits: pd.DataFrame,
    *,
    types: Iterable[str] = MM_TYPES,
    min_units: float | None = None,
    max_units: float | None = None,
    check_units: bool = True,
    address_col: str = "address",
    split_merged: bool = False,
) -> pd.DataFrame:
    """Permit rows → one row per building (D-082 §2).

    Key: `source` × `parcel_id` × `issue_year` × normalized street address, over rows whose
    `building_type_std` is in `types`. Units (`units_new`) are summed across the building's permits.

    - **No address column** (the processed `permits` table drops addresses): the key is parcel × issue year,
      and `address_used` is False on every row. Two buildings on one parcel in one year then count as one.
    - **Missing parcel ID:** the row cannot be grouped with others, so each such permit is its own building
      (`parcel_missing` True). It is kept in the building counts, and left out of every parcel join (rTH, r56,
      s_td, the roll) where it is reported instead.
    - **Aggregate rows** (`n_buildings` set: a source that publishes type × year totals) are not permits
      and are dropped; the count is in `attrs["aggregate_rows"]`.
    - **Status:** `ok` if `min_units ≤ units ≤ max_units`; `units_missing` if any permit in the building has
      no unit count; `units_out_of_range` otherwise. Only `ok` buildings are counted anywhere. With
      `check_units=False` (townhouses, which have no unit bound in D-082) every building with units is `ok`.

    - **Per-permit split** (`split_merged=True`; D-082 deviation 2026-11-12, chosen by Ben after run 1): when
      a group's units sum above `max_units` and **every** permit in it has a unit count inside
      `min_units … max_units`, each permit is its own building (`split` True). Without an address, this
      separates several 2–4 buildings permitted on one parcel in one year. Groups with a permit below
      `min_units` (one permit per duplex side) stay merged.

    Columns: source, jurisdiction_geoid, parcel_id, issue_year, address_key, units, n_permits, is_conversion
    (any permit flagged), parcel_missing, address_used, split, status.
    """
    refuse_never_read(permits, "collapse_buildings")
    lo = _p("mm_collapse_min_units") if min_units is None else min_units
    hi = _p("mm_collapse_max_units") if max_units is None else max_units
    rows = permits.loc[permits["building_type_std"].isin(list(types))]
    agg = rows["n_buildings"].notna() if "n_buildings" in rows else pd.Series(False, index=rows.index)
    n_agg = int(agg.sum())
    rows = rows.loc[~agg]
    has_address = address_col in rows
    pid = (
        rows["parcel_id"].astype("string").str.strip()
        if "parcel_id" in rows
        else pd.Series(pd.NA, index=rows.index, dtype="string")
    )
    pid = pid.mask(pid == "")
    missing = pid.isna()
    df = pd.DataFrame(
        {
            "source": rows["source"].astype("string"),
            "jurisdiction_geoid": rows["jurisdiction_geoid"].astype("string"),
            "parcel_id": pid,
            "issue_year": pd.to_numeric(rows["issue_year"]).astype("Int64"),
            "address_key": _address(rows[address_col]) if has_address else "",
            "units": pd.to_numeric(rows["units_new"]).astype("Float64"),
            "is_conversion": rows["is_conversion"].astype("boolean").fillna(False)
            if "is_conversion" in rows
            else False,
            "parcel_missing": missing,
        },
        index=rows.index,
    )
    # A permit with no parcel ID is its own building: give it a key no other row can share.
    df["group_key"] = df["parcel_id"].where(~missing, "permit:" + rows["permit_id"].astype("string"))
    keys = ["source", "group_key", "issue_year", "address_key"]
    df["split"] = False
    if split_merged:
        grp = df.groupby(keys, sort=False, dropna=False)["units"]
        total = grp.transform(lambda u: u.sum() if u.notna().all() else pd.NA).astype("Float64")
        inside = ((df["units"] >= lo) & (df["units"] <= hi)).fillna(False).astype(bool)
        all_inside = inside.groupby([df[k] for k in keys], dropna=False).transform("all")
        cut = (total > hi).fillna(False).astype(bool) & all_inside
        df.loc[cut, "address_key"] = "permit:" + rows.loc[cut, "permit_id"].astype("string")
        df.loc[cut, "split"] = True
    g = df.groupby(keys, sort=True, dropna=False)
    out = g.agg(
        jurisdiction_geoid=("jurisdiction_geoid", "first"),
        parcel_id=("parcel_id", "first"),
        units=("units", lambda u: u.sum() if u.notna().all() else pd.NA),
        n_permits=("units", "size"),
        is_conversion=("is_conversion", "any"),
        parcel_missing=("parcel_missing", "first"),
        split=("split", "first"),
    ).reset_index()
    out = out.drop(columns="group_key")
    out["units"] = out["units"].astype("Float64")
    out["address_used"] = has_address
    in_range = (out["units"] >= lo) & (out["units"] <= hi) if check_units else out["units"].notna()
    out["status"] = "ok"
    out.loc[out["units"].isna(), "status"] = "units_missing"
    out.loc[out["units"].notna() & ~in_range.fillna(False).astype(bool), "status"] = "units_out_of_range"
    out.attrs["aggregate_rows"] = n_agg
    return out


def collapse_report(buildings: pd.DataFrame) -> dict[str, int | bool]:
    """Counts behind a collapse: permits, buildings by status, missing parcel IDs, aggregate rows dropped."""
    st = buildings["status"].value_counts()
    return {
        "permits": int(buildings["n_permits"].sum()),
        "buildings": int(len(buildings)),
        **{f"buildings_{s}": int(st.get(s, 0)) for s in COLLAPSE_STATUS},
        "buildings_parcel_missing": int(buildings["parcel_missing"].sum()),
        "buildings_split": int(buildings["split"].sum()) if "split" in buildings else 0,
        "address_used": bool(buildings["address_used"].all()) if len(buildings) else False,
        "aggregate_rows_dropped": int(buildings.attrs.get("aggregate_rows", 0)),
    }


def ok(buildings: pd.DataFrame) -> pd.DataFrame:
    """The buildings that count (status `ok`)."""
    return buildings.loc[buildings["status"] == "ok"]


# ------------------------------------------------------------------------------------------ coverage and k


def coverage_k(
    permit_buildings: int, bps_buildings: int, *, z: float | None = None
) -> dict[str, float | bool]:
    """k_src = permit buildings ÷ BPS 2–4 unit buildings, with an interval and the D-082 entry rule.

    Interval: **conditional binomial (Wilson)**. Treat both counts as Poisson; given their total
    n = a + b, a is Binomial(n, p) with p = k / (1 + k). The Wilson interval on p (z = 1.6449, 90% two-sided,
    by default) is mapped back through k = p / (1 − p). It is the standard interval for a ratio of two Poisson
    counts and
    reuses `validation.undercount.wilson`. The entry rule uses the point k, not the interval.
    """
    z = _p("mm_coverage_interval_z") if z is None else z
    a, b = int(permit_buildings), int(bps_buildings)
    lo_k, hi_k = _p("mm_coverage_k_low"), _p("mm_coverage_k_high")
    if b == 0:
        k = math.inf if a > 0 else math.nan
    else:
        k = a / b
    n = a + b
    if n == 0:
        lo, hi = math.nan, math.nan
    else:
        plo, phi = wilson(a, n, z)
        lo = plo / (1 - plo) if plo < 1 else math.inf
        hi = phi / (1 - phi) if phi < 1 else math.inf
    enters = bool(math.isfinite(k) and lo_k <= k <= hi_k)
    return {"permit_buildings": a, "bps_buildings": b, "k": k, "k_lo": lo, "k_hi": hi, "enters": enters}


def bps_buildings_24(bps: pd.DataFrame, geoids: Iterable[str], years: Iterable[int]) -> int:
    """BPS 2–4 unit buildings (`bldgs_2 + bldgs_3_4`, D-038) over `geoids` and `years`."""
    refuse_never_read(bps, "bps_buildings_24")
    rows = bps.loc[bps["geoid"].astype("string").isin(list(geoids)) & bps["year"].isin(list(years))]
    return int(
        pd.to_numeric(rows["bldgs_2"]).fillna(0).sum() + pd.to_numeric(rows["bldgs_3_4"]).fillna(0).sum()
    )


def coverage_screen(
    buildings: pd.DataFrame,
    bps: pd.DataFrame,
    *,
    geoids: Iterable[str],
    first_event_year: int,
    first_year: int,
    z: float | None = None,
) -> dict[str, float | bool]:
    """k_src over the source's area (`geoids`) and the years `first_year` … `first_event_year − 1` (before the
    source's events). Permit buildings are the `ok` collapsed 2–4 buildings in those places and years,
    conversions included (BPS counts new buildings only; that is why the screen has an upper bound)."""
    geoids = list(geoids)
    years = list(range(first_year, first_event_year))
    b = ok(buildings)
    a = int((b["jurisdiction_geoid"].isin(geoids) & b["issue_year"].isin(years)).sum())
    out = coverage_k(a, bps_buildings_24(bps, geoids, years), z=z)
    out["years"] = f"{first_year}-{first_event_year - 1}" if years else ""
    return out


def area_coverage(
    buildings: pd.DataFrame,
    bps: pd.DataFrame,
    windows: Mapping[str, tuple[int, int]],
    *,
    z: float | None = None,
) -> dict[str, float | bool | str]:
    """k_src for a source whose places have different events: `windows` maps each place GEOID to its own
    pre-event years (first, last), inclusive. Permit buildings (`ok`, conversions included) and BPS 2–4 unit
    buildings are summed over every place's own years, then `coverage_k` is applied once to the totals, so
    the source still gets a single k (D-082 §2: one k per source, never pooled across sources).

    By hand: G1 years 2016–2017 and G2 year 2018 → only those place-years count."""
    b = ok(buildings)
    a = n = 0
    for g, (y0, y1) in windows.items():
        years = list(range(int(y0), int(y1) + 1))
        a += int((b["jurisdiction_geoid"].isin([g]) & b["issue_year"].isin(years)).sum())
        n += bps_buildings_24(bps, [g], years)
    out = coverage_k(a, n, z=z)
    out["years"] = "; ".join(f"{g} {y0}-{y1}" for g, (y0, y1) in windows.items() if y1 >= y0)
    return out


def strong_source(
    permits: pd.DataFrame,
    coverage: Mapping[str, float | bool],
    *,
    first_event_year: int,
    fill: float | None = None,
    min_pre_years: float | None = None,
) -> dict[str, float | bool]:
    """The four D-082 §2 tests for one source's permit rows (all types):

    - `has_units`: some U2/U3_4 row has a numeric `units_new`;
    - `parcel_fill`: share of rows with a parcel ID, at least 0.85;
    - `pre_years`: distinct issue years before `first_event_year`, at least 3;
    - `coverage`: `coverage["enters"]` (from `coverage_screen`).
    """
    fill = _p("mm_strong_parcel_fill") if fill is None else fill
    min_pre = _p("mm_strong_min_pre_years") if min_pre_years is None else min_pre_years
    mm = permits["building_type_std"].isin(list(MM_TYPES))
    has_units = bool(pd.to_numeric(permits.loc[mm, "units_new"]).notna().any())
    pid = (
        permits["parcel_id"].astype("string").str.strip()
        if "parcel_id" in permits
        else pd.Series(pd.NA, index=permits.index, dtype="string")
    )
    share = float(((pid.notna()) & (pid != "")).fillna(False).mean()) if len(permits) else 0.0
    years = pd.to_numeric(permits["issue_year"])
    pre_years = int(years.loc[years < first_event_year].nunique())
    tests = {
        "has_units": has_units,
        "parcel_fill": share,
        "parcel_fill_ok": share >= fill,
        "pre_years": pre_years,
        "pre_years_ok": pre_years >= min_pre,
        "coverage_ok": bool(coverage.get("enters", False)),
    }
    tests["strong"] = bool(
        tests["has_units"] and tests["parcel_fill_ok"] and tests["pre_years_ok"] and tests["coverage_ok"]
    )
    return tests


# ------------------------------------------------------------------------------------------- uplift ratios

RATIOS = ("r56", "rTH", "rCV", "s_td")


def prior_roll(buildings: pd.DataFrame, rolls: pd.DataFrame, column: str) -> pd.Series:
    """Each building's value of `column` in the **prior roll**: the latest roll vintage strictly before its
    issue year, on the same parcel. NA when the building has no parcel ID, no earlier roll exists, or the
    parcel is not on that roll. `rolls` has `parcel_id`, `vintage` and `column` (one row per parcel ×
    vintage).
    """
    out = pd.Series(pd.NA, index=buildings.index, dtype="object")
    if rolls is None or rolls.empty or column not in rolls:
        return out
    refuse_never_read(rolls, "prior_roll")
    r = rolls[["parcel_id", "vintage", column]].copy()
    r["parcel_id"] = r["parcel_id"].astype("string").str.strip()
    r["vintage"] = pd.to_numeric(r["vintage"]).astype("int64")
    vintages = sorted(r["vintage"].unique())
    by_v = {
        v: r.loc[r["vintage"] == v].drop_duplicates("parcel_id").set_index("parcel_id")[column]
        for v in vintages
    }
    for i, (pid, y) in enumerate(zip(buildings["parcel_id"], buildings["issue_year"], strict=True)):
        if pd.isna(pid) or pd.isna(y):
            continue
        earlier = [v for v in vintages if v < int(y)]
        if not earlier:
            continue
        val = by_v[earlier[-1]].get(pid, pd.NA)
        out.iloc[i] = val
    return out


def _in_years(b: pd.DataFrame, first_year: int, last_year: int) -> pd.DataFrame:
    return b.loc[b["issue_year"].between(first_year, last_year)]


def source_ratios(
    permits: pd.DataFrame,
    rolls: pd.DataFrame | None,
    *,
    first_year: int = 2016,
    last_year: int = 2025,
    r56_measured: bool = False,
    window: int | None = None,
    split_merged: bool = False,
) -> pd.DataFrame:
    """D-082 §3 ratios for one source over `first_year` … `last_year`: one row per ratio with its numerator,
    denominator and value (NaN when not measured).

    The denominator of r56, rTH and rCV is **new 2–4 unit buildings**: `ok` collapsed U2/U3_4 buildings with
    no conversion permit. Conversions are rCV's numerator, not part of the base.

    - **r56** = `ok` U5_6 buildings (5–6 units after collapse) on parcels with `sf_only_zoned` True in the
      prior roll. Measured only when `r56_measured` (Minneapolis; elsewhere "not measured", NaN).
    - **rTH** = TH buildings (collapsed, no unit bound) on parcels `sf_only_zoned` in the prior roll. NaN when
      no roll is given.
    - **rCV** = `ok` 2–4 unit buildings with an `is_conversion` permit.
    - **s_td** = share of new 2–4 unit buildings whose parcel held a house (`land_use_std` SF_DETACHED) in the
      prior roll, **or** had an `is_demolition` permit (any type) on the same parcel within ±`window` years of
      the building's issue year. Its denominator is the new 2–4 buildings **with a parcel ID**; buildings
      without one cannot be joined and are reported (`no_parcel`), not counted as "no teardown". A building
      whose parcel is not on an earlier roll is judged on demolitions alone (reported as `no_prior_roll`).

    A parcel missing from the prior roll, or a building without a parcel ID, counts as "not single-family-
    zoned" in r56 and rTH; those numbers are reported (`*_unmatched`) so the bias is visible.
    """
    refuse_never_read(permits, "source_ratios")
    window = int(_p("mm_teardown_demolition_window") if window is None else window)
    b24 = _in_years(ok(collapse_buildings(permits, split_merged=split_merged)), first_year, last_year)
    new = b24.loc[~b24["is_conversion"]]
    cv = b24.loc[b24["is_conversion"]]
    n24 = len(new)
    have_roll = rolls is not None and not rolls.empty
    # r56 and rTH need single-family zoning on the prior roll; without it they are "not measured" (NaN).
    have_zoning = have_roll and "sf_only_zoned" in rolls
    rows: list[dict] = []

    # r56
    if r56_measured:
        b56 = _in_years(
            ok(
                collapse_buildings(
                    permits, types=("U5_6",), min_units=5, max_units=6, split_merged=split_merged
                )
            ),
            first_year,
            last_year,
        )
        if have_zoning:
            sf = prior_roll(b56, rolls, "sf_only_zoned")
            hit = sf.astype("boolean").fillna(False).astype(bool)
            rows.append(_ratio("r56", int(hit.sum()), n24, unmatched=int(sf.isna().sum())))
        else:
            rows.append(_ratio("r56", None, n24, u56_buildings=int(len(b56))))
    else:
        rows.append(_ratio("r56", None, n24))

    # rTH
    if have_zoning:
        bth = _in_years(
            ok(collapse_buildings(permits, types=("TH",), check_units=False)),
            first_year,
            last_year,
        )
        sf = prior_roll(bth, rolls, "sf_only_zoned")
        hit = sf.astype("boolean").fillna(False).astype(bool)
        rows.append(_ratio("rTH", int(hit.sum()), n24, unmatched=int(sf.isna().sum())))
    else:
        rows.append(_ratio("rTH", None, n24))

    # rCV
    rows.append(_ratio("rCV", len(cv), n24))

    # s_td
    joined = new.loc[~new["parcel_missing"]]
    house = (
        prior_roll(joined, rolls, "land_use_std")
        if have_roll
        else pd.Series(pd.NA, index=joined.index, dtype="object")
    )
    held_house = house.isin(list(HOUSE_USES)).astype(bool)
    demo = _demolition_near(joined, permits, window)
    td = held_house | demo
    rows.append(
        _ratio(
            "s_td",
            int(td.sum()),
            len(joined),
            no_parcel=int(new["parcel_missing"].sum()),
            no_prior_roll=int(house.isna().sum()),
        )
    )
    out = pd.DataFrame(rows)
    out.insert(0, "source", ",".join(sorted(permits["source"].astype(str).unique())) if len(permits) else "")
    return out


KEEP_THEMES = frozenset({"mm_2_4", "conversion"})  # D-082 §6: what a 2–4 or conversion count may hold


def apply_themes(permits: pd.DataFrame, themes: pd.Series) -> pd.DataFrame:
    """D-082 §6: a U2/U3_4 row whose shared theme (`build.permit_theme`) is not `mm_2_4` or `conversion`
    (an ADU filed in a 2-unit class, an alteration adding no home, a demolition) is recoded to
    `building_type_std` "OTHER", so no 2–4 collapse counts it. Rows are kept, not dropped: a recoded
    demolition still marks a teardown for s_td. `theme_recoded` says which rows changed.

    By hand: U2 themed adu → OTHER; U2 themed mm_2_4 → U2; U3_4 demolition themed other → OTHER, still
    `is_demolition`; SFD themed other → SFD (not a 2–4 type, untouched)."""
    out = permits.copy()
    mm = out["building_type_std"].isin(list(MM_TYPES))
    drop = mm & ~themes.reindex(out.index).astype("string").isin(list(KEEP_THEMES)).fillna(False).astype(bool)
    out.loc[drop, "building_type_std"] = "OTHER"
    out["theme_recoded"] = drop
    return out


def conversion_buildings(
    permits: pd.DataFrame, themes: pd.Series, first_year: int, last_year: int, *, max_added: int = 3
) -> int:
    """D-082 §3 rCV's broad numerator: permits the shared classifier calls `conversion` (an existing building
    gaining homes, of **any** `building_type_std`, e.g. Austin class 436 typed OTHER) that add 1 to
    `max_added` homes, so the result can be a 2–4 unit building. One per parcel × issue year; a permit with
    no parcel ID is its own.

    By hand: conversion rows on parcel A 2020 (+1) and A 2020 (+1) → 1; B 2021 (+2) → 1; C 2021 (+5) → not
    counted (too many added); D 2021 (+1) themed mm_2_4 → not a conversion. Total 2."""
    t = themes.reindex(permits.index).astype("string")
    yr = pd.to_numeric(permits["issue_year"])
    add = pd.to_numeric(permits["units_new"])
    keep = (t == "conversion").fillna(False).astype(bool) & yr.between(first_year, last_year)
    keep &= add.between(1, max_added).fillna(False).astype(bool)
    r = permits.loc[keep]
    pid = r["parcel_id"].astype("string").str.strip().replace("", pd.NA) if "parcel_id" in r else None
    key = pid.fillna("permit:" + r["permit_id"].astype("string")) if pid is not None else r["permit_id"]
    return int(pd.DataFrame({"k": key, "y": yr.loc[r.index]}).drop_duplicates().shape[0])


def two_unit_adu_share(permits: pd.DataFrame, themes: pd.Series, first_year: int, last_year: int) -> dict:
    """D-082 §6: among U2 permit rows in the years that add homes (theme `adu` or `mm_2_4`), the share the
    shared classifier calls ADUs: the part of a BPS-style "2-unit" count that is ADUs in this source.

    By hand: U2 rows themed adu, mm_2_4, mm_2_4, other (alteration) → 1 / 3."""
    yr = pd.to_numeric(permits["issue_year"])
    t = themes.reindex(permits.index).astype("string")
    u2 = (permits["building_type_std"] == "U2") & yr.between(first_year, last_year)
    adds = u2 & t.isin(["adu", "mm_2_4"]).fillna(False).astype(bool)
    n_adu = int((adds & (t == "adu").fillna(False).astype(bool)).sum())
    n = int(adds.sum())
    return {"u2_adding_rows": n, "u2_adu_rows": n_adu, "adu_share": n_adu / n if n else math.nan}


def _ratio(name: str, num: int | None, den: int, **extra: int) -> dict:
    measured = num is not None
    value = (num / den) if measured and den > 0 else math.nan
    return {
        "ratio": name,
        "measured": measured,
        "numerator": num if measured else pd.NA,
        "denominator": den,
        "value": value,
        **extra,
    }


def _demolition_near(buildings: pd.DataFrame, permits: pd.DataFrame, window: int) -> pd.Series:
    """True where the building's parcel has an `is_demolition` permit within ±`window` years."""
    if "is_demolition" not in permits or buildings.empty:
        return pd.Series(False, index=buildings.index)
    d = permits.loc[permits["is_demolition"].astype("boolean").fillna(False).astype(bool)]
    pid = d["parcel_id"].astype("string").str.strip()
    years: dict[str, list[int]] = {}
    for p, y in zip(pid, pd.to_numeric(d["issue_year"]), strict=True):
        if pd.notna(p) and pd.notna(y):
            years.setdefault(str(p), []).append(int(y))
    return pd.Series(
        [
            any(abs(y - int(by)) <= window for y in years.get(str(p), ()))
            for p, by in zip(buildings["parcel_id"], buildings["issue_year"], strict=True)
        ],
        index=buildings.index,
        dtype=bool,
    )


def pool_ratios(per_source: pd.DataFrame, *, min_buildings: float | None = None) -> pd.DataFrame:
    """Pool `source_ratios` rows (stacked over sources) per ratio.

    - `pooled` = Σ numerators ÷ Σ denominators over the sources where the ratio is measured: the mean of the
      source ratios weighted by their denominator buildings.
    - `low` / `high` = the lowest and highest source ratio among measured sources with at least
      `min_buildings` (50) denominator buildings; NaN if none qualifies (then no range is claimed).
    """
    min_b = _p("mm_ratio_min_buildings") if min_buildings is None else min_buildings
    out = []
    for name in RATIOS:
        r = per_source.loc[(per_source["ratio"] == name) & per_source["measured"].astype(bool)]
        num = pd.to_numeric(r["numerator"]).sum()
        den = pd.to_numeric(r["denominator"]).sum()
        big = r.loc[pd.to_numeric(r["denominator"]) >= min_b]
        out.append(
            {
                "ratio": name,
                "sources": int(len(r)),
                "sources_in_range": int(len(big)),
                "numerator": int(num),
                "denominator": int(den),
                "pooled": float(num / den) if den > 0 else math.nan,
                "low": float(big["value"].min()) if len(big) else math.nan,
                "high": float(big["value"].max()) if len(big) else math.nan,
            }
        )
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------- roll diff (test B)

ROLL_COLUMNS = ("jurisdiction_geoid", "units", "buildings", "lot_sqft")
ROLL_GROUPS = ("gained_24", "merge", "split", "none")


def roll_from_parcels(parcels: pd.DataFrame, *, impute_units: bool = False) -> pd.DataFrame:
    """Processed `parcels` rows of one vintage → the roll interface `diff_rolls_24` reads: indexed by
    `parcel_id`, columns `jurisdiction_geoid`, `units`, `buildings` (dwelling buildings), `lot_sqft`.

    The parcels table has units but no building count, so buildings are read from land use: SF_DETACHED,
    DUPLEX and TRI_QUAD with units > 0 are one dwelling building; VACANT_RESIDENTIAL is none; every other use
    is NA (not a single dwelling, vacant lot or one 2–4 building, so never in the denominator nor a gain).
    Adapters with building or card rows (Wake cards, Franklin dwelling cards, Minneapolis assessor buildings)
    should fill `buildings` and `units` directly instead: their summaries carry `dwelling_cards` and
    `dwelling_units`.
    """
    refuse_never_read(parcels, "roll_from_parcels")
    p = parcels.assign(parcel_id=parcels["parcel_id"].astype("string").str.strip()).drop_duplicates(
        "parcel_id"
    )
    lu = p["land_use_std"].astype("string")
    units = (
        pd.to_numeric(p["units"]).astype("Float64")
        if "units" in p
        else pd.Series(pd.NA, index=p.index, dtype="Float64")
    )
    # A house-coded parcel with 2+ units (house plus ADU, or a duplex coded as a house) is ambiguous: it is
    # neither a single dwelling nor surely one 2-4 building, so its building count is NA (run 3 choice).
    sf_multi = lu.isin(list(HOUSE_USES)) & (units > 1).fillna(False)
    if impute_units:
        # Run 3 choice for rolls with sparse unit counts (Met Council): a missing count is read from the land
        # use, house 1, duplex 2, triplex/fourplex 3 (any 3-4 is inside 2-4). Reported beside the plain read.
        units = units.fillna(lu.map(IMPUTED_UNITS).astype("Float64"))
    one = lu.isin(list(HOUSE_USES | ONE_BUILDING_24_USES)) & (units > 0).fillna(False) & ~sf_multi
    vacant = lu.isin(list(VACANT_USES))
    buildings = pd.Series(pd.NA, index=p.index, dtype="Float64")
    buildings[one.astype(bool)] = 1
    buildings[vacant.astype(bool)] = 0
    units = units.mask(vacant.astype(bool), 0)
    out = pd.DataFrame(
        {
            "jurisdiction_geoid": p["jurisdiction_geoid"].astype("string").values,
            "units": units.values,
            "buildings": buildings.values,
            "lot_sqft": pd.to_numeric(p["lot_sqft"]).astype("Float64").values,
        },
        index=pd.Index(p["parcel_id"].values, name="parcel_id"),
    )
    return out


def roll_from_cards(
    summary: pd.DataFrame,
    *,
    vacant_uses: Iterable[str],
    sqft_per_acre: float = 43_560.0,
) -> pd.DataFrame:
    """A dwelling-card roll summary (one row per parcel, indexed by parcel ID: `dwelling_cards`,
    `dwelling_units`, `acres`, `luc`, `jurisdiction_geoid`; e.g. `franklin_roll_diff.summarize`) → the roll
    interface `diff_rolls_24` reads.

    - `buildings` = dwelling cards, `units` = dwelling units, `lot_sqft` = acres × 43,560.
    - A parcel with **no** dwelling card is vacant (0 buildings, 0 units) only if its land-use code is in
      `vacant_uses` (residential vacant land); otherwise both are NA, so a commercial or exempt parcel with no
      dwelling is never in the denominator.

    By hand: (1 card, 1 unit, LUC 510) → single; (0 cards, LUC 500, vacant use) → vacant; (0 cards, LUC 400)
    → NA; (1 card, 2 units) → one 2-unit building; 0.5 acres → 21,780 sq ft."""
    refuse_never_read(summary.reset_index(names="parcel_id"), "roll_from_cards")
    cards = pd.to_numeric(summary["dwelling_cards"]).astype("Float64")
    units = pd.to_numeric(summary["dwelling_units"]).astype("Float64")
    none = (cards == 0).fillna(False).astype(bool)
    vacant = none & summary["luc"].astype("string").isin(list(vacant_uses)).fillna(False).astype(bool)
    cards = cards.mask(none & ~vacant)
    units = units.mask(none & ~vacant)
    out = pd.DataFrame(
        {
            "jurisdiction_geoid": summary["jurisdiction_geoid"].astype("string"),
            "units": units,
            "buildings": cards,
            "lot_sqft": pd.to_numeric(summary["acres"]).astype("Float64") * sqft_per_acre,
        },
        index=pd.Index(summary.index.astype("string"), name="parcel_id"),
    )
    return out


def _check_roll(roll: pd.DataFrame, what: str) -> None:
    missing = [c for c in ROLL_COLUMNS if c not in roll]
    if missing:
        raise ValueError(f"{what}: roll is missing {missing}")
    refuse_never_read(roll.reset_index().rename(columns={roll.index.name or "index": "parcel_id"}), what)


def diff_rolls_24(
    before: pd.DataFrame, after: pd.DataFrame, *, merge_growth: float | None = None
) -> pd.DataFrame:
    """Test B rule (D-082 §2): one row per roll-1 lot that was a **single dwelling** (one dwelling building
    with one unit) or **vacant** (no dwelling building, no units).

    Groups, in order of precedence:
    - `split`: the parcel ID is not on roll 2 (retired). Reported, not counted.
    - `merge`: lot area on roll 2 is more than `merge_growth` (20%) above roll 1. Reported, not counted,
      whether or not the lot also looks like a gain (`gained_raw` says).
    - `gained_24`: on roll 2 the lot holds one dwelling building with 2–4 units.
    - `none`: anything else.

    `before` / `after` follow the roll interface (`roll_from_parcels`): indexed by parcel ID, with
    `jurisdiction_geoid`, `units`, `buildings`, `lot_sqft`. Both must have come through `blind`.
    Lots with unknown lot area on either roll cannot be screened for merges and are not called merges.
    """
    _check_roll(before, "diff_rolls_24 (roll 1)")
    _check_roll(after, "diff_rolls_24 (roll 2)")
    growth = _p("mm_roll_merge_growth") if merge_growth is None else merge_growth
    lo, hi = _p("mm_collapse_min_units"), _p("mm_collapse_max_units")
    bu, bb = before["units"].astype("Float64"), before["buildings"].astype("Float64")
    single = ((bb == 1) & (bu == 1)).fillna(False).astype(bool)
    vacant = ((bb == 0) & (bu == 0)).fillna(False).astype(bool)
    base = before.loc[single | vacant]
    a = after.reindex(base.index)
    retired = ~base.index.isin(after.index)
    au, ab = a["units"].astype("Float64"), a["buildings"].astype("Float64")
    gained = ((ab == 1) & (au >= lo) & (au <= hi)).fillna(False).astype(bool).values
    grew = (
        (a["lot_sqft"].astype("Float64") > base["lot_sqft"].astype("Float64") * (1 + growth))
        .fillna(False)
        .astype(bool)
        .values
    )
    group = pd.Series("none", index=base.index, dtype="object")
    group[gained] = "gained_24"
    group[grew] = "merge"
    group[retired] = "split"
    out = pd.DataFrame(index=base.index)
    out["jurisdiction_geoid"] = base["jurisdiction_geoid"]
    out["start"] = pd.Series(single.loc[base.index].map({True: "single", False: "vacant"}), index=base.index)
    out["group"] = group
    out["gained_raw"] = gained & ~retired
    out["counted"] = out["group"].isin(["gained_24", "none"])
    out["gained"] = out["group"] == "gained_24"
    return out


def roll_diff_summary(diff: pd.DataFrame, by: str = "jurisdiction_geoid", z: float = 1.96) -> pd.DataFrame:
    """Per `by`: roll-1 lots, each group, merges that looked like gains, counted lots (not split, not merged),
    gains and the gain share of counted lots with a 95% Wilson interval."""
    rows = []
    for key, d in diff.groupby(by, sort=True):
        n = int(d["counted"].sum())
        k = int(d["gained"].sum())
        lo, hi = wilson(k, n, z)
        rows.append(
            {
                by: key,
                "lots": int(len(d)),
                "single": int((d["start"] == "single").sum()),
                "vacant": int((d["start"] == "vacant").sum()),
                **{g: int((d["group"] == g).sum()) for g in ROLL_GROUPS},
                "merge_looked_gained": int(((d["group"] == "merge") & d["gained_raw"]).sum()),
                "counted": n,
                "share": k / n if n else math.nan,
                "share_lo": lo,
                "share_hi": hi,
            }
        )
    return pd.DataFrame(rows)
