"""timeline.py - work out the facts that need no AI at all.

From a record (see tmmis.py) this builds, with plain rules:
  - the stops on the Decision Line (staff report, committee, City Council)
  - how decided the item is (proposed / committee / decided)
  - the wards, the list of documents, and the text used to check quotes

Because this is ordinary code, the same page always gives the same answer.
"""

import re

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]

# What the City's status word means in plain language, per kind of stop.
OUTCOME_WORDS = {
    ("committee", "Adopted"): "Agreed with staff. No changes.",
    ("committee", "Amended"): "Changed the recommendations, then agreed to them.",
    ("council", "Adopted"): "Agreed with the committee. No changes.",
    ("council", "Amended"): "Made changes, then agreed.",
}


def first_date(text: str) -> str | None:
    """'July 24 and 25, 2024' -> '2024-07-24'.  '(May 28, 2026) Report...' -> '2026-05-28'."""
    match = re.search(r"([A-Z][a-z]+) (\d{1,2})(?:[^,]*)?, (\d{4})", text or "")
    if not match or match.group(1).lower() not in MONTHS:
        return None
    month = MONTHS.index(match.group(1).lower()) + 1
    return f"{match.group(3)}-{month:02d}-{int(match.group(2)):02d}"


def _count(consideration: dict, prefix: str, must_contain: str = "") -> int:
    return sum(n for name, n in consideration["counts"].items()
               if name.startswith(prefix) and must_contain in name)


def build_stages(record: dict) -> list[dict]:
    """Oldest stop first. The page lists City Council first, so we reverse it."""
    stages = []
    considerations = list(reversed(record["considerations"]))
    for consideration in considerations:
        is_council = consideration["body"] == "City Council"
        key = "council" if is_council else "committee"
        if not is_council and not stages:
            origin = consideration["sections"].get("Origin", "")
            if origin:      # "(June 20, 2024) Report from the Director, Community Planning"
                stages.append({
                    "key": "staff", "label": "City staff report", "date": first_date(origin),
                    "date_text": origin, "outcome": "Recommended", "can_speak": False,
                    "outcome_plain": "Staff wrote a report with recommendations.",
                    "letters": 0, "speakers": 0,
                })
        status = consideration["meta"].get("Status", "")
        stages.append({
            "key": key, "label": consideration["body"],
            "date": first_date(consideration["date_text"]), "date_text": consideration["date_text"],
            "outcome": status,
            "outcome_plain": OUTCOME_WORDS.get((key, status), f"Status on the City's page: {status}." if status
                                               else "Has not met yet."),
            # In Toronto the public speaks at committees and community councils, not at City Council.
            "can_speak": not is_council,
            "letters": _count(consideration, "Communications", "City Council" if is_council else ""),
            "speakers": _count(consideration, "Speakers"),
            "statutory_meeting": any(n.startswith("Statutory") for n in consideration["sections"]),
        })
    return stages


def authority(record: dict) -> str:
    """proposed -> committee -> decided. Decided only if City Council's decision text exists."""
    for consideration in record["considerations"]:
        if consideration["body"] == "City Council" and consideration["sections"].get("City Council Decision"):
            return "decided"
    # "Committee Recommendations" / "Community Council Recommendations" mean a committee has acted.
    # A bare "Recommendations" heading is only the staff advice, so it does not count.
    if any(name.endswith(" Recommendations") and text
           for c in record["considerations"] for name, text in c["sections"].items()):
        return "committee"
    return "proposed"


def wards(record: dict) -> list[dict]:
    """[] means city-wide ('All'). Otherwise [{'code': '06', 'name': 'York Centre'}]."""
    meta = record["considerations"][0]["meta"] if record["considerations"] else {}
    text = meta.get("Ward") or meta.get("Wards") or "All"
    found = re.findall(r"(\d{1,2}) - ([^,]+)", text)
    return [{"code": f"{int(code):02d}", "name": name.strip()} for code, name in found]


def documents(record: dict) -> list[dict]:
    """Every background document once, with ids b1, b2... The item page itself is 'item'."""
    seen, result = set(), []
    for consideration in reversed(record["considerations"]):
        for doc in consideration["documents"]:
            if doc["url"] not in seen:
                seen.add(doc["url"])
                result.append({"id": f"b{len(result) + 1}", "title": doc["title"] or "Background document",
                               "url": doc["url"], "date": first_date(doc["title"]),
                               "retrieved": record.get("retrieved")})
    return result


def source_pages(record: dict) -> tuple[list[str], list[str]]:
    """The text quotes are checked against, plus a label for each 'page'.

    Page 1 is the status summary. Then one page per consideration, in page order.
    """
    pages, labels = [record["tracking"]], ["Status summary"]
    for consideration in record["considerations"]:
        parts = [consideration["title"]]
        for name, text in consideration["sections"].items():
            parts.append(name)
            parts.append(text)
        pages.append("\n".join(parts))
        labels.append(f"{consideration['body']}, {consideration['date_text']}")
    return pages, labels
