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
| Read aloud, French (machine translation, labelled), printable notice, send to a neighbour | Scheduled refresh: every 3 hours the City's pages are copied again and every sentence re-checked (`refresh.py`) |
| "Checked against the City's page" time and "What changed recently" on each decision | New item numbers in `tracked.txt` appear as "facts only" cards until an explanation is written |

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

Read the City's Open Data again, note what changed, and rebuild (needs internet, no key):

```
python refresh.py --source opendata
```

Re-read agenda item pages that a person saved from their own browser as `<id>.html`:

```
python refresh.py --source tmmis --html-dir saved_pages
```

## Live updates

`.github/workflows/refresh-and-publish.yml` runs `python refresh.py --source opendata` every 3 hours, on demand, and after every push to `main`, then publishes `web/` to GitHub Pages. It saves changed cards to the repo only when the City's data actually changed, including removing old notice cards. No API key or AI is involved in fetching, selecting, matching, extracting, checking or writing change notes.

Plain-language explanations: a card with no explanation is drafted once by an AI model if a key is set up (`OPENROUTER_API_KEY` in `pipeline/.env` locally, or as a GitHub Actions secret for the scheduled job; see `pipeline/.env.example`). Only sentences whose quotes pass the word-for-word check are shown, and the page says they were drafted by AI. A person should still read them: the check proves the words exist, not that the sentence is a fair reading.

The City's agenda item pages (secure.toronto.ca) block automated downloads. We do not get around that: no fake browser headers, no headless browser. Toronto's Open Data portal is built for programs and needs no key, so that is what the scheduled job reads.

| Source | What we take | How often | Shown as |
|---|---|---|---|
| [Public notices](https://open.toronto.ca/dataset/public-notices/) (City open data) | Notices of public meetings and applications from the last 45 days, at most 40: title, date, the notice's words, address, application numbers, notice link. Contact person and signer are left out | Every 3 hours, one read | A card per notice, `items/notice-<id>.json` |
| [Members of Toronto City Council voting record](https://open.toronto.ca/dataset/members-of-toronto-city-council-voting-record/), 2022 to 2026 (City open data) | For items with an agenda item number: committee, date, motion, result, yes and no counts. Councillors' names are never kept | Every 3 hours, one read filtered to our items | "Recorded votes (City open data)" on the decision page |
| Saved City page (agenda item page) | Stops, dates, ward, documents, counts of letters and speakers | Only when a person saves the page from their browser and runs `--source tmmis --html-dir` | The hand-made cards |

| Step | What happens |
|---|---|
| Choose notices | Last 45 days, and the title starts with "Notice of Public Meeting", "Notice of Application", "Notice of a request" or "Notice of Intention", or a topic starts with "Meetings" (`btv/notices.py`) |
| Read by rules | Exact pin and ward from the notice's address (`btv/geo.py`), the City's own "proposes" sentence, and the deadline and meeting sentences (`btv/extract.py`). A deadline comes only from a sentence that states it, never from a meeting date |
| Merge | A notice joins an existing item only if exactly one item shares its planning application number. Otherwise it gets its own card |
| Note changes | Plain notes such as "A vote was recorded on July 9, 2024 at North York Community Council: Adopt Item as Amended, Carried, 4-1." The City's result words are kept: "Carried" is never turned into "approved", because of the Steeles case |
| Re-check | Every sentence, including the rule-read deadline sentences, is checked against the saved copy by `btv/verify.py`. One that no longer matches is hidden, and a note says so |
| Forget | A notice card is deleted 120 days after its notice unless a person has written sentences for it |
| Status | `web/data/status.json` records when each source and each item was last read, from which source, and any error. If the portal cannot be reached, the error is recorded, the last data is kept, and the run still succeeds |

To turn it on: **Settings → Pages → Build and deployment → Source: GitHub Actions**, then **Actions → Refresh from the City and publish → Run workflow** once and read the report it writes on the run page.

## What is real, and what is not yet

| Part | State on 13 Nov, midday |
|---|---|
| Three real Toronto items: one open now (2027.PB1.6, Preservation Board meets 16 Nov 2026), two decided | Loaded |
| Sentences | 27 of 28 pass the check. The 28th is a wrong sentence planted on purpose to show the check working |
| Record copies in `pipeline/snapshots/` | Copied by hand from the live pages through a browser on 13 Nov. The 2026.PH31.6 deadline rests on **one sentence** copied from the notice PDF. Download the PDF and confirm it |
| Quote check, deadline guard, calendar feed, page parser, timeline rules | Work |
| `new_item.py` and `refresh.py` download step, `fetch_wards.py`, PDF reading | Written and tested on a saved sample page, **not yet run against the live sites** (the build machine had no internet access to them). The first scheduled run is the real test |
| Scheduled refresh, change notes, facts-only cards | Work offline; 83 tests pass. Item pages can no longer be downloaded automatically (the City blocks it), so they refresh only from pages a person saves |
| Open Data feed (notices and recorded votes) | Run live on 13 Nov 2026 evening: 10 notice cards, 1 with a checked deadline; 2 recorded votes attached to 2024.NY15.4 |
| `btv/summarize.py` (local model drafting through Ollama) | Written, **never run against a model**. The three items were drafted with Claude |
| Vote counts, place coordinates | Typed by hand. Coordinates are approximate and marked so |
| Meeting time and committee e-mail for the open item | Left out: the item page gives only the date, and the build now drops any time of day the record does not state |
| French | Machine translation, not reviewed, labelled as such in the interface |
| Ward outlines | Simplified. Near a boundary the "use my location" answer can be wrong |

## Do these first

1. Commit as you go. The organisers check commit history.
2. Turn on GitHub Pages (see "Live updates") and run the workflow once by hand. Read its report: it shows whether GitHub's servers can reach the City's Open Data portal, which notice cards were added, which votes were attached, and whether any sentence stopped matching.
3. Read every file in `web/js/` and `pipeline/`. The rubric penalises generated code the team cannot explain.
