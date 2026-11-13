"""new_item.py - start a new decision from its City of Toronto item number.

Run from the pipeline folder:   python new_item.py 2027.PB1.6

It downloads the official item page and writes two files:
  snapshots/<id>.txt   the words of the page, dated, with residents' names left out
  items/<id>.json      a starter item file: title, ward, stops on the line, documents,
                       and how many people wrote in or spoke. All of this comes from
                       plain rules (btv/timeline.py), not from AI.

What is left for a person or a model to add: the plain-language sentences ("claims"),
each with the exact words that support it. Then run build_cards.py to check them.

Status: the reading and file-building steps are tested on a sample page
(tests/test_tmmis.py). The download itself has NOT been run yet from this script.
For testing without internet:   python new_item.py 2024.NY15.4 --html tests/sample_item.html
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

from btv.timeline import build_stages, documents, source_pages, wards
from btv.tmmis import ITEM_URL, fetch_item, parse_item

HERE = Path(__file__).resolve().parent


def snapshot_text(record: dict) -> str:
    """The page as plain text. Lines starting with # are our notes; the checker skips them."""
    pages, labels = source_pages(record)
    lines = [f"# Text of the official City of Toronto item page, copied {record['retrieved']} from",
             f"# {record['url']}",
             "# The lists of people who wrote in or spoke are left out on purpose. Only counts are kept."]
    for label, page in zip(labels, pages):
        lines += ["", label, page]
    return "\n".join(lines) + "\n"


def starter_item(record: dict) -> dict:
    """Everything about an item that rules alone can fill in."""
    first = record["considerations"][0]
    title = re.sub(r"^[A-Z]+\d+\.\d+ - ", "", first["title"])          # drop the "NY15.4 - " prefix
    ward_list = wards(record)
    stages = build_stages(record)
    next_meeting = next((s for s in stages if s["can_speak"] and not s["outcome"]), None)
    return {
        "id": record["id"],
        "title_plain": "",                       # to write: a short title with no jargon
        "title_official": title,
        "topic": "",
        "ward": ward_list[0] if len(ward_list) == 1 else None,      # None means city-wide
        "place": None,                           # optional: {"label", "lat", "lon", "approx": true}
        "official_url": record["url"],
        "drafted_by": "",
        "documents": [{"id": "d1", "title": f"Official item page, {record['id']}", "type": "item_page",
                       "url": record["url"], "snapshot": f"snapshots/{record['id']}.txt",
                       "retrieved": record["retrieved"]}] + documents(record),
        "stages": [{"key": s["key"], "body": s["key"], "label": s["label"], "date": s["date"],
                    "result": None, "result_claim": None,     # the result needs a checked sentence
                    "can_speak": s["can_speak"],
                    "city_status": s["outcome"] or None} for s in stages],
        "say": {"deadline": None, "deadline_claim": None,
                "meeting": next_meeting["date"] if next_meeting else None, "meeting_claim": None,
                "guidance_claim": None, "contact_email": None, "methods": []},
        "claims": [],
        "votes": [],
        "heard": [{"stage": s["key"], "written": s["letters"], "speakers": s["speakers"] or None}
                  for s in stages if s["letters"] or s["speakers"]],
        "heard_note": f"Counted automatically from the item page on {record['retrieved']}. Names are not stored.",
        "unknowns": [],
    }


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python new_item.py <item id, e.g. 2027.PB1.6> [--html saved_page.html]")
    item_id = sys.argv[1]
    if "--html" in sys.argv:
        html = Path(sys.argv[sys.argv.index("--html") + 1]).read_text(encoding="utf-8")
        record = parse_item(html, item_id)
        record["retrieved"] = date.today().isoformat()
    else:
        record = fetch_item(item_id)
    if not record["considerations"]:
        sys.exit(f"No item found at {ITEM_URL.format(id=item_id)}. Check the item number.")

    snapshot = HERE / "snapshots" / f"{item_id}.txt"
    item_file = HERE / "items" / f"{item_id}.json"
    if "--print" in sys.argv:                      # look without writing anything
        print(snapshot_text(record))
        print(json.dumps(starter_item(record), indent=2, ensure_ascii=False))
        return
    snapshot.write_text(snapshot_text(record), encoding="utf-8")
    print(f"Wrote {snapshot}")
    if item_file.exists():
        print(f"{item_file} already exists, left untouched. Its quotes will be re-checked against the new snapshot.")
    else:
        item_file.write_text(json.dumps(starter_item(record), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Wrote {item_file}. Next: add claims with quotes, then run build_cards.py")


if __name__ == "__main__":
    main()
