# Before the Vote

CIVIC Hack 2026, Challenge 1: *How might we help residents understand a proposed municipal decision, how it could affect them, and when they can have a say?*

**Before the Vote** shows what a city is deciding, sorted by how long residents still have to speak. Each decision is explained in plain language, and every sentence carries the City's exact words behind it. A small program with no AI in it checks that those words are really in the City's record. A sentence that fails the check is never shown to residents.

Why that matters: Toronto item 2024.NY15.4 is titled "...Decision Report - **Approval**" and its status reads "**Adopted**". City Council **refused** it. A summary written from the title gets the decision backwards. Ours cannot, and `pipeline/tests/test_real_items.py` proves it.

Submission deadline: **Saturday 14 November 2026, 10:00 am ET. All building stops then.**

## What it does

| For residents | For staff |
|---|---|
| Departures board: decisions by time left to have a say | Start a new item from its item number (`new_item.py`) |
| Ward map drawn in the browser; location never leaves the device | Stops, ward, documents and counts filled in by rules, not AI |
| Decision Line: staff report, committee, Council, with the last stop where you can speak | Every sentence checked word for word against a dated copy of the record |
| "Source" on every sentence: the City's words, page link, date copied | "How we check" page lists every sentence and anything held back |
| Press a past stop to see what was known then, and what changed after | Deadlines shown only when the date is written in the record |
| "I rent", "I live nearby": bring forward the sentences that matter to you | Residents' names from letters and speaker lists are counted, never stored |
| How they voted; how many people wrote in or spoke | Calendar feed residents can subscribe to, with no accounts |
| Read aloud, French (machine translation, labelled), printable notice, send to a neighbour | |

## Folder map

| Path | What it is |
|---|---|
| `docs/00-COMPETITION-BRIEF.md` | Rules, deadlines, what to submit, the 100-point rubric |
| `docs/01-RESEARCH.md` | Problem evidence, how having a say works in Toronto, data sources, existing tools |
| `docs/02-PRODUCT-PLAN.md` | The idea, users, features, what is left, hour-by-hour schedule |
| `docs/03-ARCHITECTURE.md` | Requirements, UML diagrams, why this design, how it scales |
| `docs/04-UI-DESIGN.md` | Visual direction, screens, accessibility checklist |
| `docs/05-SUBMISSION-KIT.md` | Checkpoint posts, video script, Readiness Report draft, Devpost text |
| `CREDITS.md` | Every library, dataset and AI tool used |
| `pipeline/` | Python: records in, checked decision cards out |
| `web/` | The website: plain HTML, CSS and JavaScript, no build step, no libraries |

## Run it

Website:

```
cd web
python -m http.server 8000
```

Open http://localhost:8000. Add `?asof=2026-06-05` to the address to see the site as of a past day (a red banner shows you are in test view).

Check and publish the cards, and run the tests (no internet or extra packages needed):

```
cd pipeline
python build_cards.py
python -m unittest -v
```

Start a new decision from the City's item number (needs internet and `pip install -r requirements.txt`):

```
python new_item.py 2027.PB1.6
```

## What is real, and what is not yet

| Part | State on 13 Nov, midday |
|---|---|
| Three real Toronto items: one open now (2027.PB1.6, Preservation Board meets 16 Nov 2026), two decided | Loaded |
| Sentences | 27 of 28 pass the check. The 28th is a wrong sentence planted on purpose to show the check working |
| Record copies in `pipeline/snapshots/` | Copied by hand from the live pages through a browser on 13 Nov. The 2026.PH31.6 deadline rests on **one sentence** copied from the notice PDF. Download the PDF and confirm it |
| Quote check, deadline guard, calendar feed, page parser, timeline rules | Work; 29 tests pass |
| `new_item.py` download step, `fetch_wards.py`, PDF reading | Written, **not yet run against the live sites** (the build machine had no internet access to them) |
| `btv/summarize.py` (local model drafting through Ollama) | Written, **never run against a model**. The three items were drafted with Claude |
| Vote counts, place coordinates | Typed by hand. Coordinates are approximate and marked so |
| Meeting time and committee e-mail for the open item | Left out: the item page gives only the date, and the build now drops any time of day the record does not state |
| French | Machine translation, not reviewed, labelled as such in the interface |
| Ward outlines | Simplified. Near a boundary the "use my location" answer can be wrong |

## Do these first

1. `git init`, commit, push to GitHub. **Nothing is committed yet and the organisers check commit history.** Commit as you go from here.
2. Run `python new_item.py 2027.PB1.6` on your own machine. If the snapshot it writes still passes `build_cards.py`, the hand-copied text matched the live page.
3. Read every file in `web/js/` and `pipeline/`. The rubric penalises generated code the team cannot explain.
