# Credits and references

The rubric gives 5 points for crediting code, frameworks, libraries, algorithms and AI help, and the code of conduct requires crediting AI tools. Keep this file current.

## AI assistance

| Tool | Used for | Human check |
|---|---|---|
| Claude (Anthropic), model Claude Fable 5.2, in the Claude app | Reading the brief, research, planning documents, and first versions of the code in `web/` and `pipeline/`, all on 13 Nov 2026 after launch | Team reads, runs and can explain every file. Note below what you changed yourselves |
| Claude, same sessions | Drafting the plain-language sentences and French translations in `pipeline/items/*.json` from the saved City records | Every sentence is checked word for word by `btv/verify.py`. French is labelled as unreviewed machine translation |
| Ollama with a local model (fill in if used) | Optional drafting route in `btv/summarize.py` | Same check. Not yet run |

Team changes after the AI draft: (list them here as you make them)

## Libraries

| Name | Where | Licence |
|---|---|---|
| Python standard library (`html.parser`, `re`, `unicodedata`, `json`, `unittest`, `urllib`) | all of `pipeline/` for checking and building | PSF |
| [requests](https://pypi.org/project/requests/) | downloads in `btv/tmmis.py`, `btv/sources.py`, `btv/summarize.py` | Apache-2.0 |
| [pypdf](https://pypi.org/project/pypdf/) | PDF text in `btv/sources.py` | BSD-3 |
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
| Point-in-polygon by ray casting | `web/js/geo.js` | Standard method (Shimrat, 1962) |
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
| Challenge brief and opening slides, Future Cities Institute | Requirements and statistics |
