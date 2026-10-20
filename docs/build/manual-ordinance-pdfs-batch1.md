# Ordinance PDFs to fetch by hand (batch 1)

From the city-ordinance pipeline's first batch (2026-10-20): 20 Minnesota cities plus Austin, Raleigh and Durham. Each item is an official document the pipeline found but could not read, because robots.txt disallows it, the host returned 403 or a bot challenge, or it needs a login. Download it in a browser and save it under `~/lotline-data/manual/ordinances/<city>/` (outside the repo), then register it with `lotline manifest register` so it is logged like any download. Items the pipeline could read are already captured, with quotes, and are not repeated here.


## Minneapolis, MN

- [ ] **Ordinance:** Accessory dwelling units allowed citywide (zoning text amendment) (2014)  
  https://www.minneapolismn.gov/business-services/planning-zoning/applications-handouts/land-use-applications/accessory-dwelling-unit  
  _Why manual:_ Only the city's current ADU page was read. The 2014 ordinance PDF was not located; it would be on LIMS, which blocks automated access.
- [ ] **Ordinance:** Residential buildings with up to 3 units amendment (first Minneapolis 2040 zoning change) (2020-01-01)  
  https://www2.minneapolismn.gov/business-services/planning-zoning/amendments/adopted-proposed/recently-adopted/residential-buildings-3-units-amendment  
  _Why manual:_ The page returns a 301 redirect to the generic amendments landing page. The www2 robots.txt could not be read because of a redirect loop. Th
- [ ] **Ordinance:** Built Form Regulations (Built Form Overlay Districts, Chapter 552) (2021-01-01)  
  https://lims.minneapolismn.gov/File/2020-00984  
  _Why manual:_ lims.minneapolismn.gov returned 403 for robots.txt, so the site was treated as blocked. Dates come from minneapolis2040.com/implementation/b
- [ ] **Ordinance:** Off-Street Parking and Travel Demand Management Ordinance (2021-05-22)  
  http://lims.minneapolismn.gov/Download/File/5217/Off-Street%20Parking%20and%20Travel%20Demand%20Management%20Ordinance--Amended%2005-04-2021.pdf  
  _Why manual:_ The LIMS host returned 403 for robots.txt, so it was treated as blocked. Dates and summary come from minneapolis2040.com/implementation/park
- [ ] **Ordinance:** Land use rezoning policies of Minneapolis 2040 ordinances (Land Use Rezoning Study) (2023-07-01)  
  https://lims.minneapolismn.gov/file/2023-00172  
  _Why manual:_ The LIMS host returned 403 for robots.txt. The effective date comes from the city's land-use-rezoning-study page, which was read.
- [ ] **Ordinance:** Land use application fees (zoning amendment) (2024-05-23)  
  https://lims.minneapolismn.gov/file/2024-00314  
  _Why manual:_ The LIMS host returned 403 for robots.txt. Only the effective date was taken from the city's adopted amendments page.
- [ ] **Ordinance:** Residential dwelling (1-3 units) regulation updates ordinances (PROPOSED, not adopted)  
  https://lims.minneapolismn.gov/Download/Agenda/9343/6252/Proposed-Zoning-Code-Text-Amendments-Development-standards-for-dwellings-with-one-to-three-units.pdf  
  _Why manual:_ The LIMS host returned 403 for robots.txt. Status comes from the city's housing-1-3-units amendment page, which was read.
- [ ] **Look up:** Adopted 2019 ordinance allowing up to 3 units on residential lots (effective Jan 1, 2020): ordinance number, adoption date and signed PDF  
  https://www2.minneapolismn.gov/media/content-assets/www2-documents/business/Staff-report-and-draft-ordinance-prepared-for-the-City-Planning-Commission-(October-7,-2019),wcmsp-220995.pdf  
  _Why manual:_ The www2 robots.txt could not be read because of a redirect loop, and the adopted ordinance lives on LIMS (blocked). The staff report holds 
- [ ] **Look up:** 2014 citywide ADU ordinance: ordinance number, adoption and effective dates, PDF  
  https://lims.minneapolismn.gov/  
  _Why manual:_ Not located. Pre-2016 council records are in LIMS or the City Clerk's legislative archive, and LIMS is blocked.
- [ ] **Look up:** Historical building permit fee schedules for 2016-2018 and 2020-2025 (to confirm the rates were unchanged since 2019), and SAC/WAC per-unit charges (city SAC page returned 404; check the Met Council S  
  https://www.minneapolismn.gov/business-services/licenses-permits-inspections/construction-permits/permits-overview/fees/  
  _Why manual:_ There is no archive of past fee schedules on the city site. The fee ordinance (Code Title 5, ch. 91) history would need the City Clerk or LI
- [ ] **Look up:** Parkland dedication fee per unit for earlier years (2016-2025)  
  https://www.minneapolismn.gov/business-services/licenses-permits-inspections/construction-permits/permits-overview/fees/parkland-dedication-fee/schedule/  
  _Why manual:_ Only the 2026 rate ($2,043 per unit, effective Apr 1, 2026) is published. Earlier annual rates need LIMS or the City Clerk.

## St. Paul, MN

- [ ] **Ordinance:** ADUs as permitted use near University Avenue (Green Line corridor) (2016-09-14 (unverified))  
  https://www.stpaul.gov/sites/default/files/Media%20Root/Safety%20%26%20Inspections/dsi.zoning.ADU112016.pdf  
  _Why manual:_ Scanned image PDF; no text layer, so the content could not be extracted
- [ ] **Ordinance:** Citywide ADU expansion (2018-10 (unverified; council vote 6-1 per search summary))  
  https://www.stpaul.gov/sites/default/files/Media%20Root/Safety%20%26%20Inspections/Ord%2018-28.pdf  
  _Why manual:_ Scanned image PDF (CCITT fax images); no text layer, so the content could not be extracted
- [ ] **ADU program:** ADUs and the Building Code (DSI handout) (2023-12)  
  https://www.stpaul.gov/sites/default/files/2023-12/ADUsAndTheBuildingCode.pdf  
  _Why manual:_ Not fetched (fetch budget)
- [ ] **ADU program:** ADU sewer/water connection guidance letter (2023-02)  
  https://www.stpaul.gov/sites/default/files/2023-04/DSI.Bldg_Plumbing_ADU%20guidance%20letter%202-23.pdf  
  _Why manual:_ Not fetched (fetch budget)
- [ ] **Look up:** Ordinance 23-43 as adopted (clerk version linked from the ADU page): check the H1/H2 maximum principal units table (base 4, bonus to 6) and the ADU changes.  
  https://www.stpaul.gov/sites/default/files/2023-11/CC_Ordinance_23-43.pdf  
  _Why manual:_ Not fetched; the tables in the remediated version read were only partly extractable
- [ ] **Look up:** Building permit fee schedules for 2016-2021 and 2024-2026 (Leg. Code Sec. 33.04). Only the Feb 2022 and Feb 2023 schedules were found. The city moved to the PAULIE permitting system (opened Sept 17),   
  https://www.stpaul.gov/departments/safety-inspections/building-and-construction/construction-permits-and-inspections/building-permits-inspections/building-information-applications  
  _Why manual:_ No archive of older schedules found online; landing page only
- [ ] **Look up:** Saint Paul Regional Water Services water connection/tap fees and city sanitary sewer connection permit fees for a single-family home, an ADU and a 2-4 unit building  
  https://www.stpaul.gov/departments/water  
  _Why manual:_ Not located within the search/fetch budget
- [ ] **Look up:** Met Council SAC Procedure Manual: SAC unit factors for ADUs and 2-4 unit dwellings, and historical SAC rates for 2016-2025  
  https://metrocouncil.org/Wastewater-Water/Funding-Finance/Rates-Charges/Sewer-Availability-Charge/SAC-basics-for-local-government/2025-Jan-Update/2025-SAC-Procedure-Manual.aspx  
  _Why manual:_ Not fetched (fetch budget)
- [ ] **Look up:** Current parkland dedication fee per unit (check whether $1,200 has been adjusted after 2020) and later annual fee reports  
  https://www.stpaul.gov/departments/parks-recreation/design-construction/parkland-dedication-ordinance  
  _Why manual:_ Page gives no current amount; only the 2015 ordinance and the 2020 report were read
- [ ] **Look up:** Any St. Paul or HRA ADU loan, grant, fee waiver or pre-approved plan program. None was found on city pages; confirm with PED/HRA.  
  https://www.stpaul.gov/departments/planning-and-economic-development  
  _Why manual:_ No program page found within the search budget

## Rochester, MN

- [ ] **Ordinance:** Unified Development Code (UDC), Chapter 60 (new zoning ordinance replacing the Land Development Manual) (2023-01-01)  
  https://media-002-us.cdn.govstack.com/rochestermn-us/media/poageesh/unified-development-code.pdf  
  _Why manual:_ Read the current consolidated UDC (version January 2026, 488 pages). The adopting ordinance as passed on 2022-09-07 and its number were not 
- [ ] **Ordinance:** 2025 Fee Schedule (City of Rochester master fee schedule)  
  https://media-002-us.cdn.govstack.com/rochestermn-us/media/0lvmderc/2025-fee-schedule.pdf  
  _Why manual:_ The schedule was read, but the adopting resolution or ordinance number and the effective date are not printed on it. Pull them from the coun
- [ ] **Ordinance:** 2026 Master Fee Schedule (Amended V5, Final for Ordinance)  
  https://media-002-us.cdn.govstack.com/rochestermn-us/media/v5tnpxns/2026-master-fee-schedule-ammendedv5-final-for-ordinance.pdf  
  _Why manual:_ The ordinance number and adoption date are not in the PDF. Get them from the council agenda or minutes.
- [ ] **ADU program:** ADU Pilot Program (fee reimbursement)  
  https://www.rochestermn.gov/business-development/building-renovating/accessory-dwelling-units-adus/  
  _Why manual:_ Program page read. The Policy Guidelines and application PDFs (old links rochestermn.gov/home/showpublisheddocument/38054 and /38056) now re
- [ ] **Look up:** UDC adopting ordinance as passed on 2022-09-07: the ordinance number and signed PDF. Also any UDC amendment ordinances from 2023-2026 that touch ADUs, duplex-fourplex uses or parking (the consolidated  
  https://www.rochestermn.gov/business-development/planning-zoning/unified-development-code-udc/  
  _Why manual:_ Not posted on the city page. The council meeting portal (rochestercitymn.iqm2.com) refused connections, and the search budget ran out.
- [ ] **Look up:** Fee schedules for 2016, 2017 and 2018. The archive lists only 2019-2025.  
  https://www.rochestermn.gov/council-administration/plans-reports-studies/financial-reports-archive/#misc  
  _Why manual:_ Not posted online. Request them from the City Clerk or Finance, or find them in council meeting packets.
- [ ] **Look up:** Adopting resolution or ordinance numbers and effective dates for each annual fee schedule (2019-2026), especially the 2025 change of IRC plan review from 35% to 65%.  
  https://www.rochestermn.gov/council-administration/budget-finances/fee-schedule/?navid=3897  
  _Why manual:_ The fee schedule PDFs do not print adoption details.
- [ ] **Look up:** Rochester Public Utilities (RPU) water connection and meter fees for new SF, ADU and 2-4 unit buildings. The city schedule covers the sewer PIF and city sewer/water connection charges only.  
  https://www.rpu.org  
  _Why manual:_ Not checked within budget.

## Bloomington, MN

- [ ] **Ordinance:** Missing Middle Housing Phase I Ordinance (amends ADU, duplex and townhouse standards, City Code Chapter 21) (2025-05-19)  
  https://letstalk.bloomingtonmn.gov/21178/widgets/70879/documents/66715  
  _Why manual:_ Link triggers a file download (Phase I Missing Middle Housing Ordinance.pdf); fetch returned only a download notice, no text. robots.txt ret
- [ ] **Ordinance:** Missing Middle Housing Phase II Ordinance (Case PL202500199, amends City Code Chapter 21) (2026-03-23)  
  https://letstalk.bloomingtonmn.gov/21178/widgets/70879/documents/79411  
  _Why manual:_ Link triggers a file download (Missing Middle Housing Phase II Ordinance.pdf); fetch returned only a download notice.
- [ ] **Ordinance:** Accessory Dwelling Unit (ADU) Code Amendments: detached ADUs (draft 2021-22)  
  https://letstalk.bloomingtonmn.gov/15120/widgets/51369/documents/32979  
  _Why manual:_ Let's Talk Bloomington returned a sign-in page (login wall) for this project and its documents.
- [ ] **Ordinance:** City SAC Fee (sanitary sewer capacity charge) ordinance (2025-01-01)  
  https://www.bloomingtonmn.gov/pw/briefing/city-council-addresses-sanitary-sewer-capacity-2025-01-29  
  _Why manual:_ City news briefing read; the ordinance PDF itself was not located (number unknown). Year of adoption inferred from article date 2025-01-29.
- [ ] **Look up:** Phase II Council staff report 3/23/2026 (summary of zone allowances and parking)  
  https://letstalk.bloomingtonmn.gov/21178/widgets/70879/documents/79410  
  _Why manual:_ Download-only link, not attempted after the ordinance link returned no text
- [ ] **Look up:** Phase I Council staff report 5/19/2025  
  https://letstalk.bloomingtonmn.gov/21178/widgets/70879/documents/69565  
  _Why manual:_ Download-only link, not attempted
- [ ] **Look up:** ADU Code Amendments project page (adoption date of detached ADU ordinance)  
  https://letstalk.bloomingtonmn.gov/accessory-dwelling-unit-adu-code-amendments  
  _Why manual:_ Login wall (sign-in page)
- [ ] **Look up:** Phase I public hearing notice (case number, ordinance summary)  
  https://bloomingtonmn.gov/plan/news/notice-public-hearing-missing-middle-housing-ordinance-phase-i-2025-05-01  
  _Why manual:_ HTTP 403
- [ ] **Look up:** Phase II public hearing notice (Case PL202500199)  
  https://www.bloomingtonmn.gov/plan/news/public-hearing-missing-middle-housing-phase-ii-ordinance-2026-02-12  
  _Why manual:_ HTTP 403
- [ ] **Look up:** Ordinance 2021-20 (fee appendix with water/sewer connection fees $95/$257/$95 per search snippet)  
  https://www.bloomingtonmn.gov/sites/default/files/2021-08/Ord%202021-20_0.pdf  
  _Why manual:_ HTTP 404 on fetch
- [ ] **Look up:** Original 2009 ADU ordinance staff report, Case 10000A-09 (pre-2010 baseline, attached/internal ADUs only)  
  https://www.bloomingtonmn.gov/sites/default/files/media/adu_agenda_staff_report.pdf  
  _Why manual:_ HTTP 404 on fetch
- [ ] **Look up:** Annual city fee schedules / fee ordinances 2016-2025 (park dedication, permit fee tables by year)  
  https://www.bloomingtonmn.gov/  
  _Why manual:_ Only a 2018-revision permit fee table and a 2022 estimate flyer were found; yearly fee ordinances not located

## Duluth, MN

- [ ] **Ordinance:** An ordinance amending Sections 50-14, 50-19, 50-20, 50-21 and 50-41, related to dwellings and tiny houses (2019-10-28)  
  https://webapi.legistar.com/v1/duluth-mn/matters/5188/texts/5264  
  _Why manual:_ Ordinance text read through the Legistar API (that host has no robots.txt). The PDF attachments, including Attachment 3 (the 50-19.8 use tab
- [ ] **Ordinance:** An ordinance amending Sections 50-18.5, 50-19.8, 50-20.1, 50-20.3, 50-20.5, 50-24 and 50-41, relating to off-street parking requirements in the Unified Development Chapter (2023-12-11)  
  https://webapi.legistar.com/v1/duluth-mn/matters/10006/texts/10112  
  _Why manual:_ Text read through the Legistar API. The draft text has '[insert effective date]', so the effective date is not confirmed. Attachments (Table
- [ ] **Ordinance:** Chapter 29A amendment incorporating UDC parking requirements into the housing and rental code (2023-12-11)  
  https://webapi.legistar.com/v1/duluth-mn/matters/10021  
  _Why manual:_ Only the matter listing (title, passed date and enactment number) was read; the ordinance text was not fetched.
- [ ] **Ordinance:** Ordinance amending dimensional standards in residential and mixed-use zone districts (2024-06-03)  
  https://duluthmn.gov/media/pfydr42k/24-011-o.pdf  
  _Why manual:_ HTTP 404 when fetched. Try the Legistar matter 10547 attachments on duluth-mn.legistar1.com (robots-disallowed).
- [ ] **Ordinance:** An ordinance amending Chapter 50 of the Duluth City Code, 1959, as amended, relating to revisions of the Unified Development Chapter (2026-08-31)  
  https://webapi.legistar.com/v1/duluth-mn/matters/13043/texts/13202  
  _Why manual:_ Ordinance text read through the Legistar API. The adopted code PDFs (Attachments 1-7 and the cover memo) are on duluth-mn.legistar1.com, who
- [ ] **Ordinance:** Ordinance on requirements for establishing city fees (Sections 2-5, 31-6, 31-8) (2018-09-10)  
  https://webapi.legistar.com/v1/duluth-mn/matters/4148  
  _Why manual:_ Only the matter listing was read.
- [ ] **Ordinance:** UDC amendment: administrative adjustments for off-street parking flexibility (2018-04-09)  
  https://webapi.legistar.com/v1/duluth-mn/matters/3780  
  _Why manual:_ Only the matter listing was read.
- [ ] **Ordinance:** UDC amendments: general circulation and required parking spaces (2016-07-11)  
  https://webapi.legistar.com/v1/duluth-mn/matters/2198  
  _Why manual:_ Only the matter listing was read.
- [ ] **Look up:** 26-019-O (Ord. 10976) adopted attachments: Attachment 3 (Article III, use table 50-19.8, R-1 rows for two-family, townhouse and multi-family) and the cover memo  
  https://duluth-mn.legistar1.com/duluth-mn/attachments/10fd51c1-1f5e-4277-85b9-bc79106ff398.pdf  
  _Why manual:_ robots.txt on duluth-mn.legistar1.com is 'Disallow: /' for all agents. Cover memo: https://duluth-mn.legistar1.com/duluth-mn/attachments/f7f
- [ ] **Look up:** 19-050-O (Ord. 10659) Attachment 3, the 50-19.8 permitted use table (did it make two-family or ADUs permitted in R-1 in 2019?), and the Sep 2019 staff memo  
  https://duluth-mn.legistar1.com/duluth-mn/attachments/eafd4afa-e0f5-4358-a655-2104b3345037.pdf  
  _Why manual:_ robots.txt disallows all agents. Staff memo: https://duluth-mn.legistar1.com/duluth-mn/attachments/4d60be36-3cd1-4c22-86d5-89c09d69ca6f.pdf.
- [ ] **Look up:** 23-048-O (Ord. 10868) parking ordinance as adopted, with its effective date and Table 50-24-1 attachment  
  https://duluth-mn.legistar1.com/duluth-mn/attachments/9d253ad9-946d-4511-8fca-2ddcac019f5b.pdf  
  _Why manual:_ robots.txt disallows all agents. Other attachments are .docx files at the same host.
- [ ] **Look up:** Residential valuation schedule, to turn the 2026 permit formula into dollar fees for a new single-family home, ADU or duplex  
  https://duluthmn.gov/media/e4en0pwz/handout-residential-valuation-schedule-140.pdf  
  _Why manual:_ Not fetched (fetch budget). It is robots-allowed and can be fetched next run.
- [ ] **Look up:** Prior-year (2016-2025) CSI Fee Schedule for Permits and the Chapter 31 fee schedule/resolutions; also water/sewer (Comfort Systems) tap or connection charges  
  https://duluthmn.gov/csi/permits-applications/permit-fees/  
  _Why manual:_ Only the current 2026 schedule is posted. Archived years are not linked, so request them from Permitting Services or the Legistar fee resolu
- [ ] **Look up:** Duluth Legislative Code (Chapter 50 and Chapter 31) on Municode  
  https://library.municode.com/mn/duluth/codes/legislative_code  
  _Why manual:_ library.municode.com returned 403 even for robots.txt.

## Brooklyn Park, MN

- [ ] **Ordinance:** Ordinance #2024-__ amending Chapter 152 (Zoning Code) for consistency with the 2040 Comprehensive Plan (Title XV update)  
  https://www.brooklynpark.org/wp-content/uploads/2024/04/20240410-Agenda-Item-6.6.pdf  
  _Why manual:_ Read the Planning Commission staff report with the draft summary ordinance (#2024-_____). The adopted ordinance and its number were not foun
- [ ] **Fee schedule:** FY current (2026 web page, undated)  
  https://www.brooklynpark.org/?p=1866  
  _Why manual:_ Read the city's 'Estimated Costs' (development costs) web page. No adopted fee schedule ordinance or PDF is linked. The official schedule ap
- [ ] **Fee schedule:** FY current (2026 web page; ICC valuation table updated every February)  
  https://www.brooklynpark.org/building-permits-and-inspections/permit-and-plan-review-fees/  
  _Why manual:_ The page gives only per-square-foot valuation rates (new home $169.09/sf; unfinished basement $31.50/sf). The permit fee table that converts
- [ ] **Look up:** Current Brooklyn Park City Code: fee schedule appendix or chapter (building permit fee table, plan review %, WAC, park dedication), plus the ordinance history notes for Chapter 152 (adopted 2024 zonin  
  https://codelibrary.amlegal.com/codes/brooklynpark/latest/overview  
  _Why manual:_ HTTP 403 for automated fetch. robots.txt does not disallow general agents, but the host blocks them.
- [ ] **Look up:** Annual fee schedule ordinances or resolutions, 2016-2025 (usually adopted each December with the budget). Look in council agendas and minutes for 'fee schedule'.  
  https://www.brooklynpark.org/  
  _Why manual:_ No fee schedule PDF is linked from the city's fee pages, and on-site search (/?s=) is disallowed by robots.txt
- [ ] **Look up:** City Council minutes, July 13, 2026 (and the June 22, 2026 first reading): confirm the ADU ordinance was tabled and get the vote  
  https://www.brooklynpark.org/accessory-dwelling-units/  
  _Why manual:_ Official minutes not located within the search budget. Only a third-party aggregator (GatherGov) reported the tabling, alongside the city's 
- [ ] **Look up:** Development contracts / surety / escrow zoning text amendment (§152.310), planned for late 2025 or early 2026; may change fees and escrows  
  https://www.brooklynpark.org/wp-content/uploads/2025/10/10082025-PC-Work-Session-Minutes-1-1.pdf  
  _Why manual:_ Only work-session minutes were found. Adoption status is unknown.

## Plymouth, MN

- [ ] **Ordinance:** 2023 ADU zoning ordinance amendments (amends ADU section of Zoning Ordinance, Chapter 21)  
  https://plymouthmn.gov/home/showpublisheddocument/26195/638348680157270000  
  _Why manual:_ plymouthmn.gov returned HTTP 403 for robots.txt (both www and bare host), so the host blocks this agent; no pages fetched. Search snippet sa
- [ ] **Ordinance:** Draft ADU ordinance (Ordinance No. 2023-**), council packet for the Aug. 8, 2023 meeting  
  https://plymouthmn.gov/home/showpublisheddocument/25699/638245992099330000  
  _Why manual:_ Host returned 403 for robots.txt; not fetched.
- [ ] **Fee schedule:** FY 2024 (inferred)  
  https://plymouthmn.gov/home/showpublisheddocument/222/638397801142830000  
  _Why manual:_ Host returned 403 for robots.txt; not fetched. This is document 222, a version with a timestamp around late Dec 2023, probably the 2024 city
- [ ] **Fee schedule:** FY 2026 (inferred, current)  
  https://www.plymouthmn.gov/home/showpublisheddocument/222/639039779195030000  
  _Why manual:_ Host returned 403 for robots.txt; not fetched. Same document 222, newer version with a timestamp around Jan 2026, probably the current fee s
- [ ] **Look up:** plymouthmn.gov robots.txt: check whether the city site allows crawling (it returned 403 to this agent)  
  https://www.plymouthmn.gov/robots.txt  
  _Why manual:_ HTTP 403 for both www and bare host
- [ ] **Look up:** City news item announcing ADU amendments for the Aug. 8, 2023 council meeting (confirms dates)  
  https://www.plymouthmn.gov/Home/Components/News/News/7970/2158  
  _Why manual:_ Host blocks agent (403)
- [ ] **Look up:** Plymouth City Code: Chapter 21 Zoning (RSF district permitted uses, i.e. whether duplexes/2-4 units are allowed; parking minimums) and the fee schedule section. Also get the ordinance history list for  
  https://codelibrary.amlegal.com/codes/plymouthmn/latest/overview  
  _Why manual:_ robots.txt allows it, but the page returned 403; the code host URL may also differ (city link is plymouthmn.gov/citycode)
- [ ] **Look up:** Council minutes Aug. 2023 (ADU ordinance vote) and any 2024-2026 minutes on duplex/missing-middle zoning or parking changes  
  https://www.plymouthmn.gov/citycode  
  _Why manual:_ Host blocks agent (403); no direct minutes link found

## Woodbury, MN

- [ ] **Fee schedule:** FY 2024 (planning fees, dated 2024-04-03 per search snippet)  
  https://www.woodburymn.gov/DocumentCenter/View/3194  
  _Why manual:_ www.woodburymn.gov/robots.txt returned HTTP 403, so robots could not be checked and the host blocks automated fetches; not fetched.
- [ ] **Look up:** robots.txt for the city site, to confirm whether automated reading is allowed at all  
  https://www.woodburymn.gov/robots.txt  
  _Why manual:_ HTTP 403 on robots.txt; host blocks automated fetches
- [ ] **Look up:** Building permit and inspections page: download the current building permit fee schedule, plan review rate, and the city utility connection/trunk charges (water, sanitary sewer, storm) plus Met Council  
  https://www.woodburymn.gov/1346/Building-Permits-Inspections  
  _Why manual:_ Host returned 403; not fetched
- [ ] **Look up:** Inspections page (older URL): any archived fee schedules for prior years  
  https://www.woodburymn.gov/585/Inspections  
  _Why manual:_ Host returned 403; not fetched
- [ ] **Look up:** Annual fee ordinances or fee schedule resolutions adopted each December (2016-2025) in City Council agenda packets/minutes; search Agenda Center for 'fee schedule'  
  https://www.woodburymn.gov/AgendaCenter  
  _Why manual:_ Host returned 403; not fetched
- [ ] **Look up:** Woodbury City Code (Chapter 24 zoning): find whether ADUs are permitted and the ordinance number/date that added or changed them; whether duplex/triplex/fourplex are allowed in single-family (R-1/R-2)  
  https://library.municode.com/mn/woodbury/codes/code_of_ordinances  
  _Why manual:_ library.municode.com robots.txt returned 403; not fetched (code host not confirmed; may instead be on American Legal at codelibrary.amlegal.
- [ ] **Look up:** Any city ADU guide, handout or program page (fee waiver, pre-approved plans, loans) - none found in search; check the Planning/Community Development pages  
  https://www.woodburymn.gov/  
  _Why manual:_ Host returned 403; not fetched

## Maple Grove, MN

- [ ] **Ordinance:** Park dedication maximum rates ordinance  
  https://www.maplegrovemn.gov/DocumentCenter/View/210/Fee-schedule-PDF  
  _Why manual:_ Only the citation inside the 2026 fee schedule was read; the Ord. 25-05 PDF itself was not found on the city site.
- [ ] **Ordinance:** Zoning ordinance text amendment for parking recreational vehicles (Planning Commission public hearing, Nov 24, 2025)  
  https://maplegrovemn.gov/AgendaCenter/ViewFile/Item/9195?fileID=27770  
  _Why manual:_ Only the agenda listing was read; the proposed ordinance attachment was not opened.
- [ ] **Look up:** Maple Grove zoning code (Chapter 36): residential district use tables for R-1/R-2. Check whether accessory dwelling units are allowed and whether two-family or 2-4 unit homes are allowed in single-fam  
  https://library.municode.com/mn/maple_grove/codes/code_of_ordinances  
  _Why manual:_ library.municode.com robots.txt returned 403 (blocked)
- [ ] **Look up:** Municode 'Ordinances' / supplement history list for Maple Grove: adopted ordinances since 2010 on ADUs, two-family housing, residential parking and fees  
  https://library.municode.com/mn/maple_grove/ordinances/code_of_ordinances  
  _Why manual:_ library.municode.com blocked (403)
- [ ] **Look up:** Prior-year fee schedules (2016-2025). Only the current 2026 schedule (Ord. 25-17) is posted. Look for the annual fee schedule ordinances in December City Council packets for each year, or ask the City  
  https://www.maplegrovemn.gov/AgendaCenter  
  _Why manual:_ Not posted as standalone documents; the Agenda Center search does not do full-text matching, so the packets could not be found within the fe

## Blaine, MN

- [ ] **Ordinance:** Accessory dwelling units allowed in residential districts (zoning code amendment) (2021)  
  https://www.blainemn.gov/AgendaCenter  
  _Why manual:_ www.blainemn.gov returned HTTP 403 even for robots.txt, so the host blocks automated access. Number and year come from news coverage (Star T
- [ ] **Fee schedule:** FY current (undated)  
  https://www.blainemn.gov/4243/Utilities-Availability-Charges-WACSAC  
  _Why manual:_ Host returned 403 for robots.txt, so the page was not fetched. Values below come from a search-result snippet and are unverified.
- [ ] **Look up:** Annual fee schedule ordinances 2016-2026 (building permit valuation table, plan review %, park dedication per unit, WAC, trunk charges)  
  https://www.blainemn.gov/DocumentCenter  
  _Why manual:_ Host blocks automated access (403). No fee schedule URL was found by search. The city usually adopts the fee schedule each December by ordin
- [ ] **Look up:** Zoning code residential use tables (two-family, townhome, ADU) and current ADU section to establish 2-4 unit legality in R-1 zones  
  https://library.municode.com/mn/blaine  
  _Why manual:_ library.municode.com returned 403 for robots.txt
- [ ] **Look up:** Any ADU guide or program page (none found)  
  https://www.blainemn.gov  
  _Why manual:_ Host blocks automated access (403)

## Lakeville, MN

- [ ] **Ordinance:** Interim Ordinance (Housing Moratorium) pausing new residential plat, subdivision, comprehensive plan amendment and rezoning applications (2026-04-20 (city flyer says already in effect and published))  
  https://www.lakevillemn.gov/DocumentCenter/View/18954/Housing-moratorium-ordinance-flyer  
  _Why manual:_ Read the city's informational flyer only; it says it is not a substitute for the full ordinance text. The ordinance PDF (with its number) wa
- [ ] **Look up:** Lakeville City Code Title 11 (Zoning): check residential district chapters (RS-1..RS-4, RST-2, RM) for whether ADUs/accessory apartments and two-family dwellings are allowed in single-family zones, an  
  https://codelibrary.amlegal.com/codes/lakevillemn/latest/overview  
  _Why manual:_ American Legal returned HTTP 403 to automated fetch
- [ ] **Look up:** Full text and ordinance number of the April 20, 2026 interim ordinance (housing moratorium); look in the 2026-04-20 City Council packet/minutes.  
  https://www.lakevillemn.gov/AgendaCenter  
  _Why manual:_ AgendaCenter landing page returned no entries in text; the city's site search is disallowed by robots.txt, and only the flyer was found
- [ ] **Look up:** Prior-year fee schedules (2016-2025) and annual fee schedule adopting ordinances (City Council typically adopts each December); also council minutes for any ADU or zoning amendments since 2010.  
  https://la-img.lakevillemn.gov/WebLink/Browse.aspx?id=476404&dbid=0&repo=Lakeville  
  _Why manual:_ Laserfiche WebLink requires cookies/session (cookie wall); city Fee Schedule page only links the 2026 schedule
- [ ] **Look up:** 2026 City Connection Charges sheet (already read; companion to fee schedule) - optional to archive for provenance.  
  https://www.lakevillemn.gov/DocumentCenter/View/18488/2026-City-Connection-Charges-  
  _Why manual:_ Read successfully; listed only so Ben can save the PDF for provenance

## St. Cloud, MN

- [ ] **Ordinance:** Ordinance amending the St. Cloud Land Development Code to allow accessory dwelling units (ADUs) on residentially zoned one-family and two-family properties (PLDC24-0001) (2024-07-08)  
  https://www.ci.stcloud.mn.us/Archive.aspx?ADID=2049  
  _Why manual:_ These are the council minutes from July 8, 2024, which I read. The adopted ordinance text was not found on the city site. It is codified on 
- [ ] **Ordinance:** Amendment to Section 553 of the 2007 Code of Ordinances (Building Permits, Inspections and Fees), part of the cost recovery and building permit fee proposal (2026-08-31)  
  https://www.ci.stcloud.mn.us/Archive.aspx?ADID=2400  
  _Why manual:_ These are the council minutes from August 31, 2026, which I read. The adopted ordinance text and fee table were not found on the city site.
- [ ] **Ordinance:** Section 575 amendment: WAC/SAC determined by use rather than meter size (2024-01-01)  
  https://ci.stcloud.mn.us/DocumentCenter/View/19574/Current-Public-Utilities-Fee-Summary  
  _Why manual:_ The fee schedule was read, but the amending ordinance's number and adoption date were not found. Look for Section 575 history notes on Munic
- [ ] **Look up:** Adopted text of Ordinance 2928 (ADUs, July 8, 2024), its effective/publication date, and the LDC sections it amended  
  https://library.municode.com/mn/st._cloud/codes/code_of_ordinances?nodeId=COORSTCLMI_APXALADECO_ART8REDI  
  _Why manual:_ Municode's robots.txt returned 403. The agenda packet is on sws.stcloudcity.com/agenda, and its robots.txt disallows all paths.
- [ ] **Look up:** July 8, 2024 council agenda packet (staff report and draft ordinance for PLDC24-0001)  
  https://sws.stcloudcity.com/agenda  
  _Why manual:_ robots.txt on sws.stcloudcity.com is Disallow: / for all agents
- [ ] **Look up:** Section 553 building permit fee table as amended by Ord. 3005 (Aug 31, 2026): valuation table year, permit fee schedule, plan review %, effective date (reportedly Jan 1, 2027). Also the pre-2026 Secti  
  https://library.municode.com/mn/st._cloud/codes/code_of_ordinances?nodeId=17219  
  _Why manual:_ Municode robots.txt 403 (the city's /106/Code-of-Ordinances redirects there). The Aug 31, 2026 agenda packet is on the blocked sws.stcloudci
- [ ] **Look up:** Earlier Public Utilities fee schedules (2016-2025) for the WAC/SAC and trunk fee history. Only the current 2026 PDF is linked from the city site.  
  https://www.ci.stcloud.mn.us/Archive.aspx?AMID=43  
  _Why manual:_ No archive of earlier fee schedules was found. Ask the city or look for annual fee resolutions in the council minutes archive.
- [ ] **Look up:** LDC Article 16 off-street parking minimums for dwellings (current requirement for single-family and duplex homes)  
  https://library.municode.com/mn/st._cloud/codes/code_of_ordinances?nodeId=COORSTCLMI_APXALADECO_ART16OREPALO  
  _Why manual:_ Municode robots.txt 403

## Eagan, MN

- [ ] **Ordinance:** Ordinance amending Eagan City Code Chapter 11 (sections 11.60 and 11.70) to permit and regulate accessory dwelling units within single-family detached dwellings in R-1 and Estate districts (draft found in council agenda packet)  
  https://eagan.granicus.com/MetaViewer.php?view_id=8&clip_id=1376&meta_id=50903  
  _Why manual:_ robots.txt disallows
- [ ] **Ordinance:** Ordinance No. ___ 2nd Series, Eagan (candidate ADU/Chapter 11 amendment, council packet)  
  https://eagan.granicus.com/MetaViewer.php?view_id=8&clip_id=1653&meta_id=69798  
  _Why manual:_ robots.txt disallows
- [ ] **Ordinance:** Ordinance No. ___ 2nd Series, Eagan (candidate ADU/Chapter 11 amendment, council packet)  
  https://eagan.granicus.com/MetaViewer.php?view_id=8&clip_id=1654&meta_id=70129  
  _Why manual:_ robots.txt disallows
- [ ] **Ordinance:** Ordinance amending Eagan City Code Chapter 11 entitled 'Land Use Regulations (Zoning)' (council packet)  
  https://eagan.granicus.com/MetaViewer.php?view_id=8&clip_id=1818&meta_id=85204  
  _Why manual:_ robots.txt disallows
- [ ] **Ordinance:** Eagan City Code amendment (council packet, clip 2417)  
  https://eagan.granicus.com/MetaViewer.php?view_id=8&clip_id=2417&meta_id=128582  
  _Why manual:_ robots.txt disallows
- [ ] **Fee schedule:** FY 2026  
  https://www.cityofeagan.com/images/CommunityDevelopment/BuildingInspections/PermitFees/Fees2026_PermitFeeSchedule.pdf  
  _Why manual:_ robots.txt disallows
- [ ] **Fee schedule:** FY 2026 (residential valuation table)  
  https://www.cityofeagan.com/images/CommunityDevelopment/BuildingInspections/PermitFees/Fees%202026_ResidentialValuation.pdf  
  _Why manual:_ robots.txt disallows
- [ ] **Look up:** Fee schedules for 2016-2025. Try swapping the year in the Fees<YYYY>_PermitFeeSchedule.pdf filename, or find the annual December fee ordinance (City Code Chapter 2 fee schedule) in council packets or   
  https://www.cityofeagan.com/permitapplications  
  _Why manual:_ The prior-year PDFs would sit under /images/ (robots-disallowed), and the council packets are on eagan.granicus.com (robots-disallowed)
- [ ] **Look up:** Other candidate ordinance documents from the Eagan council packets. Check whether each is an ADU, zoning or fee amendment and note its number and dates.  
  https://eagan.granicus.com/MetaViewer.php?view_id=8&clip_id=1653&meta_id=69798 ; https://eagan.granicus.com/MetaViewer.php?view_id=8&clip_id=1654&meta_id=70129 ; https://eagan.granicus.com/MetaViewer.php?view_id=8&clip_id=1818&meta_id=85204 ; https://eagan.granicus.com/MetaViewer.php?view_id=8&clip_id=2417&meta_id=128582  
  _Why manual:_ eagan.granicus.com robots.txt Disallow: / for *
- [ ] **Look up:** Eagan City Code Chapter 11 (zoning). Get the ADU section, R-1 permitted uses (whether two-family or 2-4 units are allowed), residential parking minimums, and the legislative history notes giving ordin  
  https://library.municode.com/mn/eagan/codes/code_of_ordinances?nodeId=CICO_CH11LAUSREZO  
  _Why manual:_ Municode returned 403, including for robots.txt
- [ ] **Look up:** Council minutes archive (Laserfiche), to find the adoption dates for the ADU ordinance and the annual fee ordinances  
  https://eagandocs.cityofeagan.com/WebLink/Browse.aspx?id=2608584&dbid=0&repo=CityofEagan&cr=1  
  _Why manual:_ eagandocs.cityofeagan.com robots.txt Disallow: / for *
- [ ] **Look up:** Documents on the city's newer eaganmn.gov domain (for example the rental licensing ordinance PDF), which may hold current ordinance and fee PDFs  
  https://www.eaganmn.gov/images/CommunityDevelopment/rental-licensing/OrdAmend%20Ch%206%20Rental%20licensing%20Approved%2003-21-2023.pdf  
  _Why manual:_ The eaganmn.gov robots.txt could not be read because of a TLS certificate verification error, so nothing was fetched from that host

## Burnsville, MN

- [ ] **Ordinance:** Original permanent ADU ordinance (amends City Code Title 10 zoning; now codified at City Code 10-7-52)  
  https://codelibrary.amlegal.com/codes/burnsvillemn/latest/burnsville_mn/0-0-0-6553  
  _Why manual:_ HTTP 403 Forbidden on fetch; not retried
- [ ] **Ordinance:** ADU amendment reducing the minimum lot size from 1 acre to 10,000 sq ft (City Code 10-7-52)  
  https://burnsvillemn.gov/2190/Accessory-Dwelling-Units  
  _Why manual:_ could not be read
- [ ] **ADU program:** Dakota County Communities for a Lifetime ADU Guide (county)  
  https://www.co.dakota.mn.us/Government/publiccommittees/CFL/Documents/AccessoryDwellingUnitGuide.pdf  
  _Why manual:_ 301 redirect to https://dakotacountymn.gov/residents/health-medical/communities-for-a-lifetime; not followed
- [ ] **Look up:** November 2017 City Council agenda report on permanent ADU policy options (background for the 2018 ordinance)  
  https://burnsville.civicweb.net/document/14284/  
  _Why manual:_ robots.txt on burnsville.civicweb.net disallows / for User-agent *
- [ ] **Look up:** Planning Commission packet, 11 May 2020: check whether it holds the ADU lot-size amendment hearing and the draft ordinance  
  https://burnsville.civicweb.net/document/17750/Planning%20Commission%20-%2011%20May%202020.pdf?handle=030FCE37E48B4D2986C31D607C44D8CE  
  _Why manual:_ robots.txt disallows all agents on civicweb
- [ ] **Look up:** Unidentified draft ordinance found by search ('ORDINANCE NO. ___ CITY OF BURNSVILLE'): check whether it is the ADU ordinance  
  https://burnsville.civicweb.net/document/3752/  
  _Why manual:_ robots.txt disallows all agents on civicweb
- [ ] **Look up:** CivicWeb meeting archive: search 'accessory dwelling' and 'fees and charges' for the adopted ADU ordinances (2018, ~2020-21) and the annual fee ordinances for 2016-2024 and 2026 (Exhibit A schedules)  
  https://burnsville.civicweb.net/  
  _Why manual:_ robots.txt disallows all agents
- [ ] **Look up:** Fee schedules for 2016-2024: DocumentCenter/View/24983 is overwritten each year (it now holds 2026). Ask the City Clerk or look in the CivicWeb December/January council packets for each year's 'Ordina  
  https://burnsvillemn.gov/DocumentCenter/View/24983/2024-Fees-and-Charges  
  _Why manual:_ Older versions are not exposed on the city site; the archives are on CivicWeb (robots-blocked)
- [ ] **Look up:** Dakota County ADU guide (county program resources)  
  https://dakotacountymn.gov/residents/health-medical/communities-for-a-lifetime  
  _Why manual:_ Original PDF URL redirects to a landing page; not followed

## Eden Prairie, MN

- [ ] **Look up:** Eden Prairie city website, all documents. Look for: (1) ADU ordinance(s) amending City Code Chapter 11 (zoning), with ordinance number and adoption date; (2) the yearly fee schedule ordinance/resoluti  
  https://www.edenprairiemn.gov/  
  _Why manual:_ www.edenprairie.org redirects (301) to www.edenprairiemn.gov, and that host returned HTTP 403 even for robots.txt. Robots could not be read 
- [ ] **Look up:** Eden Prairie City Code (American Legal). Look for: the Chapter 11 zoning sections on accessory dwelling units and two-family dwellings in R1 districts; the code's ordinance or enactment history table   
  https://codelibrary.amlegal.com/codes/edenprairiemn/latest/overview  
  _Why manual:_ robots.txt allows Claude agents, but the page returned HTTP 403. The URL slug is unconfirmed.
- [ ] **Look up:** Metropolitan Council SAC charge history, the regional sewer availability charge per unit that applies to Eden Prairie (optional, for the water_sewer fee component).  
  https://metrocouncil.org/  
  _Why manual:_ Not attempted because of the fetch budget. Check robots.txt before fetching.

## Coon Rapids, MN

- [ ] **Ordinance:** City of Coon Rapids 2026 Fee Schedule (Ordinance 2333, Resolution 25-119; later amended by Resolutions 26-53 and 26-84) (2026-01-01 (implied by the 2026 schedule; not confirmed))  
  https://www.coonrapidsmn.gov/ArchiveCenter/ViewFile/Item/1489  
  _Why manual:_ Read the compiled fee schedule, not the adopting text of Ordinance 2333. Its adoption date was not found.
- [ ] **Ordinance:** Ordinance repealing and re-adding Chapter 11-601 General Regulations and Tables (use table)  
  https://www.coonrapidsmn.gov/DocumentCenter/View/16839/Proposed-Ordinance-2299-Repeal-and-Add-General-Regulations-and-Tables-11-601  
  _Why manual:_ Copy read is the proposed version (introduced 2024-04-02, adoption date blank). The adopted version and date need confirming in the council 
- [ ] **Ordinance:** Ordinance repealing and re-adding Chapter 11-603 (LDR-2) Low-Density Residential District  
  https://www.coonrapidsmn.gov/DocumentCenter/View/16841/Proposed-Ordinance-2301-Repeal-and-Add-LDR-2-Low-Density-Residential-District-11-603  
  _Why manual:_ Proposed version (introduced 2024-04-02, adoption date blank). The adopted version and date need confirming.
- [ ] **Ordinance:** Ordinance adding Section 11-607 (LDR-3) Low-Density Residential District (2025 (blank in copy read; a search snippet said September 2025, which is unverified))  
  https://www.coonrapidsmn.gov/DocumentCenter/View/18955/Ordinance-No-2330-  
  _Why manual:_ Signature block dates are blank in the copy read. Confirm the adoption date in the council minutes.
- [ ] **Ordinance:** Ordinance amending definitions, City Code Section 11-201 (2024 (blank in copy read))  
  https://coonrapidsmn.gov/DocumentCenter/View/18015/2321---Amending-Definitions-of-City-Code-Chapter-11-201  
  _Why manual:_ Dates blank in copy read. Confirm adoption.
- [ ] **Look up:** Current Coon Rapids City Code (Title 11 zoning: 11-601 use table, 11-603 LDR-2, 11-607 LDR-3, 11-1201 parking; 11-1506 park dedication; 12-206 building fees; 13-201/13-602 trunk water/sewer hook-up ch  
  https://library.municode.com/mn/coon_rapids/codes/code_of_ordinances  
  _Why manual:_ library.municode.com returned 403 on robots.txt / automated access; not retried.
- [ ] **Look up:** Adopted versions and adoption dates of Ordinances 2298, 2299, 2300, 2301 (introduced 2024-04-02), 2321 (2024) and 2330 (2025). Check the City Council Approved Minutes archive for 2024 and 2025.  
  https://www.coonrapidsmn.gov/ArchiveCenter/  
  _Why manual:_ Only proposed copies with blank signature dates were readable. Minutes items were not found by direct URL (404).

## Apple Valley, MN

- [ ] **Ordinance:** Apple Valley City Code §155.382, Accessory unit dwellings (adopting ordinance number and date not identified)  
  https://codelibrary.amlegal.com/codes/applevalley/latest/overview  
  _Why manual:_ An attempt to fetch a page in the code returned HTTP 403, so I did not retry. Ordinances adopted after Ord. 1140 (Dec 26, 2024) are only in 
- [ ] **Look up:** Ordinances adopted after Ord. 1140 (Dec 26, 2024), the post-codification ordinances: look for any on ADUs, two-family/townhouse uses in single-family districts, residential parking (§155.378 area), or  
  https://documents.applevalleymn.gov/WebLink/Browse.aspx?id=472458&dbid=0&repo=lf-city  
  _Why manual:_ The Laserfiche WebLink shows a cookie/login wall ('Cookies must be enabled in order to sign in'). robots.txt returned 404.
- [ ] **Look up:** The Proposed Ordinance Amendments notice for Section 155.232, to check whether it touches residential uses, parking or ADUs.  
  https://www.applevalleymn.gov/CivicAlerts.aspx?AID=4298  
  _Why manual:_ Not read because of the fetch budget. robots.txt allows it.

## Minnetonka, MN

- [ ] **Ordinance:** Zoning ordinance amendment allowing detached accessory dwelling units as conditionally-permitted uses (Minnetonka City Code Chapter 3) (2021-10-04)  
  https://minnetonkamn.gov/home/showpublisheddocument/10251/637780957940070000  
  _Why manual:_ minnetonkamn.gov returned HTTP 403 for robots.txt (www and bare host), so robots could not be checked and no city page was fetched. URL is a
- [ ] **Ordinance:** Draft ordinance relating to accessory dwelling units in residential zoning districts (planning commission, Dec 2020)  
  https://minnetonkamn.gov/home/showpublisheddocument/7896/637432767139170000  
  _Why manual:_ Host returned 403 on robots.txt; not fetched.
- [ ] **Ordinance:** Ordinance No. 2024-01 amending City Code section 710.005 regarding certain fees  
  https://minnetonkamn.gov/home/showpublisheddocument/13913/638405656351230000  
  _Why manual:_ Host returned 403 on robots.txt; not fetched.
- [ ] **Ordinance:** Ordinance 2023-02 amending various sections of Chapter 3, Zoning Regulations  
  https://minnetonkamn.gov/home/showpublisheddocument/12366/638136956398370000  
  _Why manual:_ Host returned 403 on robots.txt; not fetched.
- [ ] **ADU program:** Accessory Dwelling Unit Study (city development study page)  
  https://minnetonkamn.gov/services/projects/development-studies/accessory-dwelling-unit-study  
  _Why manual:_ Host returned 403 on robots.txt; not fetched.
- [ ] **Look up:** robots.txt for minnetonkamn.gov: confirm whether automated fetching is allowed  
  https://minnetonkamn.gov/robots.txt  
  _Why manual:_ HTTP 403 for both www and bare host, so no city documents were fetched
- [ ] **Look up:** Zoning ordinance rewrite (began ~2025): check adoption status and whether 2-4 units are permitted in single-family districts  
  https://minnetonkamn.gov  
  _Why manual:_ Host returns 403; no specific rewrite document URL found

## Edina, MN

- [ ] **Ordinance:** Accessory Dwelling Unit zoning ordinance (amendment to City Code Chapter 36, Zoning) (2024-04-16)  
  https://www.edinamn.gov/2056/Accessory-Dwelling-Units-ADUs  
  _Why manual:_ www.edinamn.gov returned HTTP 403 for robots.txt, so it was not fetched. This is the city's ADU landing page; the ordinance PDF and number w
- [ ] **Look up:** Edina's annual fee schedule ordinances, 2016-2025 and current: building permit valuation table, plan review %, water and sewer connection or availability charges, park dedication, and the Met Council   
  https://www.edinamn.gov/  
  _Why manual:_ www.edinamn.gov returned HTTP 403 for robots.txt; the fee schedule URL was not found.
- [ ] **Look up:** City Code Chapter 36 (Zoning): R-1 permitted uses, to confirm whether duplexes or 2-4 units are allowed, plus the ADU section and its amendment history notes (ordinance numbers since 2010, including a  
  https://library.municode.com/mn/edina/codes/code_of_ordinances  
  _Why manual:_ library.municode.com returned HTTP 403 for robots.txt, so I did not fetch it.

## St. Louis Park, MN

- [ ] **Ordinance:** Ordinance amending St. Louis Park City Code chapter 36 related to residential district standards (Zoning Code Update Phase 1) (2025-03-03)  
  https://www.stlouisparkmn.gov/files/assets/main/v/1/administration/documents/city-code/proposed-ordinances/250207-zoningcodeupdate-ordinance-final.pdf  
  _Why manual:_ Read, but it is the unsigned final draft ('Ordinance No. XXX-XX'; blank adoption block). The signed copy (Ord. 2690-25) is in Laserfiche id 
- [ ] **Ordinance:** Zoning map ordinance (rezoning the city into the N-1 to N-4 districts) (2025-03-03)  
  https://www.stlouisparkmn.gov/files/assets/main/v/1/administration/documents/city-code/proposed-ordinances/250210-zoning-map-ordinance.pdf  
  _Why manual:_ Not fetched because of the fetch budget. Signed copy is Laserfiche id 826141.
- [ ] **Ordinance:** Ordinance replacing chapter 36 (zoning code) in its entirety (Zoning Code Update Phase 2) (2026-08-28)  
  https://www.stlouisparkmn.gov/files/assets/main/v/1/administration/documents/city-code/proposed-ordinances/260709_ordinance-amending-chapter-36-of-zoning-code.pdf  
  _Why manual:_ Ordinance PDF not fetched. Dates come from the city's Zoning Code page. Signed copies are Laserfiche ids 1337002 and 1337347.
- [ ] **Ordinance:** Ordinance adopting fees for calendar year 2024 (2024-01-01)  
  https://www.stlouisparkmn.gov/files/assets/main/v/1/administration/documents/city-code/proposed-ordinances/230928-proposed-ordinance-adopting-fees-for-2024.pdf  
  _Why manual:_ Cover ordinance only; the Appendix A fee schedule is not in this PDF.
- [ ] **ADU program:** City ADU information page (Planning Studies: Accessory Dwelling Units)  
  https://www.stlouisparkmn.gov/government/departments-divisions/planning-zoning/planning-studies/accessory-dwelling-units  
  _Why manual:_ HTTP 404; the page appears to have been removed in the site redesign
- [ ] **Fee schedule:** FY 2027 (current adopted, effective Jan 1, 2027) (2027-01-01)  
  https://www.stlouisparkmn.gov/files/assets/main/v/1/administration/documents/city-code/proposed-ordinances/2027-fees-and-utility-rates-draft-ordinance.pdf  
  _Why manual:_ Read the draft ('2027 Proposed Fee' column). The adopted Ord. 2707-26 is in Laserfiche id 1340470 (unreachable).
- [ ] **Look up:** Signed Ordinance 2690-25 (residential districts / zoning code update Phase 1): confirm the adoption date (Mar 3, 2025), the effective date (reportedly Mar 28, 2025) and the N-1/N-2 use-table columns f  
  https://laserfiche.stlouispark.org/WebLink/DocView.aspx?id=826140&dbid=0&repo=SLP  
  _Why manual:_ laserfiche.stlouispark.org refused connections (ECONNREFUSED) for robots.txt and pages
- [ ] **Look up:** Signed Ordinance 2691-25 (zoning map): which former R-1/R-2 areas became N-1 and which became N-2  
  https://laserfiche.stlouispark.org/WebLink/DocView.aspx?id=826141&dbid=0&repo=SLP  
  _Why manual:_ Laserfiche host unreachable; the city-site draft (250210-zoning-map-ordinance.pdf) was not fetched
- [ ] **Look up:** The original ADU ordinance (before 2025): number, adoption and effective dates. The council began discussing ADUs in Jan 2019; adoption was likely 2019-2021. Search Laserfiche ordinances for 'accessor  
  https://laserfiche.stlouispark.org/WebLink/Welcome.aspx?cr=1  
  _Why manual:_ Not found on the city's Proposed Ordinances page (which starts in 2023); the city ADU page returns 404; Laserfiche unreachable
- [ ] **Look up:** Any earlier ordinance reducing residential parking minimums (a 'Parking Requirements Update' study page existed). Find its ordinance number and date  
  https://www.stlouisparkmn.gov/government/departments-divisions/planning-zoning/planning-studies/parking-requirements-update  
  _Why manual:_ Page returns 404; the ordinance archive is in Laserfiche, which was unreachable
- [ ] **Look up:** Fee schedules (Appendix A) for 2016-2024: building permit valuation table, plan review %, WAC per SAC unit, park and trail dedication per unit. The 2024 schedule was adopted by Ord. 2672-23 and 2023 b  
  https://laserfiche.stlouispark.org/WebLink/DocView.aspx?id=797705&dbid=0&repo=SLP  
  _Why manual:_ The city-site PDF for 2024 holds only the cover ordinance; schedules before 2023 are not on the Proposed Ordinances page; Laserfiche unreach
- [ ] **Look up:** Signed Ord. 2707-26 (2027 fees), to confirm the final 2027 values match the draft  
  https://laserfiche.stlouispark.org/WebLink/DocView.aspx?id=1340470&dbid=0&repo=SLP  
  _Why manual:_ Laserfiche unreachable
- [ ] **Look up:** Council minutes for the ADU and zoning votes  
  https://www.stlouisparkmn.gov/Government/City-Council/Agendas-and-Minutes  
  _Why manual:_ robots.txt disallows /Minutes-and-agenda on stlouisparkmn.gov; the council minutes were not fetched

## Austin, TX

- [ ] **Ordinance:** Ordinance eliminating minimum off-street motor vehicle parking requirements (case C20-2023-010) (2023-11-13)  
  https://services.austintexas.gov/edims/document.cfm?id=422238  
  _Why manual:_ This link is the C20-2023-039 staff review sheet that cites the ordinance, not the ordinance PDF. Download Ordinance 20231102-028 itself fro
- [ ] **Ordinance:** 2015 accessory dwelling unit amendments (Council vote of Nov 19, 2015) (2015-11-19)  
  https://www.austintexas.gov/department/city-clerk  
  _Why manual:_ No official ordinance link was found within the search budget. Get the Nov 19, 2015 ADU ordinance (number likely 20151119-0xx) from the City
- [ ] **Fee schedule:** FY FY2026-27 (current) (2026-10-01)  
  https://austin.widen.net/s/fz9rhwg8qq/fees_residential  
  _Why manual:_ robots.txt disallows
- [ ] **Look up:** Current FY2026-27 Zoning Plan Review and Other Permits fee schedules (zoning review for residential, any ADU or HOME-specific fees)  
  https://austin.widen.net/s/lvdcfhcdtd/fees_zoning  
  _Why manual:_ robots.txt on austin.widen.net disallows /s/
- [ ] **Look up:** Austin Water capital recovery (impact) fees and tap fees for a new SF home, an ADU and 2-4 units, all fiscal years; also budget response CBQ 203 (FY2025-26), which covers AW fees  
  https://www.austintexas.gov/department/water  
  _Why manual:_ Not found within the search/fetch budget
- [ ] **Look up:** Street Impact Fee ordinance (adopted ~Dec 2020, collection began ~2022) and its fee schedule per dwelling unit  
  https://www.austintexas.gov/transportation-public-works/transportation-development-services  
  _Why manual:_ Not searched or verified within the budget
- [ ] **Look up:** Parkland dedication fee per unit (Ord. and annual fee schedule), FY2016-FY2026  
  https://www.austintexas.gov/development-services/development-services-reports#fee  
  _Why manual:_ Not found within the budget
- [ ] **Look up:** Past adopted DSD fee schedules FY2016-17 to FY2022-23 (adopted budget fee schedule volumes)  
  https://www.austintexas.gov/budget-excellence/city-budget  
  _Why manual:_ The fees page lists only current schedules; archive volumes were not fetched
- [ ] **Look up:** ADU programs: Alley Flat Initiative, any ADU guides, pre-approved plans, fee waivers (e.g., S.M.A.R.T. Housing fee waivers) or AHFC ADU loans  
  https://www.austintexas.gov/department/housing  
  _Why manual:_ No official ADU program page was located (the DSD ADU URL guessed returned 404)

## Raleigh, NC

- [ ] **Ordinance:** TC-3-17 ADUs (Accessory Dwelling Unit Overlay District) (2019-05-20)  
  https://cityofraleigh0drupal.blob.core.usgovcloudapi.net/drupal-prod/COR22/TC2017.zip  
  _Why manual:_ Only offered inside a year-level ZIP archive (TC2017.zip); not downloaded.
- [ ] **ADU program:** ADU Fast Track launch announcement (2022-12-14)  
  https://raleighnc.gov/planning/city-raleigh-launches-north-carolinas-first-adu-gallery  
  _Why manual:_ HTTP 403 Forbidden
- [ ] **ADU program:** Raleigh ADU Pitchfest (Housing & Neighborhoods event)  
  https://raleighnc.gov/housing/events/raleigh-adu-pitchfest  
  _Why manual:_ HTTP 403 Forbidden
- [ ] **Look up:** Development Fee Guides for FY2017 through FY2025 (prior years): new residential building permit %, plan review %, open space, thoroughfare, water and sewer capital facility and tap fees  
  https://raleighnc.gov/permits/services/development-fee-guide-and-calculator  
  _Why manual:_ The city overwrites one PDF URL each year (COR15/DevelopmentFeeGuide.pdf) and posts no archive. Older years must come from adopted budget bo
- [ ] **Look up:** Older fee-related text changes 5-15 Fire Prevention Fee Change and 5-10 Stormwater Replacement Fund, if relevant  
  https://cityofraleigh0drupal.blob.core.usgovcloudapi.net/drupal-prod/COR22/TC2015.zip  
  _Why manual:_ Only available inside year-level ZIP archives (TC2015.zip, TC2010.zip).

## Durham, NC

- [ ] **Ordinance:** Expanding Housing Choices (EHC), UDO Text Amendment TC1800007 (2019-10)  
  https://durhamnc.gov/DocumentCenter/View/27597/CC_EXPANDING-HOUSING-CHOICES-MEMO  
  _Why manual:_ durhamnc.gov returned HTTP 403 even for robots.txt; host blocks automated access
- [ ] **Ordinance:** Expanding Housing Choices (EHC) ADU provisions (Attachment G, ADU), part of TC1800007 (2019-10)  
  https://www.durhamnc.gov/DocumentCenter/View/25615/Attachment-G_ADU-final  
  _Why manual:_ durhamnc.gov returned HTTP 403 even for robots.txt; host blocks automated access
- [ ] **Ordinance:** Simplifying Codes for Affordable Development (SCAD), UDO Text Amendment TC2200001 (2023-11-20)  
  https://www.durhamnc.gov/DocumentCenter/View/46293/TC2200001-PC-Staff-Report-091322-full-item  
  _Why manual:_ durhamnc.gov returned HTTP 403 even for robots.txt; this is the Planning Commission staff report, not the adopted ordinance
- [ ] **Fee schedule:** FY FY2024  
  https://www.durhamnc.gov/DocumentCenter/View/52048/Water-Management_Capital-Facility-Fee_FY23-24  
  _Why manual:_ durhamnc.gov returned HTTP 403 even for robots.txt; host blocks automated access
- [ ] **Look up:** EHC Final Report (Dec 2023). Look for ADU and duplex permit counts since adoption (365 EHC-enabled permits reported) and any program or date details.  
  https://www.durhamnc.gov/DocumentCenter/View/53660/Expanding-Housing-Choices-Final-Report-PDF  
  _Why manual:_ durhamnc.gov blocks automated access (403)
- [ ] **Look up:** Planning Commission minutes, Dec 13, 2022 (SCAD recommendation vote)  
  https://www.durhamnc.gov/AgendaCenter/ViewFile/Minutes/_12132022-2323  
  _Why manual:_ durhamnc.gov blocks automated access (403)
- [ ] **Look up:** City-County Inspections building permit and plan review fee schedules, FY2016 to current, plus the Planning Department development review fee schedule. Find them on the Inspections and Planning pages   
  https://www.durhamnc.gov/  
  _Why manual:_ No specific URL found within the search budget; host blocks automated access (403)
- [ ] **Look up:** Pending and adopted text amendments list. Check for later ADU or missing-middle amendments after 2023, and any ADU fee waiver, pre-approved plan or guide program.  
  https://www.durhamnc.gov/415/Pending-Text-Amendments  
  _Why manual:_ durhamnc.gov blocks automated access (403)
