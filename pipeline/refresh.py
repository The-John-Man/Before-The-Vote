"""refresh.py - keep Before the Vote in step with the City's own record.

Run from the pipeline folder:   python refresh.py
A scheduled GitHub Actions job runs it every few hours (.github/workflows/refresh-and-publish.yml).

For every tracked item (each file in items/, plus any new id listed in tracked.txt) it:

  1. downloads the official item page again                 (btv/tmmis.py)
  2. updates the facts that rules can read, with no AI:      (btv/timeline.py)
       stops on the line and their dates, ward, documents, counts of letters and speakers
  3. saves a new copy of the record in snapshots/ ONLY if its words changed
  4. writes a plain note of what changed ("City Council added to the item, July 24 and 25, 2024")
  5. rebuilds the site, which re-checks every sentence against the newest copy.
     A sentence whose quote is no longer in the record is held back, and a note says so.
  6. writes web/data/status.json: when each item was last checked, and whether it worked

A brand-new id in tracked.txt becomes a "facts only" card straight away: the rules above
fill it in, and the site says the plain-language explanation is not written yet.

Being a good citizen: one request per item, a pause between requests, a User-Agent that
names this project, and nothing else is fetched. secure.toronto.ca/robots.txt returned
404 on 13 Nov 2026, which means no crawling rules are published.

Offline testing:   python refresh.py --html-dir tests/pages
reads <id>.html from that folder instead of downloading.
"""

import argparse
import copy
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import build_cards
from btv.timeline import build_stages, documents as rule_documents, wards as rule_wards
from btv.tmmis import fetch_item, parse_item
from new_item import snapshot_text, starter_item

HERE = Path(__file__).resolve().parent
ITEMS = HERE / "items"
SNAPSHOTS = HERE / "snapshots"
TRACKED = HERE / "tracked.txt"
STATUS = HERE.parent / "web" / "data" / "status.json"
DECISIONS = HERE.parent / "web" / "data" / "decisions.json"

PAUSE_SECONDS = 3     # wait between requests to the City's site
KEEP_UPDATES = 5      # how many "what changed" entries each item keeps


# ---------------------------------------------------------------- small helpers

def toronto_now() -> datetime:
    """The current time in Toronto. Falls back to the computer's own zone if the
    time-zone database is missing (common on Windows without the tzdata package)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Toronto"))
    except Exception:
        return datetime.now().astimezone()


def body_lines(text: str) -> str:
    """The words of a snapshot without our own # notes, spaces squeezed.
    Two copies of an unchanged page give the same answer even if copied on different days."""
    kept = [line for line in text.splitlines() if not line.startswith("#")]
    return re.sub(r"\s+", " ", " ".join(kept)).strip()


def tracked_ids() -> list[str]:
    """Every item that already has a file, plus any new id in tracked.txt."""
    ids = {path.stem for path in ITEMS.glob("*.json")}
    if TRACKED.exists():
        for line in TRACKED.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if line:
                ids.add(line)
    return sorted(ids)


# ---------------------------------------------------------------- what changed

def record_facts(record: dict) -> dict:
    """A short fingerprint of the facts that matter, used to describe changes."""
    stages = [{"body": c["body"], "date": c["date_text"], "status": c["meta"].get("Status", "")}
              for c in reversed(record["considerations"])]
    urls = {d["url"] for c in record["considerations"] for d in c["documents"]}
    written = sum(n for c in record["considerations"] for k, n in c["counts"].items() if k.startswith("Communications"))
    speakers = sum(n for c in record["considerations"] for k, n in c["counts"].items() if k.startswith("Speakers"))
    return {"tracking": record["tracking"], "stages": stages, "documents": len(urls),
            "written": written, "speakers": speakers}


def describe_changes(old: dict | None, new: dict) -> list[str]:
    """Plain sentences about what is different on the City's page.

    The City's status word is never repeated as a result: "Adopted" can mean a refusal
    was adopted (see the 1875 Steeles case). We only say THAT a body has acted.
    """
    if old is None:
        return []   # first automatic check: nothing to compare with yet
    notes = []
    before = {s["body"]: s for s in old["stages"]}
    for stage in new["stages"]:
        previous = before.get(stage["body"])
        if previous is None:
            notes.append(f"{stage['body']} was added to the item ({stage['date']}).")
        elif stage["status"] and stage["status"] != previous["status"]:
            notes.append(f"The City's page now shows a result from {stage['body']}. "
                         "Read the official record; our explanation is updated once it is checked.")
        elif stage["date"] != previous["date"]:
            notes.append(f"{stage['body']} meeting date changed from {previous['date']} to {stage['date']}.")
    if new["documents"] > old["documents"]:
        n = new["documents"] - old["documents"]
        notes.append(f"{n} new document{'s' if n > 1 else ''} added to the City's page.")
    if new["written"] > old["written"]:
        n = new["written"] - old["written"]
        notes.append(f"{n} more letter{'s' if n > 1 else ''} or e-mail{'s' if n > 1 else ''} from the public.")
    if new["speakers"] > old["speakers"]:
        notes.append(f"{new['speakers'] - old['speakers']} more people registered to speak.")
    if not notes and new["tracking"] != old["tracking"]:
        notes.append("The status summary on the City's page changed.")
    return notes


# ---------------------------------------------------------------- merging rule facts into an item

def _matches(item_stage: dict, rule_stage: dict, committees_in_item: int, committees_in_rules: int) -> bool:
    if rule_stage["key"] in ("staff", "council"):
        return item_stage["body"] == rule_stage["key"]
    if item_stage["body"] != "committee":
        return False
    # Same committee by name; or the only committee on both sides (labels may differ slightly).
    return item_stage["label"] == rule_stage["label"] or (committees_in_item == 1 and committees_in_rules == 1)


def merge_stages(item_stages: list[dict], rule_stages: list[dict]) -> list[dict]:
    """Update dates and the City's status on stages we already have; add stages that are new.
    Results written by people ("refused the application") are never touched: they need a
    checked sentence, which build_cards.py enforces."""
    stages = copy.deepcopy(item_stages)
    committees_in_item = sum(s["body"] == "committee" for s in stages)
    committees_in_rules = sum(s["key"] == "committee" for s in rule_stages)
    for rule in rule_stages:
        match = next((s for s in stages if _matches(s, rule, committees_in_item, committees_in_rules)), None)
        if match:
            if rule["date"]:
                match["date"] = rule["date"]
            match["city_status"] = rule["outcome"] or None
            continue
        key = rule["key"]
        while any(s["key"] == key for s in stages):          # keep keys unique
            key += "2"
        new_stage = {"key": key, "body": rule["key"], "label": rule["label"], "date": rule["date"],
                     "result": None, "result_claim": None, "can_speak": rule["can_speak"],
                     "city_status": rule["outcome"] or None}
        council_at = next((i for i, s in enumerate(stages) if s["body"] == "council"), None)
        if rule["key"] != "council" and council_at is not None:
            stages.insert(council_at, new_stage)              # committees come before Council
        else:
            stages.append(new_stage)
    return stages


def merge_heard(item: dict, rule_stages: list[dict]) -> list[dict]:
    """Counts of letters and speakers per stage, from the page. Names are never kept."""
    heard = {h["stage"]: dict(h) for h in item.get("heard", [])}
    committees_in_item = sum(s["body"] == "committee" for s in item["stages"])
    committees_in_rules = sum(s["key"] == "committee" for s in rule_stages)
    for rule in rule_stages:
        if not (rule["letters"] or rule["speakers"]):
            continue
        stage = next((s for s in item["stages"] if _matches(s, rule, committees_in_item, committees_in_rules)), None)
        if stage:
            heard[stage["key"]] = {"stage": stage["key"], "written": rule["letters"], "speakers": rule["speakers"] or None}
    order = [s["key"] for s in item["stages"]]
    return sorted(heard.values(), key=lambda h: order.index(h["stage"]) if h["stage"] in order else 99)


def refresh_item(item: dict, record: dict, today: str) -> tuple[dict, list[str]]:
    """Bring one item in line with a freshly read record. Returns (new item, notes).
    Pure: no files, no network. Tested in tests/test_refresh.py."""
    item = copy.deepcopy(item)
    facts = record_facts(record)
    notes = describe_changes(item.get("record_facts"), facts)
    rule_stages = build_stages(record)

    item["stages"] = merge_stages(item["stages"], rule_stages)
    item["heard"] = merge_heard(item, rule_stages)
    if item.get("ward") is None and len(rule_wards(record)) == 1:
        item["ward"] = rule_wards(record)[0]

    known = {d["url"] for d in item["documents"]}
    for doc in rule_documents(record):
        if doc["url"] not in known:
            n = 1
            while any(d["id"] == f"b{n}" for d in item["documents"]):
                n += 1
            item["documents"].append({**doc, "id": f"b{n}", "type": "background"})

    # The next stop where residents can speak, as the City's page now lists it.
    upcoming = next((s for s in item["stages"] if s.get("can_speak") and s.get("date") and not s.get("city_status")), None)
    if upcoming and (item["say"].get("meeting") or "")[:10] != upcoming["date"]:
        item["say"]["meeting"] = upcoming["date"]

    item["record_facts"] = facts
    if notes:
        item.setdefault("updates", []).insert(0, {"date": today, "notes": notes})
        item["updates"] = item["updates"][:KEEP_UPDATES]
    return item, notes


def lost_sentences(before: dict | None, after: dict) -> list[str]:
    """Sentences that passed the check on the last build but fail against the new copy."""
    if not before:
        return []
    passed_before = {c["id"] for c in before["claims"] if c.get("verified")}
    return [c["text"] for c in after["claims"] if c["id"] in passed_before and not c["verified"]]


# ---------------------------------------------------------------- files and network

def read_record(item_id: str, html_dir: Path | None, today: str) -> dict:
    if html_dir:
        record = parse_item((html_dir / f"{item_id}.html").read_text(encoding="utf-8"), item_id)
        record["retrieved"] = today
    else:
        record = fetch_item(item_id)
        record["retrieved"] = today
    if not record["considerations"]:
        raise ValueError("the City's page has no item with this number")
    return record


def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add_note(item: dict, today: str, note: str):
    updates = item.setdefault("updates", [])
    if updates and updates[0]["date"] == today:
        updates[0]["notes"].append(note)
    else:
        updates.insert(0, {"date": today, "notes": [note]})
    item["updates"] = updates[:KEEP_UPDATES]


def main():
    parser = argparse.ArgumentParser(description="Re-copy tracked items from the City and rebuild the site.")
    parser.add_argument("ids", nargs="*", help="only these item ids (default: all tracked items)")
    parser.add_argument("--html-dir", type=Path, help="read <id>.html from this folder instead of downloading")
    args = parser.parse_args()

    now = toronto_now()
    today = now.date().isoformat()
    city = json.loads((HERE / "city.json").read_text(encoding="utf-8"))
    previous_cards = {}
    if DECISIONS.exists():
        previous_cards = {c["id"]: c for c in json.loads(DECISIONS.read_text(encoding="utf-8"))["decisions"]}

    status = {"checked_at": now.isoformat(timespec="minutes"), "items": {}}
    report = []
    for number, item_id in enumerate(args.ids or tracked_ids()):
        if number and not args.html_dir:
            time.sleep(PAUSE_SECONDS)
        item_path = ITEMS / f"{item_id}.json"
        try:
            record = read_record(item_id, args.html_dir, today)
        except Exception as error:   # network down, page moved, item number wrong...
            message = f"{type(error).__name__}: {error}"[:200]
            status["items"][item_id] = {"ok": False, "error": message, "checked_at": status["checked_at"]}
            report.append(f"{item_id}: could not read the City's page ({message}). Kept the last copy.")
            continue

        is_new = not item_path.exists()
        old_item = json.loads(item_path.read_text(encoding="utf-8")) if not is_new else starter_item(record)
        item, notes = refresh_item(old_item, record, today)
        if is_new:
            notes = ["Added to Before the Vote. The plain-language explanation is not written yet."]
            item["updates"] = [{"date": today, "notes": notes}]

        # Save a new copy of the record only if its words changed.
        snapshot_doc = next((d for d in item["documents"] if d.get("type") == "item_page"), None)
        if snapshot_doc:
            path = HERE / snapshot_doc["snapshot"]
            fresh = snapshot_text(record)
            if not path.exists() or body_lines(path.read_text(encoding="utf-8")) != body_lines(fresh):
                path.write_text(fresh, encoding="utf-8")
                snapshot_doc["retrieved"] = today
                if not is_new:
                    notes.append("A new copy of the City's page was saved.")

        # Re-check every sentence against the newest copy, and say so if any stopped matching.
        lost = lost_sentences(previous_cards.get(item_id), build_cards.build_card(copy.deepcopy(item), city))
        if lost:
            note = (f"{len(lost)} sentence{'s' if len(lost) > 1 else ''} no longer match"
                    f"{'es' if len(lost) == 1 else ''} the City's latest page and "
                    f"{'is' if len(lost) == 1 else 'are'} hidden until a person reviews "
                    f"{'it' if len(lost) == 1 else 'them'}.")
            add_note(item, today, note)
            notes.append(note)

        if is_new or item != old_item:
            save_json(item_path, item)
        status["items"][item_id] = {"ok": True, "error": None, "checked_at": status["checked_at"]}
        report.append(f"{item_id}: " + ("; ".join(notes) if notes else "no change"))

    build_cards.main()
    STATUS.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    print("\nRefresh report")
    for line in report:
        print("  " + line)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")   # shows the report on the Actions run page
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("## Refresh report\n\n" + "\n".join(f"- {line}" for line in report) + "\n")


if __name__ == "__main__":
    main()
