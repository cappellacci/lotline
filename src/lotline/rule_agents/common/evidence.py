"""The evidence and blocker models every rule swarm writes.

Built from the MM swarm's `findings.Evidence` (the master copy) with the fee swarm's additions: `doc_id`
(the document store's sha256 id), `page`, and `quote_status` (how the quote was checked). A category's
finding model (MM `RuleFinding`, ADU eras, fee items) holds a list of these.

Evidence rule for all three categories: every coded field cites a URL, a verbatim quote of at most 300
characters and the retrieval date; the quote is found by machine in the stored document (`quote_status`
`verbatim`), or read off a scanned page (`image_read`, never high confidence on its own), or came from a
person's lookup (`human`).
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

QUOTE_MAX = 300  # the reforms and fees schemas' source_quote limit

SOURCE_KINDS = (
    "code",  # the codified ordinance (Municode etc.)
    "ordinance",  # the adopted ordinance / signed text
    "minutes",  # council minutes or agenda packet
    "staff_report",
    "fee_schedule",  # an adopted fee or rate schedule
    "city_page",  # a city web page about the change
    "news",
    "state_law",
    "archive",  # a Wayback Machine copy of any of the above
    "mirror",  # a third-party code mirror (e.g. Zoneomics): undated; confirm on the official code
    "search_summary",  # an AI or search-engine summary: a lead only, never evidence on its own
    "human_lookup",  # an answer from the human lookup sheet
    "other",
)
# Lead-only sources: never enough on their own for a coded value (OH brief 2026-11-01; NC/MN second coding).
LEAD_ONLY = ("news", "search_summary")
# Sources that may support a value but never at high confidence on their own.
SECONDARY = ("city_page", "mirror", "news", "search_summary", "other")
QUOTE_STATUS = ("verbatim", "image_read", "human", "not_checked")
CONFIDENCE = ("high", "medium", "low")

BLOCKER_KINDS = (
    "robots_disallow",  # robots.txt forbids the path for our user agent: never fetch it
    "http_403_waf",  # 403 / Cloudflare or Akamai challenge ("Just a moment...")
    "code_host_wall",  # Municode / American Legal / eCode360 / Granicus shells that need a browser
    "login_required",
    "js_only",  # the page is an empty shell without JavaScript
    "scanned_pdf",  # a PDF with no text layer
    "not_found",  # 404 / dead link, no archive copy
    "unreachable",  # timeout, DNS failure, TLS error, connection refused (one try; not retried)
    "records_request_only",  # public-records request only: optional task for the user; agents never file
    "ambiguous_source",  # readable, but the text does not settle the field
    "conflicting_sources",
    "budget_spent",  # the place's search/fetch/token budget ran out before the field was settled
)


class Evidence(BaseModel):
    field: str  # the coded field this quote supports, or "component" / "status" for context quotes
    url: str
    quote: str = Field(max_length=QUOTE_MAX)
    retrieved: date
    section: str | None = None  # e.g. "Sec. 20.3.2 Table 2-1", "Ord. 2019-048 §3"
    page: int | None = Field(default=None, ge=1)  # PDF page, from `docs quote`
    snapshot: str | None = None  # path of the saved copy (as `fetch` printed it)
    doc_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")  # document store id (sha256)
    source_kind: Literal[SOURCE_KINDS] | None = None  # type: ignore[valid-type]
    quote_status: Literal[QUOTE_STATUS] | None = None  # type: ignore[valid-type]

    @field_validator("url")
    @classmethod
    def _http(cls, v: str) -> str:
        if not re.match(r"^https?://", v):
            raise ValueError(f"evidence url must be http(s): {v!r}")
        return v


class Blocker(BaseModel):
    url: str
    kind: Literal[BLOCKER_KINDS]  # type: ignore[valid-type]
    detail: str = ""  # status code, robots line, what the page showed
    fields: list[str] = Field(default_factory=list)  # which fields this source would have settled
    look_for: str = ""  # what a person should look for at the URL


def max_confidence(evidence: list[Evidence]) -> str:
    """The highest confidence a field can have given its evidence (shared rule, all three PRs):
    high needs a primary source whose quote was found by machine; any secondary-only, image-read-only or
    unchecked support caps it at medium; lead-only support caps it at low.

    By hand: [code, verbatim] -> high; [mirror, verbatim] -> medium; [code, image_read] -> medium;
    [news] -> low; [] -> low."""
    if not evidence:
        return "low"
    kinds = {e.source_kind for e in evidence}
    if kinds <= set(LEAD_ONLY):
        return "low"
    primary_checked = any(
        e.source_kind not in SECONDARY and e.quote_status in ("verbatim", "human") for e in evidence
    )
    return "high" if primary_checked else "medium"
