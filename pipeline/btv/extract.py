"""extract.py - read a few facts out of a notice's words with fixed rules (no AI).

Everything here returns the City's exact words next to what was read from them, so
build_cards.py can check the words are really in the saved copy of the notice, and
that the date is written in them (btv/verify.py). What is read:

  the proposal     the first sentence containing "propos", copied exactly
  the deadline     a sentence with "no later than", "deadline" or "by <time> on <date>"
                   that is about commenting, speaking or registering. The date and time
                   come from that sentence only. A deadline is NEVER worked out from a
                   meeting date.
  the meeting      a sentence saying a body "will hear" people, or that a public meeting
                   "will be held"; or a "Date: ... / Time: ..." block in a notice of public
                   meeting.
"""

import re
from datetime import date, datetime

from btv.opendata import TORONTO

MAX_EXCERPT = 300
MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]

DATE = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(\d{4})\b", re.I)
# A time like "1 2:00 p.m." (a typo in a real notice) is not read at all: the day is kept, the time dropped.
TIME = re.compile(r"(?<!\d\s)\b(\d{1,2}):(\d{2})\s*([ap])\.?\s*m\b", re.I)
NOON = re.compile(r"\bnoon\b", re.I)
DEADLINE = re.compile(r"no later than|deadline|\bby\s+(?:\d{1,2}(?::\d{2})?\s*[ap]\.?\s*m\.?|noon)\s+on\b", re.I)
ABOUT_RESIDENTS = re.compile(r"comment|speak|register|submit|presentation", re.I)   # not appeal deadlines
# Only meetings where the public is heard. "Adopted at the City Council meeting to be held on ..."
# is not one: residents cannot speak at Council.
MEETING = re.compile(r"\bwill hear\b|\bpublic meeting\b.*\b(?:to be held|will be held)\b", re.I)

DEADLINE_TEXT = "The City's notice gives this deadline to comment or ask to speak."
MEETING_TEXT = "The City's notice gives this date for the public meeting."


def sentences(text: str) -> list[str]:
    """Split notice text into sentences: every line is split after . ! or ? when the
    next word starts with a capital letter. "12:00 p.m. on" stays in one piece."""
    found = []
    for line in text.splitlines():
        found += [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", line) if part.strip()]
    return found


def proposal_excerpt(text: str) -> str | None:
    """The first sentence that says what is proposed ("The application proposes to ..."),
    copied exactly. Longer than 300 characters? Then none: we never cut the City's words."""
    for sentence in sentences(text):
        if "propos" in sentence and len(sentence) <= MAX_EXCERPT:
            return sentence
    return None


def moment(words: str, start: int = 0) -> str | None:
    """The first full date written after position `start`, with the first time of day
    after `start` if one is written. "2026-06-10T12:00:00-04:00", or "2026-06-10" with no time."""
    found = DATE.search(words, start)
    if not found:
        return None
    month, day, year = MONTHS.index(found.group(1).lower()) + 1, int(found.group(2)), int(found.group(3))
    clock = TIME.search(words, start)
    if clock:
        hour = int(clock.group(1)) % 12 + (12 if clock.group(3).lower() == "p" else 0)
        minute = int(clock.group(2))
    elif NOON.search(words, start):
        hour, minute = 12, 0
    else:
        return date(year, month, day).isoformat()
    return datetime(year, month, day, hour, minute, tzinfo=TORONTO).isoformat()


def deadline_sentences(text: str) -> list[tuple[str, str]]:
    """[(sentence, deadline)] for every sentence that states a deadline for residents."""
    found = []
    for sentence in sentences(text):
        trigger = DEADLINE.search(sentence)
        if trigger and ABOUT_RESIDENTS.search(sentence):
            when = moment(sentence, trigger.start())
            if when:
                found.append((sentence, when))
    return found


def meeting_sentence(text: str, notice_date: str) -> tuple[str, str] | None:
    """(the City's words, meeting moment) for the first meeting on or after the notice date."""
    deadlines = {sentence for sentence, _ in deadline_sentences(text)}
    for sentence in sentences(text):
        if sentence in deadlines or "was held" in sentence or not MEETING.search(sentence):
            continue
        when = moment(sentence)
        if when and when[:10] >= notice_date:
            return sentence, when
    if "public meeting" in text.lower():
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("Date:") and DATE.search(line):
                block = line
                if i + 1 < len(lines) and lines[i + 1].startswith("Time:"):
                    block += " " + lines[i + 1]
                when = moment(block)
                if when[:10] >= notice_date:
                    return block, when
    return None


def notice_say(text: str, notice_date: str, doc_id: str = "n1") -> tuple[list[dict], dict]:
    """Claims and "Have your say" facts read from one notice. Claim ids are r1, r2, ...
    build_cards.py checks each quote and each date again before anything is shown."""
    claims, say = [], {"deadline": None, "deadline_claim": None, "meeting": None, "meeting_claim": None}

    def claim(text_, quote):
        claims.append({"id": f"r{len(claims) + 1}", "section": "say", "stage": "notice", "lenses": [],
                       "text": text_, "drafted_by": "rule", "sources": [{"doc": doc_id, "quote": quote}]})
        return claims[-1]["id"]

    for sentence, when in deadline_sentences(text):
        claim_id = claim(DEADLINE_TEXT, sentence)
        if not say["deadline"]:
            say["deadline"], say["deadline_claim"] = when, claim_id
    meeting = meeting_sentence(text, notice_date)
    if meeting:
        say["meeting"], say["meeting_claim"] = meeting[1], claim(MEETING_TEXT, meeting[0])
    return claims, say
