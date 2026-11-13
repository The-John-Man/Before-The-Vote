"""sources.py - turn a source document into text we can check quotes against.

A document in an item file is one of two kinds:
  "snapshot": a text file in pipeline/snapshots/ holding the words of an official
              web page, copied on the date in "retrieved". Lines starting with #
              are our own notes and are removed before checking.
  "url" ending in .pdf: downloaded once into pipeline/cache/ and read page by page.

Either way the result is a list of strings, one per page (a snapshot is one page).
"""

import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "cache"


def snapshot_pages(relative_path: str) -> list[str]:
    lines = (HERE / relative_path).read_text(encoding="utf-8").splitlines()
    kept = [line for line in lines if not line.startswith("#")]
    return ["\n".join(kept)]


def pdf_pages(url: str) -> list[str]:
    """Download a PDF (once) and return the text of each page.
    NOT YET RUN on a real PDF. Scanned PDFs with no text give empty strings."""
    import requests                      # imported here so snapshots work without it
    from pypdf import PdfReader

    CACHE.mkdir(exist_ok=True)
    path = CACHE / (hashlib.sha256(url.encode()).hexdigest()[:16] + ".pdf")
    if not path.exists():
        response = requests.get(url, timeout=60, headers={"User-Agent": "BeforeTheVote-hackathon/0.2"})
        response.raise_for_status()
        path.write_bytes(response.content)
    return [(page.extract_text() or "") for page in PdfReader(str(path)).pages]


def load_pages(document: dict) -> list[str]:
    if document.get("snapshot"):
        return snapshot_pages(document["snapshot"])
    if document.get("url", "").lower().endswith(".pdf"):
        return pdf_pages(document["url"])
    return []  # nothing to check against: every quote from this document will fail
