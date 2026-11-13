# Product plan: Before the Vote

## The idea in two lines

> **Problem and user:** A renter or newcomer usually hears about a council decision after the last chance to speak has passed, and the official record can read as the opposite of what was decided.
> **Idea:** Before the Vote sorts real decisions by time left to have a say, explains each in plain language, and shows the City's exact words behind every sentence, checked by a program with no AI in it.

## Three ideas that make it different

1. **Organised around the window to act.** Most tools summarise what council did. This one puts the decision whose chance to speak closes soonest at the top, and marks the last stop on the line where a resident can speak. In Toronto that is the committee, not Council.
2. **Nothing reaches a resident on trust.** Whoever drafts a sentence, a model or a clerk, must attach the exact words from the record. Plain string matching confirms them. A failed sentence is held back. A stage result ("refused") or a vote is shown only if its sentence passed. A deadline is shown only if its date is written in the record; a meeting date is never turned into a deadline.
3. **The record, made followable.** One line of stops connects the staff report, the committee and Council. Press a past stop and the page shows what was known then, so you can see what changed along the way, how members voted, and how many people wrote in or spoke before the change.

## Users

| User | What they need | What they get |
|---|---|---|
| Resident new to council (renter, newcomer, student, senior, shift worker) | "Does this touch me, and can I still do something?" in a minute, on a phone | Board, ward map, plain page, time left, calendar file, link to the City's own comment form, read aloud |
| Neighbour who is offline or reads little English | To hear about it at all | A printed notice for the lobby; "send this to a neighbour"; French (machine translation, labelled) |
| Clerk, communications or engagement staff | To publish explanations without risking a wrong one | Import by item number, automatic checks, a page listing every sentence and anything held back |
| Councillor's office, community group, journalist | A fast, accurate brief to pass on | One link per decision with sources and votes |

## What is built

| Feature | Brief line it answers |
|---|---|
| Departures board by time left; open items first | "when they can have a say" |
| Ward map, ward list and "use my location", all worked out on the device | "is this near me?"; data minimisation |
| Decision Line with replay of past stops | "distinguish staff recommendations, committee decisions and final council decisions"; "follow a proposal through multiple meetings" |
| Source on every sentence, with date copied and link | "link back to the exact source passage"; "source and date for each explanation" |
| Quote check, deadline guard, result guard, vote guard | "AI-generated answers need to be checked against the records"; "do not infer a submission deadline" |
| "What changed along the way", "How they voted", "What the public sent in" | "amendments or conditions"; "how public input was considered" |
| "What the record does not say" | "preserve important conditions and uncertainty" |
| Lenses: I live nearby, I rent, I drive or park, I run a business | "personalize" without collecting anything |
| Read aloud; French toggle; 18 px legible type; keyboard-usable map | accessibility, translation |
| Printable notice; send to a neighbour; subscribe-able calendar feed | "an app alone will also miss people offline" |
| "How we check" page with live counts and limits | "make its role and limitations clear" |
| Name-publication warning before the link to comment | what residents should know |
| `new_item.py`: item number in, dated record copy and starter file out, names of residents dropped | municipal users; privacy |

## What is left, in order

| # | Task | Why |
|---|---|---|
| 1 | Commit and push now, then after each task | Commit history is checked |
| 2 | Run `new_item.py` for the three items on your machine and rebuild | Confirms the hand-copied records match the live pages and proves the import works |
| 3 | Download the PH31.6 notice PDF and confirm the deadline sentence and its page | That deadline currently rests on one copied sentence |
| 4 | Hand-read all 28 sentences against the official pages; fix or delete any you would not defend | "Accurate and neutral"; you will be asked |
| 5 | Check the two place coordinates on a map; correct them | They are approximate |
| 6 | Have a French speaker read three French sentences, or switch French off | Unreviewed translation is a risk |
| 7 | Ask someone non-technical to use it cold for five minutes; fix what confuses them | "Usable by someone outside your discipline" |
| 8 | Accessibility pass (checklist in `04-UI-DESIGN.md`) | WCAG is in the brief |
| 9 | Deploy `web/` to GitHub Pages | Working prototype link |
| 10 | Report on the organisers' template; video; Devpost form | 40 of 100 points |

Optional if time remains: add 2024.IE15.2 (Island master plan) as a fourth item; try `btv/summarize.py` with a local model and report honestly how many of its sentences pass.

Will not do: accounts, storing addresses or names, collecting comments ourselves, writing opinions for residents, a chatbot that answers live.

## Schedule from Friday midday (Eastern)

| When | Do |
|---|---|
| Fri 12 to 1 pm | Tasks 1 to 3. Read the code |
| Fri 1 to 3 pm | Task 4 and 5. Ask a municipal mentor on Discord (open until 4): "No deadline is posted on 2027.PB1.6. Is quoting the 4:30 pm general guidance the right thing to show?" |
| Fri 3 pm | Checkpoint two |
| Fri 3 to 6 pm | Tasks 6 to 8. Watch the Summit recording if you missed it and note what leaders said a city would need |
| Fri 6 pm | Checkpoint three. Re-read the submission requirements |
| Fri 6 to 9 pm | Task 9. Update UML if the code changed. Update `CREDITS.md` |
| Fri 9 pm to midnight | Readiness Report on the template, PDF into the repo |
| Sat 6:30 to 8 am | Record and cut the video, under 2:50 |
| Sat 8 am | Final checkpoint |
| Sat 8 to 9 am | Devpost form. Submit by 9:00 |
| Sat 9 to 10 am | Buffer. No new features |
| **Sat 10 am** | **Stop** |

## What would sink it

| Risk | Plan |
|---|---|
| A live page differs from the hand copy and sentences start failing | Good: that is the check working. Fix the quote or delete the sentence |
| The Preservation Board item changes before judging (a deadline appears, or it is deferred) | Re-run `new_item.py` Saturday at 8 am and rebuild |
| A wrong fact in the video | Record only after task 4. Show the Source pop-up on camera |
| Cannot explain a file when asked | Re-write it in your own words until you can |
| Judges read "AI summaries" and assume a chatbot | Open the video with the Steeles case and the planted sentence being caught |
