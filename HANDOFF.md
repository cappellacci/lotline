# Lotline: Handoff & Compliance Check

**Lotline** is the code name for our entry (repo and package: `lotline`). This is the status file for our entry in the **Housing Data and Technology Innovation Challenge** (Arnold Ventures / The Turnout). Read this first in any new conversation. It records what we've decided and what the rules require, and every requirement is checked either by `compliance_check.py` (**AUTO**) or by hand (**MANUAL**).

Sources, read 2026-09-29:
- Official Rules: https://housingchallenge.turnout.rocks/rules.html (controls if anything conflicts)
- Participant Handbook: https://housingchallenge.turnout.rocks/handbook.html
- Landing page: https://housingchallenge.turnout.rocks/

The rules say the Sponsor/Administrator can change them at any time (§22). Re-read both pages before each milestone and update the "last verified" date at the bottom.

---

## 1. Where we are

| Item | Status |
|---|---|
| Registration | **Done** (Ben confirmed 2026-10-04). Still to confirm for E5: welcome email and Challenge Platform access received. |
| Eligibility | **Open question: confirm U.S. legal residency and a U.S. bank account (see E1).** |
| Team | Undecided. 1–5 people; the roster is locked when registration closes. |
| State | **Four-state approach (Ben, 2026-10-04): develop and test on MN, TX, NC and OH, starting with MN.** Official benchmark state for the statewide total (S5) still to choose; MN recommended (`research/lotline-mn-scouting.md` §5). Re-scored against the model design: MN 37, TX 34, NC 32, OH 30 of 45 (`research/lotline-state-reassessment.md`). |
| GitHub repo | **`https://github.com/cappellacci/lotline`** (Ben's personal account `cappellacci`, public). Not created yet; commands in BUILD_PLAN §7.1. |
| Build plan | `docs/build/BUILD_PLAN.md` v1 (2026-10-04) with Claude Code workstream briefs in `docs/build/workstreams/`. **Phase 0 (repo bootstrap, WS-00) must be pushed before Oct 7, 9:00 a.m. ET.** No commits Oct 7 09:00 → Oct 14 09:01 unless the organizers confirm that week counts. |
| Research assets | "Housing Data Readiness Ranking" artifact (v3, 2026-09-30): all 50 states + DC scored on reform post-periods and lot-level data. `lotline-policy-inventory.csv`: 199 linked laws/ordinances. All states now researched; low-confidence rows flagged. |
| Scenarios | **Missing Middle + ADUs + Fee reduction** (project focus). Parking a planned stretch 4th (2026-09-30). Scenarios can be combined. All share one parcel-count and pro forma engine. |
| Outcome metric | Leaning **permits** (Census Building Permits Survey: monthly, every state, splits 1 / 2 / 3–4 / 5+ unit buildings). |
| Design principle | A general framework that any jurisdiction can feed its own data into, however sparse, with results added up to a statewide total. |

### Decisions log
| Date | Decision | Why |
|---|---|---|
| 2026-09-29 | Rank states on data quality and measurability, not policy type | Avoid overfitting to one reform; the rules reward handling sparse data (§8) |
| 2026-09-29 | Missing Middle as lead scenario (tentative) | Removes a legal barrier instead of subsidizing; strong NC/OR data fit |
| 2026-09-29 | Leading scenario set: Missing Middle + ADUs + Fees; Parking an optional 4th (tentative) | All three work on single-family parcels through one pro forma engine; none needs transit data, so it suits sparse-data states |
| 2026-09-30 | Study design: lot-by-lot before/after evidence from real reforms calibrates a statewide model | Handbook wants statewide outputs; lot-level data used as calibration input, not output |
| 2026-09-30 | Policy inventory completed (199 items); PA, NJ, DE, DC, LA, MS, AL filled in; IN HEA 1001 confirmed review-only; MD 2025 ADU law = HB 1466 (Ch. 197); Cleveland form-based code in force in 3 pilot areas | Closes gaps from the first research pass |
| 2026-09-30 | **Calibrate where reforms are old, apply where they aren't.** ADU uptake curve estimated from Portland (2010), Los Angeles/California (2017, 2020) and Seattle (2019) with controls (Clark County WA, Phoenix/Las Vegas, Puget Sound cities); weak reforms (NH, Minneapolis, DC) as contrast. Curve transported to the chosen state by home value/rent. | The tool is for states that haven't reformed yet; the strongest, oldest ADU evidence is on the West Coast. See `research/adu-study-design.md` and `research/lotline-methods-review.md` |
| 2026-09-30 | Work each theme separately, ADUs first; build moves to Claude Code in `~/Engineering/lotline` | Data pulls, tests and git need a local repo with open network access |
| 2026-09-30 | Code name **Lotline** (`lotline`) | Parcels are the model's basic unit; reads cleanly as a repo/CLI name. Understory was considered and dropped as too pessimistic |
| 2026-09-30 | **Assumptions are user controls, not just policies.** The key drivers (ADU uptake rate, construction cost, rents/home values, parking developers still build) get plain-language sliders, each showing its source and reasonable range; the headline 5-year range updates as they move | Arnold Ventures housing director's launch post asks for a tool where users "toggle across policy options and assumptions"; serves Usability (20%), Transparency (30%) and the sensitivity requirement (S6) |
| 2026-09-30 | **Scenarios can be combined** (e.g. ADUs + Missing Middle + Fees together). One shared parcel pool; overlap modeled explicitly so a lot is never counted twice (ADU vs. Missing Middle compete for the same lots; the fee cut applies to both) | "Toggle across policy options" implies stacking; the legislator's real question is "what if we pass all three?" |
| 2026-09-30 | **Parking moves from optional 4th to planned stretch scenario**; Fees stays in the benchmark set | Judge's post names ADUs, duplexes and parking cuts as the headline reforms; parking is cheap on the shared pro forma engine (we still state how much parking developers would build) |
| 2026-09-30 | If the chosen state already has a reform on the books, model it as a **labeled state-specific scenario** (S7) alongside the benchmarks (tentative) | Post stresses 30+ states have passed reforms and people want to know their yield; adds Policy Insight value |
| 2026-10-04 | **Develop and test on four states (MN, TX, NC, OH); start with MN.** One is the official benchmark state; the others are portability runs on the same code | Sparse data is the point of the challenge: running across data tiers shows the framework works where data is thin. MN scouting passed 4 of 5 deciding facts and has an ADU-flagged, permit-level metro dataset (Met Council 2009–24). |

---

## 2. Scoring rubric (Official Rules §8)

| Criterion | Weight | What raises the score |
|---|---|---|
| Transparency & Explainability | **30%** | Assumptions and logic stated clearly; data sources retrievable; limitations stated; sensitivity shown; readable by non-technical policymakers, with a technical companion document; AI-written code explained. Also the **tie-breaker** for the top 5. |
| Replicability & Scalability | **25%** | Modular, documented code; **can swap in alternative datasets**; assumptions kept separate from mechanics; meaningful tests; single-command setup; pinned, current, vulnerability-free dependencies. |
| Usability | 20% | Clear interface; easy to compare scenarios; plain-language labels; stable and responsive. |
| Methodological Soundness | 15% | Sound economic and land-use logic; valid parameters; reasonable sensitivity ranges; tests prove the code does what the methodology says. |
| Policy Insight & Interpretation | 10% | What drives the differences between scenarios; which assumptions matter most; limits. **Bonus for applying the method to states with less complete data.** |

> "Teams will not be penalized for AI assistance, but they will score lower if their code cannot be verified, explained, or reproduced." (§8)

---

## 3. Compliance checklist

Legend: **AUTO** = checked by `compliance_check.py` · **MANUAL** = a person confirms. Tick the box when it is true today, not when it's planned.

### E. Eligibility & registration: fatal if missed (Rules §2–5)
- [ ] **E1** MANUAL: Every team member is a legal resident of a U.S. state or DC **and** keeps a U.S. bank account for the whole Challenge Period (to Jan 30, 2027).
- [ ] **E2** MANUAL: Every member was 18+ (or the age of majority) on **Sept 14, 2026**.
- [ ] **E3** MANUAL: No member is an excluded person: employees of the Sponsor, Administrator, judges or mentors (or their affiliates), their immediate family or household members, or anyone with a conflict of interest.
- [ ] **E4** MANUAL: Any government employee has disclosed their status for ethics review (landing-page FAQ). Everyone has checked their employer's rules (§2, §10.6).
- [ ] **E5** MANUAL: Registered via the Microsoft Form **before 9:00 a.m. ET Oct 7, 2026**, and the welcome email and Challenge Platform access arrived. *(Registration submitted, confirmed 2026-10-04; tick once the welcome email and platform access are in hand.)*
- [ ] **E6** MANUAL: Team of 1–5; each person is on one team only; Team Leader named (they submit, receive the prize and file the W-9). **Roster locks at registration close.**
- [ ] **E7** MANUAL: Only team members build the Submission. Mentors and outsiders may advise but not build (§5).

### S. Scope (Rules §7a + Handbook)
- [ ] **S1** AUTO: Baseline plus **at least 3** of the 5 benchmark scenarios, using the Handbook's exact definitions:
  - `adu`: one ADU per parcel with an existing single-family building; detached/semi-detached ≥600 sq ft allowed; no added parking.
  - `missing_middle`: 2–6 units on single-family-only parcels, up to 3 stories; setbacks and lot coverage assumed not to constrain.
  - `tod`: more height/FAR near major transit stops; **we define and justify** the stop threshold and distance; parking may be reduced or removed.
  - `parking`: minimum parking requirements reduced or removed; **we state** how much parking developers would still build.
  - `fees`: total development fees cut 50% from a **$50,000/unit** baseline.
- [ ] **S2** AUTO: Baseline = current rules and economy, no policy change.
- [ ] **S3** AUTO: **5-year** projection horizon.
- [ ] **S4** AUTO: One outcome metric chosen (permits, starts, completions or stock growth) **with a written justification**.
- [ ] **S5** MANUAL: Results **added up to a statewide total** for one chosen state (a sub-state breakdown is optional).
- [ ] **S6** MANUAL: Results shown as ranges, sensitivity or uncertainty, **never single numbers only**.
- [ ] **S7** MANUAL: Optional state-specific extra scenarios are clearly labeled as separate from the benchmark ones.
- [ ] **S8** MANUAL: **All Submission work was created on or after Sept 14, 2026.** Pre-existing code, including our own earlier market monitors, is not reused unless it is open-source and disclosed. Rebuilding ideas is fine; copying earlier private code is the risk.

### D. Deliverables: an incomplete Submission is not scored (Rules §7a)
- [ ] **D1** AUTO+MANUAL: Interactive tool (web app or notebook) that actually works, not a mockup. URL recorded in `challenge.toml`.
- [ ] **D2** AUTO: Slide deck as **PDF, ≤30 slides**, covering approach, findings and policy implications.
- [ ] **D3** MANUAL: Demo video **≤5 min**, viewable **without an account**. Test the link in a private window.
- [ ] **D4** AUTO (sections) + MANUAL (length): **Model & Assumptions Overview**, ≤25 pages single-spaced, with all 7 sections: purpose and scope · core assumptions and rationale · data sources and cleaning steps · methodological approach (equations, logic flows, scenario definitions) · limitations and edge cases · sensitivity notes · intended users and use cases.
- [ ] **D5** AUTO: Source code with docs that let a third party run it independently.
- [ ] **D6** AUTO (sections) + MANUAL (length/tone): **Policy Scenario Comparison**, ≤4 pages single-spaced, non-technical, covering: comparison to baseline · what drives the differences · critical assumptions · limitations.
- [ ] **D7** AUTO: Data provenance: every dataset has source, version, access date, license, cleaning steps and known limitations (Handbook).
- [ ] **D8** AUTO: Disclosures of AI coding tools, pretrained models/weights/embeddings, external APIs/hosted services, and third-party code/deps/datasets with licenses; plus any dependency-license exceptions (§7b–c).
- [ ] **D9** MANUAL: Submitted by the Team Leader through the team link **before 11:59 p.m. ET Dec 16, 2026**. Nothing is accepted late.

### T. Technical, reproducibility & security gates: failing one means disqualification (Rules §7b, §7d)
- [ ] **T1** AUTO: **Public GitHub repository.**
- [ ] **T2** AUTO: Approved license file with full text: **Apache-2.0** (recommended), MIT, BSD-3-Clause or BSD-2-Clause. **No** GPL/AGPL/LGPL/MPL/EUPL, **no** CC0/Unlicense. The license is named in the README.
- [ ] **T3** AUTO: Reproducible setup from documented commands, with no undocumented manual steps. Setup command recorded in `challenge.toml` and the README.
- [ ] **T4** AUTO: Automated tests cover the core logic, **pass on a clean checkout**, and the run command is documented.
- [ ] **T5** AUTO: No committed secrets (local pattern scan) **and** GitHub secret scanning enabled with zero open alerts.
- [ ] **T6** AUTO: **Dependabot alerts** and **CodeQL** enabled, with no unaddressed critical/high findings (or each one justified in writing).
- [ ] **T7** AUTO+MANUAL: **SBOM** exported (Insights → Dependency graph → Export SBOM) and committed.
- [ ] **T8** AUTO: Every dependency has a permissive license (flag copyleft, source-available, noncommercial or unknown). ⚠ Common trap: `certifi` (pulled in by `requests`) is **MPL-2.0**, so disclose it or justify it.
- [ ] **T9** AUTO: Dependencies pinned.
- [ ] **T10** AUTO: No large source datasets committed; data comes in through **automated download scripts** from authoritative sources.
- [ ] **T11** MANUAL: Any paid or restricted data has a clear free access path for end users.
- [ ] **T12** MANUAL: Written in a memory-safe language (Python, etc.), or any gaps in the security tooling are documented.

### P. Post-submission (Rules §8–9, §17)
- [ ] **P1** MANUAL: If we're in the top 5, the Team Leader is reachable around **Jan 18, 2027**. The demo is **Jan 20, 2027**: 15 min presentation + 5 min Q&A, remote.
- [ ] **P2** MANUAL: Finalists may be asked to sign a Sponsor License Agreement (non-exclusive, non-commercial).
- [ ] **P3** MANUAL: Winners need a W-9, an ACH payment to the Team Leader, and possibly an eligibility affidavit and release. **Team prize split agreed in writing beforehand.**

---

## 4. Key dates (ET)

| Date | Event |
|---|---|
| Sept 14, 2026 | Challenge Period and registration open; work counts from this date |
| **Oct 7, 2026, 9:00 a.m.** | **Registration closes; team roster locks** |
| Oct 7 09:00 → Oct 14 09:01 | **Gap not covered by the Rules** (work must be created in the Registration or Coding Period). No commits unless organizers confirm; see BUILD_PLAN §0 |
| Oct 14, 2026, 9:01 a.m. | Coding Period opens; team submission links sent to Team Leaders |
| **Dec 16, 2026, 11:59 p.m.** | **Submission deadline** |
| Jan 18, 2027 (approx.) | Finalists contacted |
| Jan 20, 2027 | Remote demo round (top 5) |
| Jan 30, 2027 | Challenge Period ends (bank-account requirement runs to here) |
| Feb 2027 | Winners announced: $20K / $12K / $6K |

---

## 5. Using the checker

Copy these files into the repo root: `compliance_check.py`, `challenge.toml` and `.github/workflows/compliance.yml`. Fill in `challenge.toml`, then:

```bash
python compliance_check.py              # static checks (files, config, license, secrets, data size)
python compliance_check.py --run        # also runs the setup and test commands from challenge.toml
python compliance_check.py --github     # also checks GitHub settings via the `gh` CLI (public, secret scanning, Dependabot, CodeQL)
python compliance_check.py --deps       # also scans installed dependency licenses (needs `pip install pip-licenses`)
python compliance_check.py --all        # everything
```

The script exits non-zero on any **FAIL**. **WARN** items need a look, and **MANUAL** items are listed as a reminder. It only uses the Python 3.11+ standard library, so it adds no dependencies of its own.

*Last verified against the Rules and Handbook: 2026-09-29.*
