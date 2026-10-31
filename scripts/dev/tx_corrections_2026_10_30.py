# ruff: noqa: E501  (coding data: long source URLs and notes)
"""Ben's decisions on the proposed Texas corrections (2026-10-30) -> config/reforms/tx.csv.

Run from the repo root after `tx_research_2026_10_29.py`:
`uv run python scripts/dev/tx_corrections_2026_10_30.py`. Rerunning it is safe.

The proposals are in `docs/research/ordinances/tx-corrections-2026-10-29.csv` (rows #1-#35). Ben decided them on
2026-10-30:
- Accept every correction checked against a local PDF (group A) and every workbook-only one (group B). Group B
  rows keep their FLAG for a second coder.
- Denton (#29): keep 2023-03-07 and note that it is unsupported.
- Abilene (#34): keep one home per lot.
- College Station parking (#31): note only.
- Rename the four rows whose effective year moves (`RENAMES`), along with every `supersedes` that points at
  them.

Edits are field by field; each edited row gets a dated note naming the correction numbers. This script
corrects rows coded earlier; the proposals and the evidence behind them stay in the corrections file.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "reforms" / "tx.csv"
DECISIONS = ROOT / "docs" / "research" / "ordinances" / "tx-corrections-2026-10-29.csv"
DAY = "2026-10-30"
CLEARED = f"Earlier flag, cleared {DAY} by the local PDF check:"

RENAMES = {
    "TX-4865000-adu-2001": "TX-4865000-adu-2010",
    "TX-4827684-adu-2021": "TX-4827684-adu-2019",
    "TX-4841464-adu-1992": "TX-4841464-adu-2010",
    "TX-4815976-adu-2023": "TX-4815976-adu-2018",
}

# reform_id (old name where renamed) -> (correction numbers, field values, (old, new) text swaps in coding_notes, note)
EDITS: dict[str, tuple[str, dict, list[tuple[str, str]], str]] = {
    "TX-4865000-adu-2001": (
        "#1-2",
        {
            "source_url": "https://library.municode.com/tx/san_antonio/codes/unified_development_code?nodeId=ARTIIIZO_DIV7SUUSRE_S35-371ACDW; https://www.sa.gov/Directory/Departments/DSD/Constructing/Residential/ADU; https://dallascityhall.com/departments/sustainabledevelopment/planning/DCH%20Documents/ADU/ADU_ZOAC_CaseReport-10.1.2020_FINAL.pdf",
            "effective_date": "2010-01-01",
        },
        [],
        "Primary source is UDC §35-371 (history: Ords. 96564, 97568, 100126, all before 2010) and the city ADU page; the Dallas report stays as the secondary source for the '2001' wording. '2001' came only from that report, so the row is dated 2010-01-01 (rule in force before the window, adoption date not found) and renamed from TX-4865000-adu-2001.",
    ),
    "TX-4819000-adu-2018": (
        "#3-4",
        {"effective_date": "2018-06-30"},
        [("FLAG for second coder:", CLEARED)],
        "Effective 2018-06-30: Ords. 30930 and 30931 take effect on passage and publication, published 2018-06-30 (Dallas_Ord_30930_ADU_BOA.pdf pp. 8-9; Dallas_Ord_30931_ADU_Overlay.pdf pp. 9-10). Adoption stays 2018-06-27.",
    ),
    "TX-4819000-adu-2010": (
        "#5",
        {},
        [("FLAG for second coder:", CLEARED)],
        "Confirmed by Dallas_Ord_30930_ADU_BOA.pdf p. 4 (existing §51A-4.209(b)(6)(E)(i)-(ii) text).",
    ),
    "TX-4824000-adu-2011": (
        "#6-8",
        {
            "parking_min_per_unit": "",
            "parking": "no ADU-specific minimum in Ord. 17532 (on-site parking required only when the ADU takes access from an alley); general Title 20 parking table not checked",
        },
        [
            (
                "FLAG for second coder: current §20.10.035 not opened (municode 403, elaws mirror timed out).",
                "Earlier flag (current §20.10.035 not opened) narrowed below.",
            )
        ],
        "ElPaso_Ord_17532_ADU.pdf p. 8: the ADU section's only parking language ties on-site parking to alley access; the one-space figure came from a 2025 news story. FLAG for second coder: the local PDF is the unsigned April 19, 2011 agenda copy; check the ordinance number (17532), the adoption and publication or effective date, and whether Title 20 Appendix C sets a parking minimum for ADUs.",
    ),
    "TX-4804000-adu-2014": (
        "#9",
        {"effective_date": "2014-07-10"},
        [],
        "Effective 2014-07-10, the date the city's UDC amendment page gives for the base UDC; adoption of Ord. 14-039 stays 2014-06-24 (Ben's research workbook 2026-10-29). FLAG for second coder: the effective date is from the workbook, not a local PDF.",
    ),
    "TX-4858016-adu-2019": (
        "#10-12",
        {
            "coverage": "Residential districts SF-20, SF-9, SF-7, SF-6, UR, PH, SF-A, 2F, GR, MF-1, MF-2, MF-3, MH (not A or ED), lots of at least 6,000 sq ft; before 2019 only the Estate Development district (141 homes)",
            "coverage_zones": "SF-20;SF-9;SF-7;SF-6;UR;PH;SF-A;2F;GR;MF-1;MF-2;MF-3;MH",
        },
        [
            (
                "FLAG for second coder: plano.gov and the civicplus fact sheet returned 403 (§15.1800 text).",
                "Earlier flag (§15.1800 text not opened) narrowed below.",
            )
        ],
        "Districts from Plano_Ord_2019-2-10_Backyard_Cottages.pdf p. 2 ('P (51)' in 13 of 15 residential columns, read from the text layer). FLAG for second coder: the ordinance number 2019-2-10 is not printed in the local PDF (it shows ZC 2018-033); check the number and the publication date.",
    ),
    "TX-4835000-adu-2023": (
        "#13",
        {},
        [("FLAG for second coder:", CLEARED)],
        "Confirmed by Houston_LivablePlaces_Ords_2023-801_802.pdf (Ord. 2023-801 Section 9 and Exhibit A §42-1).",
    ),
    "TX-4805000-adu-2015": (
        "#14-15",
        {"effective_date": "2015-11-30"},
        [
            (": FLAG for second coder)", f"; flag cleared {DAY} by the local PDF check)"),
            ("Effective date not found: coded as the vote date.", "Effective 2015-11-30 (Part 9)."),
        ],
        "Austin_Ord_20151119-080.pdf p. 8, Part 9: 'This ordinance takes effect on November 30, 2015.' Adoption stays 2015-11-19.",
    ),
    "TX-4845744-adu-2022": (
        "#16-22",
        {
            "adus_per_lot": "1",
            "by_right": "True",
            "adu_detached_allowed": "True",
            "owner_occ": "False",
            "parking": "one additional space if the site lacks four spaces (three in the H Historic Overlay)",
            "coverage": "R43, R12, R8, R6, R5, R3, AG (not on small-lot detached or attached single-family lots)",
            "component": "UDC §205G.2.b accessory dwelling unit (backyard cottage): one detached ADU per lot in R43 to R3 and AG, up to 50% of the house (75% if 1,200 sq ft or less), same ownership, no owner occupancy",
            "source_url": "https://www.mckinneytexas.org/DocumentCenter/View/39456/Unified_Development_Code_20260303?bidId=; https://www.mckinneytexas.org/3491/Accessory-Dwelling-Units; https://zoningverdict.com/q/can-i-add-an-adu-mckinney-tx",
        },
        [
            (
                "NO ADU RULE (adus_per_lot = 0): third-party summary",
                "Recoded 2026-10-30 as a rentable ADU (was a NO ADU RULE row from a third-party summary",
            )
        ],
        "From Ben's research workbook (2026-10-29), McKinney checkpoint: the city-hosted UDC (2026-03-03 edition) §205G.2.b and Table 2-26 list the ADU as an accessory use in R43-R3 and AG with no SUP, no owner-occupancy rule and no ADU lease ban, and the city ADU page advertises renting one; the earlier 'cannot be rented' reading came from the third-party summary. adu_max_sqft stays blank (share-of-house cap). FLAG for second coder: workbook only, no local PDF; check §205G.2.b and whether the 2022-11-15 UDC adoption is the right start date.",
    ),
    "TX-4827684-adu-2021": (
        "#23-25",
        {
            "adoption_date": "2019-10-01",
            "effective_date": "2019-10-01",
            "by_right": "True",
            "supersedes": "TX-4827684-adu-2011",
        },
        [],
        "Starts with Ord. 19-10-83 (adopted 2019-10-01, effective after publication on 2019-10-04 and 2019-10-11; effective = adoption pending the publication rule), which removed the family-only occupancy limit and allowed renting when the main house is owner-occupied; Ord. 2021-07-47 (2021-07-06) only reorganized the standards. By right: §3.02 marks garage apartment and guest house P in AG, RE, SF-16 to SF-7 and OTR. Renamed from TX-4827684-adu-2021; supersedes TX-4827684-adu-2011 (Ben's research workbook 2026-10-29). FLAG for second coder: workbook only; check Ord. 19-10-83's effective clause.",
    ),
    "TX-4845000-adu-2023": (
        "#26-27",
        {"min_lot_sqft": "10000", "adu_max_sqft": ""},
        [],
        "From Ben's research workbook (2026-10-29), Lubbock checkpoint: §39.02.020.e sets a 10,000 sq ft minimum lot (6,000 in the NIO and CIO infill overlays) and caps ADU floor area at the primary home's (a share-of-house cap, left blank); the 750 sq ft was the outbuilding rule for House, Duplex and Multiplex building types, not an ADU cap. FLAG for second coder: workbook only; check §39.02.020.e.",
    ),
    "TX-4841464-adu-1992": (
        "#28",
        {"adoption_date": "", "effective_date": "2010-01-01"},
        [],
        "Dated 2010-01-01 (rule in force before the window): 1992-04-06 (Ord. 92-O-75) came from a secondary annotated code history and the official record was not found (Ben's research workbook 2026-10-29). Renamed from TX-4841464-adu-1992.",
    ),
    "TX-4819972-adu-2023": (
        "#29",
        {},
        [],
        "Ben 2026-10-30: 2023-03-07 is kept because the schema needs a date, but it is unsupported (the city's code print ties it to an outdoor storage/display amendment). Do not use this row as a dated D-025 event until the ADU amendment's enactment date is found.",
    ),
    "TX-4815976-adu-2023": (
        "#30-31",
        {"adoption_date": "2018-11-19", "effective_date": "2018-11-29"},
        [],
        "Dated by Ord. 2018-4059 (adopted 2018-11-19, effective ten days after passage), the accessory-living-quarters rental, parking and occupancy change; Ord. 2023-4454 (2023-08-10) only changed parking ratios. Renamed from TX-4815976-adu-2023. Parking: the workbook says Ord. 2023-4454 sets one space per bedroom, which conflicts with the one extra space coded here; if confirmed, that is a new 2023 row superseding this one. FLAG for second coder: workbook only; check Ord. 2018-4059 and the current UDO §7.3(H).",
    ),
    "TX-4841980-missing_middle-2020": (
        "#32",
        {
            "coverage": "RSF-2 duplex permitted (P); RSF-5 duplex by Special Use Permit (start date not found, no row yet); RSF-20, RSF-10, RSF-7 one dwelling",
            "coverage_zones": "RSF-2",
            "by_right": "True",
        },
        [],
        "LeagueCity_UDC_Article-3_2026-07-28.pdf p. 53, Table 3.13.1: 'Dwelling, Duplex' P in RSF-2, S in RSF-5; p. 52: 'P' means permitted. RSF-5's SUP duplex gets its own row once its start date is found.",
    ),
    "TX-4801000-missing_middle-2010": (
        "#33-34",
        {"adoption_date": "2010-04-22", "effective_date": "2010-06-01"},
        [],
        "Effective 2010-06-01 (Abilene_LDC_Chapter-2_Current.pdf cover); adopted 2010-04-22 (Ord. 8-2010). Ben 2026-10-30: unit_cap stays 1 because the RS district text ('a maximum of one (1) dwelling unit per lot') governs over the Land Use Matrix's C for duplexes in RS; the conflict stays for the second coder.",
    ),
    "TX-4870808-adu-2010": (
        "#35",
        {
            "component": "Development Code §2-193 and §2-71: an accessory dwelling (up to 600 sq ft, in the house or part of a detached garage) is allowed in R-1, R-1R, R-1E only if occupants pay no compensation; no rentable ADU",
        },
        [],
        "From Ben's research workbook (2026-10-29), Sugar Land checkpoint: Land Use Matrix §2-71 'Dwelling, Accessory' (Ord. 1645, 2007-10-02) allows a non-compensated accessory dwelling; still no rentable ADU (adus_per_lot 0).",
    ),
}

# correction number -> decision text for the corrections file
DECIDED = {
    29: "kept date, noted (Ben 2026-10-30)",
    31: "note only (Ben 2026-10-30)",
    34: "rejected: keep unit_cap 1 (Ben 2026-10-30)",
}


def main() -> None:
    with PATH.open(newline="") as f:
        reader = csv.DictReader(f)
        cols, rows = reader.fieldnames, list(reader)
    by_id = {r["reform_id"]: r for r in rows}
    for old, (nums, fields, swaps, note) in EDITS.items():
        r = by_id[RENAMES[old]] if RENAMES.get(old) in by_id else by_id[old]  # old ids can be reused
        tag = f" Corrected {DAY} ({nums} in tx-corrections-2026-10-29.csv, Ben's decision):"
        if tag in r["coding_notes"]:
            continue
        assert set(fields) <= set(cols), set(fields) - set(cols)
        r.update(fields)
        for a, b in swaps:
            assert a in r["coding_notes"], (old, a)
            r["coding_notes"] = r["coding_notes"].replace(a, b)
        r["coding_notes"] = r["coding_notes"].rstrip() + tag + " " + note
    present = {r["reform_id"] for r in rows}
    renames = {a: b for a, b in RENAMES.items() if b not in present}  # done once; a reused id stays
    for r in rows:
        r["reform_id"] = renames.get(r["reform_id"], r["reform_id"])
        r["supersedes"] = renames.get(r["supersedes"], r["supersedes"])
    with PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    with DECISIONS.open(newline="") as f:
        reader = csv.DictReader(f)
        dcols, drows = reader.fieldnames, list(reader)
    for i, d in enumerate(drows, start=1):
        d["decision"] = DECIDED.get(i, "accepted (Ben 2026-10-30)")
    with DECISIONS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=dcols, lineterminator="\n")
        w.writeheader()
        w.writerows(drows)
    print(f"{len(EDITS)} rows corrected, {len(RENAMES)} renamed -> {PATH}")


if __name__ == "__main__":
    main()
