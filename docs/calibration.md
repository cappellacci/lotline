# Calibration: where every fitted number comes from

About 130 values in `config/params/` are fitted to our own data (the rest are judgment, literature or the
Handbook's own numbers, each with its source). Every fitted value belongs to exactly one **calibration step**,
declared in `src/lotline/calibrate/steps.py`. Each step names:

- the values it produces;
- the decision in `docs/analysis_plan.md` it implements;
- the script or library function that computes it;
- the steps it needs first;
- whether today's value was written by code or copied from a report.

```bash
uv run lotline calibrate --list    # the steps in run order: what each produces, how, and its status
uv run lotline calibrate --check   # registry, config and lock agree (no data needed; also a test in CI)
```

`config/calibration.lock.json` records every fitted value as it stands. If a value changes in config without
its step being re-run and the lock rewritten (`lotline calibrate --write-lock`), the check fails, so a fitted
number can't drift from its fit unnoticed.

**Status of the steps.** Most are `current`. Three are marked `stale` because they were fitted on an earlier
model form and not yet re-fitted on the current one:

- `adu_state_effect` (τ, D-053);
- `adu_drift` (σ, D-090/D-091);
- `adu_ramp_share` (D-048).

One step, `v5_charlotte_prior`, is `frozen`: it serves only the frozen V5 Charlotte test.

**What comes next.** Phase 1 of the calibration design records the map; it runs no fits. In later phases each
step gets a `run` function, so `lotline calibrate --quick` (reduced draws, minutes) and a full run (same seeds
and draws, hours) re-derive the values from the fetched data and rewrite config and the lock in one command.
