"""calendar.py - write one calendar feed (.ics) with every open date to act.

Residents can subscribe to this file in any calendar app. Because the site is
static, the "alert" needs no accounts, e-mail addresses or phone numbers:
the calendar app re-reads the file by itself.
"""

from datetime import datetime, timedelta, timezone


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(",", r"\,").replace(";", r"\;").replace("\n", "\\n")


def build_feed(cards: list[dict], now: datetime) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Before the Vote//CIVIC Hack 2026//EN",
             "X-WR-CALNAME:Before the Vote: dates to have your say"]
    for card in cards:
        say = card["say"]
        when = say.get("deadline") or say.get("meeting")
        if not when:
            continue
        kind = "Deadline to comment" if say.get("deadline") else "Meeting day (no written deadline posted, comment before this day)"
        if len(when) == 10:                       # a day with no known time: an all-day entry
            day = datetime.fromisoformat(when).date()
            if day < now.date():
                continue
            timing = [f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}"]
        else:
            end = datetime.fromisoformat(when)
            if end < now:
                continue
            timing = [f"DTSTART:{_stamp(end - timedelta(hours=1))}", f"DTEND:{_stamp(end)}"]
        lines += [
            "BEGIN:VEVENT",
            f"UID:{card['id']}@before-the-vote",
            f"DTSTAMP:{_stamp(now)}",
            *timing,
            f"SUMMARY:{_escape(kind + ': ' + card['title_plain'])}",
            f"DESCRIPTION:{_escape('Official record: ' + card['official_url'])}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
