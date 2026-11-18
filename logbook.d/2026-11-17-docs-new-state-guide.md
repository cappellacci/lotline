### LB-NNN · 2026-11-17 · DOCS · A step-by-step guide for adding a new state

- **Question:** Ben: "investigate all three models and create a step by step instruction guide for adding a new
  state, one that could be followed and executed by a human." This is the "bring your own state" guide that
  HANDOFF (2026-10-28, item 4) and validation plan V8 call for.
- **Outputs:**
  - `docs/adding_a_state.md`, the guide. It covers:
    - four data levels and the evidence for each (D-075 data-tier test, scored under D-088 on 2026-11-15:
      tier 1, coded local rules for the 20 largest places, is the lowest that passes for ADUs; national
      data alone was useful in Minnesota only);
    - the thresholds the code applies;
    - 14 steps with commands;
    - per-model tables of required, used-if-present and fallback inputs for ADU, missing middle and fees;
    - every state list written into the code.
  - `README.md` "Bring your own state" now links to the guide. It no longer claims that a new state needs
    no change to model code.
- **Found, not fixed (code):** a new state cannot run `lotline results` today:
  1. It must be added to `REFORM_STATES` (`model/scenarios/adu.py:1308`), or the ADU and missing-middle
     code raises a `KeyError`.
  2. A state with no permit adapter crashes. `store.read(st, "permits")` returns None and is used unguarded
     in `observed_adu_counts` and `results.build_bundle`.
  3. `tests/core/test_config.py:8` pins the five states.
  
  The guide lists these as known blockers (§3). Missing middle and fees have no data-tier result yet
  (D-092 run 5 skipped it).
- **What Claude did:**
  - read the ADU, missing-middle and fee scenario code, the config loader, registry, CLI, build steps,
    schemas and tests, with four read-only sub-agents, one per model plus one for the shared plumbing;
  - checked each blocker and every path, flag and command the guide cites directly in the code at
    `770c8d07`;
  - wrote the guide.
- **How it was checked:** each cited file exists and each CLI flag matches `--help` or the argparse code. The
  steps were **not** run on a new state; that is the V8 test.

### LB-NNN · 2026-11-17 · DOCS · Pipeline consolidation folded into WS-SCALE

- **Question:** Ben asked to consolidate the data pipeline: "one consolidated dataset feed all 3 models, making
  the process of tagging and identifying regions as simple as possible, and keeping the schema and structure as
  straightforward as possible". Then: "fold this into WS-SCALE".
- **Outputs:** `docs/build/workstreams/WS-SCALE.md`.
  - The brief was written on 2026-11-09 and had never been committed; it existed only in the main checkout.
  - It is now on this branch, with Ben's original goals kept.
  - Added to it:
    - the three consolidation goals;
    - an audit;
    - a draft design: a `geography` table extending `jurisdictions`, per-state aliases, one shared
      resolver, two crosswalk formats, and one `place_inputs` table for all three models and the
      baseline;
    - tasks 0–12, with zero-difference checks;
    - an order and risk note against the Dec 16 deadline.
  - `docs/adding_a_state.md` §3 now points to WS-SCALE task 0. The separate blocker card was withdrawn.
- **Found (audit, `main` at `770c8d07`):**
  - **ADU and MM each build their own place frame, and fees builds one in a dev script.** The scenarios and
    the baseline cover different places.
    - ADU drops places with no ACS rent or value.
    - MM keeps them, filling the share of lots that pencil out with the state median.
    - Fees fills a missing home value and flags it.
  - **MM skips D-056's tier-3 scaling**, with no recorded decision.
  - **Parcel stats for ADU coverage and MM house share use the latest roll** with no origin cap.
  - **About 19 disk reads of `jurisdictions` per results run**, because `DataStore.read` has no cache.
  - **Jurisdiction tagging is done seven ways.** The "known GEOID, else county" step is written five times.
  - **Crosswalks:** 73 files with 20 headers; 49 already share one format.
- **What Claude did:**
  - Two read-only sub-agents mapped per-model input assembly and geography tagging.
  - Claude checked the headline claims in the code: `results.py:520`, `mm.py:293-304`, `adu.py:1314-1327`,
    `mm.py:225-232`, and the crosswalk header counts.
  - Claude wrote the brief.
  - No code was changed. The fixes in task 5 are proposals for Ben, not decisions.
- **How it was checked:** the claims above were read in the code. Nothing was run.
