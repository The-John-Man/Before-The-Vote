// board.js — the first screen: ward map plus a departures board.
// A station board sorts trains by departure time. This sorts decisions by how
// long residents still have to speak, and can narrow to one ward.

import { state } from "./state.js";
import { esc, statusAt, actBy, recentUpdate } from "./util.js";
import { formatWhen } from "./time.js";
import { wardAt, distanceKm } from "./geo.js";
import { mapSvg, wireMap } from "./map.js";

// City-wide decisions (ward = null) always show, whichever ward is picked.
function inPickedWard(decision) {
  return !state.ward || !decision.ward || decision.ward.code === state.ward;
}

function whereText(decision) {
  if (!decision.ward) return "All of Toronto";
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
    decision.facts_only ? `<span class="board-flag">Facts only. Explanation being written</span>` : "",
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

export function renderBoard(view) {
  const { data, wards, now } = state;
  const open = (d) => actBy(d, now).open;
  const decisions = data.decisions.filter(inPickedWard).sort((a, b) => {
    if (open(a) !== open(b)) return open(a) ? -1 : 1;                      // open ones first
    const A = new Date(a.say.deadline ?? a.say.meeting ?? 0), B = new Date(b.say.deadline ?? b.say.meeting ?? 0);
    return open(a) ? A - B : B - A;                                        // soonest first; then most recent
  });
  const openIds = new Set(data.decisions.filter(open).map((d) => d.id));
  const picked = wards.find((w) => w.code === state.ward);

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
        <figcaption>Yellow dot: you can still have a say. Grey dot: closed. Ward outlines are simplified.</figcaption>
      </figure>
    </section>

    <section class="board" aria-label="Decisions, soonest chance to speak first">
      <div class="board-head" aria-hidden="true"><span>Time left</span><span>Decision</span><span>Where it stands</span></div>
      <ol class="board-list">
        ${decisions.map(row).join("") || `<li class="board-empty">No decisions are loaded for this ward yet. Choose "All of the city" to see the rest.</li>`}
      </ol>
      <p class="board-foot">
        <a href="data/calendar.ics">Add every open date to my calendar</a>
        <span>${state.status
          ? `Checked against the City's pages ${esc(formatWhen(state.status.checked_at))}`
          : `Updated ${esc(formatWhen(data.generated_at.slice(0, 10)))}`}</span>
      </p>
    </section>`;

  const pick = (code) => { state.ward = code === state.ward ? null : code || null; renderBoard(view); };
  document.getElementById("ward").addEventListener("change", (e) => { state.ward = e.target.value || null; renderBoard(view); });
  document.getElementById("locate").addEventListener("click", () => locate(view));
  wireMap(view, pick);
}
