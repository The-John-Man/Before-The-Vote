"""notices.py - turn City public notices into cards, with fixed rules (no AI).

Which notices become cards (the "selection rule"):
  - dated in the last 45 days, AND
  - the title starts with "Notice of Public Meeting", "Notice of Application",
    "Notice of a request" or "Notice of Intention", OR a topic starts with "Meetings".
  - at most 40, newest first.

Each card is items/notice-<noticeId>.json, with the notice's words saved as
snapshots/notice-<noticeId>.txt so every quote can be checked.

A notice is added to an existing item instead of getting its own card only when they
share a planning application number. If two items share it, we cannot tell which is
right, so the notice gets its own card (when unsure, do not merge).

A notice card is deleted 120 days after its notice date, unless a person has written
sentences for it.
"""

import copy
from datetime import date

from btv.extract import proposal_excerpt
from btv.geo import ward_at

PREFIXES = ("notice of public meeting", "notice of application", "notice of a request", "notice of intention")
RECENT_DAYS = 45
MAX_CARDS = 40
FORGET_DAYS = 120
NOTICES_PAGE = "https://open.toronto.ca/dataset/public-notices/"
NOT_LINKED = ("This notice is not linked to a Council agenda item number, so later decisions "
              "and votes are not added to this page automatically.")
NO_PLACE = ("The address in the City's data is outside the area of the community council named "
            "in the notice, so this card shows no map pin or ward.")

# The wards each community council covers (2022-2026 term). Used to catch an address the
# City's data placed in the wrong part of the city (e.g. "Kennedy Avenue" for "Kennedy Road").
COMMUNITY_COUNCIL_WARDS = {
    "Etobicoke York Community Council": {"01", "02", "03", "05", "07"},
    "North York Community Council": {"06", "08", "15", "16", "17", "18"},
    "Toronto and East York Community Council": {"04", "09", "10", "11", "12", "13", "14", "19"},
    "Scarborough Community Council": {"20", "21", "22", "23", "24", "25"},
}


def card_id(notice: dict) -> str:
    return f"notice-{notice['id']}"


def is_selected(notice: dict, today: date) -> bool:
    if (today - date.fromisoformat(notice["date"])).days > RECENT_DAYS:
        return False
    return (notice["title"].lower().startswith(PREFIXES)
            or any(topic.startswith("Meetings") for topic in notice["topics"]))


def select(notices: list[dict], today: date) -> list[dict]:
    chosen = [n for n in notices if is_selected(n, today)]
    chosen.sort(key=lambda n: (n["date"], int(n["id"])), reverse=True)
    return chosen[:MAX_CARDS]


def snapshot_text(notice: dict, today: str) -> str:
    """The notice's words. Lines starting with # are our notes; the checker skips them."""
    return (f"# Text of City of Toronto public notice {notice['id']}, copied {today} from the\n"
            f"# City's Open Data portal (dataset public-notices, {NOTICES_PAGE})\n"
            f"# Title: {notice['title']}\n\n{notice['text']}\n")


def notice_document(notice: dict, doc_id: str, snapshot: str, today: str) -> dict:
    url = notice["documents"][0]["url"] if notice["documents"] else NOTICES_PAGE
    return {"id": doc_id, "type": "notice", "notice_id": notice["id"], "title": notice["title"],
            "url": url, "snapshot": snapshot, "retrieved": today}


def notice_card(notice: dict, wards: list[dict], today: str) -> dict:
    """Everything about a notice that rules can fill in. Pure: no files, no network."""
    first = notice["addresses"][0] if notice["addresses"] else None
    place = {**first, "approx": False} if first else None
    ward = ward_at(place["lon"], place["lat"], wards) if place else None
    unknowns = [NOT_LINKED]
    area = COMMUNITY_COUNCIL_WARDS.get(notice["body"])
    if place and area and (ward is None or ward["code"] not in area):
        place, ward = None, None
        unknowns.append(NO_PLACE)
    doc = notice_document(notice, "n1", f"snapshots/{card_id(notice)}.txt", today)
    return {
        "id": card_id(notice),
        "source": "opendata",
        "notice_id": notice["id"],
        "notice_date": notice["date"],
        "title_plain": "",
        "title_official": notice["title"],
        "topic": notice["topics"][0].split(" > ")[0] if notice["topics"] else "",
        "ward": ward,
        "place": place,
        "official_url": doc["url"],
        "drafted_by": "Rules, no AI: read from the City's public notice (Open Data)",
        "application_numbers": notice["application_numbers"],
        "documents": [doc],
        "stages": [{"key": "notice", "body": "staff", "label": "City notice", "date": notice["date"],
                    "result": None, "result_claim": None, "can_speak": False}],
        "say": {"deadline": None, "deadline_claim": None, "meeting": None, "meeting_claim": None,
                "guidance_claim": None, "contact_email": None, "methods": []},
        "claims": [],
        "votes": [],
        "heard": [],
        "heard_note": "",
        "unknowns": unknowns,
        "notice_excerpt": proposal_excerpt(notice["text"]),
    }


def matching_item(notice: dict, items: list[dict]) -> str | None:
    """The one existing item that shares a planning application number with the notice."""
    numbers = set(notice["application_numbers"])
    if not numbers:
        return None
    hits = [item["id"] for item in items if numbers & set(item.get("application_numbers") or [])]
    return hits[0] if len(hits) == 1 else None


def is_handwritten(claim: dict) -> bool:
    return claim.get("drafted_by") != "rule"


def can_forget(item: dict, today: date) -> bool:
    """An old notice card that nobody has written sentences for."""
    if not item["id"].startswith("notice-") or not item.get("notice_date"):
        return False
    old = (today - date.fromisoformat(item["notice_date"])).days > FORGET_DAYS
    return old and not any(is_handwritten(c) for c in item["claims"])


RULE_OWNED = ("title_official", "topic", "ward", "place", "official_url", "application_numbers",
              "notice_date", "notice_excerpt", "stages")


def update_card(old: dict, fresh: dict) -> tuple[dict, list[str]]:
    """Bring a notice card in line with a fresh reading of its notice. Sentences written by
    people and any extra documents are kept; facts read by rules are replaced."""
    item = copy.deepcopy(old)
    notes = []
    for key in RULE_OWNED:
        item[key] = copy.deepcopy(fresh[key])
    if fresh["title_official"] != old.get("title_official"):
        notes.append("The City changed the notice's title.")
    # The notice document keeps its copy date; refresh.py changes it when the words change.
    fresh_doc = dict(fresh["documents"][0], retrieved=next(
        (d["retrieved"] for d in old["documents"] if d["id"] == "n1"), fresh["documents"][0]["retrieved"]))
    item["documents"] = [fresh_doc] + [d for d in old["documents"] if d["id"] != "n1"]
    item["claims"] = [c for c in old["claims"] if is_handwritten(c)] + copy.deepcopy(fresh["claims"])
    say_by_rules = old["say"].get("deadline_claim") in (None, *[c["id"] for c in old["claims"] if not is_handwritten(c)])
    if say_by_rules:
        for key in ("deadline", "deadline_claim", "meeting", "meeting_claim"):
            item["say"][key] = fresh["say"][key]
        if fresh["say"]["deadline"] != old["say"].get("deadline") and fresh["say"]["deadline"]:
            notes.append("The deadline in the City's notice changed.")
        if fresh["say"]["meeting"] != old["say"].get("meeting") and fresh["say"]["meeting"]:
            notes.append("The meeting date in the City's notice changed.")
    return item, notes


def attach_notice(item: dict, notice: dict, today: str) -> tuple[dict, list[str]]:
    """Add a notice to an existing item that shares its application number: a link to the
    notice and its saved words. Nothing else on the item is changed."""
    if any(d.get("notice_id") == notice["id"] for d in item["documents"]):
        return item, []
    item = copy.deepcopy(item)
    n = 1
    while any(d["id"] == f"n{n}" for d in item["documents"]):
        n += 1
    snapshot = f"snapshots/{card_id(notice)}.txt"
    item["documents"].append(notice_document(notice, f"n{n}", snapshot, today))
    return item, [f"The City posted a public notice for this application: {notice['title']}."]
