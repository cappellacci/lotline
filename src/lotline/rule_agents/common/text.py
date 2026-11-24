"""Text helpers every rule swarm shares: what a reader sees in a page, quote checks, draft markers.

Moved from the MM swarm (`mm/findings.py`) when the shared core was built (2026-11-17). Quote checks are the
backbone of the evidence rule: a coded value counts only when its quote is found, by machine, in the exact
bytes the coder read (the document store's text sidecar).
"""

from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser

PAGE_MARK = re.compile(r"^=== page (\d+) ===$", re.M)

_DRAFT = re.compile(
    r"\bdraft\b|ordinance no\.?\s*(?:x{2,}|_{3,}|\[)|\[insert|effective date\]|\bx{3,}-x{2,}\b|"
    r"for discussion only|not adopted|proposed ordinance",
    re.I,
)


def draft_markers(text: str) -> list[str]:
    """Signs that a document is an unsigned draft, not the adopted text (St. Louis Park, Eagan Ord. 528,
    Burnsville 2020 looked final). By hand: "Ordinance No. XXX-XX ... [insert effective date]" -> two
    markers; a signed ordinance -> []."""
    return sorted({m.group(0).strip().lower() for m in _DRAFT.finditer(text)})


def norm(s: str) -> str:
    """Lower case, NFKC, straight quotes, plain dashes, `§` -> s, punctuation other than $ % . ' " - to
    spaces, single spaces."""
    s = unicodedata.normalize("NFKC", s).lower()
    s = s.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-")
    s = s.replace("—", "-").replace("§", "s")
    s = re.sub(r"[^a-z0-9$%.'\"-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class _Visible(HTMLParser):
    """Collects text outside <script>, <style>, <template> and <noscript>; comments are dropped."""

    _SKIP = frozenset({"script", "style", "template", "noscript"})
    _BREAK = frozenset({"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "table"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._depth += 1
        elif tag in self._BREAK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._depth:
            self._depth -= 1

    def handle_data(self, data):
        if not self._depth:
            self.parts.append(data)


def visible_text(html: str, *, keep_lines: bool = False) -> str:
    """What a reader sees in an HTML page: scripts, styles, comments and tags removed, entities decoded.
    Uses the stdlib parser, so odd end tags (`</script >`, `</SCRIPT foo>`) are handled like a browser.
    `keep_lines` keeps a line break at block elements (for text sidecars and excerpts)."""
    p = _Visible()
    # Older stdlib parsers (3.12.7) miss `</SCRIPT foo>` as an end tag; browsers accept it: normalise.
    p.feed(re.sub(r"</(script|style|template|noscript)\b[^>]*>", r"</\1>", html, flags=re.I))
    p.close()
    if keep_lines:
        lines = (re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in "".join(p.parts).split("\n"))
        return "\n".join(ln for ln in lines if ln)
    return " ".join(p.parts)


def looks_like_html(text: str) -> bool:
    return bool(re.search(r"<(html|body|div|p|span)\b", text[:5000], re.I))


def _parts(quote: str) -> list[str]:
    return [p for p in re.split(r"\.\.\.|…|\[\.\.\.\]", quote) if norm(p)]


def _find_parts(parts: list[str], hay: str, squash: bool) -> bool:
    pos = 0
    for p in parts:
        needle = norm(p)
        if squash:
            needle = needle.replace(" ", "")
        k = hay.find(needle, pos)
        if k < 0:
            return False
        pos = k + len(needle)
    return bool(parts)


def verify_quote(quote: str, text: str) -> bool:
    """True when `quote` appears in `text` after normalising case, whitespace, curly quotes, dashes and
    punctuation (PDF text layers break lines and hyphenate). An ellipsis ("...") in the quote splits it into
    parts that must appear in order. A second pass ignores spaces altogether, because pypdf sometimes splits
    words ("dwel ling") (ADU dry run, 2026-11-17).

    By hand: "Up to  three\\ndwelling units" in "...up to three dwelling units on a zoning lot" -> True;
    "four" in a text without it -> False; "dwelling units" in "dwel ling units" -> True."""
    if looks_like_html(text):
        text = visible_text(text)  # a quote may span markup (Minneapolis dry run)
    parts = _parts(quote)
    hay = norm(text)
    return _find_parts(parts, hay, False) or _find_parts(parts, hay.replace(" ", ""), True)


def pages(text: str) -> list[tuple[int, str]]:
    """Split a sidecar with `=== page N ===` markers into (page, text). Text without markers is page 1."""
    marks = list(PAGE_MARK.finditer(text))
    if not marks:
        return [(1, text)]
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((int(m.group(1)), text[m.end() : end]))
    return out


def quote_page(quote: str, text: str) -> int | None:
    """The first page whose text holds `quote` (`verify_quote` rules), else None. A quote that spans a page
    break is found on the page where it starts by checking each page joined with the next."""
    pg = pages(text)
    for n, t in pg:
        if verify_quote(quote, t):
            return n
    for i, (n, t) in enumerate(pg[:-1]):
        if verify_quote(quote, t + "\n" + pg[i + 1][1]):
            return n
    return None
