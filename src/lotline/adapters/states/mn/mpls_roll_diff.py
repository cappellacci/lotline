"""ADUs added to Minneapolis single-family lots between two assessor rolls, and the permit undercount k.

Implements the detection rule in `reports/mn/adu-coverage-and-undercount.md` §2 (committed in 9e4b5390 before
any count), D-074 step 1 for Minnesota:

- `summarize_roll`: building rows of one assessor table (canonical names: `pin`, `building_use`, `units`,
  `year_built`, `area_sqft`) → one row per `parcel_id` with whether any building carries an ADU label, whether
  the parcel is a duplex, its units, earliest year built and lot area.
- `diff_rolls`: two summaries + the earlier roll's `land_use_std` → one row per earlier-roll single-family
  parcel with its group (`adu_added`, `rebuild`, `duplex_adu`, `merge`, `duplex_only`, `none`).
- `permit_parcels`: the CCS permit rows → parcel sets P (ADU-typed, in the window) and the group-(a)
  candidates for each version of the rule (as written, duplexes removed, wide).
- `undercount`: |P∩R|, (a), (b), P \\ R, k with its 90% interval and the Chapman total.

The interval and capture–recapture formulas are NC's (`lotline.adapters.states.nc.wake_roll_diff`),
reused, not copied. No data is read here: `scripts/dev/mn_mpls_roll_adu_diff.py` reads the rolls and
permits through `DataStore` and `holdout.apply`.
"""

from __future__ import annotations

import pandas as pd

from lotline.adapters.states.nc.wake_roll_diff import chapman, k_undercount

HENNEPIN = "27053"
FIRST_NEW_YEAR = 2017  # the earlier roll's year: a main building built in or after it replaced the house
MERGE_AREA_GROWTH = 0.20
ADU_LABELS = frozenset(
    {
        "R WITH ACCESSORY DWELLING",
        "M WITH ACCESSORY DWELLING",
        "SF HOUSE W/ADU",
        "DUPLEX W/ADU",
        "DETACHED ADU",
    }
)
DUPLEX_ADU = "DUPLEX W/ADU"
IN_R = ("adu_added", "rebuild", "duplex_adu")
GROUP_LABELS = {
    "adu_added": "ADU added (strict)",
    "rebuild": "Rebuild with an ADU",
    "duplex_adu": "Duplex with an ADU",
    "merge": "Possible merge (not counted)",
    "duplex_only": "Duplex, no ADU (not in R)",
    "none": "No ADU",
}
NEW_RES_OCCUPANCY = {"SFD", "TFD", "TH"}
DUPLEX_OCCUPANCY = {"TFD"}
WIDE_WORK = {"Accessory", "Conversion", "UnitCon"}
CANCELLED = {"Cancelled", "Void", "Withdrawn", "Denied", "Expired"}


def _text(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip().str.upper().str.replace(r"\s+", " ", regex=True)


def parcel_id(pin: pd.Series) -> pd.Series:
    """Raw PIN (`p0102924...`, punctuation) → `27053` + 13 digits; else missing (the adapter's key)."""
    digits = pin.astype("string").str.upper().str.replace(r"[^0-9]", "", regex=True)
    return (HENNEPIN + digits).where(digits.str.fullmatch(r"\d{13}").fillna(False)).astype("string")


def summarize_roll(rows: pd.DataFrame) -> pd.DataFrame:
    """Building rows of one table → one row per parcel, indexed by `parcel_id`."""
    use = _text(rows["building_use"]).fillna("")
    df = pd.DataFrame(
        {
            "parcel_id": parcel_id(rows["pin"]),
            "use": use,
            "adu": use.isin(ADU_LABELS),
            "duplex_adu": use == DUPLEX_ADU,
            "duplex_label": use.str.startswith("DUPLEX") & (use != DUPLEX_ADU),
            "units": pd.to_numeric(rows["units"], errors="coerce"),
            "year": pd.to_numeric(rows["year_built"], errors="coerce"),
            "area": pd.to_numeric(rows["area_sqft"], errors="coerce"),
        }
    )
    df = df[df["parcel_id"].notna()]
    g = df.groupby("parcel_id")
    out = pd.DataFrame(
        {
            "adu": g["adu"].any(),
            "duplex_adu": g["duplex_adu"].any(),
            "duplex_label": g["duplex_label"].any(),
            "units": g["units"].sum(min_count=1),
            "year_built": g["year"].min(),
            "area": g["area"].max(),
            "buildings": g.size(),
        }
    )
    out["use"] = g["use"].first()  # first listed building (2017-2024: the only one)
    return out


def is_single_family(before: pd.DataFrame, land_use: pd.Series) -> pd.Series:
    """Denominator: SF_DETACHED, no ADU label, TOTAL_UNITS = 1 (all on the earlier roll)."""
    lu = land_use.reindex(before.index)
    return (lu == "SF_DETACHED") & ~before["adu"] & (before["units"] == 1)


def classify(b: pd.DataFrame, a: pd.DataFrame) -> pd.Series:
    """Group of each single-family parcel (rows aligned: `b` earlier roll, `a` later roll)."""
    rebuilt = (a["year_built"] >= FIRST_NEW_YEAR) & (b["year_built"] < FIRST_NEW_YEAR)
    merged = (a["area"] > b["area"] * (1 + MERGE_AREA_GROWTH)).fillna(False)
    duplex = a["duplex_label"] | (a["units"] >= 2).fillna(False)
    group = pd.Series("none", index=b.index, dtype="object")
    group[~a["adu"] & duplex] = "duplex_only"
    group[a["adu"]] = "adu_added"
    group[a["adu"] & rebuilt.fillna(False)] = "rebuild"
    group[a["duplex_adu"]] = "duplex_adu"
    group[a["adu"] & merged] = "merge"  # set aside whatever else it looked like
    return group


def diff_rolls(before: pd.DataFrame, after: pd.DataFrame, land_use: pd.Series) -> pd.DataFrame:
    """One row per earlier-roll single-family parcel that is on both rolls, with its group and `in_r`."""
    sf = before.loc[is_single_family(before, land_use)]
    both = sf.index.intersection(after.index)
    out = pd.DataFrame(index=both)
    out["group"] = classify(sf.loc[both], after.loc[both])
    out["in_r"] = out["group"].isin(IN_R)
    out["strict"] = out["group"] == "adu_added"
    out.attrs["sf_before"] = int(len(sf))
    out.attrs["sf_before_dropped"] = int(len(sf) - len(both))
    return out


def _class_parts(raw: pd.Series) -> pd.DataFrame:
    """`permit_class_raw` `Res:SFD:New:Closed` → permit type, occupancy, work type, status."""
    parts = raw.astype("string").str.split(":", n=3, expand=True).reindex(columns=range(4))
    parts.columns = ["ptype", "occupancy", "work", "status"]
    return parts


def permit_parcels(permits: pd.DataFrame, start: str, end: str) -> dict[str, set[str]]:
    """Parcel sets from CCS permit rows (one row per permit; `-ADU` rows count as ADU-typed).

    `P`: ADU-typed, issued in [start, end]; `P_outside`: ADU-typed, issued outside it; `P_live`: P without
    cancelled/expired/void/withdrawn/denied permits. Group-(a) candidates, non-ADU permits in the window:
    `a_written` (work New on SFD/TFD/TH, or units_new >= 1; never Wrecking), `a_noduplex` (`a_written` without
    TFD or units_new >= 2), `a_wide` (`a_noduplex` plus Accessory/Conversion/UnitCon work and new accessory
    buildings), `seen_by_parser` (any non-ADU permit whose work type the parser reads)."""
    from lotline.adapters.states.mn.mpls_permits import ADU_WORK

    p = permits[permits["parcel_id"].notna()].copy()
    parts = _class_parts(p["permit_class_raw"])
    p = pd.concat([p, parts.set_index(p.index)], axis=1)
    when = pd.to_datetime(p["issue_date"])
    in_window = (when >= pd.Timestamp(start)) & (when <= pd.Timestamp(end))
    is_adu = p["building_type_std"] == "ADU"
    units = pd.to_numeric(p["units_new"], errors="coerce").fillna(0)
    not_wreck = p["ptype"] != "Wrecking"
    new_res = (p["work"] == "New") & p["occupancy"].isin(NEW_RES_OCCUPANCY)
    written = not_wreck & (new_res | (units >= 1))
    duplex = p["occupancy"].isin(DUPLEX_OCCUPANCY) | (units >= 2)
    wide_extra = not_wreck & (
        p["work"].isin(WIDE_WORK) | ((p["occupancy"] == "Accessory") & (p["work"] == "New"))
    )
    other = in_window & ~is_adu

    def ids(mask: pd.Series) -> set[str]:
        return set(p.loc[mask, "parcel_id"].astype(str))

    return {
        "P": ids(in_window & is_adu),
        "P_outside": ids(~in_window & is_adu),
        "P_live": ids(in_window & is_adu & ~p["status"].isin(CANCELLED)),
        "a_written": ids(other & written),
        "a_noduplex": ids(other & written & ~duplex),
        "a_wide": ids(other & ((written & ~duplex) | wide_extra)),
        "seen_by_parser": ids(other & not_wreck & p["work"].isin(ADU_WORK)),
    }


def undercount(r: set[str], p: set[str], a_candidates: set[str], denominator: set[str]) -> dict[str, float]:
    """D-074 step 1 quantities for one version: R, P (all, and on denominator parcels), |P∩R|, (a), (b),
    P \\ R, k (90%) and the Chapman total (95%) with P limited to denominator parcels."""
    both = r & p
    rest = r - p
    a = rest & a_candidates
    p_in = p & denominator
    k, k_lo, k_hi = k_undercount(len(both), len(a))
    n, n_lo, n_hi = chapman(len(r), len(p_in), len(both))
    return {
        "R": len(r),
        "P": len(p),
        "P_in_denominator": len(p_in),
        "P_and_R": len(both),
        "a": len(a),
        "b": len(rest - a),
        "P_not_R": len(p - r),
        "P_not_R_in_denominator": len(p_in - r),
        "P_not_R_outside": len(p - denominator),
        "k": k,
        "k_lo90": k_lo,
        "k_hi90": k_hi,
        "chapman": n,
        "chapman_lo95": n_lo,
        "chapman_hi95": n_hi,
        "chapman_over_P": n / len(p_in) if p_in else float("nan"),
    }
