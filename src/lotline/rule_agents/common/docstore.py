"""The primary-document store shared by the MM, ADU and fee rule swarms.

Ben's requirement (2026-11-17): "an intelligent way of storing and referencing primary documents and other
necessary data". Designed from the three swarms' SHARED_CANDIDATES proposals; MM's layout is the master,
with ADU's citation log and drop folder and the fee swarm's schedule history.

A **document** is a set of bytes. Its id (`doc_id`) is their sha256, so the same county code fetched by the
ADU swarm for one town and by the fee swarm for another is one document, read and extracted once. A URL whose
bytes change gives a new document that `supersedes` the old one; both are kept.

Layout (all under `LOTLINE_DATA_DIR`, never in the repo)::

    raw/rule_docs/<YYYY-MM-DD>/<host>/<url-hash><ext>   downloads, through lotline.io.http.fetch (manifest)
    raw/rule_docs_manual/<YYYY-MM-DD>/<file>             files a person saved, through DataStore.register
    rule_docs/blobs/<sha[:2]>/<sha><ext>                 hard link to the bytes: one blob per document
    rule_docs/blobs/<sha[:2]>/<sha>.txt                  text sidecar, `=== page N ===` markers
    rule_docs/index.jsonl                                append-only document events (latest wins)
    rule_docs/citations.jsonl                            append-only: which coded value cites which page
    rule_docs/blocks.jsonl                               append-only: hosts/URLs that refused us, and when
    rule_docs/inbox/                                     drop folder for files a person saved by hand

Rules: index, citation and block files are append-only JSON lines written under a file lock, so swarms that
run at the same time never clash and a swarm never assumes another has run. Nothing is deleted: a document
found to be wrong is `withdrawn` with a reason, and every citation of it can be listed (`cited_by`).
A document flagged `may_contain_outcomes` (staff reports with permit counts, dashboards) is a holdout risk:
`find` returns it with the flag set and agents must not open it for a place whose holdout is still blind.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from lotline.rule_agents.common import text as T

CATEGORIES = ("mm", "adu", "fees")
DOC_TYPES = (
    "code_section",  # one section or chapter of a codified ordinance
    "code_full",  # a whole code book
    "ordinance",  # an adopted (signed) ordinance
    "draft",  # an unsigned draft or proposed ordinance
    "minutes",
    "agenda_packet",
    "staff_report",
    "fee_schedule",
    "rate_ordinance",  # utility rates / system development charges
    "budget_book",
    "state_law",
    "city_page",
    "mirror",
    "news",
    "other",
)
TEXT_STATUS = ("text", "scanned", "image_read", "none")
_LIST_FIELDS = ("urls", "jurisdictions", "states", "categories", "notes")
_EXT_OK = (".pdf", ".htm", ".html", ".txt", ".json", ".xml", ".csv", ".xlsx", ".docx")
SCAN_CHARS_PER_PAGE = 200  # fewer text-layer characters per page than this = a scan (MM access.classify)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class DocRecord:
    """The current view of one document (all its index events folded together)."""

    doc_id: str
    path: str = ""  # blob path relative to the store root
    ext: str = ""
    bytes: int = 0
    pages: int | None = None
    text_status: str = "none"
    urls: list[dict] = field(default_factory=list)  # [{"url": ..., "retrieved": "YYYY-MM-DD"}]
    title: str = ""
    publisher: str = ""  # issuing body or host: "City of Raleigh", "municode", "wayback"
    doc_type: str = "other"
    jurisdictions: list[str] = field(default_factory=list)  # GEOIDs it governs (a county code: many)
    states: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)  # swarms that used it
    label: str = ""  # e.g. "FY2027", "amended through 2025-12-09"
    adopted_date: str = ""
    effective_date: str = ""
    supersedes: str = ""  # an earlier doc_id from the same URL or the same issuer's schedule
    added_by: str = ""  # run id, or human:<initials>
    may_contain_outcomes: bool = False
    draft_markers: list[str] = field(default_factory=list)
    withdrawn: str = ""  # reason, when withdrawn
    first_seen: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def first_url(self) -> str:
        return self.urls[0]["url"] if self.urls else ""


@dataclass
class Citation:
    doc_id: str
    category: str
    row_key: str  # reform_id, fee key, or "<geoid>/<rule>" before ids exist
    field: str
    quote: str
    page: int | None = None
    section: str = ""
    quote_status: str = "verbatim"
    run_id: str = ""
    at: str = ""


@dataclass
class Hit:
    """A `find` result: the document and, for a text search, the pages where every word occurs."""

    doc: DocRecord
    pages: list[int] = field(default_factory=list)


class DocStore:
    """Read and write the shared document store. `root` defaults to `$LOTLINE_DATA_DIR`."""

    def __init__(self, root: Path | None = None):
        from lotline.io.store import data_dir

        self.data_root = Path(root or data_dir()).expanduser().resolve()
        self.root = self.data_root / "rule_docs"

    # ---- files -------------------------------------------------------------------------------------------
    @property
    def index_path(self) -> Path:
        return self.root / "index.jsonl"

    @property
    def citations_path(self) -> Path:
        return self.root / "citations.jsonl"

    @property
    def blocks_path(self) -> Path:
        return self.root / "blocks.jsonl"

    @property
    def inbox(self) -> Path:
        return self.root / "inbox"

    def blob(self, doc_id: str, ext: str) -> Path:
        return self.root / "blobs" / doc_id[:2] / f"{doc_id}{ext}"

    def sidecar(self, doc_id: str) -> Path:
        return self.root / "blobs" / doc_id[:2] / f"{doc_id}.txt"

    @contextmanager
    def _locked(self, path: Path) -> Iterator:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield fh
            finally:
                fh.flush()
                fcntl.flock(fh, fcntl.LOCK_UN)

    def _append(self, path: Path, rows: Iterable[dict]) -> None:
        with self._locked(path) as fh:
            for r in rows:
                fh.write(json.dumps(r, sort_keys=True, default=str) + "\n")

    @staticmethod
    def _read(path: Path) -> list[dict]:
        if not path.exists():
            return []
        out = []
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # a line another process is still writing
        return out

    # ---- index -------------------------------------------------------------------------------------------
    def records(self, *, include_withdrawn: bool = False) -> dict[str, DocRecord]:
        """Fold every index event into one record per doc_id. Lists grow (union, first-seen order);
        scalars take the latest non-empty value; `withdrawn` sticks once set."""
        out: dict[str, DocRecord] = {}
        known = set(DocRecord.__dataclass_fields__)
        for ev in self._read(self.index_path):
            did = ev.get("doc_id")
            if not did:
                continue
            rec = out.setdefault(did, DocRecord(doc_id=did, first_seen=ev.get("at", "")))
            for k, v in ev.items():
                if k not in known or k in ("doc_id", "first_seen"):
                    continue
                if k in _LIST_FIELDS or k == "draft_markers":
                    cur = getattr(rec, k)
                    items = v if isinstance(v, list) else [v] if v else []
                    for item in items:
                        if k == "urls":
                            if not any(u["url"] == item["url"] for u in cur):
                                cur.append(item)
                        elif item not in cur:
                            cur.append(item)
                elif v not in (None, "", [], False) or k == "may_contain_outcomes" and v:
                    setattr(rec, k, v)
        if not include_withdrawn:
            out = {k: r for k, r in out.items() if not r.withdrawn}
        return out

    def get(self, doc_id: str) -> DocRecord | None:
        doc_id = self.resolve(doc_id)
        return self.records(include_withdrawn=True).get(doc_id)

    def resolve(self, prefix: str) -> str:
        """A full doc_id from a unique prefix of at least 8 characters (agents quote short ids)."""
        if re.fullmatch(r"[0-9a-f]{64}", prefix):
            return prefix
        if len(prefix) < 8:
            raise KeyError(f"doc id prefix {prefix!r} is too short (8+ characters)")
        hits = [d for d in self.records(include_withdrawn=True) if d.startswith(prefix)]
        if len(hits) != 1:
            raise KeyError(f"doc id prefix {prefix!r} matches {len(hits)} documents")
        return hits[0]

    def annotate(self, doc_id: str, **fields) -> None:
        """Add facts about a document (title, jurisdictions, dates, flags...) as a new index event."""
        bad = set(fields) - set(DocRecord.__dataclass_fields__)
        if bad:
            raise ValueError(f"unknown document fields: {sorted(bad)}")
        if "doc_type" in fields and fields["doc_type"] not in DOC_TYPES:
            raise ValueError(f"doc_type must be one of {DOC_TYPES}")
        for k in ("categories",):
            for c in fields.get(k) or []:
                if c not in CATEGORIES:
                    raise ValueError(f"category must be one of {CATEGORIES}, not {c!r}")
        self._append(
            self.index_path,
            [{"doc_id": self.resolve(doc_id), "event": "annotate", "at": utc_now(), **fields}],
        )

    def withdraw(self, doc_id: str, reason: str) -> list[Citation]:
        """Mark a document as not to be used (wrong town, unrelated ordinance...). Returns the citations
        that now rest on it, so their rows can be re-checked."""
        if not reason.strip():
            raise ValueError("a reason is required to withdraw a document")
        did = self.resolve(doc_id)
        self._append(
            self.index_path,
            [{"doc_id": did, "event": "withdraw", "at": utc_now(), "withdrawn": reason.strip()}],
        )
        return self.cited_by(did)

    # ---- adding documents --------------------------------------------------------------------------------
    def ingest(
        self,
        file: Path,
        *,
        url: str,
        retrieved: str | None = None,
        added_by: str,
        category: str | None = None,
        **facts,
    ) -> DocRecord:
        """Put a file that is already in `raw/` (a download or a registered manual file) into the store:
        link the blob, write the text sidecar, append an index event. Idempotent on the bytes: the same file
        from another URL only adds that URL. A new file from a URL already held is linked to the earlier
        document as `supersedes` (schedule and code-version history)."""
        from lotline.io.store import sha256_file

        file = Path(file)
        did = sha256_file(file)
        ext = file.suffix.lower() if file.suffix.lower() in _EXT_OK else ".html"
        blob = self.blob(did, ext)
        known = self.records(include_withdrawn=True)
        if not blob.exists():
            blob.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(file, blob)
            except OSError:
                shutil.copy2(file, blob)
        ev: dict = {
            "doc_id": did,
            "event": "seen",
            "at": utc_now(),
            "urls": [{"url": url, "retrieved": retrieved or date.today().isoformat()}],
        }
        if category:
            if category not in CATEGORIES:
                raise ValueError(f"category must be one of {CATEGORIES}")
            ev["categories"] = [category]
        if did not in known:
            ev.update(self._extract(did, blob))
            ev.update(
                path=str(blob.relative_to(self.root)), ext=ext, bytes=blob.stat().st_size, added_by=added_by
            )
            host = (urlparse(url).hostname or "").lower()
            ev.setdefault("publisher", host)
            prev = [r for r in known.values() if any(u["url"] == url for u in r.urls)]
            if prev and "supersedes" not in facts:
                ev["supersedes"] = max(prev, key=lambda r: r.first_seen).doc_id
        for k, v in facts.items():
            if v not in (None, "", []):
                ev[k] = v
        if "doc_type" in ev and ev["doc_type"] not in DOC_TYPES:
            raise ValueError(f"doc_type must be one of {DOC_TYPES}")
        self._append(self.index_path, [ev])
        return self.records(include_withdrawn=True)[did]

    def _extract(self, did: str, blob: Path) -> dict:
        """Write the text sidecar and return pages / text_status / draft markers for the index."""
        side = self.sidecar(did)
        out: dict = {}
        if blob.suffix == ".pdf":
            from lotline.rule_agents.common.pdftext import extract

            try:
                text, pages, chars = extract(blob)
            except Exception:  # noqa: BLE001 - an unreadable PDF is read off the page image by a person
                text, pages, chars = "", None, 0
            out["pages"] = pages
            out["text_status"] = (
                "text" if pages and chars / max(pages, 1) >= SCAN_CHARS_PER_PAGE else "scanned"
            )
        elif blob.suffix in (".htm", ".html", ".xml"):
            raw = blob.read_text(errors="replace")
            text = T.visible_text(raw, keep_lines=True) if T.looks_like_html(raw) else raw
            out["pages"], out["text_status"] = 1, "text" if text.strip() else "none"
            title = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
            if title:
                out["title"] = " ".join(T.visible_text(title.group(1)).split())[:200]
        elif blob.suffix in (".txt", ".csv", ".json"):
            text = blob.read_text(errors="replace")
            out["pages"], out["text_status"] = 1, "text"
        else:
            text, out["text_status"] = "", "none"
        side.write_text(text)
        out["draft_markers"] = T.draft_markers(text[:200000])
        return out

    def add(
        self,
        file: Path,
        *,
        url: str,
        added_by: str,
        retrieved: str | None = None,
        license: str = "public record (local government publication)",
        **facts,
    ) -> DocRecord:
        """A file a person saved by hand (the human slot): recorded in the manifest through
        `DataStore.register` (source `rule_docs_manual`), then ingested. `url` is the page it came from;
        `added_by` is `human:<initials>`."""
        from lotline.io.store import DataStore

        if not added_by.startswith("human:"):
            raise ValueError("added_by for a hand-saved file is 'human:<initials>'")
        vintage = retrieved or date.today().isoformat()
        entry = DataStore(self.data_root).register(
            Path(file), source="rule_docs_manual", url=url, license=license, vintage=vintage
        )
        return self.ingest(
            self.data_root / entry.path, url=url, retrieved=vintage, added_by=added_by, **facts
        )

    def pending_inbox(self) -> list[Path]:
        """Files in the drop folder not yet in the store (a person saved them; `docs add` takes them in)."""
        if not self.inbox.exists():
            return []
        from lotline.io.store import sha256_file

        known = self.records(include_withdrawn=True)
        return [p for p in sorted(self.inbox.iterdir()) if p.is_file() and sha256_file(p) not in known]

    # ---- reading -----------------------------------------------------------------------------------------
    def text(self, doc_id: str, page: int | None = None) -> str:
        t = self.sidecar(self.resolve(doc_id))
        if not t.exists():
            return ""
        txt = t.read_text(errors="replace")
        if page is None:
            return txt
        return next((p for n, p in T.pages(txt) if n == page), "")

    def path(self, doc_id: str) -> Path | None:
        r = self.get(doc_id)
        return self.root / r.path if r and r.path else None

    def by_url(self, url: str) -> DocRecord | None:
        """The newest current document served by `url`, if any."""
        hits = [r for r in self.records().values() if any(u["url"] == url for u in r.urls)]
        if not hits:
            return None
        return max(hits, key=lambda r: max(u["retrieved"] for u in r.urls if u["url"] == url))

    def find(
        self,
        *,
        geoid: str | None = None,
        county: str | None = None,
        state: str | None = None,
        category: str | None = None,
        doc_type: str | None = None,
        url: str | None = None,
        text: str | None = None,
        include_withdrawn: bool = False,
    ) -> list[Hit]:
        """Documents matching every filter given. `geoid` also matches documents tagged with the place's
        state (its first two digits: state law covers every place) and, when given, its `county` GEOID (a
        county code covers its towns; a place GEOID does not contain its county, so the caller passes it).
        `text` matches pages holding every word (case-insensitive, after `norm`). Newest first."""
        words = T.norm(text).split() if text else []
        out = []
        for r in self.records(include_withdrawn=include_withdrawn).values():
            if geoid and not ({geoid, geoid[:2], county} & set(r.jurisdictions)):
                continue
            if (
                state
                and state.upper() not in r.states
                and not any(j[:2] == _fips(state) for j in r.jurisdictions)
            ):
                continue
            if category and category not in r.categories:
                continue
            if doc_type and r.doc_type != doc_type:
                continue
            if url and not any(u["url"] == url for u in r.urls):
                continue
            pages: list[int] = []
            if words:
                for n, pt in T.pages(self.text(r.doc_id)):
                    hay = T.norm(pt)
                    if all(w in hay for w in words):
                        pages.append(n)
                if not pages:
                    continue
            out.append(Hit(r, pages))
        return sorted(out, key=lambda h: h.doc.first_seen, reverse=True)

    def quote(self, doc_id: str, quote: str) -> tuple[str, int | None]:
        """Check a quote against the stored text: ("verbatim", page) when found; ("image_read", None) for a
        scanned document (a person or the coder read it off the page image); ("not_found", None) else."""
        r = self.get(doc_id)
        if r is None:
            raise KeyError(doc_id)
        if r.text_status in ("scanned", "none"):
            return "image_read", None
        pg = T.quote_page(quote, self.text(r.doc_id))
        return ("verbatim", pg) if pg is not None else ("not_found", None)

    def history(self, doc_id: str) -> list[DocRecord]:
        """The supersession chain through `doc_id`, oldest first (a fee schedule's versions, a code's
        editions)."""
        recs = self.records(include_withdrawn=True)
        did = self.resolve(doc_id)
        back = []
        cur = recs.get(did)
        seen = set()
        while cur and cur.doc_id not in seen:
            seen.add(cur.doc_id)
            back.append(cur)
            cur = recs.get(cur.supersedes) if cur.supersedes else None
        newer = {r.supersedes: r for r in recs.values() if r.supersedes}
        fwd = []
        cur = newer.get(did)
        while cur and cur.doc_id not in seen:
            seen.add(cur.doc_id)
            fwd.append(cur)
            cur = newer.get(cur.doc_id)
        return list(reversed(back)) + fwd

    # ---- citations ---------------------------------------------------------------------------------------
    def cite(self, citations: Iterable[Citation]) -> int:
        rows = []
        for c in citations:
            if c.category not in CATEGORIES:
                raise ValueError(f"category must be one of {CATEGORIES}")
            c.doc_id = self.resolve(c.doc_id)
            c.at = c.at or utc_now()
            rows.append(asdict(c))
        self._append(self.citations_path, rows)
        return len(rows)

    def cited_by(self, doc_id: str) -> list[Citation]:
        did = self.resolve(doc_id)
        return [Citation(**c) for c in self._read(self.citations_path) if c.get("doc_id") == did]

    # ---- blocks ------------------------------------------------------------------------------------------
    def record_block(self, url: str, kind: str, detail: str = "", category: str = "") -> None:
        host = (urlparse(url).hostname or "").lower()
        self._append(
            self.blocks_path,
            [
                {
                    "url": url,
                    "host": host,
                    "kind": kind,
                    "detail": detail,
                    "category": category,
                    "at": utc_now(),
                }
            ],
        )

    def recent_block(self, url: str, *, days: int = 30) -> dict | None:
        """A refusal from this URL's host within `days` (any swarm). Hosts that refuse scripts (403/WAF,
        code-host walls, robots, logins) are not asked again: one refusal closes the host for a month, so a
        second swarm spends no fetch, no robots read and no tokens on it (LESSONS R-5, Medford/Charlotte)."""
        host = (urlparse(url).hostname or "").lower()
        cutoff = datetime.now(UTC) - timedelta(days=days)
        host_kinds = {"http_403_waf", "code_host_wall", "login_required", "robots_unavailable"}
        for b in reversed(self._read(self.blocks_path)):
            if datetime.fromisoformat(b["at"]) < cutoff:
                continue
            if b["url"] == url or (b["host"] == host and b["kind"] in host_kinds):
                return b
        return None

    # ---- catalogue ---------------------------------------------------------------------------------------
    def catalog_rows(self) -> list[dict]:
        """A data-free catalogue (one row per current document: id, first URL, title, type, places,
        categories, first retrieved). Committed so a judge can re-fetch each document and check it by hash
        without the repo holding any document."""
        rows = []
        for r in sorted(self.records().values(), key=lambda r: (r.states, r.first_url)):
            rows.append(
                {
                    "doc_id": r.doc_id,
                    "url": r.first_url,
                    "retrieved": r.urls[0]["retrieved"] if r.urls else "",
                    "title": r.title,
                    "doc_type": r.doc_type,
                    "jurisdictions": ";".join(r.jurisdictions),
                    "categories": ";".join(r.categories),
                    "text_status": r.text_status,
                    "added_by": r.added_by.split(":")[0] if r.added_by else "",
                    "supersedes": r.supersedes,
                }
            )
        return rows


_STATE_FIPS = {
    "AL": "01",
    "AK": "02",
    "AZ": "04",
    "AR": "05",
    "CA": "06",
    "CO": "08",
    "CT": "09",
    "DE": "10",
    "DC": "11",
    "FL": "12",
    "GA": "13",
    "HI": "15",
    "ID": "16",
    "IL": "17",
    "IN": "18",
    "IA": "19",
    "KS": "20",
    "KY": "21",
    "LA": "22",
    "ME": "23",
    "MD": "24",
    "MA": "25",
    "MI": "26",
    "MN": "27",
    "MS": "28",
    "MO": "29",
    "MT": "30",
    "NE": "31",
    "NV": "32",
    "NH": "33",
    "NJ": "34",
    "NM": "35",
    "NY": "36",
    "NC": "37",
    "ND": "38",
    "OH": "39",
    "OK": "40",
    "OR": "41",
    "PA": "42",
    "RI": "44",
    "SC": "45",
    "SD": "46",
    "TN": "47",
    "TX": "48",
    "UT": "49",
    "VT": "50",
    "VA": "51",
    "WA": "53",
    "WV": "54",
    "WI": "55",
    "WY": "56",
}


def _fips(state: str) -> str:
    return _STATE_FIPS.get(state.upper(), "")
