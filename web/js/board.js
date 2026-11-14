// board.js — the first screen: ward map plus a departures board.
// A station board sorts trains by departure time. This sorts decisions by how
// long residents still have to speak, and can narrow to one ward.

import { state } from "./state.js";
import { esc, statusAt, actBy, recentUpdate } from "./util.js";
import { formatWhen, toDate } from "./time.js";
import { wardAt, distanceKm } from "./geo.js";
import { mapSvg, wireMap } from "./map.js";

// City-wide decisions (ward = null) always show, whichever ward is picked.
function inPickedWard(decision) {
  if (!state.ward) return true;
  // A notice whose address could not be placed is not city-wide: show it only under "All of the city".
  if (!decision.ward) return !decision.id.startsWith("notice-");
  return decision.ward.code === state.ward;
}

function whereText(decision) {
  // A notice with no ward is not city-wide: its address could not be placed safely.
  if (!decision.ward) return decision.id.startsWith("notice-") ? "Ward not known" : "All of Toronto";
  const place = decision.place ? decision.place.label + ", " : "";
  let text = `${place}Ward ${Number(decision.ward.code)} ${decision.ward.name}`;
  if (state.me && decision.place) {
    text += `, about ${distanceKm(state.me, decision.place).toFixed(1)} km from you`;
  }
  return text;
}

function row(decision) {
  const act = actBy(decision, state.now);
  const status = statusAt(decision, state.now);
  const update = recentUpdate(decision, state.now);
  const flags = [
    update ? `<span class="board-flag is-new">Updated ${esc(formatWhen(update.date))}</span>` : "",
    decision.facts_only ? `<span class="board-flag">Facts only. No explanation yet</span>` : "",
  ].join("");
  return `
    <li>
      <a class="board-row ${act.open ? "is-open" : "is-closed"}" href="#/d/${encodeURIComponent(decision.id)}">
        <span class="board-time"><strong>${esc(act.big)}</strong><small>${esc(act.small)}</small></span>
        <span class="board-what">
          <strong>${esc(decision.title_plain)}</strong>
          <small>${esc(decision.topic)}. ${esc(whereText(decision))}</small>
          ${flags ? `<span class="board-flags">${flags}</span>` : ""}
        </span>
        <span class="board-stage level-${status.level}">${esc(status.short)}</span>
      </a>
    </li>`;
}

// Ask the device where it is. The answer is used in this tab only.
function locate(view) {
  const note = document.getElementById("locate-note");
  if (!navigator.geolocation) { note.textContent = "This device cannot share a location. Pick your ward instead."; return; }
  note.textContent = "Finding you…";
  navigator.geolocation.getCurrentPosition(
    (position) => {
      state.me = { lat: position.coords.latitude, lon: position.coords.longitude };
      const ward = wardAt(state.me.lon, state.me.lat, state.wards);
      state.ward = ward ? ward.code : null;
      renderBoard(view);
      if (!ward) document.getElementById("locate-note").textContent = "You seem to be outside Toronto. Showing every decision.";
    },
    () => { note.textContent = "Location was not shared. Pick your ward on the map or in the list."; }
  );
}

// The latest date we know for a decision: its date to act, or else its latest stop.
function latestDate(decision) {
  const dates = [decision.say.deadline, decision.say.meeting, ...decision.stages.map((s) => s.date)].filter(Boolean);
  return dates.length ? Math.max(...dates.map((d) => toDate(d).getTime())) : 0;
}

const CLOSED_SHOWN = 8;   // closed decisions shown before "Show all decisions"

// Open decisions first, the soonest to close at the top. Then the most recent closed ones.
function boardList(decisions, now) {
  const when = (d) => toDate(d.say.deadline ?? d.say.meeting).getTime();
  const open = decisions.filter((d) => actBy(d, now).open).sort((a, b) => when(a) - when(b));
  const closed = decisions.filter((d) => !actBy(d, now).open).sort((a, b) => latestDate(b) - latestDate(a));
  if (state.onlyOpen) return { rows: open, hidden: 0 };
  const shown = state.showAll ? closed : closed.slice(0, CLOSED_SHOWN);
  return { rows: [...open, ...shown], hidden: closed.length - shown.length };
}

export function renderBoard(view) {
  const { data, wards, now } = state;
  const { rows, hidden } = boardList(data.decisions.filter(inPickedWard), now);
  const openIds = new Set(data.decisions.filter((d) => actBy(d, now).open).map((d) => d.id));
  const picked = wards.find((w) => w.code === state.ward);
  const empty = state.onlyOpen
    ? "Nothing open for comment here right now. Choose Everything to see past decisions."
    : `No decisions are loaded for this ward yet. Choose "All of the city" to see the rest.`;
  const checked = state.status
    ? `Checked against ${state.status.source === "tmmis" ? "saved City pages" : "City open data"} ${formatWhen(state.status.checked_at)}`
    : `Updated ${formatWhen(data.generated_at.slice(0, 10))}`;

  view.innerHTML = `
    <section class="hero">
      <div class="hero-text">
        <h1>What is ${esc(data.municipality.short)} deciding, and can you still have a say?</h1>
        <p class="lede">Each decision is explained in plain language, with the date your chance to speak runs out
          and the City's own words behind every sentence.</p>
        <div class="near">
          <label>My ward
            <select id="ward">
              <option value="">All of the city</option>
              ${wards.map((w) => `<option value="${esc(w.code)}" ${w.code === state.ward ? "selected" : ""}>${Number(w.code)} ${esc(w.name)}</option>`).join("")}
            </select>
          </label>
          <button class="btn-plain" id="locate">Use my location</button>
          <p class="near-note" id="locate-note">${picked ? `Showing Ward ${Number(picked.code)} ${esc(picked.name)} and city-wide decisions.` : "Your location stays on this device. It is never sent or saved."}</p>
        </div>
      </div>
      <figure class="hero-map">
        ${mapSvg(wards, data.decisions, openIds)}
        <figcaption>Yellow: you can still have a say. Grey: closed. A dot is the exact address in the City's data;
          a ring is an approximate location. Ward outlines are simplified.</figcaption>
      </figure>
    </section>

    <section class="board" aria-label="Decisions, soonest chance to speak first">
      <div class="board-filter" role="group" aria-label="Which decisions to show">
        <span>Show:</span>
        <button class="chip ${state.onlyOpen ? "" : "is-on"}" data-only-open="no" aria-pressed="${!state.onlyOpen}">Everything</button>
        <button class="chip ${state.onlyOpen ? "is-on" : ""}" data-only-open="yes" aria-pressed="${state.onlyOpen}">Only where I can still have a say</button>
      </div>
      <div class="board-head" aria-hidden="true"><span>Time left</span><span>Decision</span><span>Where it stands</span></div>
      <ol class="board-list">
        ${rows.map(row).join("") || `<li class="board-empty">${esc(empty)}</li>`}
      </ol>
      ${hidden ? `<p class="board-more"><button class="btn-plain" id="show-all">Show all decisions (${hidden} more)</button></p>` : ""}
      <p class="board-foot">
        <a href="data/calendar.ics">Add every open date to my calendar</a>
        <span>${esc(checked)}</span>
      </p>
    </section>`;

  const pick = (code) => { state.ward = code === state.ward ? null : code || null; renderBoard(view); };
  document.getElementById("ward").addEventListener("change", (e) => { state.ward = e.target.value || null; renderBoard(view); });
  document.getElementById("locate").addEventListener("click", () => locate(view));
  view.querySelectorAll("[data-only-open]").forEach((b) => b.addEventListener("click", () => {
    state.onlyOpen = b.dataset.onlyOpen === "yes";
    renderBoard(view);
    view.querySelector(`[data-only-open="${b.dataset.onlyOpen}"]`).focus();   // keep the keyboard where it was
  }));
  document.getElementById("show-all")?.addEventListener("click", () => {
    state.showAll = true;
    renderBoard(view);
    view.querySelectorAll(".board-row")[rows.length]?.focus();   // the first row that was hidden
  });
  wireMap(view, pick);
}
