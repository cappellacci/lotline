"""Moved to the shared core: `lotline.rule_agents.common.fetch` (store first, robots-respecting, one try).

ADU fetches go into the shared document store (`$LOTLINE_DATA_DIR/rule_docs/`, one copy per document for
every swarm): a URL any swarm already holds is served with no request; a refusal any swarm met in the last
30 days is returned with no request; a 403 is never retried with another user agent, curl or browser
headers (lessons L-R6). Text PDFs get a page-marked sidecar (pypdf), so quotes are checked by machine and
the page is named; a PDF with no text layer is a `scanned_pdf` blocker (read by eye, `image_read`).

Quote checks are `common.text.verify_quote` / `quote_page`, re-exported here for the ADU modules.
"""

from __future__ import annotations

from lotline.rule_agents.common.fetch import (  # noqa: F401 - re-exported for ADU callers and tests
    AGENT_TOKENS,
    HOST_INTERVAL,
    FetchResult,
    allowed,
    snapshot_name,
)
from lotline.rule_agents.common.fetch import get as _get
from lotline.rule_agents.common.text import quote_page  # noqa: F401
from lotline.rule_agents.common.text import verify_quote as quote_in_text  # noqa: F401

CATEGORY = "adu"


def get(url: str, run_id: str, **kw) -> FetchResult:
    """`common.fetch.get(url, "adu", run_id, ...)`; `kw` are document facts (jurisdictions, doc_type...)."""
    return _get(url, CATEGORY, run_id, **kw)
