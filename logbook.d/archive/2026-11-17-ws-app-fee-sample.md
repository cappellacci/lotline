### LB-NNN · 2026-11-17 · Deliverables: the fee card shows what builders pay today, by kind of home
- **Question:** If the real fee is lower than the Challenge benchmark's $50,000, how much lower, and how do fees fall on houses, duplexes, fourplexes and ADUs?
- **What I did:**
  - **Data:** `src/lotline/dashboard/fees.py` lays out the fee scenario's own inputs for each state, with no new method. For every place with a coded fee schedule it gives:
    - the fee per home for a house, duplex, fourplex and ADU (`fee_levels.place_fees`, D-065, D-066: 2025 dollars, missing permit and water/sewer charges filled from the state median);
    - the house fee split into its parts;
    - the fee per lot;
    - the fee as a share of building cost (`pencil_out.row`; that cost does not depend on home value).
    It goes into the data dashboard summary (`summarize.state_fees`), which the app already reads. `fee_levels.component_fees` is a new public split of `coded_fees` by component.
  - **App, fee card:** a "What builders pay in fees today" section sits between the two versions and the year chart:
    - the typical, lowest and highest fee for a new house, and how many times lower it is than the Challenge's $50,000;
    - whether the $25,000 cut is more than the whole fee, and what halving the real fee saves;
    - a dot strip of every place against the benchmark;
    - a table by kind of home: fee per home, range, fee per lot and share of building cost. The typical fourplex pays about 4× a house's fee on one lot, at 2.5–2.9% of its cost against 1.5–2.0% for a house (8.7% against 5.8% in Oregon);
    - an ADU note; the ADU column shows only where some place charges ADUs differently from a house (e.g. Portland's waiver);
    - a folded table of every place, with the parts of each house fee.
    Holdouts' fees are shown: they are inputs, not outcomes (as in `docs/research/fee-levels-vs-handbook.md`).
  - **Wording (Ben):** the app calls the Handbook's benchmark the "Challenge benchmark"; the Handbook is still named as the document.
- **Inputs:** Ben's requests (2026-11-17); `config/fees/*.csv`; `docs/research/fee-levels-vs-handbook.md` and `docs/research/fee-pencil-out.md` (from the restored "Fees model/scenario plan" session) as the reference numbers.
- **Outputs:** `src/lotline/dashboard/fees.py`, `src/lotline/dashboard/summarize.py`, `src/lotline/model/fee_levels.py`, `src/lotline/app/build.py`, `src/lotline/app/template.html`; tests in `tests/dashboard/test_fee_sample.py`, `tests/model/test_fee_levels.py` and `tests/app/test_build.py`.
- **AI:** Claude Code wrote the change and tests (hand-worked fixtures). State medians were checked against the generated fee-levels doc: MN $9,168, NC $6,683, OH $7,194, OR $34,454, TX $6,516. Checked in the browser pane on all five states.
- **Open / next:** the published app needs the data dashboard summary regenerated (`scripts/build_data_dashboard.py`) so it carries the fee block. Most coded cities have no separate ADU charge, so their ADUs are shown paying a house's fee.
