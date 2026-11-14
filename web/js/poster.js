// poster.js — a one-page notice to print and pin up in a lobby, laundry room,
// library or shop window. A website alone misses neighbours who are offline;
// a sheet of paper does not.

import { state } from "./state.js";
import { esc, statusAt, actBy, shownClaims } from "./util.js";
import { formatWhen } from "./time.js";

export function renderPoster(view, decision) {
  const act = actBy(decision, state.now);
  const status = statusAt(decision, state.now);
  const main = shownClaims(decision, state.now).filter((c) => c.section === "what").slice(0, 2);
  const pageAddress = location.href.replace("#/poster/", "#/d/");

  view.innerHTML = `
    <div class="poster-tools">
      <a class="back" href="#/d/${encodeURIComponent(decision.id)}">Back to the decision</a>
      <button class="btn-plain" id="print">Print this notice</button>
    </div>
    <article class="poster">
      <p class="poster-kicker">The City of ${esc(state.data.municipality.short)} is deciding</p>
      <h1>${esc(decision.title_plain)}</h1>
      <p class="poster-where">${decision.place ? esc(decision.place.label) + ". " : ""}${decision.ward ? `Ward ${Number(decision.ward.code)} ${esc(decision.ward.name)}`
        : decision.id.startsWith("notice-") ? "See the City's notice for the location" : "All of Toronto"}</p>
      ${main.map((c) => `<p class="poster-text">${esc(c.text)}</p>`).join("")}
      <p class="poster-status">${esc(status.text)}</p>
      ${act.open ? `
        <div class="poster-act">
          <p>${act.kind === "deadline" ? "You can have a say until" : "You can have a say before the meeting on"}</p>
          <p class="poster-date">${esc(formatWhen(act.value))}</p>
          <p>${esc(decision.say.methods.join(". "))}.${decision.say.contact_email ? ` E-mail ${esc(decision.say.contact_email)}` : ""}</p>
        </div>` : `<div class="poster-act"><p>The time to comment has passed.</p></div>`}
      <p class="poster-foot">Plain-language explanation with sources: ${esc(pageAddress)}<br>
        Official record: ${esc(decision.official_url)}<br>
        Summary drafted with AI and checked against the City's record. The official record is the authority.
        Printed from data updated ${esc(state.data.generated_at.slice(0, 10))}.</p>
    </article>`;
  document.getElementById("print").addEventListener("click", () => window.print());
}
