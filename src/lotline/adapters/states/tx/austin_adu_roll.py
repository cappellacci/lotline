"""Austin ADUs from TCAD's improvement records and the city's permits (descriptive counts, no table).

Implements the rules in `reports/tx/adu-coverage-and-undercount.md` §0 (committed before any count):

- `read_improvements`: TCAD `IMP_INFO.TXT` / `IMP_DET.TXT` / `PROP.TXT` in a registered zip → improvement
  rows (prop_id, imprv_id, type code) with their year built, and prop_id → parcel_id. Only the positional
  fields named in `INFO_FIELDS`, `DET_FIELDS` and `tcad_parcels.PROP_FIELDS` are sliced; no owner, address or
  other personal field is read.
- `improvement_years`: segment rows → one year built per improvement (earliest living-floor segment, else
  earliest segment; 1800 to the roll year).
- `classify_parcels`: improvements → one row per parcel with its main house year, whether it is in the
  universe (a pre-2019 main house, no townhome or condo improvement) and the group of its newest second
  dwelling built in a window (`alq`, `house`, `multi`, `moho` or `none`).
- `home_adu`: the HOME rule (§0.5): permits that add a building to a lot whose house stays.
- `match`: R vs P and groups (a)/(b) for k (§0.4); k itself is `nc.wake_roll_diff.k_undercount`.

No data is read except by `read_improvements`; `scripts/dev/tx_austin_adu_k.py` passes the registered zip.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pandas as pd

from lotline.adapters.states.tx import tcad_parcels as tcad

INFO_FIELDS = {"prop_id": (1, 12), "imprv_id": (17, 12), "type_cd": (29, 10)}
DET_FIELDS = {"prop_id": (1, 12), "imprv_id": (17, 12), "det_type": (41, 10), "yr_built": (86, 4)}
PROP_ID_FIELDS = {k: tcad.PROP_FIELDS[k] for k in ("prop_id", "prop_type_cd", "sup_num", "geo_id")}
FILES = {"imp_info": ("IMP_INFO.TXT", "APPRAISAL_IMPROVEMENT_INFO.TXT")}

MAIN = "01"  # 1 FAM DWELLING
ALQ = frozenset({"120", "21"})  # ADDITIONAL LIVING QUARTER, GARAGE APARTMENT
MULTI = frozenset({"02", "03", "04"})  # 2 FAM DWELLING, TRIPLEX, FOURPLEX
MOHO = frozenset({"11", "12", "13", "14"})  # mobile homes (single/double, personal/real)
DWELLING = frozenset({MAIN}) | ALQ | MULTI | MOHO
ATTACHED_OWNERSHIP = frozenset({"15", "16", "22"})  # CONDO (STACKED), TOWNHOMES, HIRISE CONDO/APT
LIVING_SEGMENT = re.compile(r"^(?:[1-5](?:ST|ND|RD|TH)|RSBLW)$")
MIN_YEAR = 1800
UNIVERSE_BEFORE = 2019  # main house built before this year
WINDOW = (2019, 2023)  # second dwelling built in these years (inclusive) → R

HOME_START = pd.Timestamp("2024-02-05")  # HOME phase 1 effective date
HOME_CLASSES = frozenset({"101", "102", "103", "436"})
DEMOLITION_CLASSES = frozenset({"645", "646"})
DEMOLITION_LOOKBACK_YEARS = 3


def _members(zf: zipfile.ZipFile, names: tuple[str, ...]) -> str | None:
    wanted = {n.upper() for n in names}
    return next((n for n in zf.namelist() if Path(n).name.upper() in wanted), None)


def _rows(zf: zipfile.ZipFile, member: str, fields: dict[str, tuple[int, int]]):
    with zf.open(member) as fh:
        for raw in fh:
            line = raw.decode(tcad.ENCODING).rstrip("\r\n")
            if line.strip():
                yield tcad._slice(line, fields)


def read_improvements(path: Path, parcel_ids: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Registered TCAD zip → (improvement segments, improvement types) for real property in `parcel_ids`.

    Segment rows: prop_id, imprv_id, det_type, yr_built (text). Type rows: prop_id, imprv_id, type_cd,
    parcel_id. Properties are kept when "48453" + their geo_id digits is in `parcel_ids`."""
    with zipfile.ZipFile(path) as zf:
        pid: dict[str, tuple[float, str]] = {}
        for r in _rows(zf, tcad._member(zf, "prop"), PROP_ID_FIELDS):
            if r["prop_type_cd"].upper() != "R":
                continue
            parcel = tcad.TRAVIS_FIPS + re.sub(r"\D", "", r["geo_id"])
            sup = float(r["sup_num"] or 0)
            if parcel in parcel_ids and sup >= pid.get(r["prop_id"], (-1.0, ""))[0]:
                pid[r["prop_id"]] = (sup, parcel)
        keep = {p: v[1] for p, v in pid.items()}
        info = [r for r in _rows(zf, _members(zf, FILES["imp_info"]), INFO_FIELDS) if r["prop_id"] in keep]
        det = [r for r in _rows(zf, tcad._member(zf, "imp_det"), DET_FIELDS) if r["prop_id"] in keep]
    types = pd.DataFrame(info, columns=list(INFO_FIELDS)).drop_duplicates(["prop_id", "imprv_id"])
    types["parcel_id"] = types["prop_id"].map(keep)
    return pd.DataFrame(det, columns=list(DET_FIELDS)), types


def improvement_years(det: pd.DataFrame, roll_year: int) -> pd.Series:
    """Segment rows → year built per (prop_id, imprv_id): earliest living-floor year, else earliest year."""
    d = det.assign(year=pd.to_numeric(det["yr_built"], errors="coerce"))
    d = d[d["year"].between(MIN_YEAR, roll_year)]
    living = d["det_type"].astype(str).str.strip().str.upper().str.match(LIVING_SEGMENT)
    key = ["prop_id", "imprv_id"]
    all_min = d.groupby(key)["year"].min()
    liv_min = d[living].groupby(key)["year"].min()
    return liv_min.combine_first(all_min).rename("year")


def group_of(type_cd: str) -> str:
    if type_cd in ALQ:
        return "alq"
    if type_cd == MAIN:
        return "house"
    if type_cd in MULTI:
        return "multi"
    if type_cd in MOHO:
        return "moho"
    return "other"


def classify_parcels(types: pd.DataFrame, years: pd.Series, window: tuple[int, int] = WINDOW) -> pd.DataFrame:
    """One row per parcel: main_year, universe, group (newest second dwelling built in `window`), new_year.

    `types`: prop_id, imprv_id, type_cd, parcel_id. `years`: year built indexed by (prop_id, imprv_id)."""
    t = types.assign(type_cd=types["type_cd"].astype(str).str.strip())
    t = t.join(years, on=["prop_id", "imprv_id"])
    attached = t.groupby("parcel_id")["type_cd"].agg(lambda s: bool(set(s) & ATTACHED_OWNERSHIP))
    dw = t[t["type_cd"].isin(DWELLING)].copy()
    houses = dw[(dw["type_cd"] == MAIN) & dw["year"].notna()].sort_values(["parcel_id", "year", "imprv_id"])
    main = houses.drop_duplicates("parcel_id", keep="first").set_index("parcel_id")
    out = pd.DataFrame(index=pd.Index(sorted(t["parcel_id"].dropna().unique()), name="parcel_id"))
    out["main_year"] = main["year"].reindex(out.index)
    out["attached"] = attached.reindex(out.index).fillna(False).astype(bool)
    out["universe"] = (out["main_year"] < UNIVERSE_BEFORE) & ~out["attached"]
    main_key = set(zip(main["prop_id"], main["imprv_id"], strict=True))
    second = dw[[(p, i) not in main_key for p, i in zip(dw["prop_id"], dw["imprv_id"], strict=True)]]
    new = second[second["year"].between(*window)].sort_values(["parcel_id", "year", "imprv_id"])
    newest = new.drop_duplicates("parcel_id", keep="last").set_index("parcel_id")
    out["group"] = newest["type_cd"].map(group_of).reindex(out.index).fillna("none")
    out["new_year"] = newest["year"].reindex(out.index)
    out.loc[~out["universe"], "group"] = "none"
    out["in_r"] = out["group"].isin(["alq", "house"])
    return out


def _code(permit_class_raw: pd.Series) -> pd.Series:
    return permit_class_raw.astype("string").str.extract(r"(\d{3})", expand=False)


def home_adu(permits: pd.DataFrame, main_year: pd.Series, attached: pd.Series) -> pd.Series:
    """HOME rule (§0.5): True where a permit adds a building to a lot whose house stays.

    `permits`: parcel_id, issue_date, permit_class_raw, is_demolition. `main_year` and `attached` are
    indexed by parcel_id (from `classify_parcels`). Applied to every permit given; callers pick the years."""
    p = permits.copy()
    code = _code(p["permit_class_raw"])
    issued = pd.to_datetime(p["issue_date"], errors="coerce")
    new_bldg = code.isin(HOME_CLASSES) & ~p["is_demolition"].fillna(False).astype(bool)
    house_year = p["parcel_id"].map(main_year)
    house_stays = (
        house_year.notna()
        & (house_year < issued.dt.year)
        & ~p["parcel_id"].map(attached).fillna(False).astype(bool)
    )
    demo = p[code.isin(DEMOLITION_CLASSES)].assign(d=issued[code.isin(DEMOLITION_CLASSES)])
    demo = demo.dropna(subset=["parcel_id", "d"])
    demolished = pd.Series(False, index=p.index)
    if not demo.empty:
        by_parcel = demo.groupby("parcel_id")["d"].apply(list)
        lookback = pd.DateOffset(years=DEMOLITION_LOOKBACK_YEARS)
        for i in p.index[new_bldg & house_stays]:
            ds = by_parcel.get(p.at[i, "parcel_id"])
            if ds is not None and any(d >= issued[i] - lookback for d in ds):
                demolished[i] = True
    return (new_bldg & house_stays & ~demolished).astype(bool)


def match(
    roll: pd.DataFrame,
    flagged: pd.Series,
    unflagged: pd.DataFrame,
    exclude_codes: frozenset[str] = frozenset({"103"}),
) -> dict[str, int]:
    """R vs P and groups (a)/(b) (§0.4).

    `roll`: `classify_parcels` output. `flagged`: parcel_ids of ADU-flagged permits in the window.
    `unflagged`: parcel_id and permit_class_raw of unflagged new-residential permits in the window.
    Group (a) leaves out parcels whose only unflagged permits carry a code in `exclude_codes` (the D-074
    duplex deviation); `a_as_written` keeps them."""
    universe = set(roll.index[roll["universe"]])
    r = set(roll.index[roll["in_r"]])
    p_all = set(flagged.dropna())
    p = p_all & universe
    rest = r - p
    uf = unflagged.dropna(subset=["parcel_id"]).assign(code=_code(unflagged["permit_class_raw"]))
    any_permit = set(uf["parcel_id"]) & rest
    adu_like = set(uf.loc[~uf["code"].isin(exclude_codes), "parcel_id"]) & rest
    return {
        "universe": len(universe),
        "R": len(r),
        "P": len(p),
        "P_outside_universe": len(p_all - universe),
        "both": len(r & p),
        "a": len(adu_like),
        "a_as_written": len(any_permit),
        "b": len(rest - any_permit),
        "P_not_R": len(p - r),
    }
