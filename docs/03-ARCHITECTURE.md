# Requirements, design and architecture

Diagrams are Mermaid; GitHub draws them. Keep them in step with the code.

## Requirements

Functional

| ID | The system shall | From the brief |
|---|---|---|
| F1 | show what is proposed and why in plain language | success criteria |
| F2 | show the ward and place of a decision, and let a resident filter to their own ward | "is this near me?" |
| F3 | show a deadline only when its date is written in the record; otherwise show the meeting date and say no deadline is posted | "do not infer a deadline" |
| F4 | link every sentence to the exact source words, the document, and the date it was copied | constraints |
| F5 | label each item as staff recommendation, committee recommendation or Council decision | constraints |
| F6 | show a stage result or a vote only when a checked sentence supports it | "worse than no summary" |
| F7 | let a resident see the item as it stood at each past stage | "follow a proposal through multiple meetings" |
| F8 | show counts of letters and speakers per stage, without names | "how public input was considered"; privacy |
| F9 | list what the record does not say | "preserve uncertainty" |
| F10 | give staff a list of every sentence with its check result | municipal users |
| F11 | offer a printable notice, a share text and a calendar feed | offline residents |
| F12 | create a starter item from an item number | municipal users |

Non-functional

| ID | Requirement |
|---|---|
| N1 | Privacy: no accounts, cookies, analytics or storage. Ward, location, lens and language live in memory and are gone when the tab closes. No map tiles are requested |
| N2 | Accuracy: the check uses no AI and has tests, including a real misleading record |
| N3 | Accessibility: WCAG 2.1 AA target; keyboard and screen-reader usable; phone-first |
| N4 | Neutral tone |
| N5 | Cost: free static hosting; checking needs only Python |
| N6 | Portability: a new city supplies `city.json`, item files and, ideally, a page reader for its agenda system |
| N7 | Explainable: no frameworks; every file short enough to walk through |

## Use cases

```mermaid
flowchart LR
  R([Resident]) --> U1[See decisions by time left]
  R --> U2[Filter to my ward]
  R --> U3[Read a decision in plain language]
  U3 --> U4[Check a sentence against its source]
  U3 --> U5[Replay a past stop]
  U3 --> U6[Bring forward what matters to me]
  R --> U7[Add date to calendar / open City form]
  N([Neighbour or community group]) --> U8[Print a notice / send to a neighbour]
  S([Clerk / comms staff]) --> U9[Start an item from its number]
  S --> U10[Add or edit sentences with quotes]
  S --> U11[Run checks and publish]
  S --> U12[Review what was held back]
```

## Components

```mermaid
flowchart TB
  subgraph City["City of Toronto (public)"]
    OD[Open Data portal, CKAN API: public notices, voting record]
    PAGE[Item page, HTML, saved by a person]
    PDF[Notices and reports, PDF]
    FORM[Comment / speak form]
  end
  subgraph Pipeline["pipeline/ (Python, run by staff)"]
    GHA[GitHub Actions, every 3 hours] --> REF[refresh.py --source opendata: read, note changes]
    REF --> ODP[btv/opendata.py: fetch rows, clean notices, count votes, no names]
    REF --> NOT[btv/notices.py: choose notices, build cards, merge by application number]
    NOT --> EXT[btv/extract.py: proposal, deadline and meeting sentences]
    NOT --> GEO[btv/geo.py: ward from the address]
    REF -. "--source tmmis --html-dir" .-> TM
    REF --> SNAP
    REF --> ITEM
    REF --> BUILD
    NEW[new_item.py] --> TM[btv/tmmis.py: read page, drop names]
    NEW --> TL[btv/timeline.py: stops, ward, documents, counts]
    NEW --> SNAP[(snapshots/*.txt, dated)]
    NEW --> ITEM[(items/*.json, drafts)]
    SUM[btv/summarize.py: optional model draft] -.-> ITEM
    BUILD[build_cards.py] --> SRC[btv/sources.py]
    BUILD --> VER[btv/verify.py: quote check, deadline guard]
    BUILD --> CAL[btv/calendar.py]
    SNAP --> SRC
    ITEM --> BUILD
    CITY[(city.json)] --> BUILD
    WARDS[fetch_wards.py]
  end
  OD --> ODP
  PAGE --> TM
  PDF --> SRC
  BUILD --> JSON[(web/data/decisions.json)]
  CAL --> ICS[(web/data/calendar.ics)]
  WARDS --> WTXT[(web/data/wards.txt)]
  subgraph Web["web/ (static files, any host)"]
    APP[app.js router] --> BOARD[board.js + map.js + geo.js]
    APP --> DEC[decision.js + speak.js + ics.js]
    APP --> POSTER[poster.js]
    APP --> METHOD[method.js]
    STATE[state.js: in memory only]
  end
  JSON --> APP
  WTXT --> BOARD
  DEC --> FORM
```

## Data sources

| Source | Read by | How | Kept | Left out |
|---|---|---|---|---|
| [Public notices](https://open.toronto.ca/dataset/public-notices/), City open data | `btv/opendata.py`, `btv/notices.py` | CKAN `package_show`, then `datastore_search` 1000 rows a page, 1 s pause, 60 s timeout, User-Agent naming the project | Title, date, notice words (as a dated snapshot), first address and its coordinates, application numbers, notice link | Contact person, signer |
| [Council voting record](https://open.toronto.ca/dataset/members-of-toronto-city-council-voting-record/), 2022 to 2026 term, City open data | `btv/opendata.py` | Same API, one query filtered to our agenda item numbers | Committee, date, motion type, the City's result words, yes and no counts | Every councillor's name, vote descriptions |
| Agenda item pages (secure.toronto.ca) | `btv/tmmis.py` | Only from pages a person saved in their own browser (`refresh.py --source tmmis --html-dir`). The site blocks automated downloads and we do not get around it | Stops, dates, ward, documents, counts of letters and speakers | Names of people who wrote in or spoke |
| [City Wards](https://open.toronto.ca/dataset/city-wards/), City open data | `fetch_wards.py` | Once, by hand | Simplified outlines in `web/data/wards.txt` | |

Everything in this table is read by fixed rules. No AI is used to fetch, choose, match, extract, check or write change notes.

## Data model (one decision card)

```mermaid
classDiagram
  class Decision { id; title_plain; title_official; topic; official_url; unknowns[] }
  class Ward { code; name }
  class Place { label; lat; lon; approx }
  class Stage { key; body; label; date; result; result_claim; can_speak }
  class Say { deadline; deadline_claim; meeting; meeting_claim; guidance_claim; methods[] }
  class Claim { id; section; stage; lenses[]; text; fr; verified; planted }
  class Source { doc; page; quote; verified }
  class Document { id; title; type; url; snapshot; retrieved }
  class Vote { stage; motion; result; yes; no; claim }
  class RecordedVote { committee; date; motion; result; yes; no }
  class Heard { stage; written; speakers }
  Decision "1" --> "0..1" Ward
  Decision "1" --> "0..1" Place
  Decision "1" --> "1..*" Stage
  Decision "1" --> "1" Say
  Decision "1" --> "1..*" Claim
  Decision "1" --> "1..*" Document
  Decision "1" --> "*" Vote
  Decision "1" --> "*" Heard
  Decision "1" --> "*" RecordedVote : votes_from_record
  Claim "1" --> "1..*" Source
  Source "*" --> "1" Document
  Stage ..> Claim : result_claim
  Vote ..> Claim : claim
  Say ..> Claim : deadline_claim
```

## Publishing a card

```mermaid
sequenceDiagram
  participant Staff
  participant N as new_item.py
  participant B as build_cards.py
  participant V as verify.py
  Staff->>N: python new_item.py 2027.PB1.6
  N-->>Staff: snapshots/2027.PB1.6.txt + starter items/2027.PB1.6.json
  Staff->>Staff: add sentences, each with exact words (by hand or with a model)
  Staff->>B: python build_cards.py
  loop every sentence
    B->>V: verify_claim(claim, pages)
    V-->>B: verified true / false
  end
  B->>V: deadline_supported(deadline, quote)
  B->>B: drop deadline, stage results and votes that rest on a failed sentence
  B-->>Staff: decisions.json, calendar.ics, list of what was held back
```

## Why this architecture

| Choice | Reason | Trade-off |
|---|---|---|
| Static site reading one JSON file | No server to attack, to pay for, or to log a resident's location. Any city IT team can host it. The site keeps working if the pipeline is down | Content changes only when staff rebuild. Agendas change on a publishing schedule, so this fits |
| Summaries prepared ahead, not a live chatbot | Every sentence can be checked and reviewed before a resident sees it. A chatbot can say something new and wrong to each visitor | No free-form questions |
| Draft by anyone, check by plain code | The drafter can be a model or a person and is never trusted. The check is about 80 lines with tests | It proves the words exist, not that the sentence reads them fairly. Human review stays |
| Dated text copies of the record | The check is repeatable; the reader sees when the record was copied; a re-copy shows what changed | Copies go stale until refreshed |
| Rules, not AI, for stops, ward, documents and counts | These are structured on the City's page. Same page in, same answer out | Tied to this page layout; a layout change needs a parser fix (the tests would catch it) |
| Our own SVG ward map | No map tiles, so no outside server learns where a resident is looking. Each ward is a real keyboard-reachable button | No street detail |
| No JavaScript framework or build step | A first-time reader can follow it; nothing to install; fast on old phones | More hand-written HTML strings; revisit past about ten screens |
| Local model option (Ollama) | Records and prompts stay on the City's computer; no API key | Smaller models draft worse; not yet tested |

## Scaling

| Dimension | Now | Path |
|---|---|---|
| Visitors | Static files on a CDN | No change needed |
| Items | One JSON file, fine into the low hundreds | One file per item plus a small index |
| Staff effort | Minutes per item to draft and review | Model drafts by default; staff review only what the check or a reviewer flags |
| Freshness | Built: a scheduled GitHub Actions job reads City open data every 3 hours, adds new notice cards, attaches recorded votes, notes what changed, hides sentences that stop matching, and republishes | Ask the City for agenda item numbers in the notices dataset; alert staff by e-mail when a sentence is hidden |
| Cities | Toronto reader in `tmmis.py` | One reader per agenda system (eSCRIBE, Legistar, CivicWeb) producing the same record shape; everything after that is shared |
| Languages | English, unreviewed French | Reviewed translations stored per sentence; quotes stay in the original language |

## Known limits

- The check passes a real quote attached to a misleading sentence. A person must still review.
- Agenda item pages cannot be downloaded automatically (the City blocks it). The three hand-made cards refresh only when a person saves their pages from a browser.
- Public notices in City open data carry no agenda item number. A notice is matched to another item only by a shared planning application number, and only when exactly one item has it. So a notice card does not show the later committee or Council decision, and its votes are not attached.
- Notice cards use the notice's first address. If the City's data places it outside the community council named in the notice (seen once: "411 Kennedy Avenue" for "Kennedy Road", Scarborough), the card shows no pin or ward rather than a wrong one.
- Deadline and meeting rules read English sentence patterns found in real notices. A notice worded differently gives no deadline (the card then shows "No date"), never a guessed one.
- Recorded votes come from the 2022 to 2026 term's voting record only. Items from the next term need the next resource name in `btv/opendata.py`.
- Hand-made cards: claim-backed vote counts and approximate place coordinates are typed by hand.
- Ward outlines are simplified; location-to-ward can be wrong near a boundary.
- Only item pages and one notice excerpt are used. Long staff reports (PDF) are linked but not yet summarised.
- `summarize.py` has never been run against a model.
