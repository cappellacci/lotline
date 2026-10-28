# ruff: noqa: E501  (coding data: long source URLs and notes)
"""Texas rule rows from Ben's research workbook (2026-10-27) -> config/reforms/tx.csv.

Run from the repo root: `uv run python scripts/dev/tx_research_2026_10_27.py`. The workbook
(`~/lotline-data/manual/texas/Texas-Municipal-ADU-and-Missing-Middle-Research.xlsx`, an agentic research run
Ben made, with the Austin HOME ordinance and SB 15 PDFs beside it) is research input, not data, so it stays out
of the repo. This script only appends: `ROWS` adds rows whose id is new, and `NOTES` appends a sentence to the
`coding_notes` of rows coded earlier (once; rerunning is safe). Nothing coded earlier is replaced.

The workbook's facts were not re-read by Claude at their sources (the Corpus Christi code host disallows AI
agents; no PDF reader in this environment), so every row or note here says where it came from and the new row
is flagged for a second coder, as `tx_adu_rows.py` does for facts read on mirrors.
"""

import csv
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "config" / "reforms" / "tx.csv"
COLS = next(csv.reader(PATH.open()))
SOURCE = "Ben's research workbook (2026-10-27, lotline-data/manual/texas)"
FLAG = " FLAG for second coder: "

ROWS: list[dict] = [
    {
        "reform_id": "TX-4817000-adu-2021",
        "state": "TX",
        "jurisdiction_geoid": "4817000",
        "theme": "adu",
        "component": "UDC §5.3.2.A (Ord. 032357): one detached ADU per lot in any residential district, full "
        "kitchen allowed; size cap by district (FR, RE, RS-22: 1,000 sq ft; RS-15, RS-10: 800; RS-6, RS-4.5: 500, "
        "or 800 on lots over 10,000 sq ft), never above the main house's floor area; the owner lives in the "
        "principal dwelling or the ADU",
        "status": "in_force",
        "adoption_date": "2021-02-23",
        "effective_date": "2021-02-23",
        "by_right": "True",
        "owner_occ": "True",
        "adu_max_sqft": "500",
        "adu_detached_allowed": "True",
        "adus_per_lot": "1",
        "coverage": "All residential zoning districts",
        "source_url": "https://online.encodeplus.com/regs/corpuschristi-tx/doc-view.aspx?print=1&tocid=; "
        "https://www.corpuschristitx.gov/department-directory/development-services/unified-development-code-udc/",
        "source_section": "UDC §5.3.2.A",
        "coder": "claude",
        "coder_agreement": "single_coder",
        "coding_notes": f"From {SOURCE}: the current UDC attributes §5.3.2.A to Ord. 032357 (2021-02-23). The "
        "ordinance's effective clause was not recovered, so effective_date is the adoption date (as for "
        "TX-4805000-parking-2023). 'May be permitted, one per lot, in any residential zoning district subject to "
        "standards' is read as by right. adu_max_sqft = 500 is the cap every lot gets (RS-6 and RS-4.5; same "
        "convention as Columbus). Parking left blank: no ADU-specific row; the UDC §7.2.2.B default may apply. "
        "Long-term rental is not restricted in this subsection; short-term rental rules not checked. The rule "
        "before 2021 is not known, so there is no earlier row and D-022 fills 2010-2020."
        + FLAG
        + "read from the workbook, not opened by Claude (enCodePlus robots.txt disallows AI agents); check the "
        "effective date and the pre-2021 rule.",
    },
]

NOTES: dict[str, str] = {
    "TX-4805000-missing_middle-2024": f" {SOURCE}, from Ord. 20231207-001 Part 21: in effect 2023-12-18, for "
    "applications filed on or after 2024-02-05. effective_date stays 2024-02-05, the first day the new rules "
    "could be used; the legal effective date is 2023-12-18.",
    "TX-4805000-adu-2024": f" {SOURCE}, from Ord. 20231207-001 Part 21: in effect 2023-12-18, for applications "
    "filed on or after 2024-02-05 (effective_date stays 2024-02-05). The city's ADU page now sends ADUs to the "
    "two- and three-unit rules (SF-1 to SF-3, lots of 5,750 sq ft or more).",
    "TX-4865000-adu-2023": f" {SOURCE}: Information Bulletin 402 (dated 2023-01-01) and the city ADU page "
    "agree with this row: one ADU in R-1 to R-6 and RM-4 to RM-6, owner occupancy by an affidavit recorded with "
    "Bexar County, up to 800 sq ft or 50% of the main house (at most 1,600), a parking space only above 800 sq "
    "ft. The amending ordinance's number is still not found.",
}


def main() -> None:
    with PATH.open(newline="") as f:
        existing = list(csv.DictReader(f))
    by_id = {r["reform_id"]: r for r in existing}
    for rid, note in NOTES.items():
        assert rid in by_id, rid
        if note.strip() not in by_id[rid]["coding_notes"]:
            by_id[rid]["coding_notes"] = by_id[rid]["coding_notes"].rstrip() + note
    added = 0
    for r in ROWS:
        assert not set(r) - set(COLS), set(r) - set(COLS)
        if r["reform_id"] not in by_id:
            existing.append({c: r.get(c, "") for c in COLS})
            added += 1
    with PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(existing)
    print(f"{added} rows added, {len(NOTES)} notes checked -> {PATH}")


if __name__ == "__main__":
    main()
