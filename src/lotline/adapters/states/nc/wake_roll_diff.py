"""Second homes added to Wake County single-family lots between two real estate rolls (descriptive counts).

Implements the detection rule in `reports/nc/wake-roll-adu-diff.md` §1 (committed before any count):

- `summarize_cards`: card rows of one roll → one row per `REAL_ESTATE_ID` with the number of **dwelling
  cards** (Type & Use 01/02/03/04/72 with heated area above 0), their units, card 01's Type & Use and year
  built, the newest year built among the other dwelling cards, deeded acreage and the 10-digit PIN.
- `diff_rolls`: two summaries (same REID in both) → one row per **2019 single-family parcel** (land use
  `SF_DETACHED`, one dwelling card with one unit) with its group: `new_card_new`, `new_card_old`,
  `unit_change`, `rebuild`, `merge` or `none`. `gained` is True for the first four (the headline count);
  `strict` for `new_card_new` alone.
- `rates`: counts and rates per 1,000 parcels a year by jurisdiction, with a 95% Wilson interval.
- `match_permits`, `flag_share` and `chapman`: the Raleigh undercount check (both / roll only / permits only,
  the flagged share of roll finds, and a capture–recapture total).

No data is read here: callers pass the card rows (`scripts/dev/nc_wake_roll_adu_diff.py` reads them from the
registered rolls through `DataStore`).
"""

from __future__ import annotations

import math

import pandas as pd

DWELLING_USES = frozenset({"01", "02", "03", "04", "72"})  # one/two/three/four family, mobile home
TWO_FAMILY = "02"
FIRST_NEW_YEAR = 2019  # a card built in or after the 2019 roll's year counts as newly built
MERGE_ACRE_GROWTH = 0.20  # acreage up by more than 20% → possible merge, set aside
GAINED_GROUPS = ("new_card_new", "new_card_old", "unit_change", "rebuild")
GROUP_LABELS = {
    "new_card_new": "New card, built 2019 or later",
    "new_card_old": "New card, older building",
    "unit_change": "Unit or use change",
    "rebuild": "Teardown and rebuild with two homes",
    "merge": "Possible merge (not counted)",
    "none": "No second home",
}


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def pin10(pin: pd.Series) -> pd.Series:
    """Roll PIN `1714.09 05 9993 000` → Raleigh's 10-digit `1714059993` (map, block, lot); else missing."""
    parts = pin.astype("string").str.extract(r"^\s*(\d{4})\.\d{2}\s+(\d{2})\s+(\d{4})")
    return (parts[0] + parts[1] + parts[2]).astype("string")


def summarize_cards(cards: pd.DataFrame) -> pd.DataFrame:
    """Card rows (text columns as in the roll) → one row per REID, indexed by REID."""
    df = pd.DataFrame(
        {
            "reid": cards["REAL_ESTATE_ID"].astype("string").str.strip(),
            "card": _num(cards["CARD_NUMBER"]),
            "use": cards["TYPE_AND_USE"].astype("string").str.strip(),
            "units": _num(cards["UNITS"]).fillna(0),
            "heated": _num(cards["HEATED_AREA"]).fillna(0),
            "year": _num(cards["Year_Built"]).fillna(0),
            "acres": _num(cards["Deeded_Acreage"]),
            "pin": cards["Parcel_Identification"],
        }
    )
    df = df.loc[df["reid"].notna() & (df["reid"] != "")].sort_values(["reid", "card"])
    df["dwelling"] = df["use"].isin(DWELLING_USES) & (df["heated"] > 0)
    main = df.drop_duplicates("reid", keep="first").set_index("reid")  # card 01 (lowest number)
    dw = df.loc[df["dwelling"]]
    extra = dw.loc[dw.duplicated("reid", keep="first")]  # dwelling cards after the first one
    out = pd.DataFrame(index=main.index)
    out["dwelling_cards"] = dw.groupby("reid").size().reindex(out.index, fill_value=0)
    out["dwelling_units"] = dw.groupby("reid")["units"].sum().reindex(out.index, fill_value=0)
    out["main_use"] = main["use"]
    out["main_year"] = main["year"]
    out["extra_year"] = extra.groupby("reid")["year"].max().reindex(out.index)
    out["acres"] = main["acres"]
    out["pin10"] = pin10(main["pin"])
    return out


def is_single_family(before: pd.DataFrame, land_use: pd.Series) -> pd.Series:
    """Denominator: SF_DETACHED land use, exactly one dwelling card, one unit (all in the earlier roll)."""
    lu = land_use.reindex(before.index)
    return (lu == "SF_DETACHED") & (before["dwelling_cards"] == 1) & (before["dwelling_units"] == 1)


def classify(b: pd.DataFrame, a: pd.DataFrame) -> pd.Series:
    """Group of each single-family parcel (rows aligned: `b` earlier roll, `a` later roll)."""
    two_cards = a["dwelling_cards"] >= 2
    unit_up = (a["dwelling_units"] >= 2) | ((b["main_use"] == "01") & (a["main_use"] == TWO_FAMILY))
    gained = two_cards | unit_up
    rebuilt = (a["main_year"] >= FIRST_NEW_YEAR) & (b["main_year"] < FIRST_NEW_YEAR)
    merged = a["acres"] > b["acres"] * (1 + MERGE_ACRE_GROWTH)
    group = pd.Series("none", index=b.index, dtype="object")
    group[gained & ~two_cards & ~rebuilt] = "unit_change"
    group[two_cards & ~rebuilt & (a["extra_year"] < FIRST_NEW_YEAR)] = "new_card_old"
    group[two_cards & ~rebuilt & (a["extra_year"] >= FIRST_NEW_YEAR)] = "new_card_new"
    group[gained & rebuilt] = "rebuild"
    group[gained & merged.fillna(False)] = "merge"  # set aside whatever else it looked like
    return group


def diff_rolls(
    before: pd.DataFrame,
    after: pd.DataFrame,
    land_use: pd.Series,
    jurisdiction: pd.Series,
) -> pd.DataFrame:
    """One row per earlier-roll single-family parcel whose REID is in both rolls.

    `land_use` and `jurisdiction` are indexed by REID and describe the earlier roll."""
    sf = before.loc[is_single_family(before, land_use)]
    both = sf.index.intersection(after.index)
    b, a = sf.loc[both], after.loc[both]
    out = pd.DataFrame(index=both)
    out["jurisdiction_geoid"] = jurisdiction.reindex(both)
    out["pin10"] = b["pin10"]
    out["group"] = classify(b, a)
    out["gained"] = out["group"].isin(GAINED_GROUPS)
    out["strict"] = out["group"] == "new_card_new"
    out["extra_year"] = a["extra_year"]
    out.attrs["sf_2019"] = int(len(sf))
    out.attrs["sf_2019_dropped"] = int(len(sf) - len(both))  # REID gone by the later roll
    return out


def vacant_two_homes(before: pd.DataFrame, after: pd.DataFrame, land_use: pd.Series) -> pd.Index:
    """REIDs vacant in the earlier roll with two or more dwelling cards in the later one (not in the rate)."""
    vac = land_use.reindex(before.index) == "VACANT_RESIDENTIAL"
    ids = before.index[vac].intersection(after.index)
    return ids[after.loc[ids, "dwelling_cards"] >= 2]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion k/n."""
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def rates(diff: pd.DataFrame, years: float, by: str = "jurisdiction_geoid") -> pd.DataFrame:
    """Per group of `by`: parcels, gains (headline, strict, each group) and rate per 1,000 a year."""
    g = diff.groupby(by)
    out = pd.DataFrame({"sf_parcels": g.size(), "gained": g["gained"].sum(), "strict": g["strict"].sum()})
    for grp in (*GAINED_GROUPS, "merge"):
        out[grp] = g["group"].apply(lambda s, grp=grp: int((s == grp).sum()))
    per = 1000 / years
    out["rate"] = out["gained"] / out["sf_parcels"] * per
    out["rate_strict"] = out["strict"] / out["sf_parcels"] * per
    ci = [wilson(int(k), int(n)) for k, n in zip(out["gained"], out["sf_parcels"], strict=True)]
    out["rate_lo"] = [lo * per for lo, _ in ci]
    out["rate_hi"] = [hi * per for _, hi in ci]
    return out


def match_permits(roll_pins: pd.Series, permit_pins: pd.Series, outside_pins: pd.Series) -> dict[str, int]:
    """Roll-flagged parcels vs ADU-flagged permits, by 10-digit PIN.

    `roll_pins`: PINs the roll flags (denominator parcels that gained a second home).
    `permit_pins`: PINs of ADU-flagged permits in the window (one per parcel is counted).
    `outside_pins`: PINs of denominator parcels; a permit PIN not among them is `permits_outside`."""
    roll = set(roll_pins.dropna())
    denom = set(outside_pins.dropna())
    permits = set(permit_pins.dropna())
    inside = permits & denom
    return {
        "both": len(roll & inside),
        "roll_only": len(roll - inside),
        "permits_only": len(inside - roll),
        "permits_outside": len(permits - denom),
        "permits_in_denominator": len(inside),
    }


def chapman(roll: int, permits: int, both: int, z: float = 1.96) -> tuple[float, float, float]:
    """Chapman (bias-corrected Lincoln–Petersen) total and a normal 95% interval: (estimate, lo, hi)."""
    n = (roll + 1) * (permits + 1) / (both + 1) - 1
    var = (roll + 1) * (permits + 1) * (roll - both) * (permits - both) / ((both + 1) ** 2 * (both + 2))
    se = math.sqrt(var)
    seen = roll + permits - both
    return (n, max(seen, n - z * se), n + z * se)


def flag_share(both: int, roll: int) -> tuple[float, float, float]:
    """Share of roll-detected second homes that carry an ADU-flagged permit, with its 95% Wilson interval.

    Its inverse is the number of real (built and carded) ADUs per flagged one."""
    lo, hi = wilson(both, roll)
    return (both / roll if roll else math.nan, lo, hi)


Z90 = 1.6449  # two-sided 90%


def k_undercount(both: int, unflagged: int, z: float = Z90) -> tuple[float, float, float]:
    """D-072 flag undercount k = (|P∩R| + |a|) / |P∩R|, with a binomial (Wilson) 90% interval.

    The interval is the Wilson interval on the flagged share |P∩R| / (|P∩R| + |a|), inverted, so
    k's lower bound is 1 / (upper bound of the share)."""
    n = both + unflagged
    if both == 0:
        return (math.nan, math.nan, math.nan)
    lo, hi = wilson(both, n, z=z)
    return (n / both, 1 / hi, 1 / lo)
