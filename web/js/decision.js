// decision.js — one decision, explained.
//
// What is on the screen, top to bottom:
//   status line        how decided is it (staff / committee / Council)
//   Decision Line      the stops this item passes through. Press a past stop to
//                      replay the page as it stood on that day.
//   lenses             "I rent", "I drive"... brings matching sentences forward
//   sections           plain sentences, each with a Source button
//   votes, public input, and what the record does not say
//   Have your say      countdown, official link, calendar, print, share

import { state } from "./state.js";
import { esc, statusAt, actBy, shownClaims, claimText, lastCheck } from "./util.js";
import { formatWhen, reached, endOfDay } from "./time.js";
import { downloadReminder } from "./ics.js";
import { canSpeak, toggleSpeech } from "./speak.js";

const SECTIONS = [
  { key: "what", heading: "What is proposed" },
  { key: "why", heading: "Why, and on what conditions" },
  { key: "changed", heading: "What changed along the way" },
];

let replay = null;      // { id, at, label } when the resident is looking at a past stop
let speaking = false;

// The moment the page describes: a replayed stop, or today.
function viewTime(decision) {
  return replay && replay.id === decision.id ? replay.at : state.now;
}

function line(decision, at) {
  const next = decision.stages.find((s) => s.date && !reached(s.date, state.now));
  const stops = decision.stages.map((s) => {
    const done = reached(s.date, at);
    const isNext = s === next && at === state.now;
    const canReplay = reached(s.date, state.now); // only real past stops can be replayed
    const result = done && s.result ? s.result : done ? "Done" : s.date ? "Coming up" : "Date not set";
    const inner = `
      <span class="dot" aria-hidden="true"></span>
      <strong>${esc(s.label)}</strong>
      <span class="stop-date">${s.date ? esc(formatWhen(s.date)) : "Date not set"}</span>
      <span class="stop-state">${esc(result.charAt(0).toUpperCase() + result.slice(1))}</span>
      ${s.can_speak && isNext ? `<span class="speak-tag">You can speak at this stop</span>` : ""}
      ${s.can_speak && !isNext ? `<span class="stop-note">Residents could speak here</span>` : ""}`;
    const classes = `stop ${done ? "is-done" : "is-ahead"} ${isNext ? "is-next" : ""} ${s.can_speak && isNext ? "window-open" : ""}`;
    return canReplay
      ? `<li class="${classes}"><button class="stop-btn" data-replay="${esc(s.key)}"
           aria-label="Show this decision as it stood after: ${esc(s.label)}">${inner}</button></li>`
      : `<li class="${classes}"><div class="stop-btn">${inner}</div></li>`;
  });
  return `<ol class="line" aria-label="The stops this decision passes through">${stops.join("")}</ol>`;
}

function sourceButton(claimId, onDark = false) {
  return `<button class="source-btn ${onDark ? "is-on-dark" : ""}" data-claim="${esc(claimId)}">Source</button>`;
}

function sentence(claim) {
  const lensHit = state.lens && claim.lenses?.includes(state.lens);
  return `<p class="claim ${lensHit ? "is-lens" : ""}" ${state.lang === "fr" && claim.fr ? 'lang="fr"' : ""}>
    ${esc(claimText(claim, state.lang))} ${sourceButton(claim.id)}</p>`;
}

function lensChips(claims) {
  const used = state.data.lenses.filter((lens) => claims.some((c) => c.lenses?.includes(lens.key)));
  if (!used.length) return "";
  return `
    <div class="lenses" role="group" aria-label="Bring forward what matters to you">
      <span>Show what matters if</span>
      ${used.map((lens) => `<button class="chip ${state.lens === lens.key ? "is-on" : ""}" data-lens="${esc(lens.key)}"
          aria-pressed="${state.lens === lens.key}">${esc(lens.label)}</button>`).join("")}
      <small>Your choice stays on this device.</small>
    </div>`;
}

function votes(decision, at) {
  const shown = decision.votes.filter((v) => reached(decision.stages.find((s) => s.key === v.stage)?.date, at));
  if (!shown.length) return "";
  return `
    <section><h2>How they voted</h2>
      <ul class="votes">
        ${shown.map((v) => {
          const stage = decision.stages.find((s) => s.key === v.stage);
          const counted = v.yes !== null && v.no !== null;
          const share = counted ? Math.round((v.yes / (v.yes + v.no)) * 100) : 0;
          return `<li>
            <strong>${esc(stage.label)}: ${esc(v.motion)}</strong>
            ${counted
              ? `<span class="vote-bar" aria-hidden="true"><span style="width:${share}%"></span></span>
                 <span>${esc(v.result)}. ${v.yes} yes, ${v.no} no.</span>`
              : `<span>${esc(v.result)}. The record shows no count for this vote.</span>`}
            ${sourceButton(v.claim)}
          </li>`;
        }).join("")}
      </ul>
    </section>`;
}

function heard(decision, at) {
  const shown = decision.heard.filter((h) => reached(decision.stages.find((s) => s.key === h.stage)?.date, at));
  if (!shown.length) return "";
  return `
    <section><h2>What the public sent in</h2>
      <ul>
        ${shown.map((h) => {
          const stage = decision.stages.find((s) => s.key === h.stage);
          const parts = [h.written === 1 ? "1 letter or e-mail" : `${h.written} letters or e-mails`];
          if (h.speakers !== null) parts.push(h.speakers === 1 ? "1 person spoke" : `${h.speakers} people spoke`);
          return `<li>${esc(stage.label)}: ${esc(parts.join(", "))}.</li>`;
        }).join("")}
      </ul>
      <p class="small-note">${esc(decision.heard_note ?? "")}
        <a href="${esc(decision.official_url)}" target="_blank" rel="noopener">Read them on the official page</a>.</p>
    </section>`;
}

// What changed on the City's page recently, written by refresh.py from plain rules.
function updates(decision) {
  if (!decision.updates?.length) return "";
  return `
    <section class="updates">
      <h2>What changed recently</h2>
      <ul>${decision.updates.slice(0, 3).map((u) =>
        `<li><strong>${esc(formatWhen(u.date))}.</strong> ${u.notes.map(esc).join(" ")}</li>`).join("")}</ul>
    </section>`;
}

const isNotice = (decision) => decision.id.startsWith("notice-");

// A card with no checked explanation yet. Say so plainly, then give what rules could read.
function factsOnly(decision) {
  if (!decision.facts_only) return "";
  const read = isNotice(decision)
    ? "straight from the City's public notice (City open data) by fixed rules, without AI: the dates, the address and ward, and the deadline when the notice gives one"
    : "straight from the City's page by fixed rules, without AI: the stops, dates, ward, documents and how many people wrote in or spoke";
  return `
    <section class="facts-only">
      <h2>The plain-language explanation is not written yet</h2>
      <p>No sentence explaining this item has been written and checked yet. Everything on this page was read ${read}.</p>
    </section>`;
}

// The City's own sentence about what is proposed, copied exactly and never shortened.
function noticeExcerpt(decision) {
  if (!decision.notice_excerpt) return "";
  const doc = decision.documents.find((d) => d.type === "notice");
  return `
    <section><h2>In the City's words</h2>
      <blockquote lang="en">“${esc(decision.notice_excerpt)}”</blockquote>
      ${doc ? `<p class="small-note">From the City's public notice, copied ${esc(formatWhen(doc.retrieved))}.
        <a href="${esc(doc.url)}" target="_blank" rel="noopener">Open the notice</a></p>` : ""}
    </section>`;
}

// Votes from the City's open voting record: counts only, and the City's own words for
// the motion and the result. "Carried" on "Adopt Item" can mean a refusal was adopted
// (1875 Steeles), so we never turn it into "approved".
function recordedVotes(decision, at) {
  const record = decision.votes_from_record;
  const shown = (record?.motions ?? []).filter((m) => reached(m.date, at));
  if (!shown.length) return "";
  return `
    <section><h2>Recorded votes (City open data)</h2>
      <ul class="votes">
        ${shown.map((m) => {
          const counted = m.yes + m.no > 0;
          const share = counted ? Math.round((m.yes / (m.yes + m.no)) * 100) : 0;
          return `<li>
            <strong>${esc(m.committee)}, ${esc(formatWhen(m.date))}: ${esc(m.motion)}</strong>
            ${counted ? `<span class="vote-bar" aria-hidden="true"><span style="width:${share}%"></span></span>` : ""}
            <span>${esc(m.result)}. ${m.yes} yes, ${m.no} no.</span>
          </li>`;
        }).join("")}
      </ul>
      <p class="small-note">Motion and result in the City's words, counted from the
        <a href="https://open.toronto.ca/dataset/members-of-toronto-city-council-voting-record/" target="_blank" rel="noopener">Members of Toronto City Council voting record</a>,
        copied ${esc(formatWhen(record.retrieved))}. "Carried" means the motion passed, not that the proposal was approved:
        check what the motion said on the official record.</p>
    </section>`;
}

function documentList(decision) {
  const docs = decision.documents.filter((d) => d.type !== "guidance" && d.type !== "item_page");
  if (!docs.length) return "";
  return `
    <section><h2>Documents on the City's page</h2>
      <ul>${docs.map((d) => `<li><a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.title)}</a></li>`).join("")}</ul>
    </section>`;
}

function sayPanel(decision) {
  const act = actBy(decision, state.now); // always today: you cannot act in the past
  const guidance = decision.claims.find((c) => c.id === decision.say.guidance_claim && c.verified);
  const sourceId = decision.say.deadline_claim ?? decision.say.meeting_claim;
  return `
    <aside class="say ${act.open ? "" : "is-closed"}" aria-label="Have your say">
      <h2>Have your say</h2>
      <p class="say-big">${esc(act.big)}</p>
      <p class="say-small">${esc(act.small)}</p>
      ${act.value ? `<p>${act.kind === "deadline" ? "Deadline in the City's notice" : "Meeting"}:
        <strong>${esc(formatWhen(act.value))}</strong> ${sourceId ? sourceButton(sourceId, true) : ""}
        ${decision.say.meeting_from === "page" && act.kind === "meeting" ? `<br><small>Date as listed on the City's page. The time is not posted.</small>` : ""}</p>` : ""}
      ${act.open && guidance ? `<p class="say-guidance">${esc(claimText(guidance, state.lang))} ${sourceButton(guidance.id, true)}</p>` : ""}
      ${act.open ? `<ul>${decision.say.methods.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>` : ""}
      <a class="btn" href="${esc(decision.official_url)}" target="_blank" rel="noopener">
        ${isNotice(decision)
          ? (act.open ? "Open the City's notice to see how to comment or speak" : "Open the City's notice")
          : (act.open ? "Open the official page to comment or ask to speak" : "Open the official record")}</a>
      ${act.open ? `<button class="btn btn-quiet" id="remind">Add this date to my calendar</button>` : ""}
      <a class="btn btn-quiet" href="#/poster/${encodeURIComponent(decision.id)}">Make a notice to print</a>
      <button class="btn btn-quiet" id="share">Send this to a neighbour</button>
      <p class="say-privacy" id="share-note">${act.open
        ? "Good to know: if you write or speak to a committee, the City publishes your name with the item, and search engines may list it."
        : "The time to comment on this item has passed."}</p>
    </aside>`;
}

function openReceipt(decision, claimId) {
  const claim = decision.claims.find((c) => c.id === claimId);
  if (!claim) return;
  document.getElementById("receipt-body").innerHTML = `
    <p class="receipt-claim">${esc(claimText(claim, state.lang))}</p>
    ${state.lang === "fr" && claim.fr ? `<p class="small-note">Traduction automatique, non révisée. The City's words below stay in English.</p>` : ""}
    ${claim.sources.map((source) => {
      const doc = decision.documents.find((d) => d.id === source.doc);
      return `
        <div class="receipt-source">
          <blockquote lang="en">${esc(source.quote)}</blockquote>
          <p>${esc(doc.title)}. Copied ${esc(doc.retrieved)}.
            An automatic check found these exact words in the record.</p>
          <p><a href="${esc(doc.url)}" target="_blank" rel="noopener">Open the record</a></p>
        </div>`;
    }).join("")}`;
  document.getElementById("receipt").showModal();
}

async function share(decision) {
  const act = actBy(decision, state.now);
  const text = `${decision.title_plain}. ${statusAt(decision, state.now).text}`
    + (act.open ? ` ${act.kind === "deadline" ? "Comment by" : "Meeting on"} ${formatWhen(act.value)}.` : "");
  const note = document.getElementById("share-note");
  try {
    if (navigator.share) await navigator.share({ title: "Before the Vote", text, url: location.href });
    else { await navigator.clipboard.writeText(text + " " + location.href); note.textContent = "Copied. Paste it into a text or e-mail."; }
  } catch { note.textContent = "Could not share from this browser. Copy the address at the top of the page instead."; }
}

export function renderDecision(view, decision) {
  if (replay && replay.id !== decision.id) replay = null;
  const at = viewTime(decision);
  const status = statusAt(decision, at);
  const claims = shownClaims(decision, at);
  const hasFrench = decision.claims.some((c) => c.fr);
  const check = lastCheck(decision);

  view.innerHTML = `
    <article class="decision">
      <div class="toolbar">
        <a class="back" href="#/">All decisions</a>
        <span class="tools">
          ${hasFrench ? `<button class="btn-plain" id="lang">${state.lang === "fr" ? "English" : "Français"}</button>` : ""}
          ${canSpeak ? `<button class="btn-plain" id="speak" aria-pressed="${speaking}">${speaking ? "Stop reading" : "Read this aloud"}</button>` : ""}
        </span>
      </div>

      ${replay ? `<p class="replay-note">You are seeing this decision as it stood after: <strong>${esc(replay.label)}</strong>.
        <button class="btn-plain" id="today">Back to today</button></p>` : ""}

      <p class="status level-${status.level}">${esc(status.text)}</p>
      <h1>${esc(decision.title_plain)}</h1>
      <p class="official">Official title: ${esc(decision.title_official)}
        (${isNotice(decision) ? `City notice ${esc(decision.notice_id)}` : `item ${esc(decision.id)}`}).
        ${decision.place ? `${esc(decision.place.label)}${decision.place.approx !== false ? " (approximate location)" : ""}, ` : ""}${decision.ward
          ? `Ward ${Number(decision.ward.code)} ${esc(decision.ward.name)}`
          : isNotice(decision) ? "Ward not known" : "All of Toronto"}.</p>
      ${check ? `<p class="checked ${check.ok ? "" : "is-stale"}">${esc(check.text)}</p>` : ""}
      ${decision.claims.some((c) => c.ai_drafted && c.verified)
        ? `<p class="official">The plain-language sentences were drafted by AI. Each one was checked word for word against the City's ${isNotice(decision) ? "notice" : "page"}: use its Source button to see the City's words.</p>` : ""}

      ${line(decision, at)}
      <p class="line-hint">Press a stop that has passed to see what was known then.</p>

      <div class="decision-grid">
        <div class="decision-main">
          ${factsOnly(decision)}
          ${noticeExcerpt(decision)}
          ${updates(decision)}
          ${lensChips(claims)}
          ${SECTIONS.map((section) => {
            const list = claims.filter((c) => c.section === section.key);
            return list.length ? `<section><h2>${section.heading}</h2>${list.map(sentence).join("")}</section>` : "";
          }).join("")}
          ${votes(decision, at)}
          ${recordedVotes(decision, at)}
          ${heard(decision, at)}
          ${documentList(decision)}
          ${decision.unknowns.length ? `<section class="unknowns">
            <h2>What the record does not say</h2>
            <ul>${decision.unknowns.map((u) => `<li>${esc(u)}</li>`).join("")}</ul>
          </section>` : ""}
        </div>
        ${sayPanel(decision)}
      </div>
    </article>`;

  const again = () => renderDecision(view, decision);
  view.querySelectorAll("[data-claim]").forEach((b) => b.addEventListener("click", () => openReceipt(decision, b.dataset.claim)));
  view.querySelectorAll("[data-lens]").forEach((b) => b.addEventListener("click", () => {
    state.lens = state.lens === b.dataset.lens ? null : b.dataset.lens; again();
  }));
  view.querySelectorAll("[data-replay]").forEach((b) => b.addEventListener("click", () => {
    const stage = decision.stages.find((s) => s.key === b.dataset.replay);
    replay = { id: decision.id, at: endOfDay(stage.date), label: stage.label }; again();
  }));
  document.getElementById("today")?.addEventListener("click", () => { replay = null; again(); });
  document.getElementById("lang")?.addEventListener("click", () => { state.lang = state.lang === "fr" ? "en" : "fr"; again(); });
  document.getElementById("speak")?.addEventListener("click", () => {
    const text = [decision.title_plain, status.text, ...claims.filter((c) => c.section !== "vote").map((c) => claimText(c, state.lang))];
    toggleSpeech(text, state.lang, (on) => { speaking = on; const b = document.getElementById("speak"); if (b) { b.textContent = on ? "Stop reading" : "Read this aloud"; b.setAttribute("aria-pressed", on); } });
  });
  document.getElementById("remind")?.addEventListener("click", () => downloadReminder(decision, actBy(decision, state.now)));
  document.getElementById("share").addEventListener("click", () => share(decision));
}
