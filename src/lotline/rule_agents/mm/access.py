"""Polite access: robots.txt checks and the blocker classifier.

The retrieval agent never works around a block. Before fetching a URL it asks `robots_allows` (robots.txt
read with the stdlib parser, for the project's user agent and for `*`); after a fetch it asks `classify`
whether what came back is a usable page or a blocker. A blocker becomes a human lookup task
(`handoff.task_for`), never a guess.

Code hosts (Municode, American Legal, eCode360, Granicus/Legistar, Laserfiche WebLink, CivicPlus Archive
Center) are listed in `CODE_HOSTS` with the browser-only workaround a person can use, learned in the Oct-Nov
2026 data threads (docs/build/rule-agents/mm/LESSONS.md).
"""

from __future__ import annotations

import re
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

# Our fetches use lotline.io.http.USER_AGENT; robots rules are matched on its product token.
UA_TOKEN = "lotline"

# host suffix -> (label, what a person does in a browser)
CODE_HOSTS = {
    "municode.com": (
        "Municode Library",
        "Open the code in a browser, use the 'Versions' (clock) menu to compare dated versions, and the "
        "ordinance history note at the end of the section ('Ord. No. ..., § x, date').",
    ),
    "amlegal.com": (
        "American Legal Publishing",
        "Open in a browser; the section's history note in brackets gives the ordinance and date; "
        "'Code Alert'/'Ordinances' lists recent unadded ordinances.",
    ),
    "ecode360.com": (
        "eCode360 (General Code)",
        "Open in a browser; the chapter's 'History' tab and the 'New Laws' list give adoption dates.",
    ),
    "codepublishing.com": (
        "Code Publishing",
        "Open in a browser; the section's history note gives the ordinance and date.",
    ),
    "legistar.com": (
        "Granicus Legistar",
        "Search 'Legislation' for the ordinance or file number; the 'History' tab lists the vote date "
        "and attachments (signed ordinance, staff report).",
    ),
    "granicus.com": ("Granicus", "Open the agenda item; attachments hold the ordinance and staff report."),
    "civicplus.com": (
        "CivicPlus",
        "Use the city's Archive Center or Agenda Center; download the adopted ordinance PDF.",
    ),
    "laserfiche": (
        "Laserfiche WebLink",
        "Browse the city's WebLink repository in a browser (Ordinances folder by year); search by number.",
    ),
}

_CHALLENGE = re.compile(
    r"just a moment\.\.\.|cf-chl|checking your browser|attention required! \| cloudflare|"
    r"access denied|request blocked|incapsula|akamai|perimeterx|are you a robot",
    re.I,
)
_LOGIN = re.compile(r"<input[^>]+type=[\"']?password|sign in to continue|please log ?in", re.I)
_JS_SHELL = re.compile(r"enable javascript|you need to enable javascript|<noscript>", re.I)
_RECORDS = re.compile(r"public records request|records request portal|submit a request for records", re.I)


def host_label(url: str) -> tuple[str, str] | None:
    """(label, browser workaround) when `url` is on a known code host, else None."""
    host = (urlparse(url).hostname or "").lower()
    for suffix, info in CODE_HOSTS.items():
        if host == suffix or host.endswith("." + suffix) or suffix in host:
            return info
    return None


def robots_allows(robots_txt: str | None, url: str, ua: str = UA_TOKEN) -> bool:
    """Whether robots.txt lets `ua` fetch `url`. A missing robots.txt (None, e.g. a 404) allows everything;
    an empty string allows everything. Rules for our token win over `*`, as the stdlib parser applies them.
    By hand: "User-agent: *\\nDisallow: /search" -> /search/x False, /code True."""
    if robots_txt is None:
        return True
    rp = RobotFileParser()
    rp.parse(robots_txt.splitlines())
    return rp.can_fetch(ua, url)


def robots_url(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}/robots.txt"


def classify(
    url: str,
    status: int | None,
    *,
    content_type: str = "",
    text: str = "",
    pdf_text_chars: int | None = None,
    pdf_pages: int | None = None,
) -> tuple[str, str] | None:
    """(blocker kind, detail) for a fetch result, or None when the page is usable.

    `text` is the body (HTML or extracted PDF text; the first 500 kB are read). For a PDF pass
    `pdf_text_chars` (characters in its text layer) and `pdf_pages`: fewer than 200 characters per page means a scan (OCR is a human task;
    we don't ship an OCR engine). By hand: 403 with "Just a moment..." -> http_403_waf; 200 Municode shell
    with "enable JavaScript" and under 2,000 characters -> code_host_wall; a 12-page PDF with 300 characters
    of text -> scanned_pdf; 200 with ordinance text -> None.
    """
    code_host = host_label(url)
    head = text[:500000]
    # Challenge words count only in what a reader sees (title + body text), never in scripts: a normal city
    # page loading an Akamai script was misread as a bot wall in the 2026-11-17 dry run (St. Louis Park).
    visible = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", head, flags=re.S | re.I)
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", visible)).strip()
    challenge = bool(_CHALLENGE.search(visible[:3000]))
    if status == 401 or (status == 200 and _LOGIN.search(head)):
        return "login_required", f"HTTP {status}: login form"
    if status in (403, 429, 503) or (status == 200 and challenge and len(visible) < 3000):
        kind = "code_host_wall" if code_host else "http_403_waf"
        return kind, f"HTTP {status}: " + ("bot challenge" if challenge else "refused")
    if status is not None and status >= 400:
        return "not_found", f"HTTP {status}"
    if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
        if pdf_text_chars is not None and pdf_pages:
            if pdf_text_chars / max(pdf_pages, 1) < 200:
                return "scanned_pdf", f"{pdf_text_chars} text characters over {pdf_pages} pages"
        return None
    if _JS_SHELL.search(head) and len(visible) < 2000:
        return ("code_host_wall" if code_host else "js_only"), "page is a JavaScript shell"
    if _RECORDS.search(head) and len(visible) < 4000:
        return "records_request_only", "page offers only a records request"
    return None
