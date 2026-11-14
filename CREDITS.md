# Credits and references

The rubric gives 5 points for crediting code, frameworks, libraries, algorithms and AI help, and the code of conduct requires crediting AI tools. Keep this file current.

## AI assistance

| Tool | Used for | Human check |
|---|---|---|
| Claude (Anthropic), model Claude Fable 5.2, in the Claude app | Reading the brief, research, planning documents, and first versions of the code in `web/` and `pipeline/`, all on 13 Nov 2026 after launch | Team reads, runs and can explain every file. Note below what you changed yourselves |
| Claude (Anthropic) in Cursor, 13 Nov 2026 evening | Code for the Open Data feed: `btv/opendata.py`, `btv/notices.py`, `btv/extract.py`, `btv/geo.py`, the new `refresh.py` and the website changes, with their tests | Team to read and explain each file. The feed itself uses no AI |
| Claude, same sessions | Drafting the plain-language sentences and French translations in `pipeline/items/*.json` from the saved City records | Every sentence is checked word for word by `btv/verify.py`. French is labelled as unreviewed machine translation |
| DeepSeek Chat (`deepseek/deepseek-chat`) through OpenRouter, 13 Nov 2026 evening | Drafting the plain sentences, titles and "not in the record" lists of the 10 notice cards (`ai_drafted: true`) | Checked word for word by `btv/verify.py` (25 of 26 passed). On review, Claude in Cursor reworded 3 that went beyond the notice's words (`edited_by_person: true`). The team should still read every one |
| Ollama with a local model (fill in if used) | Optional drafting route in `btv/summarize.py` | Same check. Not yet run |

Team changes after the AI draft: (list them here as you make them)

## Libraries

| Name | Where | Licence |
|---|---|---|
| Python standard library (`html.parser`, `re`, `unicodedata`, `json`, `unittest`, `urllib`) | all of `pipeline/` for checking and building | PSF |
| [requests](https://pypi.org/project/requests/) | downloads in `btv/opendata.py`, `btv/sources.py`, `btv/summarize.py`, and `new_item.py` | Apache-2.0 |
| [pypdf](https://pypi.org/project/pypdf/) | PDF text in `btv/sources.py` | BSD-3 |
| [tzdata](https://pypi.org/project/tzdata/) | Toronto time zone for `refresh.py` on Windows | Apache-2.0 |
| GitHub Actions: `actions/checkout`, `actions/setup-python`, `actions/configure-pages`, `actions/upload-pages-artifact`, `actions/deploy-pages` | `.github/workflows/refresh-and-publish.yml` | MIT |
| No JavaScript libraries or frameworks | `web/` uses browser features only: ES modules, `fetch`, `<dialog>`, SVG, Geolocation, Web Speech, Web Share | n/a |

## Fonts

| Name | Why | Licence |
|---|---|---|
| [Atkinson Hyperlegible](https://www.brailleinstitute.org/freefont/) (Braille Institute), via Google Fonts | Body text. Letters designed to stay distinct for low-vision readers | OFL |
| [Bricolage Grotesque](https://fonts.google.com/specimen/Bricolage+Grotesque), via Google Fonts | Headings | OFL |

## Algorithms and methods

| Idea | Where | Reference |
|---|---|---|
| Normalised exact-substring quote check | `btv/verify.py` | Our own. Related to extractive grounding / citation checking for language models |
| Deadline guard: day, month and year must appear in the quoted words | `btv/verify.py` | Our own rule, from the brief's constraint not to infer deadlines |
| Point-in-polygon by ray casting | `web/js/geo.js`, and the same method in Python in `pipeline/btv/geo.py` | Standard method (Shimrat, 1962) |
| Paging through an API table | `btv/opendata.py` | CKAN Data API (`package_show`, `datastore_search`), [docs.ckan.org](https://docs.ckan.org/en/latest/maintaining/datastore.html) |
| Notice rules: selection, deadline and meeting sentences, address sanity check by community council | `btv/notices.py`, `btv/extract.py` | Our own fixed rules, written from real notices in the dataset |
| Distance between two points (haversine) | `web/js/geo.js` | Standard formula |
| Equirectangular map projection | `web/js/geo.js` | Standard; fine at city scale |
| Line simplification for ward outlines | `pipeline/fetch_wards.py` | Distance-threshold thinning, a simpler relative of Douglas–Peucker (1973) |
| iCalendar files | `btv/calendar.py`, `web/js/ics.js` | RFC 5545 |

## Data and documents

All retrieved 13 Nov 2026. Contains information licensed under the Open Government Licence – Toronto.

| Source | Used for |
|---|---|
| [Item 2027.PB1.6](https://secure.toronto.ca/council/agenda-item.do?item=2027.PB1.6), 1337 Queen Street West | Open item |
| [Item 2024.NY15.4](https://secure.toronto.ca/council/agenda-item.do?item=2024.NY15.4), 1875 Steeles Avenue West | Decided item; the "Approval / Adopted / refused" test case |
| [Item 2026.PH31.6](https://secure.toronto.ca/council/agenda-item.do?item=2026.PH31.6) and its [public notice](https://www.toronto.ca/legdocs/mmis/2026/ph/bgrd/backgroundfile-287491.pdf) | Decided item with a written deadline |
| City guidance: [Have your say (TMMIS)](https://www.toronto.ca/legdocs/tmmis/have-your-say.htm), [Have your say](https://www.toronto.ca/city-government/council/council-committee-meetings/have-your-say/), [Participate](https://www.toronto.ca/city-government/council/council-committee-meetings/participate/) | General rules for speaking and writing in |
| [City Wards](https://open.toronto.ca/dataset/city-wards/), Toronto Open Data (dataset last refreshed 20 Feb 2026) | Ward outlines in `web/data/wards.txt` |
| [Public Notices](https://open.toronto.ca/dataset/public-notices/), Toronto Open Data, Open Government Licence – Toronto. First retrieved 13 Nov 2026 (dataset last refreshed that morning); re-read every 3 hours by the scheduled job | Notice cards (`items/notice-*.json`), their saved words (`snapshots/notice-*.txt`), and the test rows in `pipeline/tests/fixtures/notices.json` |
| [Members of Toronto City Council – Voting Record](https://open.toronto.ca/dataset/members-of-toronto-city-council-voting-record/), resource `member-voting-record-2022-2026`, Toronto Open Data, Open Government Licence – Toronto. First retrieved 13 Nov 2026 (dataset last refreshed 7 Nov 2026); re-read every 3 hours | "Recorded votes" counts (names are not kept), and the test rows in `pipeline/tests/fixtures/votes.json` |
| Challenge brief and opening slides, Future Cities Institute | Requirements and statistics |
