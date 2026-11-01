# Ohio ordinance lookups: research brief (2026-11-01)

For a research agent working for Ben. The aim is to finish dating Ohio's ADU and missing-middle (MM) rules for
Lotline, a housing-reform simulator. Each finding becomes a dated row in `config/reforms/oh.csv`, and that row
decides whether and when a place counts as "treated" in the estimation panels.

## What counts as an answer

- **Effective date beats adoption date.** Report both if you can. If only the passage date is known, give it and
  say which effective-date rule applies (the city charter's, or Ohio R.C. 731.29's 30 days; an emergency
  ordinance takes effect on passage).
- **"First allowed"** means the earliest enacted ordinance that permitted the use anywhere in the city, by right
  or conditionally. An amendment to existing ADU rules is **not** a first date.
- **A dated "no ADUs" finding is useful.** It needs a code edition or ordinance date that shows ADUs were not
  allowed, plus the section that shows it (for example "accessory structures may not be dwellings").
- **Sources, in order:** the official code publisher (American Legal, Municode, enCodePlus), official city
  ordinance PDFs and Legistar records, council minutes, then court opinions. News and secondary notices are leads
  only.
- **Quote** the deciding sentence (under 15 words) and give the URL, the section and the page.
- **Mark anything unresolved as unresolved.** Missing evidence is not proof of a ban.

## Return format (one row per place)

| place | question | answer | effective date (precision) | adoption date | ordinance / section | quote | URL(s) | confidence | still open |
|---|---|---|---|---|---|---|---|---|---|

## The lookups

### 1. Westerville (GEOID 3983342): when were ADUs first allowed?
- **Known.** ADU rules are in §1175.06. Ord. 2023-15 (passed 2023-12-05; by the Charter's 30-day rule, effective
  2024-01-04) **amended** §1175.06, so ADUs were allowed before it. Later revisions: Ord. 2024-11 and 2025-14.
- **Find:** the ordinance that first added §1175.06 (or ADUs to the zoning code) and its effective date; whether
  that first rule was by right or conditional; and the actual effective date of 2023-15.
- **Start:** the code history note under §1175.06,
  https://codelibrary.amlegal.com/codes/westerville/latest/westerville_oh/0-0-0-14201; the city ordinance index,
  https://www.westerville.org/home/showpublisheddocument/40047/638871370620470000

### 2. Reynoldsburg (3966390): when were ADUs first allowed?
- **Known.** §1105.05 has the ADU standards and cites amendments Ord. 33-2020 (2020-03-23) and Ord. 103-2021
  (2021-07-26), so ADUs predate 2020. The 2024 code and the new code (effective 2026-01-15) both keep ADUs.
- **Find:** the ordinance that first allowed ADUs, with its date and terms (by right or conditional, owner
  occupancy, detached allowed). Also check whether the 2026 code changed the rules.
- **Start:** https://codelibrary.amlegal.com/codes/reynoldsburg/latest/reynolds_oh/0-0-0-70831;
  https://reynoldsburg.gov/DocumentCenter/View/3100/Zoning-Code_Master-Code-08232024;
  https://www.reynoldsburg.gov/DocumentCenter/View/4372/Zoning-Code-2026

### 3. Lorain (3944856): were ADUs allowed before the 2021 code?
- **Known.** The current zoning code (Ord. 4-21, effective 2021-02-05) lists ADUs as conditional in residential
  districts (§11.06A, Table 4-2).
- **Find:** the pre-2021 code's treatment of accessory dwellings: allowed (since when, on what terms) or not
  allowed (with a dated edition). If not allowed, the answer is "none before; conditional from 2021-02-05".
- **Start:** https://www.cityoflorain.org/653/Planning-Zoning-Division;
  https://cityoflorain.org/DocumentCenter/View/3220/Lorain-Zoning-Code; archived pre-2021 code editions.

### 4. Grandview Heights (3931304): date the "no ADUs" rule
- **Known.** §1153.02 says accessory structures can't contain or be used as a dwelling unit (code current through
  2026-04-13). An Ohio Tenth District appeals decision, **2020-Ohio-1395**, applied this to an accessory in-law
  suite.
- **Find:** that decision's release date and case name. Better still, the date §1153.02's prohibition was enacted
  (from its history note). Either one dates a "no ADUs" row.
- **Start:** https://www.supremecourt.ohio.gov/rod/docs/PDF/10/2020/2020-Ohio-1395.pdf (it refused our
  connections; try another route); https://codelibrary.amlegal.com/codes/grandviewhts/latest/grandviewhts_oh/0-0-0-41758

### 5. Canal Winchester (3911332): date the "no ADUs" finding
- **Known.** No general ADU permission was found in the online code, but the city warns its online codification
  may lag, and a zoning-code rewrite was under review in 2026.
- **Find:** the edition or supplement date of the online zoning code (or the ordinance that adopted the current
  code), confirming no ADU use. Also check whether the rewrite was adopted, and whether it allows ADUs.
- **Start:** https://www.canalwinchesterohio.gov/142/Zoning-Code;
  https://codelibrary.amlegal.com/codes/canalwinchester/latest/canalwinchester_oh/0-0-0-14352

### 6. Akron (3901000): date the "no ADUs" finding, or find the rule
- **Known.** No general ADU or accessory-apartment provision was found in Chapter 153 (Municode). Akron adopted
  a form-based code on 2024-03-11, which may differ.
- **Find:**
  - whether either code (Chapter 153, or the 2024 form-based code and its districts) allows ADUs, with section
    and date;
  - if neither does, the supplement or edition date that shows it;
  - any Council ordinance on ADUs, 2015–2026.
- **Start:** https://library.municode.com/oh/akron/codes/code_of_ordinances?nodeId=TIT15LAUS_CH153ZOCO; the
  form-based code PDF,
  https://www.akronohio.gov/Departments/Planning%20And%20Urban%20Development/Zoning%20Map%20And%20Code/Akron%20Form-Based%20Code%202024-03-11%20Approved.pdf;
  https://www.akroncitycouncil.org/legislationminutes

### 7. Parma (3961000): date the "no ADUs" finding
- **Known.** The single-family accessory-use list (§1153.03) has no dwelling unit. No ADU authorization was found.
- **Find:** the edition date of the code showing this (the city posts a "February 2025" zoning code PDF), and
  whether any earlier or later ordinance allows ADUs.
- **Start:** https://parmany.gov/pdf/home-page/Parma%20Zoning%20Code%20February%202025.pdf;
  https://codelibrary.amlegal.com/codes/parma/latest/Parma_oh/0-0-0-211955

### 8. Canton (3912000): is the older ADU rule still in force?
- **Known.** A city handout describes earlier ADU permissions (internal and freestanding), with no date. The
  current code (through 2026-09-28, §1139.01) bars accessory structures built to be used as a dwelling.
- **Find:** the handout's date and the ordinance behind it; whether it was repealed (and when) or still applies
  to internal units; the current rule for an ADU inside the house.
- **Start:** https://www.cantonga.gov/home/showpublisheddocument/703/637798464167570000 (check that this is
  Canton, **Ohio**: the domain may belong to Canton, Georgia);
  https://codelibrary.amlegal.com/codes/canton/latest/canton_oh/0-0-0-47490

### 9. Cuyahoga Falls (3919778): standards and first date
- **Known.** The current use table lists "accessory units" as limited uses in R-R, R-5, R-6, R-C and R-M, not
  in R-1 to R-4. The standards are in Chapter 1133, which wasn't readable.
- **Find:**
  - Chapter 1133's ADU standards: owner occupancy, size, detached allowed, parking, by right or conditional;
  - the ordinance that first added accessory units, with its date;
  - whether R-R, R-5 and R-6 are single-family districts.
- **Start:** https://online.encodeplus.com/regs/cuyahogafalls-oh/doc-view.aspx?pn=0&secid=381;
  https://www.cityofcf.com/sites/default/files/2025-10/69-2025%20Amending%20CF%20Development%20Code.pdf

### 10. Grove City (3932592): missing middle, duplexes before 2010?
- **Known.** Ord. C12-79 (passed 1979-02-19) authorizes doubles, twin singles and duplexes in residential and PUD
  districts (§1135.09(a)). Ben's earlier research read those districts as including single-family districts.
- **Find:** in the current §1135.09(a), are duplexes allowed **by right** in the single-family districts
  (which ones), or only by special approval? If by right since 1979, we'll code a pre-2010 MM row like Dayton's.
- **Start:** https://codelibrary.amlegal.com/codes/grovecity/latest/gcity_oh/0-0-0-96542

### 11. Cleveland Heights (3916014): standards in Ord. 142-2026
- **Known.** Council passed Ord. 142-2026 on 2026-10-19, amended after the 2026-10-15 hearing. It's coded as
  effective 2026-11-18 (the Charter's 30 days, computed).
- **Find:** the signed final text. We need the districts, by right or conditional, owner occupancy, size cap,
  detached allowed, parking, and the stated effective date (or confirmation of the 30-day rule).
- **Start:** https://www.clevelandheights.gov/1707/Accessory-Dwelling-Units-ADUS; the city's Legistar or council
  packet for 2026-10-19.

### 12. Findlay (3927048): full text of Ord. 2026-094
- **Known.** A published notice says Ord. 2026-094 (passed 2026-10-06) adds §1161.01.5 and takes effect
  2027-01-01. The full text is "available at the Mayor's Office".
- **Find:** the full text (districts, by right or conditional, owner occupancy, size, detached, parking), from the
  city's legislation page, a council packet or the code publisher once codified. Also confirm the effective
  date.
- **Start:** https://www.noticeregistry.com/ohio/notice/ordinance-findlay-331499;
  https://www.findlayohio.gov/government/legislation/
