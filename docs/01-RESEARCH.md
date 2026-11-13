# Research

Gathered 13 Nov 2026. Each fact has its source.

## The problem in numbers

| Fact | Source |
|---|---|
| Only 20% of Canadians say they have ever taken part in a municipal public consultation; 9% say they are very likely to in future | Ipsos and Municipal World, quoted in the challenge brief |
| Ontario's average municipal turnout fell to a record low of about 36% in 2022, from 38.3% in 2018, and has not passed 40% in 40 years | AMO, quoted in the challenge brief. AMO's later published figure for 2022 is 32.9% ([summary](https://www.amo.on.ca/sites/default/files/assets/DOCUMENTS/Healthy%20Democracy/2025%20AMO%20Voter%20Turnout%20Framework%20_SUMMARY%20December%202025.pdf)). Quote the brief's number and say it is the brief's |
| In a City of Toronto survey, residents' top challenges were that information is hard to find and that they are unaware of ways to give input | City of Toronto, quoted in the challenge brief |
| Those least likely to take part: renters, newcomers, students, shift workers | Challenge brief |

## The finding that shaped the product

Toronto item [2024.NY15.4](https://secure.toronto.ca/council/agenda-item.do?item=2024.NY15.4) is a zoning application for three towers and 960 homes at 1875 Steeles Avenue West, on a site with 120 rental units.

| What the official page shows | What it means |
|---|---|
| Title ends "Decision Report - Approval" | Staff recommended approval |
| North York Community Council status: "Amended" | It replaced the recommendation with one to refuse, after a public meeting, 13 letters or e-mails and 9 speakers |
| City Council status: "Adopted" | Council adopted the refusal. The towers were refused |

A resident skimming the page, or an AI summarising from the title and status, would conclude the opposite of what happened. The brief warns that "a summary that mis-states a decision is worse than no summary". This one page shows why, and it also answers the brief's question about showing how public input was considered: the record of letters, speakers and the changed recommendation is all there, just not readable.

## A decision that is open right now

Item [2027.PB1.6](https://secure.toronto.ca/council/agenda-item.do?item=2027.PB1.6): a taller base for the City-led Parkdale Hub affordable housing building at 1337 Queen Street West, Ward 4. The Toronto Preservation Board considers it on 16 November 2026. The page has Submit Comments and Request to Speak buttons and states no deadline. So the tool shows the meeting date, says plainly that no written deadline is posted, and quotes the City's general guidance instead of inventing a date.

## How having a say works in Toronto

These rules shape the product. All from the City's own pages.

| Rule | Why it matters to us | Source |
|---|---|---|
| Residents can write in or speak at committee and board meetings. **Presenters are not heard at City Council itself**, except where a law requires it | The committee is usually the last stop where a resident can speak. The Decision Line marks it | [Have your say](https://www.toronto.ca/city-government/council/council-committee-meetings/have-your-say/) |
| The City asks speakers to register by 4:30 pm the day before the meeting. Individual public notices can set a different time (our test notice says 12 noon) | The deadline differs per item. Never compute it; read it from the item | [TMMIS have your say](https://www.toronto.ca/legdocs/tmmis/have-your-say.htm) |
| Each agenda item page has "Submit Comments" and "Request to Speak" buttons | We link to the official page instead of collecting comments ourselves | [Participate](https://www.toronto.ca/city-government/council/council-committee-meetings/participate/) |
| Presentations are limited to five minutes | Goes in the "what to expect" help text | same |
| A correspondent's or speaker's name is listed in the public record and may be indexed by search engines | Residents should know this before they act. Shown in the Have your say panel | same |
| Late comments are not distributed to members | Reason the countdown is the headline | [TMMIS have your say](https://www.toronto.ca/legdocs/tmmis/have-your-say.htm) |

## Data sources

| Source | What it gives | Access | Limits |
|---|---|---|---|
| TMMIS agenda item pages, `secure.toronto.ca/council/agenda-item.do?item=YYYY.XXn.n` | Tracking status, one block per committee or Council consideration, status, ward, recommendations, decision, summary, background files, counts of letters and speakers, motions and results | Plain server-rendered HTML, one page per item. `pipeline/btv/tmmis.py` reads it | No documented API. Page structure could change without notice. Names of residents appear on the page; we count them and do not store them |
| Background files and public notices, `toronto.ca/legdocs/mmis/...pdf` | Staff reports, notices with deadlines | Direct PDF links | Inconsistent structure; scanned PDFs have no text |
| [Members of Toronto City Council – Voting Record](https://open.toronto.ca/dataset/members-of-toronto-city-council-voting-record/) | Recorded votes with item references and results | Toronto Open Data (CKAN): CSV, JSON, XML | A vote may be on an amendment; not every decision has a recorded vote; show-of-hands votes are missing ([note](https://live.toronto.votingrecords.webcomand.com/about/)) |
| Report Request Log, City Council and Committees | Council requests for staff reports, due dates, status | Toronto Open Data | A closed request does not prove the wider commitment was delivered (brief) |
| City Wards boundary file | Ward polygons for "is this near me?" | Toronto Open Data, GeoJSON | Find the exact dataset page and record the date |
| Development Applications, Committee of Adjustment Applications | Addresses and coordinates for site-specific items | Toronto Open Data | Matching an agenda item to an application needs care |

A community-written note on TMMIS's undocumented endpoints exists ([tmmis-data-fetcher](https://github.com/jamesan/tmmis-data-fetcher), 2014). It is old. Do not depend on it this weekend.

## The three test items

| Item | Why it was chosen | State |
|---|---|---|
| 2027.PB1.6, 1337 Queen Street West | Open now; site-specific; affordable housing and heritage; no written deadline on the page | Staff recommendation |
| 2024.NY15.4, 1875 Steeles Avenue West | Title and status mislead; recommendation reversed after public input; renters affected | Refused by Council |
| 2026.PH31.6, permit parking exclusions | City-wide by-law; public notice with a written deadline a day before the meeting; passed unchanged | Adopted by Council |

A good fourth item for breadth: 2024.IE15.2, the Toronto Island Park Master Plan, amended at committee and again at Council (a low-income ferry fare option and wetland protection were added along the way).

## Existing tools

| Tool | What it does | Gap we fill |
|---|---|---|
| [Engagic](https://civictech.guide/projects/engagic) | Scrapes US council meetings, plain-English agenda summaries by city | Organised by meeting, not by the resident's deadline |
| [citymeetings.nyc](https://citymeetings.nyc/) | AI chapters of NYC meeting video | After the meeting, not before the vote |
| [Chicago Councilmatic](https://notes.chicago.councilmatic.org/blog/automated-bill-summaries.html), [Seattle Councilmatic](https://directory.civictech.guide/listing/seattle-councilmatic) | Legislation tracking with auto summaries | Aimed at people who already follow council |
| [Civic Sunlight](https://www.cjr.org/analysis/ai-local-news-civic-sunlight-maine.php) | AI digests of Maine meetings; the article notes the process is far from perfect | Shows accuracy is the open problem |
| [Climate Voting Records Toronto](https://civictech.ca/projects/Climate%20Voting%20Records%20Toronto/) | How councillors voted on climate items | After the fact |

What none of them centre: the **window to act**, sentence-level proof, a clear label for how decided something is, and a route to people offline.

## Risks and harms to name in the report

- A wrong summary or deadline does real damage. Mitigation: quote check, deadline guard, staff review, "official record wins" on every page.
- Simplifying can drop conditions. Mitigation: the prompt keeps conditions; "What we do not know" section.
- People who are offline, have low literacy or limited English are still missed by a website. Mitigation: print notice; translation and reading levels are next.
- Asking for an address is personal data. Mitigation: ward choice or on-device lookup only; nothing stored.
- Residents may not realise their name becomes public when they comment. Mitigation: warning before the link.
- Appearing partisan. Mitigation: describe only; no "should"; same template for every item.
