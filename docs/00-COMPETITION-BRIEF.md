# Competition brief: CIVIC Hack 2026

Sources, all read on 13 Nov 2026: the [Devpost page](https://civic-hack-2026.devpost.com/), the [CIVIC Hack site](https://fciprojects.ca/hackathons/2026-civic-hack), the challenge brief (Word file from Discord) and the opening ceremony slides.

Not read yet: the Devpost "Rules" tab, the expanded 1/3/5 rubric descriptions on the CIVIC Hack site, the Municipal Readiness Report template, the demo video guide, and the Friday livestream from the Summit. Read the first four before writing the report and recording the video.

## The challenge that won the vote

**1. Making municipal decisions easier to understand.** How might we help residents understand a proposed municipal decision, how it could affect them, and when they can have a say?

Build a working proof of concept a municipality could realistically pilot: web app, data tool, map, dashboard or other. A municipal leader should be able to use it without your team in the room.

Summit attendees cast 30 votes; this challenge got 13. The slides call the event "36 hours to reimagine municipal innovation with AI", so judges expect AI to be part of the answer and its role to be explained.

## Dates (all Eastern)

| When | What |
|---|---|
| Thu 12 Nov, 7 pm | Hacking began. Nothing built before this may be used |
| Fri 13 Nov, 8 am | Checkpoint one: post your problem, user and idea in two lines |
| Fri 13 Nov, 8:30 to 10 am | Live from the Summit. Leaders say what a city would need. "What they say is your brief for the next 24 hours" |
| Fri 13 Nov, 10 am to 4 pm | Mentor office hours on Discord |
| Fri 13 Nov, 3 pm | Checkpoint two: where you've got to |
| Fri 13 Nov, 6 pm | Checkpoint three: progress, read submission requirements |
| Sat 14 Nov, 8 am | Final checkpoint |
| **Sat 14 Nov, 10 am** | **Hacking ends. No code, no generating, no edits. Late submissions not considered** |
| Sat 14 Nov, 12 pm | Top five announced |
| Sat 14 Nov, 12:30 pm | Finalists: 5-minute pitch or live demo, 3 minutes of questions |

## Hard rules

- Team of 1 to 4. At least one University of Waterloo student.
- No pre-built tools or code written in advance. **Commits will be checked.**
- Use only public, open or organiser-provided data. No personal or confidential information.
- Credit open-source code, datasets and AI tools.
- You must understand and be able to explain your code, including AI-generated code. Unexplained generated code is penalised.
- The team owns its work; FCI and Waterloo may show the hackathon version with credit.

## What to submit on Devpost

0. **Project name and team members** (from the slides).
1. **Code repository link** (required). Working prototype link welcome ("ideally", say the slides).
2. **Demo video, 2 to 3 minutes** (required). Show it working, say who it's for. Over 3:00 is not considered.
3. **Municipal Readiness Report, one page** (required). Who uses it, data and resources needed, rough cost, privacy, what residents should know, how other cities could adapt it. A PDF in the repo is fine. Use the organisers' template.
4. **Short description** (required). Problem, who it's for, solution, what's next.

## Rubric (100 points) and where we earn each

| Criterion | Pts | Our answer |
|---|---|---|
| Problem understanding, stakeholders, harms and trade-offs | 10 | `01-RESEARCH.md`; the Steeles case; "What the record does not say"; name-publication warning |
| Project quality and functionality: core task works on a relevant example, **checked outputs**, real not simulated, limits made clear | 15 | Three real items, one open now; 27 of 28 sentences pass a non-AI check and the planted wrong one is caught; limits listed on the "How we check" page |
| Design, clarity, feasibility: usable outside your discipline, realistic to run | 10 | Departures board, Decision Line, ward map; static files, no server |
| Impact and practical value; how other cities adapt | 5 | One `city.json` and item files per city; `new_item.py` shows the import path |
| Requirements and design (UML) | 5 | `03-ARCHITECTURE.md` |
| Architecture rationale and scalability | 5 | `03-ARCHITECTURE.md` |
| Source code awareness | 5 | Small commented files, 29 tests; you can walk through each |
| References for code, libraries, algorithms, AI | 5 | `CREDITS.md` |
| Municipal Readiness Report | 20 | Draft in `05-SUBMISSION-KIT.md` |
| Demo video | 20 | Script in `05-SUBMISSION-KIT.md` |

Presentation is 40 of 100. Budget real hours for the video and the report.

Special recognition: most community-centred project (residents' needs and equity) and best storytelling and visualisations (video and pitch).

## What the Challenge 1 brief asks for

**Success looks like** a tool that takes a real decision or staff report and shows in plain language: what is proposed and why; who and where it affects ("is this near me?"); key dates and how and when to have a say; a link back to the source for every claim, connected to the original reports and decision "including important amendments or conditions". It should give thought to who it might leave out, be tested on two or three real agenda items, be accurate and neutral, and be usable by a municipal leader alone.

**Lines in the brief that shaped the build**
- "The tool needs to distinguish an upcoming opportunity for input from a decision that has already been made."
- "Explaining an issue accurately can require connecting several records."
- "translate, personalize and time information: telling a resident what is proposed near them, what it would change, and the next date they can act."
- "How can municipalities show how public input was considered, even if it did not change the final decision?"
- "An app alone will also miss people offline."
- "Explain your thinking... how you checked its outputs... If you use AI, make its role and limitations clear."

**Constraints**
- Tell apart staff recommendations, committee decisions and final council decisions.
- Show source and date for each explanation.
- Keep conditions and uncertainty. Every summary links to the exact source passage. A summary that mis-states a decision is worse than no summary.
- Verify participation information on the official item page. **Do not infer a submission deadline from a meeting date.**
- Clear, accessible language. No unnecessary personal information from public correspondence. Non-partisan.

**Technical points they raise**: inconsistent PDFs; models that omit, distort or invent; geolocation from addresses and legal descriptions; personalisation versus data minimisation; consistent timelines across decision types; WCAG, plain language, translation, mobile-first.

**Datasets they name**: Report Request Log (City Council and Committees) and Members of Toronto City Council Voting Record, both on Toronto Open Data. Others allowed: agendas, minutes and staff reports, municipal open data (zoning, ward boundaries, development applications), public notice pages, plain-language and accessibility guidelines. Record sources and dates, make data limits visible.

**Primary users**: residents unfamiliar with council, including renters, newcomers, youth, seniors, people with lower literacy or limited English; community groups. An app alone misses people offline.
**Municipal users**: clerks, communications and engagement staff, councillors and their staff.
**Others**: community associations, local businesses, local journalists, civil advocates.

**What the host values** (opening slides): tools "built to replicate across jurisdictions"; transparency ("what FCI learns is shared in the open"); "a loop, not a pipeline", meaning capture, validate and share so other municipalities can adopt it. The Readiness Report should speak to exactly this.

**Judges**: Eryn Stewart (strategy, Indigenous partnerships), Clarence Woudsma (planner, transportation, GIS), Melanie Hains (UX, storytelling with data), Susan Brown (knowledge mobilisation), Pedro Miranda (secure data, consent and privacy).
