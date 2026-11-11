# Fort Worth and Dallas: parser hand check after the shared parser fix, 2026-11-11

**What:** a new recall check of the shared ADU description parser (`lotline.parse.permit_text`) on two Texas
parser sources, `fw_permits` (Fort Worth) and `dallas_permits` (Dallas), after #376 and #380 changed what they
count. Method: D-074 step 1 as amended by D-078 §2–3 (`docs/analysis_plan.md`), run per source, never pooled.
Ben approved the check on 2026-11-11. No engine, scenario, fit or dev-run script was run, nothing was
downloaded, and `--unblind` was not used.

**Headline.**

| Source | Flagged ADUs (main) | Precision among flagged | Recall | k = 1 / recall (90%) |
|---|---:|---:|---:|---:|
| Fort Worth | 117 | 0.77 (23/30; 90% Wilson 0.62–0.87) | **0.40** (0.27–0.55) | **2.49 (1.83–3.66)** |
| Dallas | 1 | 1/1 | 1 of 6 true ADUs found (0.17) | **Can't be estimated.** The whole pool holds 6 true ADUs |

The parser misses more than half of Fort Worth's ADUs. With k at 2.49, Fort Worth is a low-recall row under
D-078 §3, in the same class as the Texas inferred-ADU rule (2.30). Dallas has too few ADUs in its table to
measure recall. Both results come mostly from phrasings the parser does not read yet (§4), so a parser fix
followed by a fresh check would change both numbers.

## 1. Data and the two pools

- **Rows:** the rebuilt processed tables in `LOTLINE_DATA_DIR` (`processed/tx/permits/*.parquet`, rebuilt
  2026-11-11; `reports/adu-rebuild-2026-11-11.md`). These tables are holdout-filtered. Every sampled permit is
  a row in them.
- **Descriptions:** processed tables do not keep the work description (it can hold addresses), so it was
  joined back by `permit_id` from the cached 2026-11-11 raw pages (`raw/<source>/2026-11-11/permits/q-*/`). The
  pages were read straight from disk and nothing was fetched. The descriptions were read in memory, with
  phone numbers and emails scrubbed, and none were stored. Only short snippets appear below, with addresses
  removed.
- **"Flagged" means flagged by the parser on `main`** (`14add706`, which includes #380). Each source's own
  adapter `build()` ran in memory on those raw pages. Fort Worth gives the same 117 ADUs as the processed
  table. Dallas gives **1**, against 2 in the processed table: the rebuild ran before #380 merged, and #380
  drops the storage-shed false positive (`1105231031`, "CAN NOT BE USED AS SECOND DWELLING UNIT"). That permit
  now sits in the near-miss pool, where it was judged NOT_ADU.
- **Near-miss pool:** permits the parser on `main` does not flag whose description matches an ADU-like word
  (case-insensitive): garage apartment / garage apt, guest house / quarters / suite / cottage, servant,
  living quarters, additional living, second / 2nd (living) unit or dwelling, accessory dwelling, ADU,
  in-law, granny, casita, carriage house, quarters.

| Source | Flagged (N) | Near-miss pool (N) | Sampled flagged | Sampled near-miss |
|---|---:|---:|---:|---:|
| Fort Worth | 117 | 400 | 30 | 30 |
| Dallas | 1 | 18 | **1 (all)** | **18 (all)** |

**Draw:** `numpy.random.default_rng(20261111)`, one generator per source. The flagged draw was taken first,
then the near-miss draw, each of `min(30, N)` without replacement. Dallas's pools are smaller than 30, so the
check covers all of them, a census rather than a sample.

Dallas's table holds only building permits for new construction and additions (`dallas_permits` `WHERE`).
Garage conversions filed as alterations are not in it, so this check cannot see them.

## 2. The judging rule, fixed before any sampled description was read

Written at 11:56 on 2026-11-11, after the pool sizes were known and before any sampled description was
printed. Each permit gets one label from its description and its permit type, subtype and use:

- **NEW_ADU:** the permit creates a new dwelling unit accessory to a house on the same lot. That can be a new
  detached unit, an addition built as a separate living unit, or a conversion of a garage or accessory
  building into a living unit. Named forms count when the permit's work is to build or convert them: garage
  apartment, in-law / mother-in-law suite or quarters, ADU, accessory dwelling, second / 2nd dwelling (unit),
  servant's or additional living quarters, guest house *with* living, bed, bath or kitchen words. A kitchen
  need not be stated. Fort Worth's own permits bar a separate kitchen service for "detached habitable
  accessory" units, so "no kitchen / no stove" in-law suites are Fort Worth's ADU form.
- **LEGALIZE:** the unit already exists and the permit legalizes it ("already built", "without permit",
  "permitting existing", "work has been done"). **Not a new ADU** (Ben, 2026-11-11).
- **SFD_WITH_ADU:** a permit for a new main house that also names an ADU or guest quarters. **One SFD**, not an
  ADU.
- **CONTEXT:** the ADU is only context. This covers work on an existing ADU, work on the main house, a
  structure "not to be used as a second dwelling", or a removal.
- **NOT_ADU:** anything else (room additions, a guest *suite* inside the house, duplexes, build-to-rent
  "casita" cottages).
- **UNCLEAR:** too short to tell, e.g. "guest house" with no living words. It is counted as not an ADU in the
  central case and as an ADU in a sensitivity.

**One label added while judging, for transparency.** **REPERMIT** is a new permit for a unit that already
has a flagged permit. One Fort Worth permit cites a previous permit that is itself flagged as an ADU. It is
a real unit, but the second permit double-counts it, so it is judged not new.

**One reading made under the rule.** "Living quarters" in a separate building, a new detached garage with
living quarters above for example, was read as NEW_ADU, under "additional living quarters". A sensitivity
reads those as UNCLEAR.

**Estimators.** Precision = NEW_ADU ÷ flagged sample. Recall is weighted back to the two pools:
true ADUs among flagged ≈ precision × N_flagged, true ADUs among near-misses ≈ (NEW_ADU share of the near-miss
sample) × N_near-miss, and recall = flagged true ÷ (flagged true + near-miss true). k = 1 / recall. The 90%
interval combines the two strata's 90% Wilson endpoints, flagged low with near-miss high and the reverse.
This is wider than a true 90% interval, so it errs on the safe side. A parametric bootstrap (Jeffreys draws,
seed 20261111, 200,000 draws) is shown beside it as a check. For Dallas the pool is a full census, so recall is
a plain Wilson interval on found ÷ true.

**Assumption:** a permit with none of the ADU-like words is assumed not to be an ADU. Any ADU filed without
those words lowers true recall below these numbers, so the recall here is an upper bound and k a lower bound.

## 3. Results

### 3.1 Fort Worth (`fw_permits`)

| Label | Flagged sample (30) | Near-miss sample (30) |
|---|---:|---:|
| NEW_ADU | **23** | **10** (3 of them "living quarters") |
| LEGALIZE | 2 | 1 |
| REPERMIT | 1 | 0 |
| SFD_WITH_ADU | 1 | 0 |
| CONTEXT | 1 | 7 |
| NOT_ADU | 0 | 4 |
| UNCLEAR | 2 | 8 |

| Case | Precision (90%) | Recall (90%, Wilson-combined) | Bootstrap recall | k = 1 / recall (90%) | precision ÷ recall |
|---|---:|---:|---:|---:|---:|
| **Central (strict NEW_ADU)** | **0.77 (0.62–0.87)** | **0.40 (0.27–0.55)** | 0.31–0.52 | **2.49 (1.83–3.66)** | 1.91 |
| "Living quarters" as UNCLEAR | 0.77 | 0.49 (0.32–0.66) | 0.36–0.64 | 2.04 (1.52–3.09) | 1.56 |
| UNCLEAR counted as ADU | 0.83 | 0.29 (0.22–0.37) | 0.24–0.35 | 3.46 (2.68–4.60) | 2.88 |
| LEGALIZE counted as ADU (not the rule; for comparison) | 0.83 | 0.40 (0.28–0.53) | 0.31–0.51 | 2.50 (1.89–3.54) | 2.09 |

Pool totals in the central case: about 90 true ADUs among the 117 flagged and about 133 among the 400
near-misses.

**Legalizations (Ben's rule).** There were 3 in the samples: 2 flagged and 1 near-miss. A keyword screen of
the full pools ("already built", "without (a) permit", "as-built", "work has been done", "permitting
existing") finds **6 of the 117 flagged** and **9 of the 400 near-misses** with legalization wording. That is
a screen, not a hand check. The #376 fix already drops "already built" in some phrasings (2 permits, per the
rebuild report), but not "Accessory already built without permit" or "(WORK HAS BEEN DONE)". Both of those
are still flagged.

Example snippets (shortened, addresses removed):

- Flagged, NEW_ADU: "CONVERT GARAGE TO APARTMENT"; "NEW 2 BEDROOM 1 BATH MOTHER IN LAW SUITE"; "Garage
  converted to ADU. New bathroom, small kitchen"; "DETACHED MOTHER IN LAW SUITE - Not allowed separate
  service … in kitchenette".
- Flagged, not new: "Accessory Dwelling 924 square feet … already built without permit" (LEGALIZE);
  "CONVERTING GARAGE INTO APARTMENT (WORK HAS BEEN DONE)" (LEGALIZE); "GARAGE APARTMENT/REPLACE 1 EXTERIOR
  DOOR" (CONTEXT); "New Barndo with … attached garage and mother-in-law suite" on a new single-family permit
  (SFD_WITH_ADU); "300 SQ FT IN LAW SUITE PREVIOUS PERMIT PB22-…" where that earlier permit is also flagged
  (REPERMIT).
- Flagged, UNCLEAR: "LOFT OR IN-LAW SUITE ABOVE"; a garage addition with "a room and kitchenette and
  bathroom for the above ground pool".
- Missed, NEW_ADU: "DETACHED GARAGE APT"; "SFR/ NEW DETACHED MOTHER IN LAW SUITE/"; "NEW ADDITION TO
  EXISTING GARAGE TO CREATE A MOTHER-IN-LAW SUITE WITH NO STOVE"; "DETACHED LIVING QUARTER"; "New garage on
  1st floor/Living quarters on 2nd floor; separate building from residence"; "ADD BATHROOM TO DETACHED
  GARAGE//REVISE TO CONVERT GARAGE TO GUEST HOUSE"; "to be construct second dwelling onto first existing
  floor".
- Near-miss, not ADU: "Remodel of existing mother-in-law suite" (CONTEXT); "PERMITTING EXISTING GUEST HOUSE"
  (LEGALIZE); D.R. Horton build-to-rent "Casita Master" cottages (NOT_ADU); "NEW CONSTRUCTION OF GUEST
  HOUSE" (UNCLEAR).

### 3.2 Dallas (`dallas_permits`)

| Label | Flagged (1, all) | Near-miss (18, all) |
|---|---:|---:|
| NEW_ADU | **1** | **5** |
| SFD_WITH_ADU | 0 | 1 |
| CONTEXT | 0 | 2 |
| NOT_ADU | 0 | 4 (3 are "may not / cannot be used as a 2nd dwelling", incl. the #380 shed) |
| UNCLEAR | 0 | 6 ("guest house" with no living words) |

- **Precision:** 1/1 ("ADU APPROVED BY BOA").
- **Recall:** the parser finds 1 of 6 true ADUs (0.17, 90% Wilson 0.04–0.50, so k = 6 with a 90% range of
  2–26). With UNCLEAR counted, it finds 1 of 12 (0.08). **This is not a usable estimate.** Six true ADUs in
  the whole table, from 1999 to 2024, are too few, and the range covers a factor of 13. Recall is reported
  here as a plain fact, not as a k.
- **Missed, NEW_ADU:** "CONSTRUCT DETACHED GARAGE WITH SECOND DWELLING"; "2ND DWELLING UNIT"; "ADDITION OF
  400SF ACCESSORY DWELLING UNIT(BDA…)"; "ADDITION PORCH/GARAGE/2ND DWELLING UNIT" (two-family land use, so
  the adapter does not consider it); "Finish work on revoked permit … 2nd dwelling approved by bda".
- **What Dallas does show:** ADU permits there are rare. Even counting every candidate, the table holds 6 to
  12 over 25 years, which fits Dallas allowing rentable ADUs only by special exception
  (TX-4819000-adu-2018). The low count is real, but the parser's count of 1 understates it.

## 4. Why recall is low: parser phrasings to fix (follow-up, not done here)

Each of these was run through `parse_description` on `main`, and each returns no building type:

- "DETACHED GARAGE APT" (the abbreviation "APT");
- "SFR/ NEW DETACHED MOTHER IN LAW SUITE/" and "… EXISTING GARAGE TO CREATE A MOTHER-IN-LAW SUITE WITH NO
  STOVE";
- "DETACHED LIVING QUARTER(S)" / "living quarters on 2nd floor; separate building" (left out by design for
  precision; this check finds them to be ADUs in Fort Worth);
- "CONSTRUCT DETACHED GARAGE WITH SECOND DWELLING", "2ND DWELLING UNIT", "ACCESSORY DWELLING UNIT(BDA…"
  (Rule 3b and the ADU name do not fire on these strings).

The parser also still flags two legalization phrasings, "already built without permit" and "(WORK HAS BEEN
DONE)", and one repair of an existing unit ("GARAGE APARTMENT/REPLACE 1 EXTERIOR DOOR").

A parser change is a shared-contract change (WS-CORE). Under D-078 §3, when a parser fix raises a source's
measured recall, a new hand check replaces the old k. So the k proposed below holds only until that fix
lands.

## 5. Limits

- One judge (Claude Code), with no second coder. The UNCLEAR and "living quarters" sensitivities show how
  much the judgment matters. It moves Fort Worth's k between 2.0 and 3.5.
- Recall is measured only within the word-defined pool, so it is an upper bound (k a lower bound).
- Fort Worth permits are dated by filing year. The sample covers 2003–2026, unweighted by year. Earlier
  years may have used different phrasings.
- Some missed ADUs sit on permits the adapter already types as SFD or U2 with units. Scaling the ADU count
  by k does not remove them from those counts. In the Fort Worth near-miss sample, 2 of the 10 missed ADUs
  already carry 1 counted unit in the processed table (one typed SFD, one typed OTHER via a parser
  conversion). In the Dallas census, none of the 5 missed ADUs carries a counted unit.
- Precision is below 1. k = 1 / recall (D-074 / D-078) scales flagged counts that include about 23% non-new
  permits. The correction that maps flagged counts to true ADUs is precision ÷ recall (1.91 for Fort Worth,
  central). Both are shown so Ben can choose. The proposed row follows the method as written.

## Proposed undercount-table rows

For `adu_flag_undercount` in `config/params/adu.yaml`. Proposed only; that file is not edited here.

| Source | k | 90% range | Citation |
|---|---:|---|---|
| `fw_permits` (Fort Worth) | **2.49** | **1.83–3.66** | This report §3.1. Recall 0.40 (Wilson-combined 0.27–0.55) from 30 flagged + 30 near-miss permits, seed 20261111, rule in §2. A low-recall row under D-078 §3: mark it on the results page and report Fort Worth with and without it. Sensitivities: 2.04 ("living quarters" unclear), 3.46 (unclear as ADU). Precision ÷ recall alternative: 1.91 |
| `dallas_permits` (Dallas) | **none: recall not estimable** | (1/6 found; Wilson k 2–26) | This report §3.2. A census of the 1 flagged and 18 near-miss permits holds 6 true ADUs. Under D-078 §2, Dallas has no usable k and does not enter the fit until a parser fix and a fresh check, or until it enters as a floor source (count only, `floor: true`) if Ben prefers |

## How this was made

Claude Code wrote throwaway scripts in its scratch folder, outside the repo. They read the cached raw pages
from disk, re-ran each adapter's `build()` with the `main` parser in memory, kept only `permit_id`s present in
the holdout-filtered processed tables, built the two pools and drew the seeded samples. Claude Code wrote down
the judging rule before printing any sampled description, read and labelled each sampled description by hand,
and computed the estimators and Wilson and bootstrap intervals with numpy. No data was written to the repo,
the data dir or the manifest.
