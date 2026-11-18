"""Moved to the shared core: `lotline.rule_agents.common.fetch` (2026-11-17).

MM fetches now go into the shared document store (one copy per document for all three swarms), store
first: a URL any swarm already holds is served with no request. `get(url, run_id)` keeps the MM signature.
"""

from __future__ import annotations

from lotline.rule_agents.common.fetch import (  # noqa: F401 - re-exported for MM callers and tests
    AGENT_TOKENS,
    HOST_INTERVAL,
    FetchResult,
    allowed,
    snapshot_name,
)
from lotline.rule_agents.common.fetch import get as _get


def get(url: str, run_id: str, **kw) -> FetchResult:
    return _get(url, "mm", run_id, **kw)
