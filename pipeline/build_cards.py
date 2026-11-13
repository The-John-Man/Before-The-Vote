"""build_cards.py - check every item file and publish the cards the website reads.

Run from the pipeline folder:   python build_cards.py

An item file (pipeline/items/<id>.json) is a DRAFT. It may be written by a person,
by an AI model (see btv/summarize.py), or both. This script does not trust it.
For every item it:

  1. loads the text of each source document           (btv/sources.py)
  2. checks every quote word for word                 (btv/verify.py, no AI)
  3. removes anything that depends on a failed check:
       - a deadline or meeting date that is not written in a verified quote
         (a time of day is dropped too unless the record states one)
       - a stage result ("refused", "adopted") whose sentence failed
       - a vote whose sentence failed
  4. writes web/data/decisions.json and web/data/calendar.ics

Sentences that fail stay in the file marked verified=false. The public pages hide
them; the "How we check" page lists them so staff can fix or delete them.
"""

import json
from datetime import datetime
from pathlib import Path

from btv.calendar import build_feed
from btv.sources import load_pages
from btv.verify import deadline_supported, supported_moment, verify_claim

HERE = Path(__file__).resolve().parent
WEB_DATA = HERE.parent / "web" / "data"


def is_verified(claim: dict) -> bool:
    return bool(claim["sources"]) and all(source["verified"] for source in claim["sources"])


def build_card(item: dict, city: dict) -> dict:
    # 1. text of every document this item may quote (its own plus city-wide guidance)
    documents = item["documents"] + city["documents"]
    pages = {doc["id"]: load_pages(doc) for doc in documents}

    # 2. check each sentence
    for claim in item["claims"]:
        for source in claim["sources"]:
            source.setdefault("page", None)
        verify_claim(claim, pages)
        claim["verified"] = is_verified(claim)
    good = {claim["id"]: claim for claim in item["claims"] if claim["verified"]}

    # 3a. deadline guard
    say = item["say"]
    deadline_claim = good.get(say.get("deadline_claim"))
    quote = " ".join(s["quote"] for s in deadline_claim["sources"]) if deadline_claim else ""
    if not (say.get("deadline") and deadline_supported(say["deadline"], quote)):
        say["deadline"], say["deadline_claim"] = None, None
    # The meeting date needs the same proof. A time of day is kept only if the record states one.
    meeting_claim = good.get(say.get("meeting_claim"))
    quote = " ".join(s["quote"] for s in meeting_claim["sources"]) if meeting_claim else ""
    say["meeting"] = supported_moment(say["meeting"], quote) if say.get("meeting") else None
    if not say["meeting"]:
        say["meeting_claim"] = None
    if say.get("guidance_claim") not in good:
        say["guidance_claim"] = None

    # 3b. stage results and 3c. votes must rest on a verified sentence
    for stage in item["stages"]:
        if stage.get("result") and stage.get("result_claim") not in good:
            stage["result"], stage["result_claim"] = None, None
    item["votes"] = [vote for vote in item.get("votes", []) if vote.get("claim") in good]

    item["documents"] = documents
    return item


def main():
    city = json.loads((HERE / "city.json").read_text(encoding="utf-8"))
    now = datetime.now().astimezone()
    cards = []
    for path in sorted((HERE / "items").glob("*.json")):
        cards.append(build_card(json.loads(path.read_text(encoding="utf-8")), city))

    result = {
        "generated_at": now.isoformat(timespec="seconds"),
        "municipality": city["municipality"],
        "lenses": city["lenses"],
        "decisions": cards,
    }
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    (WEB_DATA / "decisions.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (WEB_DATA / "calendar.ics").write_text(build_feed(cards, now), encoding="utf-8", newline="")

    # Report, so the person running this sees exactly what was held back.
    for card in cards:
        claims = card["claims"]
        failed = [c for c in claims if not c["verified"]]
        print(f"{card['id']}: {len(claims) - len(failed)} of {len(claims)} sentences passed the quote check")
        for claim in failed:
            tag = " (planted test sentence)" if claim.get("planted") else ""
            print(f"   HELD BACK {claim['id']}{tag}: {claim['text']}")
    print(f"Wrote {len(cards)} cards to {WEB_DATA / 'decisions.json'}")


if __name__ == "__main__":
    main()
