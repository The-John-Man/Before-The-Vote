"""extract.py - read a few facts out of a notice's words with fixed rules (no AI).

Everything here returns the City's exact words next to what was read from them,
so build_cards.py can check the words are really in the saved copy of the notice.
"""

import re

MAX_EXCERPT = 300


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
