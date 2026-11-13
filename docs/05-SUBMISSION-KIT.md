# Submission kit

Drafts to edit. Replace every bracket with something you measured or checked yourself.

## Checkpoint posts

**Two (Fri 3 pm).** "Before the Vote is running on three real Toronto items, one open now (Preservation Board, 16 Nov). 27 of 28 sentences pass our non-AI quote check; the 28th is a wrong sentence we planted and it is caught. This afternoon: hand review, a cold user test, accessibility."

**Three (Fri 6 pm).** "Working site at [link]. Residents see time left to speak, a plain explanation, the City's exact words behind every sentence, what changed between stages, and a printable notice. Tonight: Readiness Report and video."

## Demo video (target 2:45, hard limit 3:00)

| Time | On screen | Say |
|---|---|---|
| 0:00 to 0:25 | The City's page for 1875 Steeles: zoom on "Approval" in the title, then "Status: Adopted" | "Three towers, 960 homes, on a site with 120 rental units. The title says Approval. The status says Adopted. So it was approved? No. Council refused it. If the official record can be read backwards, residents don't stand a chance. This is for them: renters, newcomers, anyone new to council." |
| 0:25 to 0:50 | Board, tap Ward 4 on the map | "Before the Vote sorts what the city is deciding by how long you have left to have a say. Tap your ward; nothing leaves your phone. This one is open now: the Preservation Board meets Monday." |
| 0:50 to 1:20 | Parkdale decision: status label, line, Have your say panel | "Staff recommend it. Nothing is decided. This is the stop where you can speak. The City posted no deadline, so we show the meeting date and say so. We never turn a meeting date into a deadline." |
| 1:20 to 1:45 | Press Source; then "How we check", the planted sentence in red | "Every sentence shows the City's exact words. A small program, with no AI in it, checks they are really in the record. We planted the wrong sentence, 'Council approved the application'. It was held back." |
| 1:45 to 2:10 | Steeles decision: press the staff stop, then committee, then Council; votes; what the public sent in | "Follow it stop by stop. Staff recommended approval. Thirteen letters and nine speakers later, the community council voted 4 to 1 to refuse. Council agreed." |
| 2:10 to 2:30 | "I rent" lens; Français; Read aloud; notice; send to a neighbour | "Bring forward what matters to you. Hear it read. Print a notice for the lobby, for neighbours who are not online." |
| 2:30 to 2:45 | Terminal: `python new_item.py ...` then architecture diagram | "Staff start an item from its number. Static files, no accounts, no tracking. Another city changes one reader and its item files." |

Record at 1080p, speak slowly, add captions. Say only numbers you have re-checked. Check the final length twice.

## Municipal Readiness Report (one page). Move this into the organisers' template

**Who would use it.** Residents new to council processes. City Clerk's, communications and engagement staff, who add items and review explanations. Councillors' offices and community groups, who pass them on.

**What it does.** Turns a council agenda item into a plain-language page: what is proposed, how decided it is, what changed between stages, and how long is left to have a say, with the City's exact words behind every sentence.

**Data and resources.** The public item page and notices. Open data for ward outlines. About [15] minutes of staff time per item to draft and review. A laptop with Python. Any static web host.

**Rough cost.** Hosting: free to a few dollars a month. Drafting: free with a local model or cents per item with a hosted one. The real cost is review time: about [N] staff hours a week for [M] items.

**Privacy.** No accounts, cookies, analytics or stored data. Ward, location and choices stay in the browser's memory and vanish when the tab closes. No map tiles are loaded. Names of residents who wrote in or spoke are counted and never stored. With a local model, records never leave the City's computer.

**What residents should know.** Explanations are drafted with AI and checked, and are not the official record. "Checked" means the quoted words were found in the City's record on the date shown; it does not guarantee the explanation is complete. A deadline appears only when the City wrote one. If you comment or speak, the City publishes your name. French is machine translation.

**How we checked it.** Three real Toronto items, [28] sentences. Automatic check: [27] passed; one deliberately wrong sentence was held back. Hand review by the team: [result]. Tested with [n] people outside the team: [what they got stuck on].

**Limits.** Record copies are refreshed by hand. Long PDF reports are linked, not yet summarised. Ward outlines are simplified. A website still misses people offline; the printed notice is a first step, not a fix.

**How another municipality could adapt it.** Keep the website, the checks and the card format. Replace `city.json`, the ward file and the item files. Cities on common agenda systems (eSCRIBE, Legistar, CivicWeb) need one page reader like `tmmis.py`. Open source, [licence].

**Before a pilot.** Clerk and legal sign-off on wording and the disclaimer. A named reviewer. An accessibility audit. Reviewed translations for the city's main languages. A way for residents to report an error. A scheduled refresh on agenda publishing days.

## Devpost short description

**Problem.** Residents usually learn about a municipal decision after their chance to speak has passed, and the official record is hard to read: one Toronto item is titled "Approval", marked "Adopted", and was in fact refused.

**Who it's for.** Residents unfamiliar with council, and the clerks and communications staff who explain decisions to them.

**Solution.** Before the Vote sorts real decisions by time left to have a say, explains each in plain language, and shows the City's exact words behind every sentence. A non-AI check holds back any sentence, result, vote or deadline the record does not support. Residents can follow an item stop by stop, see how public input preceded a change, and print a notice for neighbours offline.

**What's next.** Scheduled refresh with alerts when the record changes, long-report summaries, reviewed translations, readers for other agenda systems, a pilot with one clerk's office.

## Final checks before submitting

- [ ] Repo public; commits spread across the event; README runs from a clean clone
- [ ] Project name and team members on Devpost
- [ ] `CREDITS.md` complete, including what the team changed after the AI drafts
- [ ] UML in `03-ARCHITECTURE.md` matches the code
- [ ] Report is one page, PDF in the repo, on the organisers' template
- [ ] Video between 2:00 and 3:00, public or unlisted
- [ ] Every number in the report and video re-checked
- [ ] Open item re-copied Saturday morning
- [ ] Submitted by 9:00 am Saturday
