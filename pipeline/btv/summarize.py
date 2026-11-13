"""summarize.py - ask a local language model to draft the "claims" of an item file.

NOT YET TESTED against a running model. The three item files in pipeline/items/
were drafted with Claude and then checked by build_cards.py; this file is the
route for a city that wants to run drafting on its own computer with Ollama, so
documents and prompts never leave the building and cost nothing.

Usage, from the pipeline folder:
    python -m btv.summarize items/2027.PB1.6.json
It prints draft claims as JSON. A person pastes the good ones into the item file,
then runs build_cards.py, which checks every quote. The model is never trusted.
"""

import json
import sys

from btv.sources import load_pages

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1"   # change to a model shown by `ollama list`

PROMPT = """You explain municipal records to residents in plain language (about Grade 8).
Stay neutral: describe, never argue for or against.

Return JSON: {{"claims": [{{"section": "what" | "why" | "changed" | "say",
  "stage": "staff" | "committee" | "council" | null,
  "lenses": [any of "nearby", "rent", "drive", "business"],
  "text": "one plain sentence",
  "sources": [{{"doc": "{doc_id}", "quote": "exact words copied from the record, 5 words or more"}}]}}],
  "unknowns": ["what a resident would want to know that the record does not say"]}}

Rules:
- Copy quotes character for character.
- Say who acted: staff recommend, a committee recommends, Council decided. Never mix them.
  The title of an item can disagree with the final decision. Trust the decision text.
- Keep conditions ("subject to", "or a later meeting").
- Only give a deadline if the record states one. Never work it out from a meeting date.
- If the record does not say, add it to "unknowns". Do not guess.

RECORD:
{text}
"""


def draft_claims(doc_id: str, pages: list[str]) -> dict:
    import requests
    response = requests.post(OLLAMA_URL, timeout=600, json={
        "model": MODEL, "stream": False, "format": "json",
        "options": {"temperature": 0},
        "messages": [{"role": "user", "content": PROMPT.format(doc_id=doc_id, text="\n\n".join(pages))}],
    })
    response.raise_for_status()
    return json.loads(response.json()["message"]["content"])


if __name__ == "__main__":
    item = json.load(open(sys.argv[1], encoding="utf-8"))
    first = item["documents"][0]
    print(json.dumps(draft_claims(first["id"], load_pages(first)), indent=2, ensure_ascii=False))
