"""Short, page-cited passages from stored documents: what a coder reads instead of a whole code.

Why: the 2026-11-17 dry runs spent 200k-370k tokens per place, most of it coders reading whole code
chapters, agenda packets and 300-page code books into context. A coder needs the use table row, the
definition, the standards section and the adoption/effective-date lines. `excerpts` finds those by
keyword in the text sidecar (no model involved), and returns the best passages up to a character budget,
each tagged with its document id and page so the quote can be checked and cited.

How: the sidecar is split into pages, each page into blocks (paragraphs, or section headings where a
page is one long block); each block is scored by weighted keyword hits for the category plus date and
enactment words; the highest-scoring blocks are kept until `max_chars`, then returned in document order.
A coder that needs more asks for another page (`docs text DOC --page N`) or a wider window, not the whole
document. `outline` lists headings with pages so a coder can aim at a section.

By hand: a 3-page text where page 2 says "Accessory dwelling units are permitted in R-1 ... adopted
June 4, 2019" and pages 1 and 3 are about signs -> `excerpts(..., "adu", max_chars=500)` returns the
page-2 block only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from lotline.rule_agents.common import text as T

# Words that mark a passage as relevant (weight 3 = topic word; 1 = supporting). Lower case, normalised.
KEYWORDS: dict[str, dict[str, int]] = {
    "mm": {
        "duplex": 3,
        "triplex": 3,
        "fourplex": 3,
        "quadplex": 3,
        "two-family": 3,
        "three-family": 3,
        "multi-family": 2,
        "multifamily": 2,
        "dwelling units per lot": 3,
        "units per lot": 3,
        "middle housing": 3,
        "townhouse": 2,
        "cottage": 2,
        "single-family": 1,
        "use table": 2,
        "permitted use": 1,
        "conditional use": 1,
        "special use": 1,
        "density": 1,
        "lot area": 1,
    },
    "adu": {
        "accessory dwelling": 3,
        "adu": 3,
        "accessory apartment": 3,
        "granny": 2,
        "carriage house": 2,
        "guest house": 2,
        "secondary dwelling": 3,
        "garage apartment": 2,
        "owner-occup*": 2,
        "owner occup*": 2,
        "floor area": 1,
        "square feet": 1,
        "parking": 1,
        "detached": 1,
        "attached": 1,
        "permitted use": 1,
    },
    "fees": {
        "impact fee": 3,
        "system development": 3,
        "capacity fee": 3,
        "tap fee": 3,
        "connection fee": 3,
        "connection charge": 3,
        "park fee": 2,
        "parkland": 2,
        "fee schedule": 3,
        "building permit": 2,
        "plan review": 2,
        "per unit": 2,
        "per dwelling": 2,
        "per square foot": 2,
        "meter": 1,
        "valuation": 1,
        "$": 1,
        "surcharge": 2,
        "school": 1,
        "water": 1,
        "sewer": 1,
        "transportation": 1,
    },
}
DATE_WORDS = {
    "adopted": 2,
    "effective": 2,
    "ordinance no": 2,
    "ord. no": 2,
    "passed": 1,
    "enacted": 2,
    "amended": 1,
    "publication": 1,
    "repeal": 1,
    "fiscal year": 1,
    "fy": 1,
}
_HEADING = re.compile(
    r"^\s*((sec(tion)?\.?|§|article|chapter|division|part|table)\s*[\w.\-]+.*|\d+(\.\d+){1,4}\s+[A-Z].*)$",
    re.I | re.M,
)
_MONTH_DATE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}", re.I
)


@dataclass
class Passage:
    doc_id: str
    page: int
    score: float
    text: str

    def render(self) -> str:
        return f"[{self.doc_id[:12]} p.{self.page}] (score {self.score:g})\n{self.text.strip()}"


def blocks(page_text: str, window: int = 1200) -> list[str]:
    """Paragraph blocks, split further at section headings, and long blocks cut to `window` characters
    with a 15% overlap so a sentence is not lost at a cut."""
    paras = [p for p in re.split(r"\n\s*\n", page_text) if p.strip()]
    if len(paras) <= 1:
        cuts = [m.start() for m in _HEADING.finditer(page_text)]
        if cuts:
            cuts = sorted({0, *cuts})
            paras = [
                page_text[a:b]
                for a, b in zip(cuts, [*cuts[1:], len(page_text)], strict=True)
                if page_text[a:b].strip()
            ]
    out = []
    step = int(window * 0.85)
    for p in paras:
        if len(p) <= window:
            out.append(p)
        else:
            out += [p[i : i + window] for i in range(0, len(p), step)]
    return out


def _count(hay: str, kw: str) -> int:
    """Whole-word hits of `kw` in normalised text; a trailing `*` makes it a prefix ("owner-occup*")."""
    if kw == "$":
        return hay.count("$")
    prefix = kw.endswith("*")
    k = re.escape(T.norm(kw.rstrip("*")))
    return len(re.findall(rf"(?<![a-z0-9]){k}" + ("" if prefix else r"(?![a-z0-9])"), hay))


def score(block: str, category: str, words: dict[str, int] | None = None) -> float:
    """Weighted topic-word hits (each word counted at most 5 times), plus date and enactment words. A block
    scores only when it holds a strong topic word (weight 3): "parking" or "square feet" alone is not ADU
    evidence (Sunfish Lake code book check, 2026-11-17)."""
    hay = T.norm(block)
    s, strong = 0.0, False
    for kw, w in (words or KEYWORDS[category]).items():
        n = _count(hay, kw)
        if n:
            s += w * min(n, 5)
            strong = strong or w >= 3
    if not strong:
        return 0.0
    for kw, w in DATE_WORDS.items():
        if _count(hay, kw):
            s += w
    s += 2 * min(len(_MONTH_DATE.findall(block)), 3)
    return s


def excerpts(
    docs,
    doc_id: str,
    category: str,
    *,
    max_chars: int = 6000,
    extra: list[str] | None = None,
    pages: list[int] | None = None,
    window: int = 1200,
    min_ratio: float = 0.3,
    follow: int = 5,
) -> list[Passage]:
    """The best passages of one stored document for `category`, at most `max_chars` in all, in page order.
    `extra` adds words to look for (weight 3, e.g. a district code "R-1" or an ordinance number);
    `pages` limits the search to those pages. Blocks scoring under `min_ratio` of the best block are
    dropped even when the budget has room. Each strong block brings the next `follow` blocks on its page
    (the lettered standards under a heading, "A. ... D. Maximum size ..."), scored a little below it, so a
    heading is never returned without the rules it introduces."""
    if category not in KEYWORDS:
        raise ValueError(f"category must be one of {sorted(KEYWORDS)}")
    did = docs.resolve(doc_id)
    kws = dict(KEYWORDS[category])
    for w in extra or []:
        kws[w.lower()] = 3
    cands: list[tuple[int, Passage]] = []
    for n, pt in T.pages(docs.text(did)):
        if pages and n not in pages:
            continue
        bl = blocks(pt, window)
        scores = [score(b, category, kws) for b in bl]
        for k in range(len(bl)):
            for back in range(1, follow + 1):  # a follower of a strong block just above it
                if k - back >= 0 and scores[k - back] > 0 and scores[k] < scores[k - back] * 0.8:
                    scores[k] = max(scores[k], scores[k - back] * (0.8 - 0.05 * back))
            if scores[k] > 0:
                cands.append((len(cands), Passage(did, n, round(scores[k], 2), " ".join(bl[k].split()))))
    top = max((p.score for _, p in cands), default=0)
    chosen, used = [], 0
    for i, p in sorted(cands, key=lambda c: -c[1].score):
        if p.score < min_ratio * top:
            break
        if used + len(p.text) > max_chars:
            continue
        chosen.append((i, p))
        used += len(p.text)
    return [p for _, p in sorted(chosen, key=lambda c: c[0])]


def outline(docs, doc_id: str, *, limit: int = 80) -> list[tuple[int, str]]:
    """(page, heading) for section/article/chapter/table headings, so a coder can ask for one page."""
    out = []
    for n, pt in T.pages(docs.text(docs.resolve(doc_id))):
        for m in _HEADING.finditer(pt):
            h = " ".join(m.group(0).split())[:120]
            if len(h) > 3:
                out.append((n, h))
            if len(out) >= limit:
                return out
    return out
