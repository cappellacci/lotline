# ruff: noqa: E501  (coding data: long notes)
"""Duplex and fourplex water/sewer rows (manual fee lookups, priority 1) -> config/fees/<st>.csv. Rerunning it is safe.

    uv run python scripts/dev/plex_utility_fees_2026_11_09.py

The fee model compares a house, a duplex (U2: 2 units of about 1,000 sq ft) and a fourplex (U3_4: 4 units of about
1,000 sq ft, one building, one lot). Where a place had only house water/sewer rows, `fee_levels` charged the house
fee again for every unit (`from SFD`). This script codes each place's own rule where an official source states it.

- One row per charge per building type, `fee_component = water_sewer`. `amount_usd` is the schedule's own number;
  `amount_per_unit_usd` is the building total / units for the typical case; `amount_per_unit_low_usd` /
  `amount_per_unit_high_usd` hold the alternatives when the amount depends on a builder's choice (one master meter
  vs one meter per unit, unit size, bedrooms) that the code leaves open.
- **Typical case = one meter (or service) per dwelling unit** wherever metering is the builder's choice: it is
  the utilities' default (WSFCU Part A Sec. 14(A): "Each water Customer shall be required to have a separate
  meter"; Austin and Dallas take one application per dwelling unit), and it is required once units are sold
  separately. The master-meter cases are the range.
- Places whose rule could not be read from an official source get no row (the model keeps `from SFD`); they are
  listed in the PR. Existing house rows are not touched.
- Metro cities whose Met Council SAC is an `OTHER` row (Coon Rapids, Lakeville, Maple Grove, Brooklyn Park) get no
  U2/U3_4 rows: the OTHER row already prices one SAC per dwelling unit, which is the SAC manual's rule, and a
  type-specific row would make `fee_levels` drop the city's own OTHER water/sewer rows for that type.

Rows are recognised by TAG in `notes`: a rerun removes them and writes them again.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEES = ROOT / "config" / "fees"
LABEL = {"U2": "Duplex unit", "U3_4": "Fourplex unit"}
TAG = "Plex utility rule 2026-11-09 (manual fee lookups P1):"

WSFCU_RULE_SRC = "https://cityofws.org/DocumentCenter/View/38360"
WSFCU_FEE_SRC = "https://www.cityofws.org/DocumentCenter/View/38803/User-Rate--Fee-Manual-FY27-eff-July-2026-PDF"
WSFCU_QUOTE = (
    "Each water Customer shall be required to have a separate meter; provided, that one (1) meter may be used for "
    "several premises, apartments, and blocks of stores where they are the property of the same Owner."
)


def wsfcu(geoid: str, place: str) -> list[dict]:
    # SDF by meter size (FY27 manual p.5 water, p.7 sewer): 5/8-3/4", 1", 1.5"
    water, sewer = (816, 2040, 4081), (2861, 7153, 14305)
    out = []
    for bt, n in (("U2", 2), ("U3_4", 4)):
        for comp, (m34, m1, m15) in (("Water", water), ("Sewer", sewer)):
            low, high = (m34 / 2, m1 / 2) if n == 2 else (m1 / 4, m15 / 4)
            lo_txt = (
                "one 5/8-3/4-inch master meter for the building" if n == 2 else "one 1-inch master meter"
            )
            hi_txt = "one 1-inch master meter" if n == 2 else "one 1 1/2-inch master meter"
            out.append(
                dict(
                    state="NC", jurisdiction_geoid=geoid, year=2026, effective_date="2026-07-01",
                    fee_type=f"{comp} System Development Fee, one 5/8 or 3/4-inch meter per dwelling unit",
                    building_type_std=bt, basis="per_lue", amount_usd=m34, amount_per_unit_usd=m34,
                    amount_per_unit_low_usd=low, amount_per_unit_high_usd=high, dollar_year=2026,
                    source=f"{WSFCU_FEE_SRC}; {WSFCU_RULE_SRC}",
                    source_section=f"WSFCU User Rate & Fee Manual FY 2026-27, {comp} System Development Fees by meter size; Utility rules Part A Art. I Sec. 14(A) (separate meters) and Sec. 42(B)",
                    source_quote=WSFCU_QUOTE,
                    notes=f"{place}; {TAG} WSFCU charges the SDF per new connection by meter size ('The fee will be determined by meter size', Sec. 42(B); sewer Sec. 128(b)); no per-dwelling-unit or multifamily rate. Each customer must have its own meter, but one owner may serve several apartments through one meter, so a rental plex may use a master meter. Typical: one 5/8 or 3/4-inch meter per unit (the rule's default; required if units are sold separately) = house amount per unit. Low: {lo_txt} (${low:,.2f}/unit); high: {hi_txt} (${high:,.2f}/unit). Master-meter size is not set by the code (plumbing sizing); a fourplex on one 3/4-inch meter would be ${m34 / 4:,.2f}/unit. {n} units of about 1,000 sq ft.",
                )
            )
    return out


def brunswick() -> list[dict]:
    src = {"Water": "https://brunswickcountync.gov/DocumentCenter/View/8019/WaterRatesFY26-27effJan1-PDF",
           "Sewer": "https://brunswickcountync.gov/DocumentCenter/View/7661/SewerRatesFY26-27"}
    fees = [("Water", "Water Capital Recovery Fee", 955.0, "Capital Recovery Fee, p. 5"),
            ("Water", "Water Transmission Capital Recovery Fee", 119.0, "Water Transmission Capital Recovery Fee, p. 5"),
            ("Sewer", "Sewer Capital Recovery Fee", 1956.0, "Capital Recovery Fee, p. 4"),
            ("Sewer", "Sewer Transmission Capital Recovery Fee", 252.0, "Sewer Transmission Capital Recovery Fee, p. 4")]
    out = []
    for bt, n in (("U2", 2), ("U3_4", 4)):
        for kind, name, amt, sec in fees:
            out.append(dict(
                state="NC", jurisdiction_geoid="37019", year=2026, effective_date="",
                fee_type=f"{name}, residential, 2-bedroom dwelling unit", building_type_std=bt, basis="other",
                amount_usd=amt, amount_per_unit_usd=2 * amt, amount_per_unit_low_usd=amt,
                amount_per_unit_high_usd=3 * amt, dollar_year=2026, source=src[kind],
                source_section=f"Brunswick County Public Utilities, {kind.replace('Sewer', 'Wastewater')} Fee Schedule FY 26-27, {sec}",
                source_quote=f"{name.upper() if 'Transmission' in name else 'CAPITAL RECOVERY FEE'} Residential per Bedroom $ {amt:,.2f}",
                notes=f"Brunswick County unincorporated; {TAG} charged per bedroom for residential ('Residential per Bedroom'); commercial uses pay per gallon per day. The schedule has no duplex or multifamily line; a plex is treated as residential (the sewer rate schedule bills 'Master-Meter Multi-Family' as residential units). Assumes 2 bedrooms per 1,000 sq ft unit: {n} units x 2 x ${amt:,.0f} = ${n * 2 * amt:,.0f} for the building. Low 1 bedroom, high 3 bedrooms per unit. A house (3 bedrooms) pays 3 x ${amt:,.0f}, so a plex unit pays less only because it has fewer bedrooms. Not checked: whether the county bills multifamily as commercial gallons per day instead (about $44.92/gpd, all four fees). Applies only where the building connects to county water and sewer.",
            ))
    return out


BEND_SRC = "https://bendoregon.gov/wp-content/uploads/2026/06/3487-Resolution.pdf"
BEND_SEC = "Resolution 3487 (adopted 2026-06-17, effective 2026-07-01), Exhibit A: SDC Schedule, Residential Categories (Year 3, starting 7/1/26); Exhibit B definitions"
PDX_W_SRC = "https://efiles.portlandoregon.gov/record/17900475/file/document; https://www.portland.gov/code/21/30/070"
PDX_S_SRC = "https://www.portland.gov/bes/full-list-environmental-services-rates-and-charges; https://www.portland.gov/policies/environment-built/sewer-stormwater-erosion-control/enb-405-administrative-rules-sanitary"
PDX_EXEMPT = "Temporary Housing SDC exemption (PCC 17.14.070.J; https://www.portland.gov/ppd/current-fee-schedules/housing-sdc-exemption): permits for new dwelling units issued 2025-08-15 to 2028-09-30 may be exempt from SDCs (foundation inspection within 12 months or a completion guarantee); not applied here, as on the house and fourplex rows."


def oregon() -> list[dict]:
    rows = []
    for comp, amt, lo, hi in (("Water", 4559, 2698, 6008), ("Sewer", 5463, 3417, 5949)):
        rows.append(dict(
            state="OR", jurisdiction_geoid="4105800", year=2026, effective_date="2026-07-01",
            fee_type=f"{comp} SDC, Single Unit & Middle Housing Tier 2 (601-1,200 sq ft)", building_type_std="U2",
            basis="per_unit", amount_usd=amt, amount_per_unit_usd=amt, amount_per_unit_low_usd=lo,
            amount_per_unit_high_usd=hi, dollar_year=2026, payment_timing="building permit issuance",
            source=BEND_SRC, source_section=BEND_SEC,
            source_quote="Single unit housing with up to 4 units on one lot or parcel. Includes middle housing (duplexes, triplexes, quadplexes, cottage developments up to 4 units on one lot or parcel, and townhouses) | Tier 2 (601-1200 SQ FT) Dwelling Unit $4,559 $5,463 $6,999 $17,021",
            notes=f"Bend; {TAG} charged per dwelling unit by the unit's size tier; a duplex is 'Single Unit & Middle Housing' (Exhibit B). Assumes 1,000 sq ft units (Tier 2): duplex ${2 * amt:,} for the building. Low: Tier 1 (<600 sq ft) ${lo:,}; high: Tier 3 (1,201-1,600 sq ft) ${hi:,}. Exhibit A columns read as Water, Sewer, Transportation, Total (they sum). No meter basis (meters matter only for irrigation-only meters).",
        ))
    rows.append(dict(
        state="OR", jurisdiction_geoid="4159000", year=2026, effective_date="2026-07-01",
        fee_type="Water SDC, 5/8-inch meter per dwelling unit (Portland Water Bureau)", building_type_std="U2",
        basis="per_lue", amount_usd=5483, amount_per_unit_usd=5483, amount_per_unit_low_usd=4112,
        amount_per_unit_high_usd=6853.5, dollar_year=2026, payment_timing="building permit issuance",
        source=PDX_W_SRC,
        source_section="PWB FY 2026-27 Rate Ordinance (Ord. 192183) Exhibit A: System Development Charges by Meter Size; PCC 21.30.070 Separate Service, A and B",
        source_quote="Separate meters may be installed to supply water to: ... New residential and multifamily developments with more than one unit. | 5/8” $5,483 3/4\" $8,224 1” $13,707",
        notes=f"Portland; {TAG} the water SDC is charged per meter by size. Separate meters are required for buildings under separate ownership (PCC 21.30.070 A) and optional for a new development with more than one unit (B), so a rental duplex may share one meter. Typical: one 5/8-inch meter per unit (as the fourplex rows; required if the units are sold separately) = $10,966 for the building. Low: one shared 3/4-inch meter $8,224 ($4,112/unit); high: one shared 1-inch meter $13,707 ($6,853.50/unit). Meter size is set by the W-3 fixture worksheet (not read). {PDX_EXEMPT}",
    ))
    rows.append(dict(
        state="OR", jurisdiction_geoid="4159000", year=2026, effective_date="2026-07-01",
        fee_type="Sanitary sewer SDC, residential (60% of Tier 1 rate per drainage fixture unit)", building_type_std="U2",
        basis="other", amount_usd=623, amount_per_unit_usd=5980.8, dollar_year=2026,
        payment_timing="building permit issuance", source=PDX_S_SRC,
        source_section="BES rates and charges FY 2026-2027: System development charges (SDCs); ENB-4.05 s.5.B",
        source_quote="SDCs for residential units, including those within mixed-use developments, are charged 60-percent of the Tier 1 rate per DFU.",
        notes=f"Portland; {TAG} charged per drainage fixture unit (DFU) actually installed; no per-dwelling rule or minimum. Duplex unit: same 16 DFU per dwelling as the house and fourplex rows (0.6 x $623 x 16 = $5,980.80; the 16 DFU figure is ENB-4.05's assumed credit for an existing house, used here as an assumption). A unit with fewer fixtures pays less. {PDX_EXEMPT}",
    ))
    return rows


def minnesota() -> list[dict]:
    rows = []
    stc_src = "https://ci.stcloud.mn.us/DocumentCenter/View/19574/Current-Public-Utilities-Fee-Summary; https://ci.stcloud.mn.us/DocumentCenter/View/763/Meter--Tap-Fees-and-WAC--SAC"
    for bt, per, n in (("U2", 3100.0, 2), ("U3_4", 2325.0, 4)):
        for name in ("Sewer Availability Charge (SAC)", "Water Availability Charge (WAC)"):
            rule = ("2 units is not 'Multi Family' (>2 units), so each unit pays one full unit charge" if n == 2
                    else "a fourplex is 'Multi Family' (>2 units) and gets the 2026 25% discount on total units: 4 x 0.75 = 3 units charged")
            rows.append(dict(
                state="MN", jurisdiction_geoid="2756896", year=2026, effective_date="2026-01-01",
                fee_type=f"{name}, per residential unit", building_type_std=bt, basis="per_unit",
                amount_usd=3100.0, amount_per_unit_usd=per, dollar_year=2026, source=stc_src,
                source_section="2026 Public Utilities Fee Schedule, Multi Family Development WAC & SAC Unit Determination Schedule (effective 2026-01-01); City Code Sec. 575:25 Table 1",
                source_quote="Multiple Family Residential (per residential unit) ... Residential Unit 1 ... (>2 Units is considered a Multi Family Facility Type) | WAC/SAC (Multi Family, >2 units) 25% discount on total units",
                notes=f"St. Cloud; {TAG} charged per residential unit, determined by use, not meter size; {rule}. {n} units: ${per * n:,.0f} for the building (${per:,.0f}/unit). The discount was 75% in 2024 and 50% in 2025; the Public Services Director or City Engineer calculates the units, so a project can differ.",
            ))
    for bt, n in (("U2", 2), ("U3_4", 4)):
        rows.append(dict(
            state="MN", jurisdiction_geoid="2758000", year=2026, effective_date="2026-01-01",
            fee_type="Sewer Availability Charge (SAC), Met Council, one SAC unit per dwelling unit", building_type_std=bt,
            basis="per_lue", amount_usd=2485.0, amount_per_unit_usd=2485.0,
            amount_per_unit_low_usd=(1988.0 if n == 4 else None), amount_per_unit_high_usd=(2485.0 if n == 4 else None),
            dollar_year=2026, source="https://metrocouncil.org/SACmanual",
            source_section="Metropolitan Council SAC Procedure Manual, issued January 1, 2026, Sec. 3 and Sec. 5.1 (residential)",
            source_quote="Single family houses, townhouses, condominiums, duplex units, and most apartments each equal one SAC per dwelling unit",
            notes=f"St. Paul; {TAG} one SAC unit per dwelling unit ($2,485 in 2026), collected through city permits: {n} units = ${2485 * n:,} for the building." + (" Low: a rental with no laundry plumbing in any unit may get the 20% apartment discount with prior Council approval ('A qualifying discounted apartment is a building with 4 or more dwelling units'): 3.2 SAC = $7,952 ($1,988/unit)." if n == 4 else "") + " No Saint Paul Regional Water Services capacity charge found (only connection installation at cost); none coded.",
        ))
    return rows


def texas() -> list[dict]:
    rows = []
    aus_tap = "https://austintexas.gov/sites/default/files/files/Water/Customer_Service/ResidentialTapApplication__031519_.pdf"
    aus_q = "Separate applications are required for separate dwelling units on the same property."
    aus_note = f"Austin; {TAG} impact fees are per service unit by meter size (2023 Impact Fee Report: 'The service unit is based on the size of water meter sold'), and Austin Water takes a separate residential tap application for each dwelling unit (form lists 'Duplex'), so a duplex is two 5/8-inch services: per unit = house. Duplex total $16,238.84 with meter, tap and inspection."
    for name, amt, lo, hi in (("Water impact fee, lots platted after 2023-10-01 (all zones), one service unit per dwelling unit", 4800.0, 600, 5400),
                              ("Wastewater impact fee, lots platted after 2023-10-01 (all zones), one service unit per dwelling unit", 2900.0, 400, 2900)):
        rows.append(dict(
            state="TX", jurisdiction_geoid="4805000", year=2023, effective_date="2023-10-01", in_force_through=2026,
            fee_type=name, building_type_std="U2", basis="per_lue", amount_usd=amt, amount_per_unit_usd=amt,
            amount_per_unit_low_usd=lo, amount_per_unit_high_usd=hi, dollar_year=2023,
            source=f"https://www.austintexas.gov/water/rates-and-fees; {aus_tap}",
            source_section="Impact fees (Capital Recovery Fees), schedules by plat date; Austin Water Residential Tap Application (rev. 2019-03-15)",
            source_quote=aus_q,
            notes=aus_note + " Low and high are the plat-date cohorts, as on the house row (Ben's 2026-10-30 rule).",
        ))
    for name, amt in (("Water meter fee, 5/8-inch meter, one per dwelling unit", 111.3),
                      ("Tap/reconnection fee, 5/8-inch service, one per dwelling unit", 200.22),
                      ("Residential utility inspection fee, 5/8-inch service, one per dwelling unit", 107.9)):
        rows.append(dict(
            state="TX", jurisdiction_geoid="4805000", year=2026, effective_date="2026-10-01", fee_type=name,
            building_type_std="U2", basis="per_unit", amount_usd=amt, amount_per_unit_usd=amt, dollar_year=2026,
            source=f"https://www.austintexas.gov/water/divisions/utility-permitting-office; {aus_tap}",
            source_section="Austin Water Utility Permitting Office fee schedule, FY2026-27; Residential Tap Application",
            source_quote=aus_q, notes=aus_note,
        ))
    saws_src = "https://docsonline.sanantonio.gov/FileUploads/dsd/CurrentFeeSchedule.pdf; https://apps.saws.org/business_center/developer/impactfees/docs/ImpactFeesMeterSizeChart_201906.pdf"
    saws_q = "Apartments, duplexes, townhomes, and condominiums served through a master meter will be charged on a basis of 1/2 EDU per unit."
    for bt, n in (("U2", 2), ("U3_4", 4)):
        for name, amt, lo_area, hi_area, what in (
            ("SAWS water impact fee (flow + system development + water supply), middle elevation, 1 EDU per dwelling unit", 4908.0, 4749.0, 5097.0, "elevation areas"),
            ("SAWS wastewater impact fee (collection + treatment), middle basin, 1 EDU per dwelling unit", 2073.0, 1171.0, 3451.0, "sewer basins"),
        ):
            rows.append(dict(
                state="TX", jurisdiction_geoid="4865000", year=2026, effective_date="", fee_type=name,
                building_type_std=bt, basis="per_lue", amount_usd=amt, amount_per_unit_usd=amt,
                amount_per_unit_low_usd=lo_area / 2, amount_per_unit_high_usd=hi_area, dollar_year=2026,
                source=saws_src,
                source_section="FY2027 Development Fee Schedule, SAWS Water and Sewer Impact Fees; SAWS Impact Fee Meter Size chart (plats recorded on or after 2019-06-01)",
                source_quote=saws_q,
                notes=f"San Antonio (SAWS); {TAG} impact fees are per EDU by meter size (5/8-inch = 1, 3/4 = 1.5, 1 = 2, 1 1/2 = 5, 2 = 14); a plex on one master meter pays 1/2 EDU per unit. Typical: one 5/8-inch meter per unit (1 EDU/unit, as a house), the central {what} amount; {n} units = ${amt * n:,.0f}. Low: master meter at 1/2 EDU in the cheapest of the {what} (${lo_area / 2:,.1f}/unit); high: one meter per unit in the dearest (${hi_area:,.0f}). Under the master-meter rule the building pays half a house per unit everywhere. The 2019 chart's 5/8-inch water totals ($4,749/$4,908/$5,097) match the FY2027 schedule; the 2024 Impact Fee Report (robots-disallowed) was not read to confirm the 1/2-EDU rule.",
            ))
    dal_src = "https://dallas.gov/departments/pnv/Documents/AH%20Memos/MeterFeeSchedule25-001.pdf; https://dallas.gov/departments/sustainabledevelopment/buildinginspection/DCH%20documents/pdf/BI_Water%20Wastewater%20FAQ.pdf"
    dal_q = "Complete two separate water/wastewater applications with one building permit. | Most single-family homes and duplexes have 3/4” service lines."
    dal_note = f"Dallas; {TAG} a duplex takes two water/wastewater applications (one per unit) on one building permit, so each unit has its own 3/4-inch service and 6-inch lateral and pays the house's inspection charges: $1,862 for the building, $931/unit. Assumes each application pays one water service inspection and one lateral inspection (the meter fee schedule is robots-disallowed and was not re-read; amounts as on the house rows)."
    for name, amt in (("Water service inspection, 3/4-inch service installed by bonded contractor, one per dwelling unit", 465.5),
                      ("Wastewater lateral inspection, 6-inch lateral installed by bonded contractor, one per dwelling unit", 465.5)):
        rows.append(dict(
            state="TX", jurisdiction_geoid="4819000", year=2025, effective_date="2025-10-01", fee_type=name,
            building_type_std="U2", basis="per_unit", amount_usd=amt, amount_per_unit_usd=amt, dollar_year=2025,
            source=dal_src, source_section="Development meter fee schedule effective 2025-10-01; Building Inspection Water/Wastewater FAQ",
            source_quote=dal_q, notes=dal_note,
        ))
    rows.append(dict(
        state="TX", jurisdiction_geoid="4819000", year=2025, effective_date="",
        fee_type="Water and wastewater impact fee: none (the city does not charge utility impact fees)",
        building_type_std="U2", basis="per_unit", amount_usd=0, amount_per_unit_usd=0, dollar_year=2025,
        source="https://citysecretary2.dallascityhall.com/pdf/COUNCIL%20COMMITTEES/2023/120423_ECO_MIN.pdf; https://codelibrary.amlegal.com/codes/dallas/latest/dallas_tx/0-0-0-125993",
        source_section="Committee minutes 2023-12-04, Exhibit C p. 23 (fee-study briefing); City Code Ch. 49 Art. V",
        source_quote="The City of Dallas does not charge utility impact fees as other Cities do.",
        notes=f"Dallas; {TAG} no water or wastewater impact fee on any building type (as the house row); coded so the duplex total is complete.",
    ))
    return rows


def all_rows() -> dict[str, list[dict]]:
    return {
        "nc": wsfcu("3775000", "Winston-Salem") + wsfcu("37067", "Forsyth County unincorporated") + brunswick(),
        "or": oregon(),
        "mn": minnesota(),
        "tx": texas(),
    }


def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def main() -> None:
    from lotline.config import load_fees

    for st, new in all_rows().items():
        path = FEES / f"{st}.csv"
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            cols, rows = reader.fieldnames, [r for r in reader if TAG not in (r.get("notes") or "")]
        for r in new:
            assert r["building_type_std"] in ("U2", "U3_4"), r
            q = r["source_quote"]
            assert len(q) <= 300, (len(q), q)
            lo, mid, hi = r.get("amount_per_unit_low_usd"), r["amount_per_unit_usd"], r.get("amount_per_unit_high_usd")
            assert lo is None or lo <= mid, r["fee_type"]
            assert hi is None or hi >= mid, r["fee_type"]
            row = {c: "" for c in cols}
            row.update({k: fmt(v) for k, v in r.items()})
            row["fee_component"] = "water_sewer"
            # own prefix, so the rows never join a house fee group keyed on fee_type (tx_fee_rule, fee_ranges)
            row["fee_type"] = f"{LABEL[r['building_type_std']]}: {r['fee_type']}"
            assert set(row) == set(cols), set(row) ^ set(cols)
            rows.append(row)
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        load_fees(st, FEES.parent)
        print(f"{path.name}: {len(new)} plex water/sewer rows")


if __name__ == "__main__":
    main()
