"""opendata.py - read the City of Toronto's Open Data portal (no AI, no key needed).

Why this file exists: the City's agenda item pages (secure.toronto.ca) block automated
downloads, and we do not try to get around that. The Open Data portal is the City's
own service for programs. We read two of its datasets:

  public-notices                                   notices of public meetings and applications
  members-of-toronto-city-council-voting-record    every recorded vote, member by member

The portal runs CKAN. Two calls are enough:
  package_show?id=<dataset>                  lists the files ("resources") of a dataset
  datastore_search?id=<resource>&limit=...   returns the rows of one file, a page at a time

Being a good citizen: a 1 second pause before every page, a 60 second timeout,
and a User-Agent that names this project.

What we keep: the words of each notice, its addresses, application numbers and document
links. What we drop on purpose: the contact person and who signed it (no names on cards),
and every councillor's name in the voting record (only the counts are kept).
"""

import html
import json
import re
import time
from datetime import datetime, timedelta, timezone

API = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/"
USER_AGENT = "BeforeTheVote/0.3 (+https://github.com/The-John-Man/Before-The-Vote)"
PAGE_SIZE = 1000
PAUSE_SECONDS = 1
TIMEOUT_SECONDS = 60

NOTICES = "public-notices"
VOTES = "members-of-toronto-city-council-voting-record"
VOTES_RESOURCE = "member-voting-record-2022-2026"
VOTES_PAGE = "https://open.toronto.ca/dataset/members-of-toronto-city-council-voting-record/"

try:
    from zoneinfo import ZoneInfo
    TORONTO = ZoneInfo("America/Toronto")
except Exception:            # no time-zone database on this computer: Eastern Standard Time
    TORONTO = timezone(timedelta(hours=-5))


# ---------------------------------------------------------------- downloading

def _call(action: str, **params) -> dict:
    import requests          # imported here so the tests run without it
    response = requests.get(API + action, params=params, timeout=TIMEOUT_SECONDS,
                            headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    body = response.json()
    if not body.get("success"):
        raise RuntimeError(f"the Open Data portal said no to {action}: {body.get('error')}")
    return body["result"]


def fetch_rows(dataset: str, resource_name: str | None = None, filters: dict | None = None) -> list[dict]:
    """Every row of a dataset's table, read 1000 at a time.

    Uses the dataset's resource that has a live table (datastore_active). If a dataset
    has several, `resource_name` picks one (the voting record has one per Council term).
    `filters` asks the portal for matching rows only, e.g. {"Agenda Item #": ["2024.NY15.4"]},
    so we do not download 47,000 votes to find ten.
    """
    resources = [r for r in _call("package_show", id=dataset)["resources"] if r.get("datastore_active")]
    if resource_name:
        resources = [r for r in resources if r["name"] == resource_name]
    if not resources:
        raise ValueError(f"no readable table in dataset {dataset} ({resource_name or 'any'})")
    params = {"id": resources[0]["id"], "limit": PAGE_SIZE}
    if filters:
        params["filters"] = json.dumps(filters)
    rows, offset = [], 0
    while True:
        time.sleep(PAUSE_SECONDS)
        page = _call("datastore_search", offset=offset, **params)["records"]
        rows += page
        if len(page) < PAGE_SIZE:          # a short page is the last one
            return rows
        offset += PAGE_SIZE


# ---------------------------------------------------------------- notices

def _json(value):
    """Some fields arrive as JSON written inside a string ("[...]"). Read them either way."""
    if isinstance(value, str):
        try:
            return json.loads(value) if value.strip() else None
        except ValueError:
            return None
    return value


def notice_text(raw_html: str | None) -> str:
    """The notice's HTML as plain text: one paragraph (or line break) per line,
    &amp; and &nbsp; turned into normal characters, runs of spaces squeezed to one."""
    text = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>|</tr>", "\n", raw_html or "")
    text = html.unescape(re.sub(r"<[^>]+>", " ", text)).replace("\xa0", " ")
    lines = (re.sub(r"\s+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def toronto_date(epoch_ms) -> str:
    """noticeDate is milliseconds since 1970 (as text). Return the day in Toronto, YYYY-MM-DD."""
    return datetime.fromtimestamp(int(epoch_ms) / 1000, tz=TORONTO).date().isoformat()


def parse_notice(row: dict) -> dict:
    """One notice row, cleaned. Contact and signedBy are left out on purpose."""
    addresses = []
    for place in _json(row.get("addressList")) or []:
        try:
            lat, lon = float(place["latitudeCoordinate"]), float(place["longitudeCoordinate"])
        except (KeyError, TypeError, ValueError):
            continue                       # an address without coordinates cannot be placed
        label = place.get("streetAddress") or place.get("fullAddress") or ""
        addresses.append({"label": label.strip(), "lat": lat, "lon": lon})
    documents = [{"title": " ".join((d.get("description") or "Notice").split()), "url": d["url"]}
                 for d in _json(row.get("backgroundInformationList")) or [] if d.get("url")]
    return {
        "id": str(row["noticeId"]),
        "title": " ".join((row.get("title") or "").split()),
        "date": toronto_date(row["noticeDate"]),
        "body": (row.get("decisionBody") or "").strip(),
        "topics": _json(row.get("topics")) or [],
        "text": notice_text(row.get("noticeDescription")),
        "addresses": addresses,
        "application_numbers": _json(row.get("planningApplicationNumbers")) or [],
        "documents": documents,
    }


# ---------------------------------------------------------------- votes

def group_votes(rows: list[dict], item_ids) -> dict:
    """Turn member-by-member vote rows into one entry per motion, with counts only.

    Returns {item_id: [{committee, date, motion, result, yes, no}]}. Names are never
    copied. The City's result text ("Carried, 4-1") is kept word for word: "Carried"
    on "Adopt Item" can mean a refusal was adopted, so we never rewrite it as "approved".
    """
    wanted = set(item_ids)
    motions = {}
    for row in rows:
        item_id = row.get("Agenda Item #")
        if item_id not in wanted:
            continue
        key = (item_id, row.get("Committee"), row.get("Date/Time"), row.get("Motion Type"),
               row.get("Vote Description"), row.get("Result"))
        motion = motions.setdefault(key, {
            "committee": row.get("Committee") or "", "date": (row.get("Date/Time") or "")[:10],
            "motion": row.get("Motion Type") or "", "result": row.get("Result") or "", "yes": 0, "no": 0})
        vote = (row.get("Vote") or "").strip().lower()
        if vote in ("yes", "no"):          # "Absent" is not counted
            motion[vote] += 1
    grouped = {}
    for key in sorted(motions, key=lambda k: k[2] or ""):      # oldest vote first
        grouped.setdefault(key[0], []).append(motions[key])
    return grouped
