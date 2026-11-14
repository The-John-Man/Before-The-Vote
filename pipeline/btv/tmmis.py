"""tmmis.py - read one agenda item page from the City of Toronto's meeting system (TMMIS).

An item page (https://secure.toronto.ca/council/agenda-item.do?item=2024.NY15.4) is plain
HTML. It holds one block per "consideration": one for the committee or community council
and, later, one for City Council. Each block has a title, a status, a ward, and headed
sections such as "Committee Recommendations", "City Council Decision", "Summary" and "Motions".

parse_item() turns that page into a dictionary we call a record.

Privacy by design: the page lists the names of residents who wrote in or spoke.
This parser only COUNTS them. The names are never stored.

Status: tested on a hand-made sample that copies the page's structure (tests/sample_item.html).
Not yet run against the live site from this code. Run build_cards.py --refresh to do that.
"""

import re
from datetime import date
from html.parser import HTMLParser

import requests

ITEM_URL = "https://secure.toronto.ca/council/agenda-item.do?item={id}"

# Tags that start a new line of text.
BLOCK_TAGS = {"p", "div", "br", "li", "h2", "h3", "h4", "dl", "tr"}
# Small pieces we capture whole, and the tag that ends each one.
CAPTURE_END = {"heading": "button", "title": "h3", "dt": "dt", "dd": "dd", "h4": "h4", "h2": "h2"}


def _tidy(text: str) -> str:
    """Collapse spaces, trim each line, drop empty lines."""
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


class _ItemParser(HTMLParser):
    """Walks the HTML once and fills self.record."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.record = {"tracking": "", "considerations": []}
        self.capture = None      # name of the small piece being read, or None
        self.buffer = []         # text of that piece so far
        self.current = None      # the consideration being filled
        self.section = None      # current section heading inside it
        self.in_tracking = False
        self.link = None         # href of the <a> we are inside, in a Background section
        self.doc_title = []      # text seen since the last document link
        self.meta_key = None
        self.accordion_depth = 0  # how many <div>s deep we are inside the accordion
        self.in_script = 0        # inside <script> or <style>, whose text is code, not words

    # -- helpers -------------------------------------------------------------
    def _in(self, prefix: str) -> bool:
        return bool(self.section) and self.section.startswith(prefix)

    def _add_text(self, text: str):
        if self.current is not None and self.section and not self._in("Communications") \
                and not self._in("Background Information"):
            self.current["sections"][self.section] += text

    # -- HTMLParser hooks ----------------------------------------------------
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.in_script += 1
            return
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        # Track the accordion that holds the considerations, so we know when it ends.
        # Without this, the page footer (Jobs, Contact us, social media...) was read as
        # part of the last section and its links as background documents.
        if tag == "div" and (self.accordion_depth or "accordion" in classes):
            self.accordion_depth += 1
        if "accordin-heading" in classes:
            self.capture, self.buffer = "heading", []
        elif "accordion" in classes or "accordion__controls" in classes:
            self.in_tracking = False
        elif tag == "h2" and "section-title" in classes:
            self.capture, self.buffer = "h2", []
        elif self.current is not None and tag == "h3" and "heading" in classes:
            self.capture, self.buffer = "title", []
        elif self.current is not None and tag in ("dt", "dd", "h4"):
            self.capture, self.buffer = tag, []
        elif tag == "a" and self._in("Background Information") and "/legdocs/" in (attrs.get("href") or ""):
            self.link = attrs.get("href")   # only the City's agenda documents, never site links
        elif tag == "span" and "rpt-text" in classes and self._in("Communications"):
            self.current["counts"][self.section] = self.current["counts"].get(self.section, 0) + 1
        if tag in BLOCK_TAGS:
            self._add_text("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.in_script = max(0, self.in_script - 1)
            return
        if tag == "div" and self.accordion_depth:
            self.accordion_depth -= 1
            if self.accordion_depth == 0:
                # The accordion is closed. Stop adding text to the last consideration.
                # We keep reading, so if the City's HTML closed it early by mistake, a
                # later consideration heading still starts a new block.
                self.current, self.section = None, None
                return
        if self.capture and CAPTURE_END[self.capture] == tag:
            text = _tidy(" ".join(self.buffer)).replace("\n", " ")
            kind, self.capture = self.capture, None
            if kind == "heading":            # "City Council consideration on July 24 and 25, 2024"
                body, _, when = text.partition(" consideration on ")
                self.current = {"body": body, "date_text": when, "title": "", "meta": {},
                                "sections": {}, "documents": [], "counts": {}}
                self.record["considerations"].append(self.current)
                self.section = None
            elif kind == "h2":
                self.in_tracking = (text == "Tracking Status")
            elif kind == "title":
                self.current["title"] = text
            elif kind == "dt":
                self.meta_key = text.rstrip(":")
            elif kind == "dd":
                self.current["meta"][self.meta_key] = text
            elif kind == "h4":
                self.section = text
                self.current["sections"].setdefault(text, "")
                self.doc_title = []
        elif tag == "a" and self.link:
            self.current["documents"].append({"title": _tidy(" ".join(self.doc_title)).replace("\n", " "),
                                              "url": self.link})
            self.link, self.doc_title = None, []

    def handle_data(self, data):
        if self.in_script:
            return
        data = re.sub(r"\s+", " ", data)
        if self.capture:
            self.buffer.append(data)
        elif self.in_tracking and self.current is None:
            self.record["tracking"] += data
        elif self._in("Background Information"):
            if self.link is None:            # the text of the link itself is just the URL again
                self.doc_title.append(data)
        else:
            self._add_text(data)


def parse_item(html: str, item_id: str) -> dict:
    """Turn the HTML of an item page into a record (see module docstring)."""
    parser = _ItemParser()
    parser.feed(html)
    record = parser.record
    record["id"] = item_id
    record["url"] = ITEM_URL.format(id=item_id)
    record["tracking"] = _tidy(record["tracking"].replace(". ", ".\n"))
    for consideration in record["considerations"]:
        sections = {name: _tidy(text) for name, text in consideration["sections"].items()}
        # Speakers are residents: keep how many, never who.
        for name in [n for n in sections if n.startswith("Speakers")]:
            text = sections.pop(name)
            consideration["counts"][name] = len(text.split("\n")) if text else 0
        for name in [n for n in sections if n.startswith("Communications")]:
            sections.pop(name)
        consideration["sections"] = sections
    return record


def fetch_item(item_id: str) -> dict:
    """Download the live page and parse it. Adds the retrieval date."""
    response = requests.get(ITEM_URL.format(id=item_id), timeout=60,
                            headers={"User-Agent": "BeforeTheVote-hackathon/0.2"})
    response.raise_for_status()
    record = parse_item(response.text, item_id)
    record["retrieved"] = date.today().isoformat()
    record["captured_by"] = "pipeline, full page"
    return record
