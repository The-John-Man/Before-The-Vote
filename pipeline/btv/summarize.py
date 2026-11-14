"""summarize.py - ask a language model to draft the plain-language "claims" of an item file.

The model is never trusted. Every sentence it writes must carry exact words from the
City's record, and build_cards.py publishes a sentence only if those words are found.
A sentence that fails stays hidden and is listed on the "How we check" page.

Providers (pick with BTV_AI_PROVIDER, or the first one with a key is used):
    openai     OPENAI_API_KEY      default model gpt-4o-mini
    deepseek   DEEPSEEK_API_KEY    default model deepseek-chat
    openrouter OPENROUTER_API_KEY  default model deepseek/deepseek-chat (keys start sk-or-)
    ollama     no key, runs on this computer (http://localhost:11434)   default llama3.1
BTV_AI_MODEL overrides the model. Keys go in pipeline/.env (see pipeline/.env.example)
or, for the scheduled job, in GitHub Actions secrets.

refresh.py calls draft_item() for items that have no explanation yet (rule-read deadline
and meeting sentences do not count), once per item.
By hand, from the pipeline folder:
    python -m btv.summarize items/2027.PB1.6.json            print the drafts
    python -m btv.summarize items/2027.PB1.6.json --write    save them into the item file
"""

import json
import os
import sys
from pathlib import Path

from btv.env import load_env
from btv.sources import load_pages

PROVIDERS = {
    "openai": {"url": "https://api.openai.com/v1/chat/completions", "key": "OPENAI_API_KEY", "model": "gpt-4o-mini"},
    "deepseek": {"url": "https://api.deepseek.com/chat/completions", "key": "DEEPSEEK_API_KEY", "model": "deepseek-chat"},
    "openrouter": {"url": "https://openrouter.ai/api/v1/chat/completions", "key": "OPENROUTER_API_KEY",
                   "model": "deepseek/deepseek-chat"},
    "ollama": {"url": "http://localhost:11434/api/chat", "key": None, "model": "llama3.1"},
}
SECTIONS = {"what", "why", "changed"}
LENSES = {"nearby", "rent", "drive", "business"}

PROMPT = """You explain municipal records to residents in plain language (about Grade 8).
Stay neutral: describe, never argue for or against.

Return JSON: {{"title_plain": "a short title with no jargon, under 12 words",
  "topic": "one to three words, such as Housing, Parking, Heritage",
  "claims": [{{"section": "what" | "why" | "changed",
  "stage": {stages} | null,
  "lenses": [any of "nearby", "rent", "drive", "business"],
  "text": "one plain sentence",
  "sources": [{{"doc": "{doc_id}", "quote": "exact words copied from the record, 5 words or more"}}]}}],
  "unknowns": ["what a resident would want to know that the record does not say"]}}

Rules:
- Copy quotes character for character.
- Say who acted: staff recommend, a committee recommends, Council decided. Never mix them.
  The title of an item can disagree with the final decision. Trust the decision text.
- Keep conditions ("subject to", "or a later meeting"). If the record says something is
  "proposed", say it is proposed, not that it will happen.
- Do not give reasons ("because ...") that the record does not state.
- Only give a deadline if the record states one. Never work it out from a meeting date.
- If the record does not say, add it to "unknowns". Do not guess.

RECORD:
{text}
"""


def choose_provider() -> tuple[str, str] | None:
    """(provider, model) from the environment, or None when no key is set."""
    load_env()
    name = (os.environ.get("BTV_AI_PROVIDER") or "").strip().lower()
    if not name:
        name = next((n for n, p in PROVIDERS.items() if p["key"] and os.environ.get(p["key"])), "")
    if not name:
        return None
    if name not in PROVIDERS:
        raise ValueError(f"BTV_AI_PROVIDER must be one of {', '.join(PROVIDERS)}, not {name!r}")
    key = PROVIDERS[name]["key"]
    if key and not os.environ.get(key):
        return None
    return name, (os.environ.get("BTV_AI_MODEL") or "").strip() or PROVIDERS[name]["model"]


def ask_model(prompt: str, provider: str, model: str) -> dict:
    import requests
    settings = PROVIDERS[provider]
    if provider == "ollama":
        response = requests.post(settings["url"], timeout=600, json={
            "model": model, "stream": False, "format": "json", "options": {"temperature": 0},
            "messages": [{"role": "user", "content": prompt}]})
        response.raise_for_status()
        return json.loads(response.json()["message"]["content"])
    response = requests.post(settings["url"], timeout=300,
                             headers={"Authorization": f"Bearer {os.environ[settings['key']]}"},
                             json={"model": model, "temperature": 0,
                                   "response_format": {"type": "json_object"},
                                   "messages": [{"role": "user", "content": prompt}]})
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def draft_claims(doc_id: str, pages: list[str], stages: list[str], provider: str, model: str, ask=ask_model) -> dict:
    stage_list = " | ".join(f'"{s}"' for s in stages) or '"staff" | "committee" | "council"'
    return ask(PROMPT.format(doc_id=doc_id, stages=stage_list, text="\n\n".join(pages)), provider, model)


def _clean_claims(raw: list, doc_id: str, stages: set[str]) -> list[dict]:
    """Keep only well-formed drafts, in the shape build_cards.py expects."""
    claims = []
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict) or not str(entry.get("text") or "").strip():
            continue
        sources = [{"doc": doc_id, "quote": str(s["quote"]).strip()}
                   for s in entry.get("sources") or [] if isinstance(s, dict) and str(s.get("quote") or "").strip()]
        if not sources:
            continue
        claims.append({
            "id": f"c{len(claims) + 1}",
            "section": entry.get("section") if entry.get("section") in SECTIONS else "what",
            "stage": entry.get("stage") if entry.get("stage") in stages else None,
            "lenses": [lens for lens in entry.get("lenses") or [] if lens in LENSES],
            "text": str(entry["text"]).strip(),
            "sources": sources,
            "ai_drafted": True,
        })
    return claims


def needs_draft(item: dict) -> bool:
    """No explanation yet: no sentence written by a person or a model. Sentences read by
    rules (deadlines, meetings) do not count. A model is asked only once per item."""
    if item.get("ai_drafted_on"):
        return False
    return not any(c.get("drafted_by") != "rule" for c in item.get("claims", []))


def draft_item(item: dict, today: str, ask=ask_model) -> int | None:
    """Add AI drafts to an item that has no explanation yet. Changes the item in place.
    Returns how many sentences were drafted, or None when no provider is set up.
    People's sentences and rule-read sentences are kept as they are."""
    if not needs_draft(item):
        return 0
    choice = choose_provider()
    if choice is None:
        return None
    provider, model = choice
    doc = next((d for d in item["documents"] if d.get("type") in ("item_page", "notice")), None)
    if doc is None:
        return 0
    stages = [s["key"] for s in item["stages"]]
    result = draft_claims(doc["id"], load_pages(doc), stages, provider, model, ask)
    drafts = _clean_claims(result.get("claims"), doc["id"], set(stages))
    item["ai_drafted_on"] = today
    item["drafted_by"] = f"{provider} {model} (AI), {today}, every quote checked word for word"
    if not drafts:
        return 0
    item["claims"] = item.get("claims", []) + drafts
    if not item.get("title_plain") and isinstance(result.get("title_plain"), str):
        item["title_plain"] = result["title_plain"].strip()
    if not item.get("topic") and isinstance(result.get("topic"), str):
        item["topic"] = result["topic"].strip()
    extra = [u.strip() for u in result.get("unknowns") or [] if isinstance(u, str) and u.strip()]
    item["unknowns"] = item.get("unknowns", []) + [u for u in extra if u not in item.get("unknowns", [])]
    return len(drafts)


if __name__ == "__main__":
    from datetime import date
    if len(sys.argv) < 2:
        sys.exit("Usage: python -m btv.summarize items/<id>.json [--write]")
    path = Path(sys.argv[1])
    item = json.loads(path.read_text(encoding="utf-8"))
    if not needs_draft(item):
        sys.exit(f"{path} already has an explanation or was drafted before.")
    count = draft_item(item, date.today().isoformat())
    if count is None:
        sys.exit("No AI provider set up. Put OPENAI_API_KEY or DEEPSEEK_API_KEY in pipeline/.env.")
    if "--write" in sys.argv:
        path.write_text(json.dumps(item, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {count} draft sentences to {path}. Run build_cards.py to check them.")
    else:
        print(json.dumps({k: item.get(k) for k in ("title_plain", "topic", "claims", "unknowns")},
                         indent=2, ensure_ascii=False))
