## What does this change do?

<!-- One or two sentences. Link the issue: Closes #NN -->

## Checklist

- [ ] Tests added or updated for any core logic this change touches (hand-worked example for each equation)
- [ ] `uv run pytest -q` and `uv run ruff check .` pass locally
- [ ] `python compliance_check.py` shows 0 FAIL
- [ ] No secrets, `.env` files or downloaded data in this change
- [ ] Any new dependency is permissively licensed, Ben approved it, and it is listed in `docs/disclosures.md`
- [ ] New parameters live in `config/params/` with a source citation
- [ ] Docs (README or `docs/`) updated if behavior changed
- [ ] Logbook fragment added at `logbook.d/<YYYY-MM-DD>-<branch>.md`

## Proposed HANDOFF decisions

<!-- Decisions for Ben to fold into HANDOFF.md, or "none". -->
