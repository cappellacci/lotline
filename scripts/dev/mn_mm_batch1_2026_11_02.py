# ruff: noqa: E501  (coding data: long notes)
"""Minnesota missing-middle rules from the batch-1 ordinance records -> config/reforms/mn.csv (thread 13, M4).

Run from the repo root: `uv run python scripts/dev/mn_mm_batch1_2026_11_02.py`. Rerunning it is safe: a row
whose reform_id is already in the file is left alone. It also writes
`docs/research/ordinances/mn-mm-lookups-todo.csv`, the fill-in table for the 40 largest places with no coded
missing-middle row (rerunning rewrites it from the same inputs, keeping any answers already filled in).

Rows come only from `docs/research/ordinances/batch1-2026-10-20.json` entries whose source was read
(`link.read = true`), with the record's own quote. Minneapolis (2020) and St. Paul (2023) are already coded,
and the 2040 Plan injunction windows already sit in the file as two `moratorium` rows with start and end dates,
which serve as the sensitivity rows. Places whose record says "unknown" go to the lookup table. All rows are
single-coder.

"One home" rows (`unit_cap = 1`) follow the Texas convention (`TX-4847892-missing_middle-2010`): a place
whose single-family districts allow no duplex is coded as untreated on evidence, not left to D-022's draw.
Where the rule's start is unknown, the date is the 2010-01-01 placeholder and the note says
`[earliest-known]`.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFORMS = ROOT / "config" / "reforms" / "mn.csv"
TODO = ROOT / "docs" / "research" / "ordinances" / "mn-mm-lookups-todo.csv"
CODED = "2026-11-02"

ROWS = [
    {
        "reform_id": "MN-2757220-missing_middle-2025",
        "jurisdiction_geoid": "2757220",
        "component": "Ord. 2690-25 (zoning code update): duplex, twinhome, courtyard cottage and three-unit dwellings permitted with standards in N-1 and N-2; four-unit dwellings in N-2 only",
        "adoption_date": "2025-03-03",
        "effective_date": "2025-03-28",
        "by_right": "True",
        "unit_cap": "3",
        "coverage": "Neighborhood districts N-1 (up to 3 units) and N-2 (up to 4 units), the former single-family districts",
        "coverage_zones": "N-1;N-2",
        "source_url": "https://www.stlouisparkmn.gov/files/assets/main/v/1/administration/documents/city-code/proposed-ordinances/250207-zoningcodeupdate-ordinance-final.pdf",
        "source_section": "Table 36-163 (residential use table)",
        "source_quote": "Dwelling, two-unit (duplex) PS PS",
        "coding_notes": "Batch-1 record (read): adopted at second reading 2025-03-03 (7-0). The effective date 2025-03-28 comes from a city page seen only in a search snippet, not opened: confirm it. 'PS' = permitted with standards (by right if the standards are met). unit_cap = 3 is N-1's; N-2 allows 4. Column alignment comes from PDF text extraction: confirm against the signed ordinance. Before 2025 the R-1 district was single-family only (inferred, not verified). Single coder: check the effective date and the table before treating this as a D-024 event.",
    },
    {
        "reform_id": "MN-2717000-missing_middle-2026",
        "jurisdiction_geoid": "2717000",
        "component": "Ordinance 26-019-O (No. 10976): more housing types made permitted uses in R-1 and R-2; multi-family in R-1 capped at 4 units",
        "adoption_date": "2026-06-29",
        "effective_date": "2026-08-31",
        "by_right": "True",
        "unit_cap": "4",
        "coverage": "R-1 and R-2 districts",
        "coverage_zones": "R-1;R-2",
        "source_url": "https://webapi.legistar.com/v1/duluth-mn/matters/13043/texts/13202",
        "source_section": "UDC 50-20.1.B.1",
        "source_quote": "A multi-family use in the R-1 district shall have no more than 4 units;",
        "coding_notes": "Batch-1 record (read): passed 2026-06-29, effective 2026-08-31 (after the D-024 window). Two-family dwellings were already allowed in R-1 before 2026 (2019 Ord. 10659 set R-1 two-family design standards; the Oct 2025 duplex-conversion handout gives a 2,000 sq ft per unit minimum lot), but whether by right or by special use is not verified, so no earlier row is coded (D-022 draws Duluth before 2026). Townhouse status in R-1 after 2026 not confirmed.",
    },
    {
        "reform_id": "MN-2754880-missing_middle-2023",
        "jurisdiction_geoid": "2754880",
        "component": "Unified Development Code: R-1 (Mixed Single-Family) allows a single-family detached house plus one ADU; duplex, triplex and fourplex allowed with staff approval only in R-2, R-2x, R-3, R-4 and some MX districts",
        "adoption_date": "2022-09-07",
        "effective_date": "2023-01-01",
        "unit_cap": "1",
        "coverage": "R-1 (Mixed Single-Family) district",
        "coverage_zones": "R-1",
        "source_url": "https://media-002-us.cdn.govstack.com/rochestermn-us/media/poageesh/unified-development-code.pdf",
        "source_section": "UDC Table 300.01-1 (p. 96)",
        "source_quote": "The R-1 district is intended to maintain and promote areas of low residential density where the emphasis is generally on the development of single-family dwellings",
        "coding_notes": "NO MISSING-MIDDLE RULE (unit_cap = 1) in R-1. Batch-1 record (consolidated UDC read; the as-adopted ordinance and its number were not found). The R-1 cells of Table 300.01-1 were read from the PDF layout: Ben should confirm them visually on p. 96. [earliest-known]: before 2023 the Land Development Manual applied and was not reviewed.",
    },
    {
        "reform_id": "MN-2707966-missing_middle-2010",
        "jurisdiction_geoid": "2707966",
        "component": "Two-family dwellings not permitted in the two lowest-density residential districts (permitted in R-3/R-4)",
        "effective_date": "2010-01-01",
        "unit_cap": "1",
        "coverage": "Lowest-density residential districts (R-1, R-2)",
        "coverage_zones": "R-1;R-2",
        "source_url": "https://www.brooklynpark.org/wp-content/uploads/2024/04/20240410-Agenda-Item-6.6.pdf",
        "source_section": "2024 zoning-code update, residential use table",
        "source_quote": "Two-family dwelling NP NP P P NP",
        "coding_notes": "NO MISSING-MIDDLE RULE (unit_cap = 1). Batch-1 record (read): the 2024 update's use table lists two-family dwellings NP in the two lowest-density districts (column alignment in the extracted table is uncertain); under the older code duplexes were allowed in R-4. [earliest-known]: 2010-01-01 is the placeholder for a rule in force before the window; no ordinance legalizing 2-4 units in single-family zones was found. The 2026 draft ADU ordinance (up to two ADUs in R-1 to R-3) was tabled.",
    },
    {
        "reform_id": "MN-2713114-missing_middle-2010",
        "jurisdiction_geoid": "2713114",
        "component": "Two-family dwellings not permitted in LDR-1 and LDR-2 (MDR only); townhouses and multi-family MDR/HDR only",
        "effective_date": "2010-01-01",
        "unit_cap": "1",
        "coverage": "Low-density residential districts LDR-1, LDR-2 (and LDR-3 from 2025, single-family only)",
        "coverage_zones": "LDR-1;LDR-2;LDR-3",
        "source_url": "https://www.coonrapidsmn.gov/DocumentCenter/View/16839/Proposed-Ordinance-2299-Repeal-and-Add-General-Regulations-and-Tables-11-601",
        "source_section": "Proposed Ord. 2299 (introduced 2024-04-02), use table 11-601",
        "source_quote": "Two Family Dwellings approved by the City prior to January 1, 2005.",
        "coding_notes": "NO MISSING-MIDDLE RULE (unit_cap = 1). Batch-1 record (read): two-family dwellings NP in LDR-1 and LDR-2; those approved before 2005-01-01 remain conforming, so duplexes have not been allowed in those districts since 2005. The table read is the proposed Ord. 2299; its adoption was not confirmed. The 2025 LDR-3 district (Ord. 2330) is single-family only. [earliest-known]: 2010-01-01 placeholder.",
    },
]

DEFAULTS = {
    "state": "MN",
    "theme": "missing_middle",
    "status": "in_force",
    "verified_by": "claude",
    "verified_date": CODED,
    "coder": "claude",
    "coder_agreement": "single_coder",
}

# The 40 largest MN places (2020 Census, jurisdictions table) with no coded missing-middle row after this
# script, plus what the batch-1 record found. Answer columns are left for Ben.
TODO_COLUMNS = [
    "place",
    "geoid",
    "pop",
    "need",
    "start_url",
    "duplex_on_single_family_lots (by_right/permit/no)",
    "triplex_fourplex (by_right/permit/no)",
    "first_allowed_date",
    "by_right_since",
    "districts",
    "ordinance",
    "source_url",
    "notes",
]
NEED = "whether duplexes, and 3-4 unit buildings, are allowed on single-family lots; since when; by right or by permit; which districts"
BATCH1 = {
    "2706616": (
        "https://letstalk.bloomingtonmn.gov/21178/widgets/70879/documents/79411",
        "Batch-1: Phase II (adopted 2026-03-23, PL202500199) added triplex, fourplex, multiplex, cottage court allowances; districts and by-right status not read (PDF not readable)",
    ),
    "2751730": ("", "Batch-1: nothing found; plymouthmn.gov and amlegal returned 403"),
    "2771428": ("", "Batch-1: not verified; city site and code hosts returned 403"),
    "2740166": (
        "https://library.municode.com/mn/maple_grove/codes/code_of_ordinances",
        "Batch-1: Municode blocked; city pages silent on 2-4 units",
    ),
    "2706382": (
        "https://library.municode.com/mn/blaine",
        "Batch-1: check the R-1 use tables (Chapter 29 / Appendix A)",
    ),
    "2735180": (
        "https://codelibrary.amlegal.com/codes/lakevillemn/latest/overview",
        "Batch-1: Title 11 on American Legal (403); interim ordinance pauses residential rezonings/plats to 2027-04-20 at the latest",
    ),
    "2756896": (
        "https://library.municode.com/mn/st._cloud/codes/code_of_ordinances?nodeId=COORSTCLMI_APXALADECO_ART8REDI",
        "Batch-1: R-2 allows two-family; R-1 unknown (Article 8); Ord. 2928 (2024-07-08) allows two ADUs per lot",
    ),
    "2717288": (
        "https://library.municode.com/mn/eagan/codes/code_of_ordinances?nodeId=CICO_CH11LAUSREZO",
        "Batch-1: ADU page suggests R-1 allows a home plus one attached/internal ADU only; Chapter 11 not read",
    ),
    "2708794": ("", "Batch-1: nothing found beyond one ADU per lot; check R-1 permitted uses in Title 10"),
    "2718116": ("", "Batch-1: not verified; city site and amlegal returned 403"),
    "2701900": ("", "Batch-1: no ordinance found; code host 403 and Laserfiche login wall"),
    "2743252": ("", "Batch-1: nothing found; zoning rewrite under way since about January 2025"),
    "2718188": ("", "Batch-1: only the 2024 ADU ordinance found; check R-1 uses in Chapter 36"),
}


def main() -> None:
    with REFORMS.open(newline="") as f:
        reader = csv.DictReader(f)
        cols, rows = reader.fieldnames, list(reader)
    have = {r["reform_id"] for r in rows}
    added = 0
    for spec in ROWS:
        if spec["reform_id"] in have:
            continue
        row = dict.fromkeys(cols, "") | DEFAULTS | spec
        unknown = set(row) - set(cols)
        if unknown:
            raise ValueError(f"{spec['reform_id']}: unknown columns {sorted(unknown)}")
        rows.append(row)
        added += 1
    with REFORMS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{added} rows added -> {REFORMS}")
    write_todo(rows)


def write_todo(reform_rows: list[dict]) -> None:
    import pandas as pd

    from lotline.io import DataStore

    coded = {r["jurisdiction_geoid"] for r in reform_rows if r["theme"] == "missing_middle"}
    j = pd.read_parquet(DataStore().processed("MN", "jurisdictions", "jurisdictions"))
    top = j[j["kind"] == "place"].nlargest(40, "pop_2020")
    old = {}
    if TODO.exists():
        with TODO.open(newline="") as f:
            old = {r["geoid"]: r for r in csv.DictReader(f)}
    out = []
    for _, p in top.iterrows():
        if p["geoid"] in coded:
            continue
        url, note = BATCH1.get(p["geoid"], ("", ""))
        row = dict.fromkeys(TODO_COLUMNS, "") | {
            "place": p["name"].removesuffix(" city"),
            "geoid": p["geoid"],
            "pop": int(p["pop_2020"]),
            "need": NEED,
            "start_url": url,
            "notes": note,
        }
        prior = old.get(p["geoid"], {})
        row |= {k: v for k, v in prior.items() if k in TODO_COLUMNS[5:] and v}  # keep answers
        out.append(row)
    with TODO.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TODO_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(f"{len(out)} places -> {TODO}")


if __name__ == "__main__":
    main()
