"""Second homes added to Franklin County single-family lots between two Auditor rolls (descriptive counts).

Implements the detection rule in `reports/oh/adu-coverage-and-undercount.md` §2.1 (committed before any
count). It mirrors `lotline.adapters.states.nc.wake_roll_diff` for the Franklin County Auditor's appraisal
files and reuses that module's interval helpers (`wilson`, `chapman`, `k_undercount`):

- `summarize`: `Dwelling.xlsx` rows (one per dwelling card) and `Parcel.xlsx` rows of one roll → one row per
  parcel number: dwelling cards (living area above 0), their units, card 1's year built and living area,
  the newest year built among the other cards, the land-use code and acreage.
- `classify` / `diff_rolls`: one row per earlier-roll single-family parcel (LUC → `SF_DETACHED`, one
  dwelling card, one unit) with its group: `new_card_new`, `new_card_old`, `unit_change`, `rebuild`, `merge`
  or `none`.
- `new_garages`: parcels with a detached-garage improvement on the later roll built in the window and absent
  from the earlier roll (the envelope; never counted).
- `undercount`: the D-074 quantities (|P∩R|, groups (a) and (b), |P\\R|, k, Chapman) from parcel sets.

No data is read here: `scripts/dev/oh_franklin_roll_adu_diff.py` reads the registered files.
"""

from __future__ import annotations

import pandas as pd

from lotline.adapters.states.nc.wake_roll_diff import chapman, k_undercount, wilson

__all__ = ["chapman", "k_undercount", "wilson"]

SINGLE_FAMILY_LUC = "510"
TWO_FAMILY_LUC = "520"
MERGE_ACRE_GROWTH = 0.20
ADDED_AREA = 200  # sq ft of added living area on card 1 (envelope only)
GARAGE_CODES = ("RG1", "RG2", "RG3", "RG4")  # detached garages (frame, block, masonry, metal)
GAINED_GROUPS = ("new_card_new", "new_card_old", "unit_change", "rebuild")


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def summarize(dwellings: pd.DataFrame, parcels: pd.DataFrame) -> pd.DataFrame:
    """One roll's dwelling cards and parcel rows → one row per parcel number (index)."""
    d = pd.DataFrame(
        {
            "pid": dwellings["PARCEL ID"].astype("string").str.strip(),
            "card": _num(dwellings["CARD"]),
            "units": _num(dwellings["LIVUNITS"]).fillna(1),
            "year": _num(dwellings["YRBLT"]).fillna(0),
            "sfla": _num(dwellings["SFLA"]).fillna(0),
        }
    )
    d = d.loc[d["pid"].notna() & (d["sfla"] > 0)].sort_values(["pid", "card"])
    main = d.drop_duplicates("pid", keep="first").set_index("pid")
    extra = d.loc[d.duplicated("pid", keep="first")]
    p = parcels.assign(pid=parcels["PARCEL ID"].astype("string").str.strip()).drop_duplicates("pid")
    p = p.set_index("pid")
    out = pd.DataFrame(index=p.index)
    out["luc"] = p["LUC"].astype("string").str.strip()
    out["acres"] = _num(p["ACRES"])
    out["dwelling_cards"] = d.groupby("pid").size().reindex(out.index, fill_value=0)
    out["dwelling_units"] = d.groupby("pid")["units"].sum().reindex(out.index, fill_value=0)
    out["main_year"] = main["year"].reindex(out.index)
    out["main_sfla"] = main["sfla"].reindex(out.index)
    out["extra_year"] = extra.groupby("pid")["year"].max().reindex(out.index)
    return out


def is_single_family(before: pd.DataFrame, land_use: pd.Series) -> pd.Series:
    """Denominator: SF_DETACHED land use, one dwelling card, one unit (earlier roll)."""
    lu = land_use.reindex(before.index)
    return (lu == "SF_DETACHED") & (before["dwelling_cards"] == 1) & (before["dwelling_units"] == 1)


def classify(b: pd.DataFrame, a: pd.DataFrame, first_new_year: int) -> pd.Series:
    """Group of each single-family parcel (rows aligned: `b` earlier roll, `a` later roll)."""
    two_cards = a["dwelling_cards"] >= 2
    unit_up = (a["dwelling_units"] >= 2) | ((b["luc"] == SINGLE_FAMILY_LUC) & (a["luc"] == TWO_FAMILY_LUC))
    gained = two_cards | unit_up
    rebuilt = (a["main_year"] >= first_new_year) & (b["main_year"] < first_new_year)
    merged = (a["acres"] > b["acres"] * (1 + MERGE_ACRE_GROWTH)).fillna(False)
    group = pd.Series("none", index=b.index, dtype="object")
    group[gained & ~two_cards & ~rebuilt] = "unit_change"
    group[two_cards & ~rebuilt & (a["extra_year"] < first_new_year)] = "new_card_old"
    group[two_cards & ~rebuilt & (a["extra_year"] >= first_new_year)] = "new_card_new"
    group[gained & rebuilt] = "rebuild"
    group[gained & merged] = "merge"
    return group


def diff_rolls(
    before: pd.DataFrame,
    after: pd.DataFrame,
    land_use: pd.Series,
    jurisdiction: pd.Series,
    first_new_year: int,
) -> pd.DataFrame:
    """One row per earlier-roll single-family parcel present in both rolls."""
    sf = before.loc[is_single_family(before, land_use)]
    both = sf.index.intersection(after.index)
    b, a = sf.loc[both], after.loc[both]
    out = pd.DataFrame(index=both)
    out["jurisdiction_geoid"] = jurisdiction.reindex(both)
    out["group"] = classify(b, a, first_new_year)
    out["gained"] = out["group"].isin(GAINED_GROUPS)
    out["strict"] = out["group"] == "new_card_new"
    out["added_area"] = (a["main_sfla"] - b["main_sfla"] >= ADDED_AREA) & (a["main_year"] == b["main_year"])
    out.attrs["sf_before"] = int(len(sf))
    out.attrs["sf_dropped"] = int(len(sf) - len(both))
    return out


def new_garages(
    before_imp: pd.DataFrame, after_imp: pd.DataFrame, first_new_year: int, last_year: int
) -> pd.Index:
    """Parcels whose later roll has a detached garage built in [first_new_year, last_year] that the earlier
    roll lacks (same parcel, code family and year). The envelope only: most new garages are just garages."""

    def garages(imp: pd.DataFrame) -> pd.DataFrame:
        g = pd.DataFrame(
            {
                "pid": imp["PARCEL ID"].astype("string").str.strip(),
                "code": imp["CODE"].astype("string").str[:3],
                "year": _num(imp["YRBLT"]),
            }
        )
        return g.loc[g["code"].isin(GARAGE_CODES)]

    a, b = garages(after_imp), garages(before_imp)
    a = a.loc[a["year"].between(first_new_year, last_year)]
    old = set(zip(b["pid"], b["year"], strict=True))
    return pd.Index(sorted({p for p, y in zip(a["pid"], a["year"], strict=True) if (p, y) not in old}))


def undercount(
    roll: set[str], flagged: set[str], denominator: set[str], unflagged: set[str]
) -> dict[str, float | int]:
    """D-074 step 1 from parcel sets.

    `roll` R: denominator parcels the roll flags. `flagged` P: parcels of ADU-flagged permits in the window.
    `denominator`: the earlier roll's single-family parcels. `unflagged`: parcels with a non-flagged
    new-structure dwelling permit in the window (group (a) where they fall in R \\ P)."""
    both = roll & flagged
    rest = roll - flagged
    a = rest & unflagged
    p_in = flagged & denominator
    k, lo, hi = k_undercount(len(both), len(a))
    n, n_lo, n_hi = chapman(len(roll), len(p_in), len(both)) if roll and p_in else (float("nan"),) * 3
    return {
        "R": len(roll),
        "P": len(flagged),
        "P_in_denominator": len(p_in),
        "P_and_R": len(both),
        "a": len(a),
        "b": len(rest - a),
        "P_not_R": len(flagged - roll),
        "P_not_R_in_denominator": len(p_in - roll),
        "k": k,
        "k_lo90": lo,
        "k_hi90": hi,
        "chapman": n,
        "chapman_lo95": n_lo,
        "chapman_hi95": n_hi,
    }
