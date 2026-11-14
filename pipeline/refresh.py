"""refresh.py - keep Before the Vote in step with the City's own record. No AI anywhere.

Two sources, chosen with --source:

  opendata (the default, used by the scheduled job)
      Reads the City of Toronto's Open Data portal (btv/opendata.py), once for notices
      and once for votes:
        1. every recent notice of a public meeting or application becomes a card
           (btv/notices.py); deadlines and meetings are read by rules (btv/extract.py)
        2. existing notice cards are updated; a card is deleted 120 days after its
           notice unless a person has written sentences for it
        3. items with an agenda item number (like 2024.NY15.4) get the votes recorded
           for them in the City's voting record, as counts with no names

  tmmis --html-dir <folder>
      Reads agenda item pages that a PERSON saved from their own browser as <id>.html.
      The City's item pages (secure.toronto.ca) block automated downloads, and we do not
      try to get around that: this script never downloads them.

Either way it then:
  - saves a new copy of the record in snapshots/ ONLY if its words changed
  - writes a plain note of what changed, and writes an item file only if it changed
  - rebuilds the site (build_cards.py), which re-checks every sentence against the newest
    copy. A sentence whose quote is no longer in the record is hidden, and a note says so.
  - writes web/data/status.json: when each item and each source was last checked, and
    whether it worked. If the portal cannot be reached, the error is recorded there, the
    last data is kept, and the script still ends normally.

Run from the pipeline folder:   python refresh.py            (same as --source opendata)
                                python refresh.py --source tmmis --html-dir saved_pages
"""

import argparse
import copy
import json
import os
import re
from datetime import date, datetime
from pathlib import Path

import build_cards
from btv import opendata
from btv.geo import load_wards
from btv.notices import attach_notice, can_forget, card_id, matching_item, notice_card, select, update_card
from btv.notices import snapshot_text as notice_snapshot
from btv.timeline import build_stages, documents as rule_documents, wards as rule_wards
from btv.tmmis import parse_item
from new_item import snapshot_text, starter_item

HERE = Path(__file__).resolve().parent
ITEMS = HERE / "items"
SNAPSHOTS = HERE / "snapshots"
TRACKED = HERE / "tracked.txt"
STATUS = HERE.parent / "web" / "data" / "status.json"
DECISIONS = HERE.parent / "web" / "data" / "decisions.json"

KEEP_UPDATES = 5      # how many "what changed" entries each item keeps
AGENDA_ITEM = re.compile(r"^\d{4}\.[A-Z]+\d+\.\d+$")    # e.g. 2024.NY15.4
OPEN_DATA = "City open data"
SAVED_PAGE = "Saved City page"


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

    # Drop links an older parser wrongly kept from the page footer; keep only agenda documents.
    item["documents"] = [d for d in item["documents"]
                         if d.get("type") != "background" or "/legdocs/" in d.get("url", "")]
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


# ---------------------------------------------------------------- recorded votes

def vote_note(motion: dict) -> str:
    day = date.fromisoformat(motion["date"])
    return (f"A vote was recorded on {day:%B} {day.day}, {day.year} at {motion['committee']}: "
            f"{motion['motion']}, {motion['result']}.")


def attach_votes(item: dict, motions: list[dict], today: str) -> tuple[dict, list[str]]:
    """Put the City's recorded votes for this item on it, as counts (no names).
    The City's words for the motion and result are kept as they are: "Carried" on
    "Adopt Item" is never turned into "approved". Pure: tested in tests/test_refresh_opendata.py."""
    old = item.get("votes_from_record")
    if old is not None and old["motions"] == motions:
        return item, []
    item = copy.deepcopy(item)
    item["votes_from_record"] = {"dataset": opendata.VOTES, "resource": opendata.VOTES_RESOURCE,
                                 "url": opendata.VOTES_PAGE, "retrieved": today, "motions": motions}
    if old is None:
        return item, []          # first check: these votes are not news
    return item, [vote_note(m) for m in motions if m not in old["motions"]]


# ---------------------------------------------------------------- files

def read_record(item_id: str, html_dir: Path, today: str) -> dict:
    """An item page a person saved from their browser. Never downloaded by this script."""
    record = parse_item((html_dir / f"{item_id}.html").read_text(encoding="utf-8"), item_id)
    record["retrieved"] = today
    if not record["considerations"]:
        raise ValueError("the saved page has no item with this number")
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


def save_snapshot(relative_path: str, text: str) -> bool:
    """Write a saved copy ONLY if its words changed. Returns True if it was written."""
    path = HERE / relative_path
    if path.exists() and body_lines(path.read_text(encoding="utf-8")) == body_lines(text):
        return False
    path.write_text(text, encoding="utf-8")
    return True


def short_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"[:200]


# ---------------------------------------------------------------- one run

class Run:
    """What every step of one refresh shares: the date, the last published cards,
    status.json being written, and the report printed at the end."""

    def __init__(self, now: datetime, city: dict, previous_cards: dict, status: dict):
        self.today = now.date().isoformat()
        self.checked_at = now.isoformat(timespec="minutes")
        self.city, self.previous_cards, self.status = city, previous_cards, status
        self.report = []

    def checked(self, item_id: str, source: str, what: str, error: str | None = None):
        """what: "page" (a saved item page), "notice" or "votes"."""
        self.status["items"][item_id] = {"ok": error is None, "error": error, "checked_at": self.checked_at,
                                         "source": source, "checked": what}

    def source(self, key: str, name: str, url: str, error: str | None = None, rows: int | None = None):
        self.status["sources"][key] = {"name": name, "url": url, "ok": error is None, "error": error,
                                       "checked_at": self.checked_at, "rows": rows}

    def save(self, item_id: str, item: dict, old_item: dict | None, notes: list[str]) -> list[str]:
        """Re-check every sentence against the newest copy (say so if any stopped matching),
        then write the item file only if something changed."""
        lost = lost_sentences(self.previous_cards.get(item_id), build_cards.build_card(copy.deepcopy(item), self.city))
        if lost:
            note = (f"{len(lost)} sentence{'s' if len(lost) > 1 else ''} no longer match"
                    f"{'es' if len(lost) == 1 else ''} the City's latest record and "
                    f"{'is' if len(lost) == 1 else 'are'} hidden until a person reviews "
                    f"{'it' if len(lost) == 1 else 'them'}.")
            add_note(item, self.today, note)
            notes.append(note)
        if item != old_item:
            save_json(ITEMS / f"{item_id}.json", item)
        return notes


def refresh_saved_pages(run: Run, ids: list[str], html_dir: Path):
    """--source tmmis: item pages a person saved from their browser."""
    for item_id in ids:
        try:
            record = read_record(item_id, html_dir, run.today)
        except Exception as error:   # file missing, not an item page...
            run.checked(item_id, SAVED_PAGE, "page", short_error(error))
            run.report.append(f"{item_id}: could not read the saved page ({short_error(error)}). Kept the last copy.")
            continue
        item_path = ITEMS / f"{item_id}.json"
        is_new = not item_path.exists()
        old_item = None if is_new else json.loads(item_path.read_text(encoding="utf-8"))
        item, notes = refresh_item(old_item or starter_item(record), record, run.today)
        if is_new:
            notes = ["Added to Before the Vote. The plain-language explanation is not written yet."]
            item["updates"] = [{"date": run.today, "notes": notes}]
        snapshot_doc = next((d for d in item["documents"] if d.get("type") == "item_page"), None)
        if snapshot_doc and save_snapshot(snapshot_doc["snapshot"], snapshot_text(record)):
            snapshot_doc["retrieved"] = run.today
            if not is_new:
                notes.append("A new copy of the City's page was saved.")
        notes = run.save(item_id, item, old_item, notes)
        run.checked(item_id, SAVED_PAGE, "page")
        run.report.append(f"{item_id}: " + ("; ".join(notes) if notes else "no change"))
    run.source("saved_pages", "Item pages saved from a browser", "https://secure.toronto.ca/council/")


def refresh_notices(run: Run, rows: list[dict], items: dict):
    """Update notice cards, add new ones, forget old ones. `items` is updated in place."""
    notices = []
    for row in rows:
        try:
            notices.append(opendata.parse_notice(row))
        except Exception:
            continue                       # one malformed row must not stop the others
    by_id = {n["id"]: n for n in notices}
    wards = load_wards()
    today = date.fromisoformat(run.today)

    # 1. cards we already have
    for item_id, old in list(items.items()):
        notice = by_id.get(old.get("notice_id")) if item_id.startswith("notice-") else None
        if notice is None:
            continue
        item, notes = update_card(old, notice_card(notice, wards, run.today))
        if save_snapshot(item["documents"][0]["snapshot"], notice_snapshot(notice, run.today)):
            item["documents"][0]["retrieved"] = run.today
            notes.append("A new copy of the City's notice was saved.")
        for note in notes:
            add_note(item, run.today, note)
        items[item_id] = item
        run.checked(item_id, OPEN_DATA, "notice")
        notes = run.save(item_id, item, old, notes)
        if notes:
            run.report.append(f"{item_id}: " + "; ".join(notes))

    # 2. new notices, oldest first, so a later notice can join an earlier card
    attached = {d.get("notice_id") for item in items.values() for d in item["documents"]}
    for notice in reversed(select(notices, today)):
        new_id = card_id(notice)
        if new_id in items or notice["id"] in attached:
            continue
        attached.add(notice["id"])
        target = matching_item(notice, list(items.values()))
        if target:
            old = items[target]
            item, notes = attach_notice(old, notice, run.today)
            save_snapshot(f"snapshots/{new_id}.txt", notice_snapshot(notice, run.today))
            for note in notes:
                add_note(item, run.today, note)
            notes = run.save(target, item, old, notes)
            items[target] = item
            run.report.append(f"{target}: " + "; ".join(notes))
            continue
        item = notice_card(notice, wards, run.today)
        save_snapshot(item["documents"][0]["snapshot"], notice_snapshot(notice, run.today))
        item["updates"] = [{"date": run.today, "notes": [
            "Added from the City's public notices (Open Data). The plain-language explanation is not written yet."]}]
        run.save(new_id, item, None, [])
        items[new_id] = item
        run.checked(new_id, OPEN_DATA, "notice")
        deadline = item["say"]["deadline"]
        run.report.append(f"{new_id}: new card" + (f", deadline {deadline}" if deadline else ", no deadline in the notice"))

    # 3. old notice cards nobody has written for
    for item_id, item in list(items.items()):
        if can_forget(item, today):
            (ITEMS / f"{item_id}.json").unlink(missing_ok=True)
            (SNAPSHOTS / f"{item_id}.txt").unlink(missing_ok=True)
            del items[item_id]
            run.report.append(f"{item_id}: removed (notice more than 120 days old, no sentences written by a person)")


def refresh_votes(run: Run, rows: list[dict], items: dict, agenda_ids: list[str]):
    grouped = opendata.group_votes(rows, agenda_ids)
    for item_id in agenda_ids:
        motions = grouped.get(item_id, [])
        item, notes = attach_votes(items[item_id], motions, run.today)
        for note in notes:
            add_note(item, run.today, note)
        if item != items[item_id]:
            save_json(ITEMS / f"{item_id}.json", item)
            items[item_id] = item
        run.checked(item_id, OPEN_DATA, "votes")
        run.report.append(f"{item_id}: {len(motions)} recorded vote{'' if len(motions) == 1 else 's'} in the City's voting record"
                          + (": " + " ".join(notes) if notes else ""))


def refresh_open_data(run: Run, fetch):
    """--source opendata: one read of the notices, one read of the votes."""
    items = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(ITEMS.glob("*.json"))}
    notices_page = "https://open.toronto.ca/dataset/public-notices/"
    try:
        rows = fetch(opendata.NOTICES)
    except Exception as error:     # portal down, network down...
        run.source("notices", "Public notices", notices_page, error=short_error(error))
        for item_id in items:
            if item_id.startswith("notice-"):
                run.checked(item_id, OPEN_DATA, "notice", short_error(error))
        run.report.append(f"Public notices: could not reach the City's Open Data portal ({short_error(error)}). Kept the last data.")
    else:
        run.source("notices", "Public notices", notices_page, rows=len(rows))
        refresh_notices(run, rows, items)

    agenda_ids = sorted(i for i in items if AGENDA_ITEM.match(i))
    if not agenda_ids:
        return
    try:
        rows = fetch(opendata.VOTES, opendata.VOTES_RESOURCE, filters={"Agenda Item #": agenda_ids})
    except Exception as error:
        run.source("votes", "Council voting record 2022-2026", opendata.VOTES_PAGE, error=short_error(error))
        run.report.append(f"Voting record: could not reach the City's Open Data portal ({short_error(error)}). Kept the last data.")
        return
    run.source("votes", "Council voting record 2022-2026", opendata.VOTES_PAGE, rows=len(rows))
    refresh_votes(run, rows, items, agenda_ids)


def main(argv: list[str] | None = None, fetch=None) -> list[str]:
    """`fetch` replaces opendata.fetch_rows in tests, so they need no network."""
    parser = argparse.ArgumentParser(description="Bring Before the Vote in step with the City's record and rebuild the site.")
    parser.add_argument("ids", nargs="*", help="with --source tmmis: only these item ids (default: all tracked items)")
    parser.add_argument("--source", choices=["opendata", "tmmis"], default="opendata",
                        help="opendata: the City's Open Data portal (default). tmmis: item pages saved from a browser")
    parser.add_argument("--html-dir", type=Path, help="with --source tmmis: the folder holding <id>.html pages")
    args = parser.parse_args(argv)
    if args.source == "tmmis" and not args.html_dir:
        parser.error("--source tmmis needs --html-dir. This script never downloads secure.toronto.ca pages: "
                     "save them from your own browser into a folder first.")

    city = json.loads((HERE / "city.json").read_text(encoding="utf-8"))
    previous_cards = {}
    if DECISIONS.exists():
        previous_cards = {c["id"]: c for c in json.loads(DECISIONS.read_text(encoding="utf-8"))["decisions"]}
    previous = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    run = Run(toronto_now(), city, previous_cards,
              {"items": previous.get("items", {}), "sources": previous.get("sources", {})})

    if args.source == "tmmis":
        refresh_saved_pages(run, args.ids or tracked_ids(), args.html_dir)
    else:
        refresh_open_data(run, fetch or opendata.fetch_rows)

    build_cards.main()
    status = {"checked_at": run.checked_at, "source": args.source,
              "items": {k: v for k, v in run.status["items"].items() if (ITEMS / f"{k}.json").exists()},
              "sources": run.status["sources"]}
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    report = run.report
    print("\nRefresh report")
    for line in report:
        print("  " + line)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")   # shows the report on the Actions run page
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("## Refresh report\n\n" + "\n".join(f"- {line}" for line in report) + "\n")
    return report


if __name__ == "__main__":
    main()
