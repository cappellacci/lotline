### LB-NNN · 2026-10-22 · Build: faster D-025 refits, estimates unchanged
- **Question:** can D-025's pooled negative-binomial refits (randomization inference, leave-one-out, checks;
  also D-024's NB via `estimate_mm.fit_nb`) run much faster without changing any estimate?
- **What I did:**
  - Timed refits and counted BFGS iterations (`RefitLog.timing`, `fit.iterations`). On hard synthetic panels
    the slowest 5% of refits take 50–57% of the time: they run 500 iterations, fail, retry and fail again.
  - Evaluated all 31 quadrature nodes at once with the same arithmetic in the same order (log-likelihoods
    and scores bit-identical); made the Hessian analytic (Louis' identity, numerical kept as
    `hessian="numerical"`); added parallel refits (`workers`, `--workers`) that reproduce the serial run.
  - Tried a BFGS warm start from the main fit's inverse Hessian (`WARM_START`, left off).
- **Inputs:** synthetic panels only (`tests/model/test_pooled_adu.py::sparse_panel`); no real data was read
  or run.
- **Outputs:** `src/lotline/model/pooled_adu.py`, `scripts/dev/estimate_pooled_adu.py` (`--workers`),
  `tests/model/test_pooled_adu.py` (speed section), `docs/analysis_plan.md` (D-025 implementation note,
  2026-10-22).
- **Findings:** 999 permutations: 719 s → 342 s serial, 95 s on 8 processes, with the same p and every
  permuted effect identical to the last bit. On 360 hard refits the outcomes were identical (303 first,
  27 retried, 30 excluded), 3.5× faster. The warm start differs at BFGS's tolerance (~1e-4) and excluded 41
  refits instead of 30, so it is not used.
- **Decisions:** none (implementation note under D-025, no new D-number). A real rerun needs Ben's approval.
- **AI:** Claude Code (Opus 5.5) wrote the code, tests and note. It checked them against a frozen copy of
  `main`'s `pooled_adu.py` on synthetic panels (bit-identity, convergence counts, timings) and with new
  tests: analytic vs numerical Hessian, serial vs parallel, the 5% stop point, and warm vs cold.
- **Open / next:** the slow tail is refits that hit the 500-iteration cap twice. Failing them sooner would
  change the D-025 rule (Ben's call). `estimate_mm`'s own NB randomization inference gets the faster fit
  automatically.
