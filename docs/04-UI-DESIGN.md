# Interface design

## Direction: transit wayfinding

A decision moves through fixed stops. Residents can only board at some of them, and missing the last one means there is nothing left to catch. That is a transit line. Station signage is also the most tested plain-language design that city residents already read every day, including people with limited English. The interface borrows three things from a station:

- **The departures board.** Home is a dark board of decisions ordered by time left to speak. The large yellow figure is the time left.
- **The line.** Each decision has a line of stops: staff report, committee, Council. Solid rail is travelled; dashed rail is still ahead. The next stop is a yellow dot, and carries a yellow tag when residents can speak there. Past stops are buttons: press one to see the decision as it stood then.
- **The network map.** Toronto's 25 wards drawn as a simple diagram. Tap your ward. Wards with decisions are tinted; a yellow dot marks a place where you can still have a say.

Everything else is quiet so those three carry the page. This is our own design language. It must not copy the TTC's logo, typeface or line colours.

Awwwards could not be read from the build environment (it returned only directory listings), so the direction comes from the subject, not from reference sites. Spend ten minutes there yourself for motion ideas; see "Motion" below for the one place motion belongs.

## Tokens

| Token | Value | Use |
|---|---|---|
| Paper | `#f3f6fa` | Page background, cool sign white |
| Ink | `#0e2038` | Text, the board, the Have your say panel |
| Rail | `#2b6ce6` | The line, focus rings, map hover |
| Signal | `#ffcb05` | Only for "you can act": time left, speak tag, open dot, main button, staff-recommendation label |
| Go | `#0a7a55` | Source buttons, "Decided by Council" |
| Stop | `#b93a1e` | Held-back sentences, test banner, "you are here" ring |
| Mute | `#55637a` | Secondary text |

Type: **Atkinson Hyperlegible** for reading (made by the Braille Institute so similar letters stay distinct) and **Bricolage Grotesque** for headings. Base size 18 px. Lines under about 62 characters.

## Screens

| Screen | Address | What is on it |
|---|---|---|
| Board | `#/` | Headline question, ward list and "use my location", ward map, departures board, calendar feed link |
| Decision | `#/d/<id>` | Status label, plain title, official title, Decision Line, lenses, sections (what is proposed; why and on what conditions; what changed along the way; how they voted; what the public sent in; what the record does not say), Have your say panel |
| Source pop-up | on any Source button | The plain sentence, the City's exact words on a yellow strip, document, date copied, link |
| Notice | `#/poster/<id>` | One printable page: what, where, status, the date to act in a yellow box, addresses |
| How we check | `#/method` | The four steps, live counts, limits, and a table of every sentence with what was held back |

On a phone the Have your say panel moves to the top and the line turns vertical.

## Words

- Sentence case. Plain twins for jargon: "deputation" becomes "speak to the committee".
- Buttons say what happens: "Add this date to my calendar", "Send this to a neighbour".
- Never "should", "good" or "bad" about a decision.
- The status label states the level and what has not happened yet: "City staff recommend approval, with a condition. Nothing is decided yet."
- Empty and error states tell the reader what to do next.

## Motion

Not built. One moment only would earn its place: on opening a decision, the rail draws from the first stop to the current one in about 600 ms. Respect `prefers-reduced-motion`. No scroll effects or card hover animations.

## Accessibility checklist

- [ ] Every action reachable and visible with the keyboard alone, including each ward on the map (Tab, then Enter or Space)
- [ ] Source pop-up traps focus and closes with Esc (native `<dialog>`; confirm)
- [ ] Screen reader announces time left, the status label and each stop in order
- [ ] Colour is never the only signal: open and closed differ by words; travelled and ahead differ by solid and dashed rail
- [ ] Text contrast at least 4.5:1. Yellow is only ever a background for navy text
- [ ] Usable at 200% zoom and at 320 px width
- [ ] French sentences carry `lang="fr"`; quotes stay `lang="en"`
- [ ] Read aloud works in the browser you will demo in (voices differ by device)
- [ ] Printed notice fits one page
