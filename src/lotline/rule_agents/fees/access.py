"""Polite access: robots.txt, blocked-response detection and quote matching (LESSONS R1-R5).

The swarm downloads only through `lotline.io.http` (one honest user agent, manifest, cache). This module adds
what that layer does not do: a robots.txt check before the first request to a host, a plain reason when a
response is a block (so it becomes a human task instead of a retry), and a word-for-word quote check against
the text of a saved file.
"""

from __future__ import annotations

import re
import unicodedata
from urllib import robotparser
from urllib.parse import urlsplit

from lotline.io.http import USER_AGENT

# Phrases that mark a bot wall, challenge or login page (case-insensitive)
_CHALLENGE = re.compile(
    r"cf-chl|just a moment\.\.\.|attention required|access denied|request unsuccessful|incapsula|"
    r"captcha|are you a robot|akamai|bot detection|enable javascript and cookies",
    re.IGNORECASE,
)
_LOGIN = re.compile(r"<input[^>]+type=[\"']?password|sign in to continue|log ?in to view", re.IGNORECASE)


def robots_url(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}/robots.txt"


def robots_allows(robots_txt: str | None, url: str, user_agent: str = USER_AGENT) -> bool:
    """Whether robots.txt lets `user_agent` fetch `url`. No robots.txt (None or empty) allows everything."""
    if not robots_txt:
        return True
    rp = robotparser.RobotFileParser()
    rp.parse(robots_txt.splitlines())
    return rp.can_fetch(user_agent, url)


def access_reason(status: int, body: str = "", robots_ok: bool = True) -> str | None:
    """None when the page can be used; otherwise a human-task reason code (handoff.REASONS).

    A 403/401/429, a challenge page or a login form is a block: the host is not retried in this run.
    """
    if not robots_ok:
        return "robots_disallow"
    if status in (401, 407) or _LOGIN.search(body or ""):
        return "login_required"
    # a challenge page is short; a long 200 page that merely names a CDN (e.g. "akamai") is not a block
    challenge = len(body or "") < 20000 and _CHALLENGE.search(body or "")
    if status in (403, 429, 503) or challenge:
        return "http_403_waf"
    if status == 404:
        return "not_found"
    if status >= 400:
        return "http_error"
    return None


def normalise(text: str) -> str:
    """Lower-case, NFKC, straight quotes and dashes, one space between words: for quote matching only."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(
        {0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"', 0x2013: "-", 0x2014: "-", 0xA0: " "}
    )
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_found(quote: str, text: str) -> bool:
    """True when `quote` appears word for word in `text` (after `normalise`); an ellipsis splits the quote
    into parts that must all appear, in order."""
    t = normalise(text)
    pos = 0
    for part in re.split(r"\s*(?:\.\.\.|…)\s*", quote):
        p = normalise(part)
        if not p:
            continue
        pos = t.find(p, pos)
        if pos < 0:
            return False
        pos += len(p)
    return True
