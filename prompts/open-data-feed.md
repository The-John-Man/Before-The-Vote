# Build: open data feed for the scheduled refresh

Implement this on the branch `live-refresh`. Commit after each numbered step, run `python -m unittest -v` from `pipeline/` after each step, and push to `live-refresh`. Don't merge to `main`.

## Step 0: get ready

- `git checkout live-refresh && git pull`
- Read first:
  - `README.md` ("Live updates")
  - `pipeline/refresh.py`, `pipeline/build_cards.py`
  - `pipeline/btv/verify.py`, `timeline.py`, `sources.py`, `calendar.py`
  - `pipeline/items/2027.PB1.6.json`, for the item file format
  - `pipeline/snapshots/*.txt`, for the snapshot format: `#` lines are notes the checker ignores
  - `web/js/geo.js` and `pipeline/fetch_wards.py`, for the format of `web/data/wards.txt`
  - `web/js/board.js`, `decision.js`, `util.js`, `map.js`, `method.js`
  - everything in `pipeline/tests/`
- Check the API is reachable before writing code:
  ```
  python -c "import requests;print(requests.get('https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=public-notices',timeout=30).status_code)"
  ```
  If it doesn't print 200, stop and report.

## Background

The City's agenda item pages (secure.toronto.ca) reject automated downloads. The scheduled refresh switches to Toronto's Open Data API (CKAN, no key). Item pages stay supported only through pages saved from a browser (`refresh.py --html-dir`, which already exists).

## The API

Base URL: `https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/`

- `package_show?id=<dataset>` lists the dataset's resources. Use the one where `datastore_active` is true. For the voting record, use the one named `member-voting-record-2022-2026`.
- `datastore_search?id=<resource_id>&limit=1000&offset=N` returns rows. Keep paging until a page has fewer than 1000 rows.
- Pause 1 second between requests, use a 60-second timeout, and send the User-Agent `BeforeTheVote/0.3 (+https://github.com/The-John-Man/Before-The-Vote)`.

**Dataset `public-notices`** (refreshed daily, about 3,000 rows)
- Fields: `noticeId`, `title`, `noticeDate`, `noticeDescription`, `noticeHeadingType`, `eventList`, `contact`, `backgroundInformationList`, `addressList`, `otherReferenceList`, `topics`, `planningApplicationNumbers`, `signedBy`, `decisionBody`, `uniqueMapUrl`.
- `noticeDate` is epoch milliseconds stored as a string.
- `noticeDescription` is HTML holding the full notice text.
- These fields are JSON strings and need `json.loads`: `eventList`, `contact`, `backgroundInformationList` (`[{description, url}]`), `addressList` (`[{streetAddress, postalCode, latitudeCoordinate, longitudeCoordinate, ...}]`), `topics` (e.g. `["Meetings > Notice of meeting"]`), `planningApplicationNumbers`.
- Known example: the notice titled "...Request to Streamline Permit Parking Exclusions for New Developments" contains "please contact the Committee no later than 12:00 p.m. on Wednesday, June 10, 2026".

**Dataset `members-of-toronto-city-council-voting-record`**, resource `member-voting-record-2022-2026`
- One row per councillor per vote.
- Fields: `Term`, `First Name`, `Last Name`, `Committee`, `Date/Time`, `Agenda Item #`, `Agenda Item Title`, `Motion Type`, `Vote` (Yes / No / Absent ...), `Result` (e.g. "Carried, 7-0"), `Vote Description`.

## What to build

### 1. `pipeline/btv/opendata.py` (new)

- `fetch_rows(dataset, resource_name=None, fetch=requests.get)` returns all rows as a list of dicts. Pass in the fetch function so tests can replace it.
- `notice_text(html)` turns the HTML into plain text: one paragraph per line, entities and `&nbsp;` decoded, whitespace squeezed.
- `parse_notice(row)` returns:
  ```
  {id, title, date, body, topics, text, addresses: [{label, lat, lon}], application_numbers, documents: [{title, url}], contact}
  ```
  `date` is the Toronto date, `body` is `decisionBody`, `text` is `notice_text`.
- `group_votes(rows, item_ids)` returns `{item_id: [{committee, date, motion, result, yes, no, members}]}`. `yes` and `no` are the counts of `Vote == "Yes"` and `Vote == "No"`. `members` is a list of `{name, vote}`.
- Save a few real rows, trimmed, as `pipeline/tests/fixtures/notices.json` and `votes.json`. Tests never use the network.

### 2. Which notices become cards

- Take notices whose `noticeDate` is within the last 45 days and that also match one of these:
  - the title starts with "Notice of Public Meeting", "Notice of Application", "Notice of a request" or "Notice of Intention"
  - a `topics` entry starts with "Meetings"
- Keep at most 40 notice cards, newest first.
- Each notice card uses these files and fields:
  - Card id: `notice-<noticeId>`
  - Item file: `pipeline/items/notice-<noticeId>.json`
  - Snapshot: `pipeline/snapshots/notice-<noticeId>.txt`, with the same `#` header style and `notice_text` as the body
  - Document entry: `{"id":"n1","type":"notice","title":<title>,"url":<first backgroundInformationList url>,"snapshot":"snapshots/notice-<id>.txt","retrieved":<today>}`
- **Matching an existing item:** merge only if the existing item has an `application_numbers` list that shares a number with the notice. In that case, add the notice as an extra document and snapshot on that item. Otherwise the notice is its own card. If unsure, don't merge.
- Delete a notice card's files once the notice is older than 120 days and the card has no hand-written claims.

### 3. Facts filled by rules for a notice card

- `title_official` is the notice title. Leave `title_plain` empty; the build falls back to the official title.
- `topic` is the first `topics` entry, up to the first " > ".
- `place` is the first address: `{label: streetAddress, lat, lon, approx: false}`.
- `ward` comes from a point-in-polygon test of that lat/lon against `web/data/wards.txt`. Port `parseWards` and `pointInRing` from `web/js/geo.js` to `pipeline/btv/geo.py`. Add a test that 689 King Street West falls in Ward 10 Spadina-Fort York.
- `stages`:
  - always `{key:"notice", body:"staff", label:"City notice", date:<notice date>, can_speak:false}`
  - when a meeting is found (step 4), also `{key:"meeting", body:"committee", label:<decisionBody>, date:<meeting date>, can_speak:true}`
- `notice_excerpt` is the first sentence of the notice text that contains "propos", up to 300 characters, copied exactly.

### 4. Deadlines and meeting dates: proposed by rules, checked like everything else

- **Deadlines** (`pipeline/btv/extract.py`): find sentences in the notice text that contain "no later than", "deadline", or "by <time> on <date>". For each one:
  - create a claim: `{id:"r1", section:"say", text:"The City's notice gives this deadline to comment or ask to speak.", drafted_by:"rule", sources:[{doc:"n1", quote:<the exact sentence>}]}`
  - set `say.deadline`, as ISO with the time when the sentence states one
- **Meetings:** find a sentence that says when a committee or council will meet or consider the item. Create a meeting claim the same way, and set `say.meeting` and `say.meeting_claim`.
- `build_cards.py` checks these quotes and the deadline with the existing guards. Leave `verify.py` unchanged, and never derive a deadline from a meeting date.
- Change `facts_only` to mean "no verified claim in the sections what, why or changed", so rule claims in `say` don't count. Update `build_cards.py` and its test.

### 5. Votes from the Voting Record

- For every item whose id is an agenda item number (pattern `\d{4}\.[A-Z]+\d+\.\d+`, e.g. `2024.NY15.4`), attach `votes_from_record` = `group_votes(...)[id]`, along with the dataset name and the retrieval date.
- Leave the existing claim-backed `votes` as they are.
- Never turn "Carried" on "Adopt Item" into "approved". Item 2024.NY15.4 adopted a refusal.
- When a new vote appears, add the change note "A vote was recorded on <date> at <committee>: <motion>, <result>."

### 6. `pipeline/refresh.py`

- Add `--source opendata|tmmis`, defaulting to `opendata`. `tmmis` requires `--html-dir`.
- An opendata run:
  - fetches notices once and votes once
  - creates or updates notice cards
  - attaches votes to agenda items
  - keeps the current behaviour: change notes, writing files only when they change, hiding sentences that stop matching, `status.json`
- If the API fails, record the error in `status.json`, keep the last data, and exit 0.
- Add `"source"` (`"City open data"` or `"Saved City page"`) to each `status.json` entry.
- In `.github/workflows/refresh-and-publish.yml`, run `python refresh.py --source opendata`, and include deletions under `pipeline/items` and `pipeline/snapshots` in the commit.

### 7. Website

- **`board.js`**:
  - Open items first, soonest first, then at most 8 closed items and a "Show all decisions" button.
  - Next to the ward select, add a filter "Show: Everything / Only where I can still have a say".
- **`decision.js`**:
  - Show `notice_excerpt` on notice cards, in quotation marks, labelled "In the City's words".
  - Add a "Recorded votes" section from `votes_from_record`: one line per vote with committee, date, motion, result text and a yes/no bar. Add an expandable list of how each member voted, and a link to https://open.toronto.ca/dataset/members-of-toronto-city-council-voting-record/.
  - On a notice card, the official-page button opens the notice document URL.
- **`map.js`**: exact pins for places with `approx: false`; keep the "approximate" note for the others.
- **`method.js`**: one line per data source with its last retrieval (from `status.json`), and rule-drafted claims counted separately from the others.
- Keep the existing tokens in `styles.css`. Phone-first, keyboard reachable, no new JavaScript libraries.

### 8. Tests (no network)

Test each of these:
- `parse_notice` on the fixtures
- the notice selection rule
- the ward lookup for 689 King St W
- the deadline extractor finds the PH31.6 sentence, and the guard accepts 2026-06-10 12:00
- a notice that only gives a meeting date produces no deadline
- `group_votes` counts are correct
- a refresh with `--source opendata` and an injected fake fetch:
  - creates a notice card
  - writes nothing on a second, identical run
  - records an API error without crashing
- the new `facts_only` rule

All existing tests must still pass.

### 9. Docs

- **`README.md` "Live updates"**: a sources table with Public Notices (daily), the Voting Record, and saved item pages.
- **`docs/03-ARCHITECTURE.md`**: the component diagram, data sources, and known limits. Notices carry no agenda item numbers, so matching is by application number only.
- **`CREDITS.md`**: both datasets, under the Open Government Licence – Toronto, with retrieval dates.

## Rules

- No AI anywhere in fetching, selecting, matching, extracting, checking or writing change notes.
- Keep files small, with plain-language comments.

## When finished

1. Run `python refresh.py --source opendata` for real, then `python build_cards.py`.
2. Report:
   - how many notice cards were created
   - how many of them have a checked deadline
   - which items got votes, and how many each
   - any errors
3. Start the site (`cd web && python -m http.server 8000`) and list what to look at.
