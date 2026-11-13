"""verify.py - the safety check at the centre of Before the Vote.

The AI writes each plain-language sentence together with the exact words from the
City document that support it (a "quote"). This file checks, with ordinary string
matching and no AI, that those words really appear in the document.

Why: the challenge brief says a summary that mis-states a decision is worse than
no summary, and that every summary must link to the exact source passage.
A language model can invent a quote. It cannot make an invented quote pass this check.
"""

import re
import unicodedata

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]

# Quotes shorter than this are too easy to match by accident ("the City").
MIN_QUOTE_WORDS = 5


def normalize(text: str) -> str:
    """Make two copies of the same passage compare equal despite PDF quirks.

    PDFs break lines mid-sentence, split words with hyphens, and use curly quotes.
    We lower-case, straighten quotes and dashes, re-join hyphenated line breaks and
    squeeze all whitespace to single spaces.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"-\s*\n\s*", "", text)   # "develop-\nment" -> "development"
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def find_quote(quote: str, pages: list[str]) -> int | None:
    """Return the 1-based page number where the quote appears, or None.

    `pages` is the document text, one string per page.
    """
    if not quote or len(quote.split()) < MIN_QUOTE_WORDS:
        return None
    needle = normalize(quote)
    for number, page_text in enumerate(pages, start=1):
        if needle in normalize(page_text):
            return number
    return None


def verify_claim(claim: dict, documents: dict[str, list[str]]) -> dict:
    """Mark each source of a claim as verified or not, and fix the page number.

    `documents` maps a document id (like "d1") to its list of page texts.
    The claim is changed in place and also returned.
    """
    for source in claim.get("sources", []):
        pages = documents.get(source.get("doc"), [])
        page = find_quote(source.get("quote"), pages)
        source["verified"] = page is not None
        if page is not None:
            source["page"] = page
    return claim


def deadline_supported(deadline_iso: str, quote: str) -> bool:
    """Is this deadline actually written in the quoted passage?

    The brief says: do not infer a submission deadline from a meeting date.
    So a deadline is only accepted if its day, month name and year all appear
    in the quote, e.g. 2026-06-10 needs "10", "june" and "2026".
    """
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", deadline_iso or "")
    if not match or not quote:
        return False
    year, month, day = match.groups()
    text = normalize(quote)
    has_day = re.search(rf"\b{int(day)}\b", text) is not None
    has_month = MONTHS[int(month) - 1] in text
    has_year = year in text
    return has_day and has_month and has_year


def supported_moment(moment: str, quote: str) -> str | None:
    """Return the part of a date/time that the quoted words really support.

    '2026-11-16T09:30:00-05:00' with a quote that only says 'November 16, 2026'
    comes back as '2026-11-16': the day is in the record, the 9:30 is not.
    If even the day is not in the quote, the answer is None.
    """
    if not deadline_supported(moment, quote):
        return None
    has_clock_time = re.search(r"\b\d{1,2}:\d{2}\b", quote or "") is not None
    return moment if (len(moment) == 10 or has_clock_time) else moment[:10]
