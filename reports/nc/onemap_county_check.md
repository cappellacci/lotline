# NC OneMap counties: check against ACS one-unit homes

*WS-NC, 2026-10-21 (thread 10, S1). Parcels coded `SF_DETACHED` in each loaded county against ACS 2020–2024 B25024_002 (one-unit detached homes). Computed from the processed `onemap_parcels` table after the statewide download (45 counties).*

**Rule used to accept a drafted county:** a ratio between 0.6 and 1.4. Nine drafted counties fell outside it and were left out (they stay on the ACS fallback): Bertie 2.84, Montgomery 2.55, Greene 2.52, Halifax 2.32, Hertford 2.10, Wayne 1.66, Pender 1.55 and Sampson 1.52 (one broad "Residential" class that also holds mobile homes, duplexes and lots), and Columbus 0.32 (houses coded "OCCUPIED RURAL", read as agricultural). The list is `EXCLUDED` in `scripts/dev/nc_onemap_crosswalks.py`.

**Read with care:** Mecklenburg's ratio is low because Charlotte and the unincorporated county are held out (V5). Wake's 1.24 is the known OneMap coding of townhouses as detached; Wake places count from the Wake roll instead. A ratio below 1 in a drafted county is mostly parcels left `UNKNOWN` (a bare "Vacant" label); D-017 then sends the jurisdictions concerned to the ACS fallback.

| County | Crosswalk | Parcels | Unknown land use | SF detached (parcels) | ACS 1-unit detached | Ratio |
|---|---|---:|---:|---:|---:|---:|
| Mecklenburg (37119) | hand | 77,715 | 0% | 52,776 | 275,566 | 0.19 |
| Davidson (37057) | drafted | 98,494 | 45% | 37,405 | 56,950 | 0.66 |
| Bladen (37017) | drafted | 31,462 | 2% | 6,624 | 9,458 | 0.70 |
| Carteret (37031) | drafted | 63,503 | 45% | 22,415 | 31,696 | 0.71 |
| Madison (37115) | drafted | 19,709 | 5% | 5,899 | 8,139 | 0.72 |
| Buncombe (37021) | hand | 134,729 | 1% | 70,306 | 85,741 | 0.82 |
| Forsyth (37067) | hand | 166,755 | 0% | 108,828 | 117,350 | 0.93 |
| Vance (37181) | drafted | 26,344 | 1% | 11,703 | 12,373 | 0.95 |
| Yadkin (37197) | drafted | 28,148 | 46% | 11,734 | 12,311 | 0.95 |
| Durham (37063) | hand | 127,998 | 1% | 80,024 | 83,495 | 0.96 |
| Onslow (37133) | drafted | 94,292 | 28% | 55,116 | 56,934 | 0.97 |
| Henderson (37089) | drafted | 68,298 | 23% | 39,495 | 40,244 | 0.98 |
| Lenoir (37107) | drafted | 35,978 | 40% | 16,036 | 16,306 | 0.98 |
| New Hanover (37129) | drafted | 103,409 | 0% | 72,099 | 73,298 | 0.98 |
| Watauga (37189) | drafted | 46,252 | 0% | 21,269 | 21,202 | 1.00 |
| Cumberland (37051) | hand | 132,422 | 0% | 93,915 | 93,087 | 1.01 |
| Alamance (37001) | drafted | 79,387 | 13% | 51,007 | 50,549 | 1.01 |
| Lee (37105) | drafted | 34,617 | 38% | 18,796 | 18,546 | 1.01 |
| Rockingham (37157) | drafted | 54,899 | 1% | 31,977 | 31,447 | 1.02 |
| Guilford (37081) | hand | 222,435 | 1% | 151,431 | 148,244 | 1.02 |
| Gaston (37071) | hand | 116,701 | 14% | 76,394 | 74,590 | 1.02 |
| Pitt (37147) | drafted | 80,611 | 27% | 41,097 | 40,124 | 1.02 |
| Nash (37127) | drafted | 55,606 | 22% | 30,213 | 29,228 | 1.03 |
| Dare (37055) | drafted | 40,480 | 18% | 29,254 | 28,100 | 1.04 |
| Wilson (37195) | drafted | 41,316 | 1% | 24,561 | 23,446 | 1.05 |
| Craven (37049) | drafted | 59,840 | 1% | 35,077 | 32,944 | 1.06 |
| Brunswick (37019) | drafted | 151,721 | 4% | 73,549 | 68,856 | 1.07 |
| Randolph (37151) | drafted | 80,939 | 21% | 46,098 | 42,804 | 1.08 |
| Johnston (37101) | drafted | 125,040 | 21% | 76,423 | 69,127 | 1.11 |
| Burke (37023) | drafted | 58,347 | 33% | 31,695 | 28,535 | 1.11 |
| Harnett (37085) | drafted | 84,508 | 5% | 43,464 | 39,030 | 1.11 |
| Moore (37125) | drafted | 74,855 | 0% | 41,250 | 36,974 | 1.12 |
| Union (37179) | hand | 116,079 | 0% | 88,082 | 76,742 | 1.15 |
| Currituck (37053) | drafted | 26,873 | 0% | 17,161 | 14,882 | 1.15 |
| Edgecombe (37065) | drafted | 31,087 | 0% | 17,601 | 15,158 | 1.16 |
| Stokes (37169) | drafted | 31,914 | 32% | 17,672 | 14,983 | 1.18 |
| Stanly (37167) | drafted | 42,456 | 29% | 27,254 | 22,812 | 1.19 |
| Person (37145) | drafted | 28,177 | 33% | 16,995 | 13,914 | 1.22 |
| Iredell (37097) | drafted | 109,254 | 1% | 73,459 | 59,989 | 1.22 |
| Wake (37183) | hand | 435,380 | 1% | 357,253 | 289,147 | 1.24 |
| Pasquotank (37139) | drafted | 22,696 | 1% | 15,552 | 12,505 | 1.24 |
| Camden (37029) | drafted | 7,908 | 16% | 4,466 | 3,499 | 1.28 |
| Rutherford (37161) | drafted | 57,581 | 35% | 30,285 | 23,690 | 1.28 |
| Lincoln (37109) | drafted | 53,874 | 2% | 37,965 | 29,377 | 1.29 |
| Cabarrus (37025) | hand | 106,541 | 100% | 0 | 71,518 | — |
