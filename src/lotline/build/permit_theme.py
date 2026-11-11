"""One theme per permit row: `adu`, `mm_2_4`, `conversion` or `other` (D-082 §6).

Why. The ADU fit counts ADU permits; the missing-middle outcome counts 2-4 unit buildings. Without one shared
rule the same permit can land in both: Austin files post-HOME second homes as two-family (R-103) permits,
which BPS counts as 2-unit buildings (`docs/research/lotline-causal-diagram-mm.md` §6.6), and Rochester files
a new house with an attached ADU as code 103 (`reports/mn/adu-coverage-and-undercount.md` §4.1). This module
gives every processed permit row (`schemas.Permits`) exactly one theme, so no permit is counted under two.

It is a pure function of the row (and, for the Austin rule, of the row's source and issue date). It reads no
data and is not yet wired into the ADU or MM counts; the wiring is a `contract-change` issue for WS-CORE.

Precedence (the first rule that matches decides; the order is the method):

1. `demolition`: `is_demolition` is True → `other`. A demolition never adds a home, whatever its type.
2. `legalized_adu`: the row is an ADU (rule 4's signal) but adds no new home (`units_new` == 0), or an
   optional `is_legalization` column is True → `other`. D-080 item 2: a permit that legalizes a unit already
   built is not new production; the formalization share (A12) already covers it. `is_legalization` is not in
   the schema today; it is for adapters (Rochester, Minneapolis) that keep a legalized ADU as a new unit.
3. `no_new_home`: `units_new` == 0 → `other`. Alterations, additions and accessory structures add no home.
4. `adu_signal`: `building_type_std` == "ADU" or `adu_type` is set (the same test as
   `model.scenarios.adu._is_adu`) → `adu`. **ADU over conversion:** a garage or basement converted into an ADU
   is an ADU, as the ADU fit counts it today. **ADU over 2-unit class:** a U2 row whose source names an ADU
   (`adu_type` set) is an ADU, not a duplex.
5. Source rules (`SOURCE_RULES`), for sources whose filing practice puts ADUs in a 2-unit class:
   - `austin_home_two_unit`: Austin (`austin_permits`), a U2 row (R-103) issued on or after HOME phase 1
     (2024-02-05) whose description names the HOME "TWO UNIT RES" use (`reform_flag_raw`) and that adds one
     home (`units_new` 1 or unknown) → `adu`. HOME removed the secondary-apartment use, so second homes on an
     existing lot moved from the ADU class (R-102) to two-family (§6.6). A TWO UNIT RES permit adding 2 homes
     builds both units at once: a duplex, left to rule 7.
   Rochester needs no rule here: its adapter already splits a 103 "SFD with attached ADU" into a house row
   (SFD → `other`) and an ADU row (`-ADU` → `adu`, rule 4).
6. `conversion`: `is_conversion` is True and the row adds homes → `conversion` (e.g. a house converted to a
   triplex, Austin class 436). Conversions come before new buildings, because a converted building is not a
   new 2-4 unit building even when its result is typed U2 or U3_4.
7. `new_2_4`: `building_type_std` in `MM_TYPES` (U2, U3_4, DTQ, as `model.estimate_mm.MM_TYPES`) → `mm_2_4`.
8. `other_type`: everything else (SFD, TH, U5_6, U7P, MF5, OTHER, UNKNOWN) → `other`. Townhouses and 5-6 unit
   buildings stay `other` here; D-082 §3's ratios select them by `building_type_std`, not by theme.

`units_new` that is missing (null) never stops a row from matching rules 4-7: a typed new building with an
unknown unit count is still that building.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "ADU",
    "CONVERSION",
    "MM_2_4",
    "OTHER",
    "THEMES",
    "MM_TYPES",
    "RULES",
    "SOURCE_RULES",
    "AUSTIN_HOME_START",
    "classify",
    "permit_theme",
]

ADU, MM_2_4, CONVERSION, OTHER = "adu", "mm_2_4", "conversion", "other"
THEMES = (ADU, MM_2_4, CONVERSION, OTHER)

# Same as model.estimate_mm.MM_TYPES; repeated here so build/ does not import the model layer.
MM_TYPES = ("U2", "U3_4", "DTQ")

# Every rule, in precedence order, with the theme it gives.
RULES: tuple[tuple[str, str], ...] = (
    ("demolition", OTHER),
    ("legalized_adu", OTHER),
    ("no_new_home", OTHER),
    ("adu_signal", ADU),
    ("austin_home_two_unit", ADU),
    ("conversion", CONVERSION),
    ("new_2_4", MM_2_4),
    ("other_type", OTHER),
)
SOURCE_RULES = ("austin_home_two_unit",)

AUSTIN_SOURCE = "austin_permits"
# HOME phase 1: applications from 2024-02-05 (causal diagram §6.6); no HOME permit is issued earlier.
AUSTIN_HOME_START = pd.Timestamp("2024-02-05")
AUSTIN_TWO_UNIT = "TWO UNIT RES"


def _col(df: pd.DataFrame, name: str, default=pd.NA) -> pd.Series:
    return df[name] if name in df else pd.Series(default, index=df.index, dtype="object")


def _true(s: pd.Series) -> pd.Series:
    """True where the value is True; null and False are False."""
    return s.astype("boolean").fillna(False).astype(bool)


def _issued(df: pd.DataFrame) -> pd.Series:
    """Issue date, falling back to 1 January of `issue_year` where only the year is known (so a year-only row
    in the HOME year counts as before HOME: the conservative side for the ADU count)."""
    date = pd.to_datetime(_col(df, "issue_date"), errors="coerce")
    year = pd.to_numeric(_col(df, "issue_year"), errors="coerce")
    jan1 = pd.to_datetime(year.astype("Int64").astype("string") + "-01-01", errors="coerce")
    return date.fillna(jan1)


def _masks(df: pd.DataFrame, source_rules: tuple[str, ...]) -> dict[str, pd.Series]:
    btype = _col(df, "building_type_std").astype("string")
    units = pd.to_numeric(_col(df, "units_new"), errors="coerce")
    adds_none = units.eq(0).fillna(False).astype(bool)
    adds = ~adds_none  # one or more, or unknown
    is_adu = btype.eq("ADU").fillna(False).astype(bool) | _col(df, "adu_type").notna()
    flag = _col(df, "reform_flag_raw").astype("string").str.strip().str.upper()
    source = _col(df, "source").astype("string")

    austin = (
        source.eq(AUSTIN_SOURCE).fillna(False).astype(bool)
        & btype.eq("U2").fillna(False).astype(bool)
        & flag.eq(AUSTIN_TWO_UNIT).fillna(False).astype(bool)
        & (_issued(df) >= AUSTIN_HOME_START).fillna(False).astype(bool)
        & (units.isna() | units.eq(1).fillna(False).astype(bool))
    )
    off = pd.Series(False, index=df.index)
    return {
        "demolition": _true(_col(df, "is_demolition")),
        "legalized_adu": (is_adu & adds_none) | _true(_col(df, "is_legalization")),
        "no_new_home": adds_none,
        "adu_signal": is_adu,
        "austin_home_two_unit": austin if "austin_home_two_unit" in source_rules else off,
        "conversion": _true(_col(df, "is_conversion")) & adds,
        "new_2_4": btype.isin(MM_TYPES).fillna(False).astype(bool),
        "other_type": pd.Series(True, index=df.index),
    }


def classify(permits: pd.DataFrame, source_rules: tuple[str, ...] = SOURCE_RULES) -> pd.DataFrame:
    """`permit_theme` and `theme_rule` for every row of a processed permits table (same index).

    `source_rules` names the source-specific rules to apply; pass `()` to see what the generic rules alone
    give (a sensitivity, and a check on how much a source rule moves). Optional input columns: `adu_type`,
    `reform_flag_raw`, `is_legalization`; missing ones are read as null.
    """
    unknown = set(source_rules) - set(SOURCE_RULES)
    if unknown:
        raise ValueError(f"unknown source rules: {sorted(unknown)}")
    masks = _masks(permits, tuple(source_rules))
    names = [name for name, _ in RULES]
    conds = [masks[name].to_numpy(dtype=bool) for name in names]
    rule = np.select(conds, names, default="other_type")
    theme = pd.Series(rule, index=permits.index).map(dict(RULES))
    return pd.DataFrame(
        {
            "permit_theme": pd.Categorical(theme, categories=list(THEMES)),
            "theme_rule": pd.Series(rule, index=permits.index, dtype="string"),
        },
        index=permits.index,
    )


def permit_theme(permits: pd.DataFrame, source_rules: tuple[str, ...] = SOURCE_RULES) -> pd.Series:
    """The theme alone (`classify(...)["permit_theme"]`)."""
    return classify(permits, source_rules)["permit_theme"]
