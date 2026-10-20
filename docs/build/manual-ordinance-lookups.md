# Manual ordinance lookups

Cities whose official zoning code our automated readers may not open: the code host refuses automated access (HTTP 403) or its `robots.txt` disallows it, and we never work around either. Each entry says where the code is and exactly what to record. Record the answers in the same fields the pipeline uses (the columns of `config/reforms/<st>.csv`, described in `docs/schemas.md` under `reforms`, and `config/fees/README.md`): the value, the section number, and a short verbatim quote. Leave anything you can't find blank: blank means *unknown* in the model (D-022), never "no restriction".

Generated from the pilot run of the city-ordinance pipeline on 2026-10-20 (8 cities). Fee schedules that the pipeline could open are coded separately and are not repeated here.

## Akron, OH (GEOID 3901000)

- **Pipeline status:** blocked; official code: https://codelibrary.amlegal.com/codes/akron/latest/overview (codelibrary.amlegal.com)
- **Blocked:** https://codelibrary.amlegal.com/codes/akron/latest/overview (HTTP 403 Forbidden on the official Akron Codified Ordinances (American Legal). Not retried); https://www.akronohio.gov/robots.txt (HTTP 403 Forbidden on robots.txt. Could not confirm crawling is allowed, so no city-site p)
- **Fees coded by the pipeline:** 0

**To look up:**

Open the official Akron Codified Ordinances in a browser at https://codelibrary.amlegal.com/codes/akron/latest/overview (it returned 403 to the automated fetch). Then: (1) In Title 15, Chapter 153 Zoning Code, look at the residential districts (R-1 single-family, R-2 two-family, etc.) and the accessory-use section (reported as 153.260). Check whether an accessory dwelling unit use exists, which zones allow it, size and lot limits, owner occupancy, parking, rentability, and whether two-, three- and four-family dwellings are allowed in single-family zones. Also check whether the Form-Based Code reportedly adopted around March 2024 changes any of this. (2) Read the code's history notes for ordinance numbers and dates since 2010 that cover ADUs, two- to four-unit housing, parking minimums and fees. (3) Find the Building Division permit fee schedule and the Akron Water/Sewer tap and connection fees on https://www.akronohio.gov/ (robots.txt returned 403). (4) Check Akron City Council legislation and minutes (start from https://www.akronohio.gov/ city council pages) for a 2026 zoning amendment. Secondary press reported the city was taking public comment on a proposal (around June 2026) to allow duplexes, triplexes and accessory units and to relax the 4,000 sq ft minimum lot size. Confirm whether council has introduced or adopted it, and record the ordinance number and dates.

## Canton, OH (GEOID 3912000)

- **Pipeline status:** blocked; official code: https://codelibrary.amlegal.com/codes/canton/latest/canton_oh/0-0-0-46288 (American Legal Publishing (codelibrary.amlegal.com))
- **Blocked:** https://codelibrary.amlegal.com/codes/canton/latest/canton_oh/0-0-0-46288 (HTTP 403 Forbidden on the American Legal Publishing page for Canton's Codified Ordinances,)
- **Fees coded by the pipeline:** 2

**To look up:**

The official Canton Codified Ordinances on American Legal Publishing returned 403, so a person needs to open it in a browser, starting at https://codelibrary.amlegal.com/codes/canton/latest/canton_oh/0-0-0-46288 (Part Eleven, Planning and Zoning Code). Look up: (1) the 'current through' date; (2) the residential district chapters (which districts allow single-family only, and whether two-, three- and four-family dwellings are permitted, conditional or not allowed there), plus minimum lot area per unit, height or stories, and parking per unit (parking chapter); (3) Chapters 1139 (Permitted Accessory Buildings and Structures) and 1140 (Permitted Accessory Uses), and the definitions chapter, for any accessory dwelling, granny flat or carriage house rule: size cap, owner occupancy, whether it can be rented, parking; (4) section history notes (Ord. No., passed dates) for changes since 2010. Fees: the building permit fees beyond $100 for a single-family home (two-family and multifamily, plan review), and the water tap and meter fees, are not posted. Ask the Engineering Dept at 330-489-3381 or Building at 330-489-3283, or look at Codified Ordinances Chapter 943 (sewer) and the water chapters. Council legislation is at https://www.cantonohio.gov/AgendaCenter.

## Parma, OH (GEOID 3961000)

- **Pipeline status:** blocked; official code: https://codelibrary.amlegal.com/codes/parma/latest/Parma_oh/0-0-0-213444 (codelibrary.amlegal.com (American Legal Publishing))
- **Blocked:** https://codelibrary.amlegal.com/codes/parma/latest/Parma_oh/0-0-0-213444 (HTTP 403 Forbidden from American Legal Publishing (the official host of Parma's Codified O)
- **Fees coded by the pipeline:** 1

**To look up:**

Parma's Codified Ordinances on American Legal returned HTTP 403, so a human must look these up there, starting at https://codelibrary.amlegal.com/codes/parma/latest/Parma_oh/0-0-0-213444.
(1) Planning and Zoning Code (Part Eleven): the single-family house district chapter (permitted uses, any accessory dwelling or in-law suite rules, lot area per dwelling) and the two-family district chapter. Record whether 2-4 units are allowed in single-family zones, and whether by right or only by rezoning or conditional use.
(2) The off-street parking chapter for residential minimums.
(3) The history notes on those sections (ordinance numbers and dates since 2010), and the code's "current through" date.
(4) Fees: the official "All Fees For Permits" schedule at https://www.cityofparma-oh.gov/DocumentCenter/View/153 (a PDF, apparently from 2018, that could not be read as a page). Also C.O. 185.04 and 185.05 at https://codelibrary.amlegal.com/codes/parma/latest/Parma_oh/0-0-0-196641 and -196650, and C.O. 1505.15 (permits and surcharges) at -214622. From these, get the full new single-family building permit fee and its basis.
(5) Water and sewer tap or connection fees. Parma gets water from Cleveland Water, and sewer may be handled by the City Engineering/Service Department or the Northeast Ohio Regional Sewer District (NEORSD). Ask the Building Department (440-885-8030).
(6) Council legislation since 2010 on ADUs, two-family uses or parking: start at https://cityofparma-oh.gov/AgendaCenter and https://cityofparma-oh.gov/221/City-Council.

## Pasadena, TX (GEOID 4856000)

- **Pipeline status:** partial; official code: https://library.municode.com/tx/pasadena/codes/code_of_ordinances (Municode (library.municode.com); land-use ordinances also posted as PDFs at pasadenatx.gov/279/Codes-Ordinances)
- **Blocked:** https://library.municode.com/tx/pasadena/codes/code_of_ordinances (library.municode.com/robots.txt returned 403 Forbidden; robots could not be verified, so t)
- **Fees coded by the pipeline:** 5

**To look up:**

1) Open the Pasadena TX Code of Ordinances on Municode: https://library.municode.com/tx/pasadena/codes/code_of_ordinances. Look in Ch. 9 (Building and General Regulations, incl. Sec. 9-76 setbacks and the off-street parking and multi-family articles) for rules on garage apartments, accessory or secondary dwellings and duplexes on residential lots. Record parking minimums per dwelling and any minimum lot area per unit. Also look in the Water and Sewer chapter for tap, connection and impact fees. Note each section's history notes, giving ordinance numbers and dates since 2010. 2) Read the land-use ordinance PDFs at https://www.pasadenatx.gov/279/Codes-Ordinances, especially Multi-Family (DocumentCenter/View/466), Townhome (469), Patio Homes (467), Off-Street Parking (472), Setback Requirements (473) and Basic Subdivision (468). They define the unit count that triggers the multi-family rules, the lot area per unit and parking per unit. 3) Read the Planning Department FAQs PDF (DocumentCenter/View/10302) and the No Zoning Letter (DocumentCenter/View/10289); WebFetch could not decode either. 4) Ask Public Works or Utility Billing (Permit Dept 713-475-5575) for current water and sewer tap fees by meter size. 5) Search council agendas and ordinances at https://www.pasadenatx.gov/450/Ordinances for amendments since 2010 to the multi-family, parking and fee ordinances.

## Greenville, NC (GEOID 3728080)

- **Pipeline status:** blocked; official code: https://codelibrary.amlegal.com/codes/greenvillenc/latest/ (codelibrary.amlegal.com)
- **Blocked:** https://codelibrary.amlegal.com/codes/greenvillenc/latest/ (HTTP 403 Forbidden on fetch (robots.txt permits); not retried); https://www.greenvillenc.gov/robots.txt (HTTP 403 Forbidden; city site (including UDO page https://www.greenvillenc.gov/605/Unified); https://library.municode.com/robots.txt (HTTP 403 Forbidden; not used)
- **Fees coded by the pipeline:** 0

**To look up:**

Both official sources returned HTTP 403 to automated fetches. Search snippets (not verified, not citable) say Greenville adopted its first Unified Development Ordinance on 2025-11-13, effective 2026-03-01, and that it replaces Title 9 Ch. 4 (Zoning) and Ch. 5 (Subdivisions). A human should: (1) open the UDO PDF from https://www.greenvillenc.gov/605/Unified-Development-Ordinance (or the American Legal code at https://codelibrary.amlegal.com/codes/greenvillenc/latest/). From it, record the ADU use standards (zones, by-right or SUP, max size or share of the main house, owner occupancy, parking, rental), the treatment of duplex, triplex and quadplex uses in the single-family districts (R15S, R9S, R6S or their UDO equivalents), lot area per unit, height and parking; (2) for history, get the UDO adoption ordinance number and any 2010-2025 Chapter 4 amendments on ADUs, duplexes and parking from the code history notes or City Council minutes (greenvillenc.gov Agendas and Minutes); (3) for fees, use the City of Greenville Inspections/Planning fee schedule (building permit) and Greenville Utilities Commission (guc.com) water and sewer tap and capacity/system development fees for a single-family home, an ADU and a 2-4 unit building.

## Corpus Christi, TX (GEOID 4817000)

- **Pipeline status:** blocked; official code: http://online.encodeplus.com/regs/corpuschristi-tx/doc-viewer.aspx#secid-1 (enCodePlus (online.encodeplus.com); fee ordinance on Municode)
- **Blocked:** http://online.encodeplus.com/regs/corpuschristi-tx/doc-viewer.aspx#secid-1 (This is the official Unified Development Code, linked from the city's UDC page as 'View th); https://library.municode.com/tx/corpus_christi/codes/code_of_ordinances (The city's Code of Ordinances, which includes Ch. 14 Development Services and Art. XIII De)
- **Fees coded by the pipeline:** 6

**To look up:**

The official Unified Development Code is on enCodePlus at http://online.encodeplus.com/regs/corpuschristi-tx/doc-viewer.aspx, linked from https://www.corpuschristitx.gov/department-directory/development-services/unified-development-code-udc/. robots.txt disallows /regs/ for AI agents, so a human needs to read it. Look up: (1) the UDC Article 4 residential district tables (RS-6, RS-4.5 and similar single-family districts) to see whether duplexes, triplexes and fourplexes are permitted, need a Special Permit, or are not allowed; (2) the UDC accessory-use section covering accessory dwelling units or 'servant's quarters'/guest houses (aggregators point to §5.3.2 but this is unverified), checking permitted districts, maximum size, owner occupancy, rental, parking and minimum lot size; (3) Article 7 parking minimums per unit; (4) the code's history notes and 'current through' date. For history since 2010, search the Legistar council records (https://corpuschristi.legistar.com/Legislation.aspx) for 'Unified Development Code' text amendments. The city amends the UDC on an annual cycle with Council action in August, effective October 1 (see IB 001: https://www.corpuschristitx.gov/media/c22f4552/ibs-001-udc-text-amendments-code-cycle-2026.pdf). A February 2024 Development Task Force presentation (https://www.corpuschristitx.gov/media/jzxhe0yy/ds-taskforce-presentation-22024-1.pdf) lists ADUs as a UDC update topic. Fees: the FY2026 schedule has no ADU-specific fee and no water meter/tap or wastewater tap fees beyond the Infrastructure Trust Fund lot fees. Water and wastewater tap fees are set separately by Corpus Christi Water: check the Water Department fee schedule and Code of Ordinances Ch. 55 on Municode (Municode's robots.txt returned 403, so it was not read). Confirm whether there are impact fees (none are listed in the development fee schedule).

## Cary, NC (GEOID 3710740)

- **Pipeline status:** partial; official code: not located (www.carync.gov (Town of Cary Land Development Ordinance; host blocked))
- **Blocked:** https://www.carync.gov/robots.txt (HTTP 403 on robots.txt; the Town's main site (LDO, ACT 32 hearing page, fee schedule) was ); https://library.municode.com/robots.txt (HTTP 403 on robots.txt; not fetched.)
- **Fees coded by the pipeline:** 0

**To look up:**

The official Cary Land Development Ordinance (LDO), ACT item pages and fee schedule are all on www.carync.gov, whose robots.txt returned 403, so they were not fetched. A human should look up: (1) LDO Chapter 5 accessory dwelling unit section (current after ACT 32): whether permitted by right, max size (reported 50% of primary dwelling, 800 sq ft cap for detached), ADUs per lot, owner-occupancy, rental, parking (reported 1 space/ADU), minimum lot; (2) LDO use table for duplex/triplex/quadplex in R-80, R-40, R-30, R-20, R-12, R-8 districts and any ACT amendments since 2010 (also NC S.L. 2023 changes); (3) parking minimum changes; (4) Town of Cary FY2026 fee schedule: building permit, development fees, water and sewer capacity/development fees for one single-family home, one ADU, 2-4 unit building. Start at https://www.carync.gov/connect-engage/transparency/public-hearings/public-hearing-cases/ldo-amendments-act-items/2024-act-items (ACT 32 record: council hearing July 25, 2024; P&Z Aug 26, 2024) and the Town's LDO page on carync.gov, plus the citizen guide https://www.carync.gov/connect-engage/town-departments-offices/planning-and-development-services/faq/citizen-guide-to-accessory-dwelling-units.

## Fayetteville, NC (GEOID 3722920)

- **Pipeline status:** partial; official code: https://online.encodeplus.com/regs/fayetteville-nc/doc-viewer.aspx#secid-9269 (enCodePlus (online.encodeplus.com))
- **Blocked:** https://online.encodeplus.com/regs/fayetteville-nc/doc-viewer.aspx#secid-9269 (Official UDO host (Chapter 30, linked from the city site). robots.txt disallows /regs/ for); https://library.municode.com/robots.txt (HTTP 403 on robots.txt; the host was not fetched further)
- **Fees coded by the pipeline:** 9

**To look up:**

The official UDO (City Code Chapter 30) is on enCodePlus, whose robots.txt blocks /regs/ for all crawlers except Google and Bing. Ben, or another person working by hand, should open https://online.encodeplus.com/regs/fayetteville-nc/doc-viewer.aspx#secid-9269 and record: (1) the ADU rules in the use-specific standards for accessory dwelling units (the Article 30-4 use standards): which districts allow them (SF-15, SF-10, SF-6 etc.), by right or by permit, max sq ft or share of the main house, owner-occupancy, parking, number per lot and minimum lot size; (2) the use table for duplex, triplex/quadplex and two-to-four-family dwellings in the SF districts, with lot size per unit, height and parking (Article 30-5 off-street parking); (3) the history notes on each section (ordinance numbers and dates since 2010, especially any ADU, missing middle or parking amendments). For council history, search https://cityoffayetteville.legistar.com/Legislation.aspx for 'accessory dwelling', 'text amendment', 'duplex' and 'parking', confirming the site is Fayetteville NC. Fees: check whether an FY26 or FY27 City Fee Schedule has replaced the FY25 PDF (Permitting & Inspections page), and look for a separate ADU building-permit line. The City of Fayetteville charges no impact fee in its fee schedule; Fayetteville PWC sets water and sewer charges.

