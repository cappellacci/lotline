# Missing middle: fast-ramp sensitivity (D-100, 2026-11-17)

Pre-registered in `docs/analysis_plan.md` (D-100, "Fast-ramp sensitivity") before the run; Ben: "Yes, add it".

The Handbook missing-middle scenario, origin 2025, 4,000 draws, run three times with C4's values, draws and seed,
changing only the ramp's half-way point: 4.0 years (C4, the main result), 1.0 year (C4's low end) and 0.5 years
(`mm_ramp_half_years_fast`, D-100 R2's ramp for places that adopted on their own).

    uv run python scripts/dev/mm_fast_ramp_run.py --out reports/mm-d100/fast-ramp   # needs CENSUS_API_KEY in the env; reads cached tables only
    uv run python scripts/dev/mm_fast_ramp_page.py

| State | C4 median (P10–P90) | 1.0 yr median | 0.5 yr median (P10–P90) |
|---|---|---|---|
| TX | 12,066 (1,774–86,570) | 39,818 | 43,589 (6,448–312,206) |
| NC | 3,078 (461–21,906) | 10,182 | 11,110 (1,679–79,624) |
| OH | 2,621 (390–18,769) | 8,615 | 9,443 (1,408–67,461) |
| MN | 1,758 (255–12,353) | 5,768 | 6,300 (931–44,809) |
| OR | 256 (37–1,853) | 852 | 927 (136–6,728) |

Five-year added 2–4 unit homes net of houses torn down. Ratios to C4 (means): 3.30 at 1.0 year, 3.61 at 0.5,
in every state, as the hand calculation predicted (ramp sums 3.837 and 4.204 against 1.163). Year 5's share of
the five years: 0.57 (C4), 0.26, 0.24.

**Reading:** a timing sensitivity, not a second forecast. The Handbook rule is a state law; Oregon's
state-required places ramped at C4's 4.0 years. θ is held at C4's; R2's own θ (0.94 per 1,000) would make the
fast case about 9% lower.

Files: `summary.csv` (every measure, period and variant), `compare.json` (five-year P10/P50/P90/mean),
`params.json`, `run-log.txt`, `results.html` (https://claude.ai/artifact/CjkLoS18nmRupLFcyskYR6).
No permits read; nothing unblinded; config's main values unchanged.
