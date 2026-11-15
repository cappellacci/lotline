# D-088 rescored on the checked rule rows

Method: D-088 in `docs/analysis_plan.md`, unchanged; see its 2026-11-15 rescoring note. Ben asked for the run on
2026-11-15 ("Score A + place types on the checked rule rows"). Run at `a40c09cf`, the top of the ADU stack, which
carries #419's source-checked rule rows. Offline from cached tables; St. Paul stays out; nothing unblinded.

```bash
# from the main checkout (the run reads CENSUS_API_KEY from .env for the cached ACS request keys)
PYTHONPATH=<worktree>/src .venv/bin/python <worktree>/scripts/dev/adu_types_refit.py --out <worktree>/reports/adu-place-types-checked --workers 7
uv run python scripts/dev/adu_types_checked_page.py . reports/adu-place-types-checked/results.html
```

## Result

- Inputs: 64 places, 491 place-years (D-088: 395). Every place keeps its type.
- Fits: m_x 0.8 for every form (D-088: 0.4). A + P: θ 0.200 per 1,000, α 1.698, core +1.84 (+1.19 to +2.54).
- **A + P is useful in 4 of 4 scorable states at tiers 1 and 2** (observed ÷ P50 at tier 1: MN 0.76, NC 1.42,
  TX 1.45, OR 1.72), so it passes D-075's claim rule at tier 1. Ohio has no targets. Form A: 0 of 4 at every tier.
- Tier-1 held-out log score, A + P over A: +13.1 (2 SE 7.5).
- **D-088's rule keeps Form A:** A + P passes 1 of tests A–B against A's 2. The difference is test A in Texas,
  College Station alone (observed 5.4; medians A 6, A + P 25).
- A′ + P beats A′ under the same rule (lower tier).
- Test D: no form useful in any state; MN about ×2.6 over-forecast, NC ×1.6 under.
- Nothing written to config.
