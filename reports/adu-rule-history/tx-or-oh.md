# D-086 ADU rule history: Texas, Oregon, Ohio places (first coder)

Coder: `claude-d086` (single coder; every new row is `single_coder`). Coded 2026-11-13 from public ordinance sources only.
No permit counts, no `LOTLINE_DATA_DIR`, no `reports/` outputs were opened. Oregon holdout (V9): no Oregon permit or
outcome data was opened. One exception to report: Portland's 2016 Accessory Structures adopted report (a city
code document read for its ADU regulatory history) has narrative remarks on ADU permit trends next to that history
(a 2010 average and a 2009 to 2014 growth rate). They were seen while reading the history, are not recorded in any row,
and were not used for any coding choice.

Files changed: `config/reforms/or.csv` (9 rows added, 3 existing rows given chain fields only),
`config/reforms/tx.csv` (1 row added).

D-023 grade: no ADUs 0; permit, conditional or special use 1/3; by right with owner occupancy 2/3; by right without it 1.

## Summary table

| Place (GEOID) | Versions in force 2014-2025 (effective date: what changed) | Grade before -> after | Rows added |
|---|---|---|---|
| Austin (4805000) | 2010 row (pre-2015 rule); 2015-11-30 Ord. 20151119-080; 2023-11-02 parking; 2024-02-05 HOME phase 1. All already coded. | 1 throughout | none |
| College Station (4815976) | **new:** 2012-04-26 no rentable ADU (living quarters for family or servants only); 2018-11-29 Ord. 2018-4059 allows rental (coded); 2023-08-10 parking (coded) | 0 -> 2018 row (adoption, not an event) | `TX-4815976-adu-2012` |
| San Antonio (4865000) | 2010 row (UDC §35-371, Ords. 96564, 97568, 100126, all pre-2010); 2023-01-01 Ord. 2022-11-03-0831 (coded) | 2/3 throughout | none |
| Bend (4105800) | **new:** 2014-01-01 pre-2016 rule, split: conditional use on SR 2 1/2, RL, RS lots created before Dec 1998, permitted elsewhere; 2016-03-18 Ord. 2260 (coded); **new:** 2019-12-06 Ord. NS-2353 deletes ADU parking; 2025-07-18 Ord. NS-2532 (coded); state rows 2018, 2020 kept | place grade 1 -> 1; **conditional part 1/3 -> 1 (candidate event, see below)** | `OR-4105800-adu-2014-cup`, `OR-4105800-adu-2014`, `OR-4105800-adu-2019` |
| Medford (4147000) | **new:** 2004-12-16 MLDC 10.821 (Ord. 7977 1995, Ord. 2004-259), in force to 2019; **new:** 2019-01-19 Ord. 2018-132 (no additional parking stated, more dwelling types and zones, 75% size); state rows kept | 1 -> 1 | `OR-4147000-adu-2004`, `OR-4147000-adu-2019` |
| Portland (4159000) | 1998 row; **new:** 2010-04-24 RICAP 5 text (the version in force at 2014-01-01); 2016-01-01, 2021-08-01, 2022-06-30 (coded); no change after 6/30/22 (current chapter still dated 6/30/22) | 1 -> 1 | `OR-4159000-adu-2010` |
| Salem (4164900) | **new:** 2014-01-01 no ADUs; **new:** 2017-08-09 Ord. Bill 10-17 (one ADU by right as a special use, 900 sq ft, no parking, no owner rule); state rows kept | 0 -> 1 (adoption, not an event) | `OR-4164900-adu-2014-none`, `OR-4164900-adu-2017` |
| Cincinnati (3915000) | no-ADU row to 2023-10-02; Ord. 0266-2023 (both coded) | 0 -> 2/3 (adoption, not an event) | none |

## Grade changes inside 2014-2025 (for the second coder)

- **Bend 2016-03-18 (candidate event, needs a decision).** Before Ord. 2260, ADUs needed a Conditional Use Permit on
  SR 2 1/2, RL and RS lots created before December 1998 (grade 1/3) and were permitted elsewhere (grade 1). Ord. 2260
  made them permitted everywhere. Coded as two rows split by coverage. The model takes the most permissive rule in
  force, so Bend's place-level grade stays 1 and the code will not build an event. If Ben or the second coder prefer
  to code pre-2016 Bend as conditional (only the `-cup` row), Bend 2016 becomes a 1/3 -> 1 event.
- Salem 2017 (0 -> 1), College Station 2018 (0 -> the 2018 row's grade) and Cincinnati 2023 (0 -> 2/3, already coded)
  are adoptions, not events under D-086.
- No other place changed grade inside the window. The new Bend 2019, Medford 2019 and Portland 2010 rows change only
  parking, coverage or uncertain fields.

## Changes to existing rows (chain fields only, noted in each row's `coding_notes`)

- `OR-4105800-adu-2016`: `supersedes` set to `OR-4105800-adu-2014-cup`; `end_date` 2019-12-06. **Effect:** its blank
  `owner_occ` now inherits False. Ord. 2260's full 3.6.200(B) text, deleted and new, has no owner-occupancy
  standard, so I believe False is right. But this changes an input of the Bend 2016-17 years that set m_x (D-053).
- `OR-4159000-adu-1998`: `end_date` 2010-04-24.
- `OR-4159000-adu-2016`: `supersedes` changed from the 1998 row to the new 2010 row (same fields).
- `TX-4815976-adu-2018` was **not** pointed at the new no-ADU row: its `by_right` is blank and would inherit False
  through `supersedes`. The no-ADU row ends by `end_date` instead.

## Uncertain points and flags

- Bend 2019: NS-2353 is a scanned PDF with no text layer. The parking deletion is read from the September 2019 code
  package memo (file 19-0597) and tied to NS-2353 by the register description and the 3.6.200 history note. The
  effective date (30 days after 2019-11-06) is computed.
- Bend pre-2016 start date: in force when Ord. 2260 was adopted. Its adoption was not researched, so the row is coded
  from 2014-01-01. Of the 2015 code ordinances, NS-2251 was read (no ADU change). NS-2240, NS-2241 and NS-2256 were not.
- Medford: Ord. 2018-132's text was not read (the code site blocks automated access). Fields come from the archived
  code as of Jan 2021, which also includes Ord. 2019-91 (Aug 2019). By right rests on the 10.314 table ('Ps' special
  use), read in a 2007 snapshot. Pre-2019 parking (two spaces per parcel, the same as a house alone) is coded as 0
  additional spaces. Some older one-space lots could not add an ADU.
- Salem: effective 2017-08-09 is computed (ORS 221.310(1)). Ord. 8-24 (2024) amended 700.007, but the current text
  still has one ADU, 900 sq ft, and no parking or owner rule. The 8-24 and 13-21 exhibits were not read.
- College Station: the no-ADU start (2012-04-26) is the date on the Article 11 header. The rule may be older. The text
  of Ord. 2018-4059 was not reachable (404).
- Portland 2010: by right is read from 33.205 (no land-use review). Table 110-2 for 2010 was not re-read.
- Existing rows I think may need a look (not changed):
  - `TX-4815976-adu-2018`: `by_right` is blank. Accessory living quarters are an allowed accessory use.
  - `TX-4865000-adu-2010`: parking is blank. The pre-2023 §35-371 text was not read.
  - `OR-4105800-adu-2016`: 600 sq ft applies on lots of 6,000 sq ft or less. `adu_max_sqft` is 800, the convention for the larger tier.

## Where nothing older or newer was found (what was searched)

- **Austin:** HOME phase 2 (Ord. 20240516-006, 2024). It cut single-family minimum lots to 1,800 sq ft, but two- and three-unit uses keep 5,750 sq ft (city HOME page, Community Impact). No ADU field changed, so no row. Nothing else was found between the 2015 and 2023 rows.
- **San Antonio:** §35-371 history (zoneomics mirror of the UDC) lists Ords. 96564, 97568, 100126, then 2022-11-03-0831 (eff. 2023-01-01). There was no amendment between 2010 and 2022.
- **Cincinnati:** the city ADU project page and WVXU (passed 2023-06-26, effective 2023-10-02). No 2024-2025 amendment to §1421-06 was found.
- **Oregon state rows** (SB 1051 2018, HB 2001 2020) were left unchanged. The new city rows overlap them consistently: every new city rule is at least as permissive as the state floor from its date.

## Sources (main)

- Bend Ord. 2260 with exhibits: https://bendoregon.gov/wp-content/uploads/2025/12/2260-with-Exhibits.pdf
- Bend 2019 code package memo: https://bendoregon.gov/home/showpublisheddocument/42896/637032924597730000
- Bend ordinance register: https://bendoregon.gov/resources/city-codes-policies-ordinances-and-resolutions/ordinances/
- Bend BDC 3.6.200 (archived 2023): https://web.archive.org/web/20230224212118/https://bend.municipal.codes/BDC/3.6.200
- Portland 33.205 (4/24/10 and 8/29/14 texts): https://web.archive.org/web/20120922064018/http://www.portlandoregon.gov/bps/article/53301 ;
  https://web.archive.org/web/20141216230752/http://www.portlandoregon.gov/bps/article/53301
- Portland Accessory Structures adopted report: https://www.portland.gov/sites/default/files/2020-02/accessory_structures_adopted_report.pdf
- Salem engrossed Ord. Bill 10-17: https://salem.legistar1.com/salem/attachments/5ade2e03-705a-4d8e-a015-b176be6f31ae.pdf ;
  staff report File 17-285: https://salem.legistar.com/LegislationDetail.aspx?GUID=CF6DE0AA-4EB4-4D90-A4F0-46A01924BD61&ID=3059723
- Medford MLDC 10.821 (archived 2014, 2021) and 10.314: https://web.archive.org/web/20140516112041/http://www.ci.medford.or.us:80/CodePrint.asp?CodeID=4038 ;
  https://web.archive.org/web/20210123170453/http://www.ci.medford.or.us/CodePrint.asp?CodeID=4038 ;
  https://web.archive.org/web/20071112174056/http://www.ci.medford.or.us/CodePrint.asp?CodeID=3818
- College Station UDO Article 11 and amendments page: https://www.cstx.gov/media/lmdesfgd/article-11.pdf ;
  https://www.cstx.gov/departments___city_hall/pds/regulations/udo
- ORS 221.310 (30-day effective rule): https://oregon.public.law/statutes/ors_221.310
