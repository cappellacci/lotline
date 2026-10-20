# ADU adoption dates to look up by hand (Twin Cities metro, priority list)

The adoption-date run (2026-10-20) found the ADU rule history for 52 of 162 metro places; 110 stay unknown, mostly because the code host blocked automated reading. The D-023 estimator needs, for each place, **whether ADUs are allowed and since when** (the ordinance and its effective date). These are the 30 largest unknown places, in order of population: each lookup adds the most data. Record: status (by right / permit / not allowed), the effective date of each change, the ordinance number and link, and a short quote. Full records: `docs/research/ordinances/metro-adu-adoption-2026-10-20.json`.

## Brooklyn Center city (GEOID 2707948, pop. 33782)
- Zoning authority: City of Brooklyn Center (the city does its own zoning; Hennepin County does not zone incorporated cities)
- [ ] Brooklyn Center's new zoning code (the rewrite run by Bolton & Menk, 2021-2023): find the adopting ordinance number, the adoption and effective dates, and the ADU section. A search  
  https://brooklyncentermn.gov/home/showpublisheddocument/1413/637611811123670000  
  _Why manual:_ brooklyncentermn.gov returned HTTP 403 even for robots.txt; per the rules I did not retry or work around it.
- [ ] Zoning rewrite housing summary PDF (BC-Zoning-Housing.pdf) that describes the proposed ADU allowance. Useful only to find the ordinance; it is a consultant-hosted document, not the  
  https://clients.bolton-menk.com/brooklyncenter2019/wp-content/uploads/sites/61/2021/07/BC-Zoning-Housing.pdf  
  _Why manual:_ The host returned HTTP 403 for robots.txt; I did not fetch it.
- [ ] Current Brooklyn Center City Code, Chapter 35 Zoning: the accessory dwelling unit section, its history note (ordinance number and date), and whether ADUs need a permit or are allow  
  https://codelibrary.amlegal.com/codes/brooklyncentermn/latest/overview  
  _Why manual:_ robots.txt allows Claude agents, but the code page returned HTTP 403 (likely a bot block), so it needs a manual read in 

## Andover city (GEOID 2701486, pop. 32601)
- Zoning authority: City of Andover (Anoka County, MN) does its own zoning under City Code Title 12 (Zoning Regulations).
- [ ] Current Andover City Code Title 12, ADU section (reported as 12-8-5), plus its ordinance history notes (adopting ordinance number and date). Search results summarizing a 2022 City   
  https://lf.andovermn.gov/WebPortal/browse.aspx?id=204150  
  _Why manual:_ The city's code portal (Laserfiche WebLink) returned a 'Cookies must be enabled in order to sign in' page and was not re
- [ ] The City of Ramsey 2022 ADU research memo that surveys neighboring cities' rules, including Andover's. Use it only to find leads; the official Andover ordinance is still needed.  
  https://public.destinyhosted.com/ramsedocs/2022/CCReg/20220111_21975/12799_Accessory%20Dwelling%20Unit%20Research.pdf  
  _Why manual:_ robots.txt on public.destinyhosted.com disallows all paths, so I did not fetch it.
- [ ] City Council minutes and ordinances adopting or amending the ADU (accessory dwelling unit) provisions in Title 12 (the date ADUs were first allowed by CUP, and the date detached AD  
  https://lf.andovermn.gov/WebPortal  
  _Why manual:_ The Agendas & Minutes portal is the same Laserfiche WebLink system, which needs cookies or sign-in; not accessible to th

## Savage city (GEOID 2758738, pop. 32465)
- Zoning authority: City of Savage (incorporated city; does its own zoning, not Scott County)
- [ ] Savage City Code zoning chapter: find whether accessory dwelling units / accessory apartments are allowed (and in which districts, by right or by permit), plus the adopting ordinan  
  https://codelibrary.amlegal.com/codes/savagemn/latest/overview  
  _Why manual:_ amlegal robots.txt allows the path, but the page returned HTTP 403; not retried
- [ ] City of Savage website: planning/zoning pages, ADU ordinance PDF, and council minutes adopting or amending ADU rules  
  https://www.savagemn.gov/  
  _Why manual:_ robots.txt request returned HTTP 403, so robots status is unknown and the site was not fetched
- [ ] Alternate code host, in case Savage's code is on Municode  
  https://library.municode.com/mn/savage  
  _Why manual:_ Municode robots.txt returned HTTP 403; not fetched

## Chaska city (GEOID 2710972, pop. 27810)
- Zoning authority: City of Chaska (its own Zoning Code; the city recodified it in-house in 2020 with Municipal Code Corporation, and it is hosted at chaska.municipalcode
- [ ] Current Chaska Zoning Code: search it for 'accessory dwelling', 'accessory apartment' and 'second dwelling unit' to see whether ADUs are allowed today (by right or by permit), and   
  https://chaska.municipalcodeonline.com/book?type=zoning#name=Preface  
  _Why manual:_ The site has no robots.txt (404), but the code text loads through /book/expand, which returns 'Unauthorized Access' to n
- [ ] Proposed and adopted ordinance changes folder (any ADU or accessory-unit ordinance PDFs and their adoption dates)  
  https://www.chaskamn.gov/DocumentCenter/Index/264  
  _Why manual:_ robots.txt allows it, but the folder's file list is rendered by JavaScript and did not come through in a plain fetch. Ne
- [ ] City Council and Planning Commission minutes and agendas that mention accessory dwelling units, to date the first allowance and later amendments (for example around the 2020 zoning  
  https://www.chaskamn.gov/134/Planning-Commission  
  _Why manual:_ There was no search budget left, and the site search path (/Search) is disallowed by robots.txt.

## Ramsey city (GEOID 2753026, pop. 27646)
- Zoning authority: City of Ramsey (Anoka County), which zones itself under City Code Chapter 106 (Zoning Code)
- [ ] Ramsey City Code Chapter 106 (Zoning Code): check whether accessory dwelling units or accessory apartments are allowed (permitted, conditional or interim use, or not listed), then   
  https://library.municode.com/mn/ramsey/codes/code_of_ordinances?nodeId=PTIICOOR_CH106ZOCO  
  _Why manual:_ library.municode.com returned HTTP 403 (its robots.txt also returned 403), so it was not retried. The session's web sear
- [ ] Ramsey zoning amendment records, or council and planning commission minutes, for any ordinance adopting or changing ADU or accessory apartment rules  
  https://www.cityoframseymn.gov/business-development/planning-and-development/development-applications-and-permits/zoning-amendments/  
  _Why manual:_ Not read because of the read budget. The city site's search for 'accessory dwelling unit' returned no results. The site'

## Prior Lake city (GEOID 2752594, pop. 27617)
- Zoning authority: City of Prior Lake (incorporated city; zones itself under its City Code, Chapter 11 zoning ordinance)
- [ ] Current Prior Lake zoning ordinance (City Code Chapter 11): does it allow accessory dwelling units / accessory apartments, as a permitted use or by conditional use permit, and is d  
  https://codelibrary.amlegal.com/codes/priorlakemn/latest/overview  
  _Why manual:_ The robots.txt allowed it, but the page returned HTTP 403 to the fetcher, so it was not retried.
- [ ] City ordinance archive, council minutes and Planning Commission records for when ADUs were first allowed and later amended (search 'accessory dwelling unit' and 'accessory apartmen  
  https://www.priorlakemn.gov/  
  _Why manual:_ The city website returned HTTP 403 even for robots.txt, so no pages were read.
- [ ] Web search for the Prior Lake ADU ordinance number and adoption date (e.g. news coverage of council approval), to find the official ordinance PDF  
  https://www.priorlakemn.gov/  
  _Why manual:_ The session's web search budget was used up (limit reached before this task), so no search ran.

## Shoreview city (GEOID 2759998, pop. 26921)
- Zoning authority: City of Shoreview (its own Development Code, Chapter 200 of the City Code, hosted on Municode)
- [ ] Shoreview Development Code (City Code Ch. 200): find the accessory dwelling unit / accessory apartment provisions (residential districts and use standards), whether they are permit  
  https://library.municode.com/mn/shoreview/codes/code_of_ordinances  
  _Why manual:_ shoreviewmn.gov/Government/City-code redirects to library.municode.com, which returned a Cloudflare managed bot challeng
- [ ] Development code update (city open house held July 16, presumably 2026): check whether it adds or changes ADU rules, and look in city council/planning commission agendas and minute  
  https://www.shoreviewmn.gov/Events-directory/Development-code-update-open-house  
  _Why manual:_ The event page has no ordinance text. The web search budget for this run was already used up (limit reached before this 
- [ ] Comprehensive Plan Chapter 7 (Housing) and Appendix 1 (zoning districts) were read; neither mentions accessory dwelling units, so they give no ADU dates. Confirm in the code itself  
  https://www.shoreviewmn.gov/files/sharedassets/city/v/1/community-development/documents/comp-plan/chapter-7-housing.pdf  
  _Why manual:_ Both PDFs were read in full by keyword search; they contain no ADU, accessory apartment or in-law unit text.

## Rosemount city (GEOID 2755726, pop. 25650)
- Zoning authority: City of Rosemount (the city does its own zoning under City Code Title 11, Zoning Regulations; a new zoning code was adopted June 4, 2024)
- [ ] Check the current Rosemount zoning code (Title 11, adopted June 4, 2024) for accessory dwelling unit / accessory apartment provisions: which districts allow them, whether permitted  
  https://codelibrary.amlegal.com/codes/rosemountmn/latest/rosemount_mn/0-0-0-9408  
  _Why manual:_ codelibrary.amlegal.com returned HTTP 403 to the fetcher (robots.txt does not block it). Not retried, per the rules.
- [ ] Find the ordinance number and adoption date of the 2024 Zoning Code Update, and any ADU rules in the pre-2024 zoning code (for history before 2024)  
  https://www.rosemountmn.gov/899/2024-Zoning-Code-Update  
  _Why manual:_ The city page gives the June 4, 2024 adoption but no ordinance number and does not mention ADUs. The code itself (amlega
- [ ] Search the city council minutes and ordinance archive for accessory dwelling, accessory apartment or secondary unit amendments  
  https://www.rosemountmn.gov/490/Ordinances  
  _Why manual:_ The web search budget ran out after 0 successful searches, so no ordinance number could be found by search. The city's T

## Champlin city (GEOID 2710846, pop. 23919)
- Zoning authority: City of Champlin (municipal zoning code, Chapter 126 of the City Code)
- [ ] Current Champlin zoning code (Chapter 126): does it allow accessory dwelling units, in which districts, and is a permit (CUP/IUP) required? Find the first adopting ordinance and da  
  https://champlinmn.gov/  
  _Why manual:_ champlinmn.gov robots.txt disallows ClaudeBot for the entire site, so no city pages were fetched. The code host (likely 
- [ ] Ordinance amending Chapter 126, Section 381 (accessory buildings and uses), scheduled for reading or adoption at the Nov 24, 2025 City Council meeting. Check whether it covers ADUs  
  https://champlinmn.gov/CivicSend/ViewMessage/message/275816  
  _Why manual:_ Found only through a search result. The host blocks ClaudeBot, so it was not read and its content is unconfirmed.
- [ ] Earlier city notice that may relate to accessory uses or ADUs  
  https://champlinmn.gov/CivicSend/ViewMessage/message/194416  
  _Why manual:_ Found through a search result. The host blocks ClaudeBot, so it was not read.

## Farmington city (GEOID 2720618, pop. 23632)
- Zoning authority: City of Farmington (Dakota County), which zones itself under City Code Title 10 (Zoning). A rewrite of the zoning ordinance (Ord. 2026-007) and a new 
- [ ] Farmington City Code Title 10 (Zoning): look for accessory dwelling unit or accessory apartment provisions (use tables and the accessory uses chapter) and the ordinance history not  
  https://codelibrary.amlegal.com/codes/farmingtonmn/latest/overview  
  _Why manual:_ American Legal's robots.txt allows the path, but the fetch returned HTTP 403, so it was not retried
- [ ] Ordinance 2026-007, the zoning ordinance update approved in September 2026, and its Sept 9, 2026 Planning Commission hearing packet: check whether the rewrite adds or changes ADU r  
  https://farmington.civicweb.net/document/178347/?splitscreen=true&media=true  
  _Why manual:_ farmington.civicweb.net robots.txt disallows all paths for User-agent *, so it was not fetched
- [ ] Sept 21, 2026 City Council meeting where Ordinances 2026-007 and 2026-008 were adopted (4-1), for the adopted text and effective date  
  https://farmington.civicweb.net/Portal/MeetingInformation.aspx?Id=2457  
  _Why manual:_ farmington.civicweb.net robots.txt disallows all paths for User-agent *, so it was not fetched

## New Brighton city (GEOID 2745430, pop. 23454)
- Zoning authority: City of New Brighton (incorporated city in Ramsey County; zones itself)
- [ ] New Brighton zoning code (Chapter 8 Zoning) accessory dwelling unit provisions: whether ADUs are permitted today, whether detached ADUs are allowed, and the adopting ordinance numb  
  https://www.newbrightonmn.gov/  
  _Why manual:_ City site returned HTTP 403 on robots.txt; did not retry or work around. The WebSearch budget for this turn was already 
- [ ] Municode-hosted New Brighton Code of Ordinances (if hosted there), to check ADU sections and their history notes listing ordinance numbers  
  https://library.municode.com/mn/new_brighton  
  _Why manual:_ library.municode.com returned HTTP 403 on robots.txt; did not fetch.
- [ ] Planning Commission and City Council minutes or adopted ordinances on accessory dwelling units (search the city's agenda center for 'accessory dwelling')  
  https://www.newbrightonmn.gov/  
  _Why manual:_ City host blocked automated access (403).

## Hastings city (GEOID 2727530, pop. 22154)
- Zoning authority: City of Hastings (incorporated city in Dakota County, MN; it does its own zoning under City Code Chapter 155, Zoning Code)
- [ ] Hastings City Code Chapter 155 (Zoning Code): find whether accessory dwelling units, accessory apartments or secondary units are allowed, in which districts, and whether by right o  
  https://hastingsmn.municipalcodeonline.com/book?type=ordinances#name=CHAPTER_155_ZONING_CODE  
  _Why manual:_ The code viewer is rendered with JavaScript. Its content endpoint (/book/expand) returned 'Unauthorized Access' to autom
- [ ] City council and planning commission agendas and minutes, to find any ordinance adopting or amending ADU or accessory-apartment rules, with dates  
  https://www.hastingsmn.gov/government-transparency/agendas-and-minutes/  
  _Why manual:_ The site search on hastingsmn.gov showed no ADU results to a non-JS fetch, and neither of the two web searches turned up
- [ ] Confirm the ADU rules with Hastings Planning & Zoning (651-480-2381)  
  https://www.hastingsmn.gov/business-development/planning-and-zoning/  
  _Why manual:_ The planning page doesn't mention ADUs at all.

## New Hope city (GEOID 2745628, pop. 21986)
- Zoning authority: City of New Hope (municipal zoning, City Code on Municode)
- [ ] New Hope City Code zoning chapter: check for accessory dwelling unit or accessory apartment provisions, and the history notes giving ordinance numbers and dates  
  https://library.municode.com/mn/new_hope/codes/code_of_ordinances  
  _Why manual:_ library.municode.com returned HTTP 403 on robots.txt, so the code could not be fetched automatically
- [ ] 2040 Comprehensive Plan housing chapter: look for any ADU policy or implementation step  
  https://www.newhopemn.gov/UserFiles/Servers/Server_9826625/File/City%20Hall/Community%20Development/2040%20Comprehensive%20Plan%20Final%20-W%20Apndx%20FINAL.pdf  
  _Why manual:_ The PDF is over 10 MB and too large for the fetch tool. It needs to be downloaded and read by hand
- [ ] City Council/Planning Commission minutes or ordinances amending the zoning code for accessory dwelling units (search the city site or ask the city at 763-531-5100)  
  http://www.newhopemn.gov/city_hall/community_development/planning_development  
  _Why manual:_ The web search budget was used up for this turn (0 searches ran), and the city's planning pages say nothing about ADUs

## Columbia Heights city (GEOID 2712700, pop. 21973)
- Zoning authority: City of Columbia Heights (incorporated city in Anoka County; it does its own zoning under its City Code, Chapter 9 Land Use / Zoning)
- [ ] Current Columbia Heights zoning code: find whether accessory dwelling units are allowed, and the section and ordinance number that added them. Check the residential district use ta  
  https://www.columbiaheightsmn.gov/  
  _Why manual:_ The city website returned HTTP 403 even for robots.txt, so I did not fetch it and did not try to get around the block.
- [ ] Columbia Heights City Code on American Legal: search for 'accessory dwelling', then use the code's history notes for the adopting ordinance numbers and dates.  
  https://codelibrary.amlegal.com/codes/columbiaheightsmn/latest/overview  
  _Why manual:_ HTTP 403 when fetched, possibly a bot block. I'm also not sure this is the right path for the city's code.
- [ ] Planning Commission and City Council agendas and minutes, plus adopted ordinances, covering any ADU text amendment (likely recent, around 2020–2025). Find the ordinance number and   
  https://www.columbiaheightsmn.gov/  
  _Why manual:_ The site returns 403 to automated fetches. Two web searches found no Columbia Heights MN ADU material, only Columbia, Mi

## Lino Lakes city (GEOID 2737322, pop. 21399)
- Zoning authority: City of Lino Lakes (it zones itself; Zoning Ordinance is City Code Chapter 1007)
- [ ] Lino Lakes Zoning Ordinance, City Code Chapter 1007: check whether accessory dwelling units / accessory apartments are permitted, conditional, or not listed in residential district  
  https://codelibrary.amlegal.com/codes/linolakes/latest/linolakes_mn/0-0-0-19403  
  _Why manual:_ American Legal Publishing returned HTTP 403 to the fetch tool (robots.txt has no rule blocking Claude); per the rules I 
- [ ] Ordinances adopted but not yet codified, and any past ADU ordinance; confirm with planning staff, since the city says the online code may lag  
  https://www.linolakes.gov/163/City-Code-Zoning-Ordinances  
  _Why manual:_ I read this page. It lists 2026 ordinances 01-26 to 05-26: rezonings and easement vacations, none about ADUs. Older ordi

## South St. Paul city (GEOID 2761492, pop. 20759)
- Zoning authority: City of South St. Paul (the city does its own zoning; Zoning Code is in the City Code on Municode, Dakota County)
- [ ] Current South St. Paul zoning code (City Code zoning chapter): check whether accessory dwelling units are a permitted, conditional or prohibited use in the R-1/R-2 districts, and t  
  https://library.municode.com/mn/south_st._paul/codes/code_of_ordinances  
  _Why manual:_ The city's own City Code and Zoning pages (southstpaul.org/223 and /185) link only to Municode, and library.municode.com
- [ ] Any ADU ordinance adopted after June 2020. The city's Master Housing Assessment and Strategy (Housing Task Force, June 1, 2020, p. ~15) lists an 'Accessory Dwelling Unit Policy' am  
  https://www.southstpaul.org/386/Ordinances-Recently-Adopted  
  _Why manual:_ The Ordinances-Recently-Adopted page lists only Ordinances 1432-1437 (parking, fences, beekeeping, block size, accessory
- [ ] Housing strategy source (read) showing ADU policy was a recommendation, not yet in place, as of June 2020  
  https://www.southstpaul.org/DocumentCenter/View/7047  
  _Why manual:_ Read. It is context only and not a zoning rule, so it is not used as a history entry.

## Forest Lake city (GEOID 2721770, pop. 20611)
- Zoning authority: City of Forest Lake (its own zoning code, Chapter 153 of the city code; Forest Lake absorbed Forest Lake Township in 2000 and zones the whole city its
- [ ] Forest Lake City Code §153.092 (use standards), parts (A) Accessory apartments and (B) Accessory dwellings. Read the full text and its history note. A third-party mirror (Zoneomics  
  https://codelibrary.amlegal.com/codes/forestlakemn/latest/forestlake_mn/0-0-0-1  
  _Why manual:_ American Legal returned HTTP 403 to the fetch (robots.txt allows the path). Per the rules, I did not retry. The mirror t
- [ ] Ordinance 736, passed 2024-04-22, which the mirror lists as the latest amendment to §153.092. Get the ordinance PDF or the council minutes and find out what it changed for accessor  
  https://www.ci.forest-lake.mn.us/  
  _Why manual:_ My searches found no official copy of the ordinance or the council packet. I ran out of searches before finding the city
- [ ] When accessory apartments were first adopted: find the first ordinance number and date in the §153.092 history note. Also check whether owner occupancy is still required, and when   
  https://codelibrary.amlegal.com/codes/forestlakemn/latest/forestlake_mn/0-0-0-1  
  _Why manual:_ Needs the official code's history notes, which were blocked by the 403.

## Anoka city (GEOID 2701720, pop. 17921)
- Zoning authority: City of Anoka (incorporated city; zones itself under its City Code, hosted on Municode)
- [ ] Anoka City Code, zoning chapter: check the definitions and the residential district permitted, conditional and accessory use lists for 'accessory dwelling unit', 'accessory apartme  
  https://library.municode.com/mn/anoka/codes/code_of_ordinances  
  _Why manual:_ Municode returned HTTP 403 for robots.txt, so it was not fetched. The site is also rendered client-side. The city's City
- [ ] Planning Commission and City Council agendas and minutes for any ADU zoning text amendment (search for 'accessory dwelling')  
  https://www.anokamn.gov/agendacenter  
  _Why manual:_ Search budget ran out. Neither web search found an Anoka ADU ordinance. A search summary claimed a 2022 Ramsey staff mem
- [ ] Ask the zoning division whether ADUs are allowed and, if so, which ordinance adopted them  
  https://www.anokamn.gov/210/Planning-and-Zoning-Division  
  _Why manual:_ The city's residential zoning page (anokamn.gov/222) and its Garage and Accessory Building Guide PDF (2016) do not menti

## Hugo city (GEOID 2730392, pop. 15766)
- Zoning authority: City of Hugo (incorporated city in Washington County, MN; it does its own zoning under its city code). Not verified from the code text.
- [ ] Hugo City Code zoning chapter (accessory dwelling / accessory apartment rules, their current status, and the ordinance numbers and dates that first allowed them and later changed t  
  https://www.ci.hugo.mn.us/  
  _Why manual:_ robots.txt on www.ci.hugo.mn.us has 'User-agent: *' with 'Disallow: /', so I did not fetch it. Read it manually.
- [ ] Hugo Code of Ordinances on Municode, if hosted there (search the zoning chapter for 'accessory dwelling' and the history notes for ordinance numbers)  
  https://library.municode.com/mn/hugo  
  _Why manual:_ library.municode.com returned HTTP 403 on its robots.txt, so I did not retry. Check manually.
- [ ] City Council minutes or ordinances adopting or amending ADU rules (also check for any 2024–2025 amendments)  
  https://www.ci.hugo.mn.us/  
  _Why manual:_ The city site disallows all crawlers. My two web searches found no official Hugo ADU document.

## Robbinsdale city (GEOID 2754808, pop. 14646)
- Zoning authority: City of Robbinsdale (Robbinsdale City Code Chapter 5, Zoning; the code is hosted on American Legal Publishing)
- [ ] Search Robbinsdale City Code Chapter 5 (Zoning) for 'accessory dwelling unit' or 'accessory apartment' to see whether ADUs are allowed today, in which districts, and by what proces  
  https://codelibrary.amlegal.com/codes/robbinsdalemn/latest/overview  
  _Why manual:_ The site returned HTTP 403 Forbidden to the fetcher. robots.txt does not block it, but per the rules there was no retry 
- [ ] Look through the city's ordinance archive in Laserfiche for any ordinance adopting or amending ADU rules, and pull the adopting ordinance PDF and its date. The city's Ordinances pa  
  https://www.robbinsdalemn.com/173/Ordinances  
  _Why manual:_ Only recent ordinances are listed on the page, and the web search budget was already used up, so older ordinances could 
- [ ] Alternatively, ask the Community Development Director whether ADUs are allowed and when they were first adopted.  
  https://www.robbinsdalemn.com/187/Zoning  
  _Why manual:_ The city's Zoning page does not mention ADUs.

## Rogers city (GEOID 2755186, pop. 13295)
- Zoning authority: City of Rogers (Hennepin County). Hassan Township no longer exists: an orderly annexation took in the whole township (MBA docket OA-992-39, approved 1
- [ ] Rogers City Code zoning chapter (Ch. 125): check whether accessory dwelling units, accessory apartments or secondary units are allowed, and under which ordinance and date. A Ramsey  
  https://codelibrary.amlegal.com/codes/rogersmn/latest/overview  
  _Why manual:_ HTTP 403 when fetched. Per the rules, I did not retry or work around it.
- [ ] City of Rogers planning or zoning pages, and council ordinances adopted since 2022, looking for any ADU ordinance  
  https://www.rogersmn.gov/  
  _Why manual:_ robots.txt disallows ClaudeBot from all paths (Disallow: /), so I did not fetch it
- [ ] Hassan Township's own zoning ordinance from before 2012, to see whether it allowed accessory or second dwellings before the 2012 annexation into Rogers  
  https://www.mba.state.mn.us/maindocket-record/47087  
  _Why manual:_ No official source for Hassan Township's old zoning ordinance was found within the search budget. The MBA record (read) 

## Rogers city (GEOID 2755186, pop. 13295)
- Zoning authority: City of Rogers (incorporated city in Hennepin County; zones itself). This comes from Rogers being an incorporated city, not from a document I read.
- [ ] Rogers City Code zoning chapter: find the section on accessory dwelling units, accessory apartments or secondary units, check whether ADUs are allowed today (by right, by permit or  
  https://www.rogersmn.gov/  
  _Why manual:_ robots.txt on www.rogersmn.gov disallows ClaudeBot (it allows User-agent *), so I fetched nothing from the city site. ro
- [ ] Online Rogers code hosts (Municode or American Legal), to find the ADU section and its ordinance history.  
  https://codelibrary.amlegal.com/codes/rogersmn/latest/overview  
  _Why manual:_ This American Legal URL returned HTTP 403, and library.municode.com also returned 403 on its robots.txt. I did not retry
- [ ] City council minutes and ordinances adopting or amending ADU rules, which would date when ADUs were first allowed and any later changes such as dropping owner occupancy or allowing  
  https://www.rogersmn.gov/  
  _Why manual:_ The web search budget was used up before any search ran, and the city site is blocked to ClaudeBot by robots.txt. A pers

## Vadnais Heights city (GEOID 2766460, pop. 12912)
- Zoning authority: City of Vadnais Heights (city zones itself; zoning code is in the City Code hosted on Municode)
- [ ] Vadnais Heights City Code, zoning chapter: check whether accessory dwelling units / accessory apartments are allowed (permitted, conditional or interim use, or prohibited), whether  
  https://library.municode.com/mn/vadnais_heights/codes/code_of_ordinances  
  _Why manual:_ The city's Code Enforcement page links to its code on Municode. library.municode.com returned HTTP 403 even for robots.t
- [ ] Alternate copy of the code to check, if Vadnais Heights also publishes there  
  https://codelibrary.amlegal.com/codes/vadnaisheightsmn/latest/overview  
  _Why manual:_ HTTP 403 Forbidden. No retry or workaround was attempted.
- [ ] City Council agendas and minutes: look for any zoning text amendment that adds or changes accessory dwelling units, and get the adopting ordinance PDF  
  https://www.cityvadnaisheights.com/AgendaCenter  
  _Why manual:_ Not reached within the budget. Without web search, no ordinance number was identified to look up.

## Lake Elmo city (GEOID 2734244, pop. 11335)
- Zoning authority: City of Lake Elmo (incorporated city; zones itself under City Code Title XV, Chapter 154 Zoning). Washington County does not zone it.
- [ ] Lake Elmo City Code Chapter 154 (Zoning): find whether 'accessory dwelling unit' is a permitted, conditional or interim use in each residential/rural district, the definition secti  
  https://codelibrary.amlegal.com/codes/lakeelmo/latest/lakeelmo_mn/0-0-0-1  
  _Why manual:_ American Legal Code Library returned HTTP 403 to the fetcher (robots.txt allows general agents); not retried per rules
- [ ] City of Lake Elmo website: adopted ordinances list, Planning Commission and City Council minutes on any ADU / accessory dwelling text amendment (look for when ADUs were first added  
  https://www.lakeelmo.gov/  
  _Why manual:_ lakeelmo.gov returned HTTP 403 even for robots.txt; legacy lakeelmo.org has an expired TLS certificate

## White Bear township (GEOID 2712369916, pop. 11049)
- Zoning authority: City of White Bear Lake (incorporated city in Ramsey County; zones itself under its own City Code zoning chapter)
- [ ] Current White Bear Lake zoning code: check the residential districts and accessory-use sections for accessory dwelling units / accessory apartments, and note the ordinance numbers   
  https://www.whitebearlakemn.gov/  
  _Why manual:_ The city site (whitebearlake.org redirects to whitebearlakemn.gov) returned HTTP 403 even for robots.txt; per the rules 
- [ ] Hosted White Bear Lake city code (American Legal): ADU provisions and the amendment history for each section  
  https://codelibrary.amlegal.com/codes/whitebearlakemn/latest/overview  
  _Why manual:_ HTTP 403 on fetch (robots.txt itself was readable and does not block ClaudeBot); I did not confirm the city's code is ho
- [ ] City council minutes and ordinances adopting or amending ADU rules (search 'accessory dwelling unit' in the agendas and minutes archive)  
  https://www.whitebearlakemn.gov/  
  _Why manual:_ City site blocked (403). No web search was possible because the session's search budget was already used up

## Victoria city (GEOID 2767036, pop. 10546)
- Zoning authority: City of Victoria (incorporated city in Carver County; zones itself). Not confirmed from a document read in this run.
- [ ] Victoria City Code zoning chapter (Chapter 1000 / zoning ordinance): check whether accessory dwelling units / accessory apartments are allowed in residential districts, by right or  
  https://library.municode.com/mn/victoria/codes/code_of_ordinances  
  _Why manual:_ library.municode.com returned HTTP 403 on robots.txt; did not retry or work around it. Web search budget for this turn w
- [ ] City of Victoria website: planning/zoning pages, adopted ordinances, and city council minutes on ADU or accessory apartment amendments (including any 2024-2025 housing-related code  
  https://www.victoriamn.gov/  
  _Why manual:_ victoriamn.gov and ci.victoria.mn.us returned HTTP 403 on robots.txt (victoriamn.org did not resolve); did not retry or 

## Arden Hills city (GEOID 2702026, pop. 9939)
- Zoning authority: City of Arden Hills (city zoning code, City Code Chapter 13, published on American Legal Publishing)
- [ ] Check the current Arden Hills City Code Chapter 13 (Zoning) for any accessory dwelling unit or accessory apartment provision. Note whether ADUs are permitted, need a CUP, or are no  
  https://codelibrary.amlegal.com/codes/ardenhills/latest/ardenhills_mn/0-0-0-1  
  _Why manual:_ codelibrary.amlegal.com returned HTTP 403 to the fetcher. Its robots.txt does not block our agents. I did not retry.
- [ ] Check whether the 2026 Zoning and Subdivision Code Update, with proposed ordinances considered in Sept–Oct 2026, adds or changes ADU rules. Find the adopted ordinance number and da  
  https://www.cityofardenhills.org/1242/Zoning-and-Subdivision-Code-Update  
  _Why manual:_ The project page lists proposed use-specific standards such as cottage courtyards but does not mention ADUs. The draft c
- [ ] Search the archived ordinances and council minutes for any earlier ADU or accessory apartment amendment.  
  https://miweblink2.metro-inet.us/ahpublic/Welcome.aspx  
  _Why manual:_ This is a Laserfiche WebLink archive that has to be browsed interactively. I did not read it within the budget.

## Mound city (GEOID 2744476, pop. 9398)
- Zoning authority: City of Mounds View (incorporated city in Ramsey County; zones itself under its city code zoning title)
- [ ] Mounds View city code zoning chapters: check for accessory dwelling unit / accessory apartment provisions, whether attached or detached ADUs are allowed, permit type, owner-occupan  
  https://codelibrary.amlegal.com/codes/moundsviewmn/latest/overview  
  _Why manual:_ amlegal returned HTTP 403 (bot challenge), so the page was not read. robots.txt does not disallow general agents. I also
- [ ] City of Mounds View website: planning/zoning pages, council minutes and adopted ordinances that mention ADUs or accessory dwelling units (search council packets for 'accessory dwel  
  https://www.moundsviewmn.org/  
  _Why manual:_ The site returned HTTP 403 even for robots.txt, so nothing was fetched.
- [ ] Possible alternate code host (Municode) for the Mounds View code, if the city's code is published there  
  https://library.municode.com/mn/mounds_view  
  _Why manual:_ library.municode.com returned HTTP 403 for robots.txt. I did not fetch it or confirm that it hosts this code.

## Oak Grove city (GEOID 2747690, pop. 8929)
- Zoning authority: City of Oak Grove (a statutory city in Anoka County; it administers its own zoning code, not the county)
- [ ] Oak Grove city code, zoning chapter: is there an accessory dwelling unit / accessory apartment provision, when was it adopted, and by which ordinance number (also check later amend  
  https://www.ci.oak-grove.mn.us/  
  _Why manual:_ The city's robots.txt sets Disallow: / for User-agent *, so the site was not fetched.
- [ ] Oak Grove code of ordinances on Municode (if hosted there): search for 'accessory dwelling' and check the ordinance history notes  
  https://library.municode.com/mn/oak_grove  
  _Why manual:_ library.municode.com returned HTTP 403 on robots.txt, so it was not retried or fetched.
- [ ] Planning commission and city council minutes or ordinances mentioning accessory dwelling units / accessory apartments, to date the first adoption and any amendments  
  https://www.ci.oak-grove.mn.us/  
  _Why manual:_ The site is blocked by robots.txt. Web search was also unavailable because the shared per-turn search limit was already 

## Minnetrista city (GEOID 2743306, pop. 8262)
- Zoning authority: City of Minnetrista (incorporated city in Hennepin County; does its own zoning)
- [ ] Minnetrista City Code zoning chapter: find the accessory dwelling unit / accessory apartment provisions, whether they are permitted or need a CUP or IUP, and the history notes list  
  https://codelibrary.amlegal.com/codes/minnetristamn/latest/overview  
  _Why manual:_ American Legal returned HTTP 403 to the fetch tool, so the page was not retried. robots.txt does not block ClaudeBot.
- [ ] City website: adopted ordinances, and planning commission or city council minutes on accessory dwelling units (for the dates and ordinance numbers)  
  https://www.cityofminnetrista.gov/  
  _Why manual:_ cityofminnetrista.com redirects to cityofminnetrista.gov, which returned HTTP 403 even for robots.txt, so the page was n
- [ ] Web search for Minnetrista ADU ordinance history  
  https://www.cityofminnetrista.gov/  
  _Why manual:_ The shared WebSearch budget for this turn ran out, so no search was run
