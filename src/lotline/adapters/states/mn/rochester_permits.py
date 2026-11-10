"""City of Rochester (MN) monthly building permit detail reports → canonical `permits` (2005-09 on).

Rochester's Building Safety department posts a **Monthly Detail Report Spreadsheet** for every month in the
city's public Laserfiche archive ("Building Permit Reports", linked from rochestermn.gov's building permit
reports archive). Each sheet lists the permits issued that month: permit type (Residential Bldg, Residential
Trade, Commercial Bldg ...), category, alteration and addition descriptions, permit ID, date of issue, the
city's parcel number, address, quadrant, Census construction type code (101 single-family house, 434
residential alteration ...), principal building use, occupancy, valuation, a free-text work description, and
the contractor and owner (name and mailing address).

**Fetch.** The archive's folder listing (`FolderListingService.aspx/GetFolderListing2`, a JSON POST the web
viewer itself uses) gives each year folder's entries; every "Detail Report Spreadsheet" is then downloaded
through `lotline.io.http.fetch` (`ElectronicFile.aspx?docid=...`), one file per month, so each lands in the
manifest with its sha256. robots.txt on `lf.rochestermn.gov` does not exist (404) and the www host's
disallows only CMS paths. Sheets to 2017-03 are `.xls` (Excel 97, read with `xlrd`, BSD-3-Clause; Ben approved
the dependency on 2026-11-10), later ones `.xlsx`. 2005-09 to 2007-10 are an extract from the city's old
permit system with its own field names (`read_legacy`): type code, permit class, issue date, units and a type
description, but no parcel and no free-text description, so they add new homes and no ADU signal.

**Privacy.** The contractor, owner and address columns are never read (`COLUMNS` lists exactly what is read;
`PERSONAL` is checked against it). The work description can name people or businesses, so it is read only by
the ADU rule and never kept.

**Rows.** A permit can be listed on several rows of a sheet (one per fee or line item); rows are collapsed to
one per `Permit ID`. Only building permits (`Permit Type` ending in "Bldg") are kept; trade permits
(electrical, plumbing, mechanical) never add a home.

**Building type and units** from the construction type code (Census BPS codes): 101 SFD, 102 TH, 103 U2,
104 U3_4, 105 MF5 (units unknown for 104/105), 434/437/438 and the local 997 accessory / 999 other codes
alterations or accessory work with 0 units (derived); 645-649 demolitions (units removed from the code).
**ADUs** (Rochester has no ADU field) come from the work description, with the ADU patterns of
`mpls_permits` (reused): the text names an ADU ("ADU", "accessory dwelling"), does not negate or postpone it
("not an ADU", "future ADU"), and is not work on an ADU that already exists (unless it legalizes one), on a
residential building permit that is not a demolition → `ADU`, 1 unit, `inferred`. Rochester files a new house
built with an attached ADU as a **two-family** permit (code 103, "Two-family dwelling (SFD with attached
ADU)"); such a new 101/103 permit that names an ADU keeps its row as the house (SFD, 1 unit, derived) and
gets a second row for the ADU (`permit_id` + `-ADU`), so its two homes are counted once each.
"Mother-in-law suite", "guest house" and "carriage house" are not read as ADUs (precision over recall).
The shared `lotline.parse.permit_text` parser was not used: it reads "future ADU" as an ADU and gives no type
for the two-family-with-ADU wording.
"""

from __future__ import annotations

import re
from pathlib import Path

import httpx
import pandas as pd

from lotline.adapters.states.mn.mpls_permits import ADU_EXISTING, ADU_KINDS, ADU_NEGATED, ADU_TEXT, LEGALIZE
from lotline.io import DataStore
from lotline.io.http import client, fetch
from lotline.schemas import validate
from lotline.validation import holdout

ADAPTER = "states.mn.rochester_permits"
VERSION = "1.0"
SOURCE = "rochester_permits"
TABLE = "permits"
LICENSE = "City of Rochester public records (Laserfiche public archive; no license stated)"
REPO = "ROCHESTER"
WEBLINK = "https://lf.rochestermn.gov/WebLink"
LISTING_URL = f"{WEBLINK}/FolderListingService.aspx/GetFolderListing2"
LANDING_URL = f"{WEBLINK}/Browse.aspx?id=3001428&dbid=0&repo={REPO}"
ROOT_FOLDER = 3001428  # "Building Permit Reports": the year folders and "*Archive"
ROCHESTER = "2754880"
MONTH = re.compile(r"\d{4}\.\d{2}")  # a sheet's folder: raw/rochester_permits/YYYY.MM/
SHEET = re.compile(r"^(\d{4})\.(\d{2}) Detail Report Spreadsheet$")

# Header label (lower case, whitespace collapsed) → canonical name. The labels change from month to month
# ("Permit ID", "Permit #", "Alt ID"; "Date of Issue", "Issue Date"), so each is a pattern. Only these
# are read; every other column (address, quadrant, contractor, owner, "Lic Prof", internal EP fields)
# never is.
COLUMNS = {
    "ptype": r"^(?:type of perm\w*|permit type|sub type level)$",
    "category": r"^categor\w*(?: level)?$",
    "alteration": r"^alteration description$",
    "addition": r"^addition description$",
    "permit_id": r"^(?:permit ?(?:#|id)?|alt id)$",
    "issue_date": r"^(?:issue date|date of issue|ep filter)$",
    "parcel": r"^parcel(?: #| all)?$",
    "code": r"^(?:const|constr?uction|contruction) ?type ?(?:code)?$|^consttypecode$",
    "use": r"^prin\w*[ _]b\w*[ _]use$",
    "occupancy": r"^occupancy(?: desc| type)?$",
    "valuation": r"^(?:valuation|ep val con)$",
    "description": r"^work ?description$",  # ADU rule input only, never kept
}
PERSONAL = re.compile(r"address|contractor|owner|lic prof|^construction$|street", re.I)

PROVENANCE = {
    "title": "City of Rochester (MN) monthly building permit detail reports (2005 on)",
    "landing_url": LANDING_URL,
    "table": TABLE,
    "attribution": "City of Rochester, Minnesota, Building Safety (public Laserfiche archive)",
    "cleaning": [
        "Each month's 'Detail Report Spreadsheet' (.xls to 2017-03 read with xlrd, .xlsx after) is found "
        "through the archive's folder listing and downloaded one file per month",
        "Only the permit type, category, alteration and addition descriptions, permit ID, date of issue, "
        "parcel, construction type code, principal building use, occupancy, valuation and work description "
        "are read; address, contractor and owner columns never are; the work description is read only by "
        "the ADU rule and never kept",
        "One row per Permit ID (rows repeat per line item); building, combo, demolition and manufactured-"
        "home permits only; trade, sign, grading and point-of-sale permits dropped; rows without a valid "
        "issue date dropped",
        "construction type code from the code column; where a month's sheet puts the code under the "
        "Occupancy label (2022-02), a 3-digit occupancy value is read as the code",
        "building_type_std and units from the Census construction type code (101 SFD, 102 TH, 103 U2, "
        "104 U3_4, 105 MF5; 434/437/438/997/999 0 units; 645-649 demolitions); units derived from the code",
        "ADU when the work description names one (mpls_permits' ADU, negation and existing-ADU patterns) on "
        "a residential building permit that is not a demolition (type and units inferred); a new 101/103 "
        "house permit that names an ADU becomes a house row (SFD, 1 unit) and an ADU row "
        "(permit_id + '-ADU')",
        "parcel_id = 'rst-' + the city's 6-digit parcel number; jurisdiction_geoid = Rochester (2754880)",
        "2005-09 to 2007-10 sheets are the old permit system's extract: type code (R + Census code; R100 "
        "attached single-family read as 102), permit class (building, demolition and manufactured-home "
        "classes kept), issue date, permit year and number (permit_id 'L' + year + '-' + number) and "
        "units (reported, where they fit the code); no parcel and no description, so no ADU can be read",
        "Where a sheet's issue dates are blank (2014-11), the report month is the issue date, "
        "date_precision=month",
    ],
    "limitations": [
        "Starts 2005-09; 2005-09 to 2007-10 come from the old permit system's extract, with no parcel and no "
        "work description (no ADU signal)",
        "No unit count: units come from the construction type code; 3-4 and 5+ unit buildings have no count",
        "The parcel number is the city's own, not the Olmsted County PIN, so permits are not joined to rolls",
        "ADUs only where the work description names one; no ADU field",
        "No license stated; posted as public records",
    ],
}

CODE_TYPES = {
    "101": ("SFD", 1),
    "102": ("TH", 1),
    "103": ("U2", 2),
    "104": ("U3_4", None),
    "105": ("MF5", None),
}
DEMOLITION_CODES = {"645": 1, "646": 2, "647": None, "648": None, "649": 0}
ZERO_UNIT_CODES = {"434", "437", "438", "990", "997", "998", "999"}
BUILDING_PTYPES = re.compile(r"Bldg|Combo|^Demolition$|^Manufactured Home$|^Building Permit$")
RESIDENTIAL_PTYPES = re.compile(r"^(?:Residential (?:Bldg|Combo)|Building Permit)$")
NEW_HOUSE_CODES = {"101", "103"}
# Legacy extract (2005-09 to 2007-10): field position → name. Positions 9-13, 15, 17 and 18 (street number,
# qualifier, name, direction, apartment, subdivision, owner, contractor) are never read.
LEGACY_FIELDS = {0: "type", 1: "class", 2: "valuation", 3: "yy", 4: "mm", 5: "dd", 6: "permit_year",
                 7: "number", 14: "type_desc", 16: "units"}  # fmt: skip
# Permit classes kept (building, demolition, manufactured home); signs (RXSG), grading (RXGP) and RXSW
# (sidewalk and site work) are dropped like the later sheets' trade and grading permits.
LEGACY_CLASSES = {"RBPR": "Residential Bldg", "RBPC": "Commercial Bldg", "RXDR": "Demolition",
                  "RXDC": "Demolition", "RXMH": "Manufactured Home"}  # fmt: skip
LEGACY_NEW = {"100", "101", "102", "103", "104", "105"}
LEGACY_CODE_ALIASES = {"100": "102"}  # "SINGLE FAMILY DWELLING (ATTACHED DWELLINGS)": a townhouse


def _norm(label: object) -> str:
    return re.sub(r"\s+", " ", str(label)).strip()


def _listing(http: httpx.Client, folder_id: int) -> list[dict]:
    body = {"repoName": REPO, "folderId": folder_id, "getNewListing": True, "start": 0, "end": 500,
            "sortColumn": "", "sortAscending": True}  # fmt: skip
    resp = http.post(LISTING_URL, json=body)
    resp.raise_for_status()
    return resp.json()["data"]["results"]


def sheet_entries(http: httpx.Client | None = None) -> list[dict]:
    """Every monthly Detail Report Spreadsheet: {'month': 'YYYY.MM', 'docid', 'extension'}, one per month."""
    own = http is None
    http = http or client()
    try:
        found: dict[str, dict] = {}
        stack = [ROOT_FOLDER]
        while stack:
            for e in _listing(http, stack.pop()):
                if e["type"] == 0:  # a folder
                    stack.append(int(e["entryId"]))
                    continue
                m = SHEET.match(_norm(e["name"]))
                if m:
                    month = f"{m[1]}.{m[2]}"
                    found.setdefault(month, {"month": month, "docid": int(e["entryId"]),
                                             "extension": (e.get("extension") or "").lower()})  # fmt: skip
        return sorted(found.values(), key=lambda r: r["month"])
    finally:
        if own:
            http.close()


def file_url(docid: int) -> str:
    return f"{WEBLINK}/ElectronicFile.aspx?docid={docid}&dbid=0&repo={REPO}"


def download(store: DataStore, *, refresh: bool = False) -> list[Path]:
    """Download every monthly sheet, .xlsx and .xls (cached); returns their paths."""
    paths = []
    with client() as http:
        for e in sheet_entries(http):
            if e["extension"] not in ("xlsx", "xls"):
                continue
            dest = store.raw(SOURCE, e["month"]) / f"detail_report.{e['extension']}"
            paths.append(
                fetch(
                    file_url(e["docid"]),
                    dest,
                    store=store,
                    source=SOURCE,
                    license=LICENSE,
                    adapter=ADAPTER,
                    adapter_version=VERSION,
                    http=http,
                    refresh=refresh,
                )  # fmt: skip
            )
    return paths


def header_map(labels: list[object]) -> dict[int, str]:
    """Column position → canonical name for one header row; personal columns can never match."""
    out: dict[int, str] = {}
    for i, label in enumerate(labels):
        text = _norm(label).lower()
        if not text or text == "nan" or PERSONAL.search(text):
            continue
        for name, pattern in COLUMNS.items():
            if re.match(pattern, text) and name not in out.values():
                out[i] = name
                break
    return out


def read_legacy(grid: pd.DataFrame) -> pd.DataFrame:
    """A 2005-09 to 2007-10 sheet (the old permit system's extract) → the `COLUMNS`, plus `units_reported`.

    The extract is one row per permit with system field names (`BPWTYP` type code, `BPWTCD` permit class,
    `BPWATD` type description, `BPWIYY/MM/DD` issue date, `BPWYER`/`BPWCNB` permit year and number,
    `BPWUNT` units); the first month labels some of them in words. Only those fields are read, by position;
    the street address, subdivision, owner and contractor fields never are. There is no parcel number and no
    free-text description (the type description stands in for it, so no ADU can be read)."""
    head = [_norm(v).upper() for v in grid.iloc[0]]
    if (
        len(head) < len(LEGACY_FIELDS)
        or head[0] not in ("BPWTYP", "TYPE")
        or head[7] not in ("BPWCNB", "PERMIT #")
    ):
        raise ValueError("not a legacy sheet")
    body = grid.iloc[1:, list(LEGACY_FIELDS)].set_axis(list(LEGACY_FIELDS.values()), axis=1)
    body = body.dropna(subset=["number"])
    code = body["type"].astype("string").str.extract(r"^R(\d{3})$", expand=False)
    yy = pd.to_numeric(body["yy"], errors="coerce") + 2000
    date = pd.to_datetime(
        {"year": yy, "month": pd.to_numeric(body["mm"], errors="coerce"),
         "day": pd.to_numeric(body["dd"], errors="coerce")}, errors="coerce")  # fmt: skip
    pyr = pd.to_numeric(body["permit_year"], errors="coerce").astype("Int64").astype("string").str.zfill(2)
    out = pd.DataFrame(
        {
            "ptype": body["class"].map(LEGACY_CLASSES),
            "category": code.map(lambda c: "New" if c in LEGACY_NEW else "Alteration"),
            "alteration": pd.NA,
            "addition": pd.NA,
            "permit_id": "L" + pyr + "-" + body["number"].astype("string").str.strip(),
            "issue_date": date.dt.strftime("%Y-%m-%d"),
            "parcel": pd.NA,
            "code": code.replace(LEGACY_CODE_ALIASES),
            "use": pd.NA,
            "occupancy": pd.NA,
            "valuation": body["valuation"],
            "description": body["type_desc"],
            "units_reported": body["units"],
        }
    )
    return out.reset_index(drop=True)


def read_sheet(path: Path) -> pd.DataFrame:
    """One monthly sheet → the `COLUMNS` (canonical names), as text; personal columns never kept."""
    engine = "xlrd" if Path(path).suffix.lower() == ".xls" else "openpyxl"
    grid = pd.read_excel(path, header=None, dtype=str, engine=engine)
    month = Path(path).parent.name if MONTH.fullmatch(Path(path).parent.name) else pd.NA
    if engine == "xlrd" and _norm(grid.iloc[0, 0]).upper() in ("BPWTYP", "TYPE"):
        return read_legacy(grid).assign(report_month=month)
    for row in range(min(len(grid), 40)):
        labels = [_norm(v).lower() for v in grid.iloc[row]]
        if any(v.startswith("parcel") for v in labels) and any("owner" in v for v in labels):
            break
    else:
        raise ValueError(f"{path}: no header row")
    keep = header_map(list(grid.iloc[row]))
    missing = set(COLUMNS) - set(keep.values())
    if {"permit_id", "issue_date", "ptype"} & missing:
        raise ValueError(f"{path}: missing required columns {sorted(missing)}")
    body = grid.iloc[row + 1 :, list(keep)].rename(columns=keep)
    for col in missing:
        body[col] = pd.NA
    return body.dropna(subset=["permit_id"]).assign(report_month=month).reset_index(drop=True)


def adu_named(text: str) -> str | None:
    """ADU form if the description names a new (or legalized) ADU, else None."""
    if not text or not ADU_TEXT.search(text) or ADU_NEGATED.search(text):
        return None
    if ADU_EXISTING.search(text) and not LEGALIZE.search(text):
        return None
    for kind, pattern in ADU_KINDS:
        if pattern.search(text):
            return kind
    return "unknown"


def classify(row: pd.Series) -> list[dict]:
    """One permit → its `permits` row facts (two rows for a new house built with an ADU)."""
    code, ptype, cat = row["code"], row["ptype"], row["category"]
    demolition = ptype == "Demolition" or code in DEMOLITION_CODES
    base = dict(adu_type=None, is_demolition=demolition, is_conversion=False, suffix="")
    kind = None if demolition or not RESIDENTIAL_PTYPES.match(ptype) else adu_named(row["description"])
    if kind and code in NEW_HOUSE_CODES and cat == "New":
        house = dict(base, building_type_std="SFD", type_confidence="high", units_new=1, units_removed=0,
                     units_confidence="derived")  # fmt: skip
        adu = dict(base, building_type_std="ADU", type_confidence="inferred", adu_type=kind, units_new=1,
                   units_removed=0, units_confidence="inferred", suffix="-ADU")  # fmt: skip
        return [house, adu]
    if kind:
        return [dict(base, building_type_std="ADU", type_confidence="inferred", adu_type=kind, units_new=1,
                     units_removed=0, units_confidence="inferred")]  # fmt: skip
    if demolition:
        n = DEMOLITION_CODES.get(code)
        return [
            dict(
                base,
                building_type_std="OTHER" if code == "649" else "UNKNOWN",
                type_confidence="unknown",
                units_new=0,
                units_removed=n,
                units_confidence="derived" if n is not None else "unknown",
            )
        ]
    if code in CODE_TYPES and cat == "New":
        btype, n = CODE_TYPES[code]
        reported = pd.to_numeric(row.get("units_reported"), errors="coerce")
        if pd.notna(reported) and reported > 0 and (n is None or reported == n):
            return [dict(base, building_type_std=btype, type_confidence="high", units_new=int(reported),
                         units_removed=0, units_confidence="reported")]  # fmt: skip
        return [dict(base, building_type_std=btype, type_confidence="high", units_new=n, units_removed=0,
                     units_confidence="derived" if n is not None else "unknown")]  # fmt: skip
    if code in ZERO_UNIT_CODES or cat in (
        "Alteration",
        "Addition",
        "Accessory Structure",
        "ReRoof",
        "Window Replacement",
        "ReSiding",
        "Deck",
    ):
        return [dict(base, building_type_std="OTHER", type_confidence="high", units_new=0, units_removed=0,
                     units_confidence="derived")]  # fmt: skip
    btype = CODE_TYPES.get(code, ("UNKNOWN", None))[0]
    return [dict(base, building_type_std=btype, type_confidence="high" if btype != "UNKNOWN" else "unknown",
                 units_new=None, units_removed=None, units_confidence="unknown")]  # fmt: skip


def _text(s: pd.Series) -> pd.Series:
    return s.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()


def build(raw: pd.DataFrame, state: str = "MN") -> pd.DataFrame:
    """Sheet rows (`read_sheet` columns, all months stacked) → validated `permits`."""
    df = raw.copy()
    for col in [*COLUMNS, "units_reported"]:
        df[col] = _text(df[col]) if col in df else pd.Series(pd.NA, index=df.index, dtype="string")
    occ_code = df["occupancy"].str.fullmatch(r"\d{3}").fillna(False)
    df["code"] = df["code"].where(df["code"].notna(), df["occupancy"].where(occ_code))
    df["code"] = df["code"].str.extract(r"^(\d{3})", expand=False)
    df["issue_date"] = pd.to_datetime(df["issue_date"], errors="coerce", format="mixed").dt.normalize()
    # A sheet lists the permits issued in its month; where a sheet leaves the date blank (2014-11), the
    # report month stands in, at month precision.
    month = df["report_month"] if "report_month" in df else pd.Series(pd.NA, index=df.index)
    month = pd.to_datetime(month.astype("string").str.replace(".", "-") + "-01", errors="coerce")
    df["precision"] = "day"
    df.loc[df["issue_date"].isna() & month.notna(), "precision"] = "month"
    df["issue_date"] = df["issue_date"].fillna(month)
    df = df[df["issue_date"].notna() & df["ptype"].str.contains(BUILDING_PTYPES).fillna(False)]
    df = df.drop_duplicates("permit_id", keep="first")
    df[["ptype", "category", "description", "code"]] = df[
        ["ptype", "category", "description", "code"]
    ].fillna("")
    rows = []
    for _, r in df.iterrows():
        for f in classify(r):
            rows.append({"permit_id": r["permit_id"] + f.pop("suffix"), "src": r.name, **f})
    facts = pd.DataFrame(rows)
    src = df.loc[facts["src"]].reset_index(drop=True)
    parcel = src["parcel"].str.replace(r"\D", "", regex=True)
    out = pd.DataFrame(
        {
            "state": state,
            "permit_id": "rst-" + facts["permit_id"],
            "parcel_id": ("rst-" + parcel).where(parcel.str.len() > 0),
            "jurisdiction_geoid": ROCHESTER,
            "issue_year": src["issue_date"].dt.year.astype("Int64"),
            "issue_date": src["issue_date"],
            "date_precision": src["precision"],
            "building_type_std": facts["building_type_std"].astype("string"),
            "type_confidence": facts["type_confidence"].astype("string"),
            "adu_type": facts["adu_type"].astype("string"),
            "permit_class_raw": src["ptype"] + ":" + src["category"] + ":" + src["code"],
            "units_new": pd.array(facts["units_new"], dtype="Int64"),
            "units_removed": pd.array(facts["units_removed"], dtype="Int64"),
            "units_confidence": facts["units_confidence"].astype("string"),
            "is_demolition": pd.array(facts["is_demolition"], dtype="boolean"),
            "is_conversion": pd.array(facts["is_conversion"], dtype="boolean"),
            "valuation_usd": pd.to_numeric(
                src["valuation"].str.replace(r"[$,]", "", regex=True), errors="coerce"
            ).where(lambda v: v >= 0),  # fmt: skip
            "source": SOURCE,
        }
    )
    out = holdout.apply(
        out, state, geoid_col="jurisdiction_geoid", date_col="issue_date", year_col="issue_year"
    )
    return validate(out.reset_index(drop=True), TABLE)


def load(state: str, store: DataStore, *, refresh: bool = False) -> pd.DataFrame:
    if state.upper() != "MN":
        raise ValueError(f"{SOURCE} covers Rochester, Minnesota only, not {state}")
    paths = download(store, refresh=refresh)
    return build(pd.concat([read_sheet(p) for p in paths], ignore_index=True), state)
