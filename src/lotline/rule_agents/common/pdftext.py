"""PDF text layer: page-marked text for quote checks, and the scan test.

Uses pypdf (BSD-3-Clause, added 2026-11-17 on Ben's OK). The text layer is good for finding a quote and for
draft markers; it is **not** trusted for use-table columns (LESSONS P-1): coders still read tables from the
page image and cite "Table X, row Y, column Z".
"""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract(path: Path) -> tuple[str, int, int]:
    """(text with `=== page N ===` markers, pages, characters of text). A page that fails to extract counts
    as empty, so a broken or scanned PDF shows up as few characters per page
    (`access.classify` -> scanned_pdf)."""
    reader = PdfReader(str(path))
    parts, chars = [], 0
    for i, page in enumerate(reader.pages, start=1):
        try:
            t = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - one bad page must not hide the rest
            t = ""
        chars += len(t.strip())
        parts.append(f"=== page {i} ===\n{t}")
    return "\n".join(parts), len(reader.pages), chars


def write_sidecar(pdf: Path, dest: Path) -> tuple[int, int]:
    """Write `extract(pdf)` text to `dest`; return (pages, characters)."""
    text, pages, chars = extract(pdf)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    return pages, chars
