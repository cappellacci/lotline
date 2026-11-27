### LB-NNN · 2026-11-27 · review · Results bundles record the data they used

**Question:** When a rerun of a published state comes out different, can anyone tell whether the data or
the code changed?

**Outputs:**
- `src/lotline/model/results.py`: `input_hashes` (sha256 of each processed table a state has, over its
  parquet files' names and bytes) and `combined_hash`. Each bundle's meta now carries `input_tables` (JSON,
  table: hash) and `input_hash`.
- `src/lotline/schemas.py`: schemas 1.26 adds both as optional fields, so older bundles still load;
  `docs/schemas.md` regenerated.
- `src/lotline/app/template.html`: the trust panel shows "Input data hash" when a bundle has one.
- `README.md`: a new section, "Reproduce the published numbers": which meta fields identify a run, and why a
  later fetch can give different inputs.
- Tests in `tests/model/test_results.py`.

**What Claude did:** Worked stability-review finding 2 (2026-11-27). Checked on real data: a Wisconsin bundle
carries schemas 1.26 and six table hashes; hashing Texas's 675 MB of processed tables takes about 2 s.

**Checked:** fast tier passed; ruff clean; compliance 0 FAIL. The tables are hashed after the holdout filter,
as built, so no hidden data is named.
