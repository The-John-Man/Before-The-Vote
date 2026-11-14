// method.js — "How we check". Two jobs:
//   1. tell residents plainly what AI did and did not do here, with live numbers
//   2. give staff the full list of sentences, including any that were held back

import { state } from "./state.js";
import { esc } from "./util.js";
import { formatWhen } from "./time.js";

const READ = { notice: "Read the notice", votes: "Read the voting record", page: "Read the saved page" };

// Where our data comes from, and when each source was last read (from status.json).
function dataSources() {
  const sources = Object.values(state.status?.sources ?? {});
  const line = (s) => `<li><strong>${esc(s.name)}</strong> (<a href="${esc(s.url)}" target="_blank" rel="noopener">source</a>):
    ${s.ok ? `last read ${esc(formatWhen(s.checked_at))}${s.rows !== null ? `, ${s.rows} rows` : ""}.`
           : `could not be read ${esc(formatWhen(s.checked_at))} (${esc(s.error)}). The last data that worked is shown.`}</li>`;
  return `
    <h2>Where the facts come from</h2>
    <ul>
      ${sources.length ? sources.map(line).join("") : `<li>No automatic check has run on this copy of the site yet.</li>`}
    </ul>
    <p class="small-note">City open data: the City of Toronto's Open Data portal, which is built for programs and needs no key.
      Item pages on secure.toronto.ca block automated downloads, so we only use copies a person saved from their own browser.</p>`;
}

// One row per tracked item: when its record was last read, and what changed.
function checks() {
  const items = state.status?.items;
  if (!items) return "";
  const rows = state.data.decisions.map((d) => {
    const check = items[d.id];
    const latest = d.updates?.[0];
    return `<tr class="${check && !check.ok ? "needs-check" : ""}">
      <td>${esc(d.id)}</td>
      <td>${check ? esc(formatWhen(check.checked_at)) : "Not checked"}</td>
      <td>${check?.ok ? esc(READ[check.checked] ?? "Read the page") : esc(check?.error ?? "")}</td>
      <td>${latest ? `${esc(formatWhen(latest.date))}: ${latest.notes.map(esc).join(" ")}` : "No change noted"}</td>
    </tr>`;
  }).join("");
  return `
    <h2>Automatic checks against the City's record</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Item</th><th>Last checked</th><th>Result</th><th>Latest change</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

export function renderMethod(view) {
  const all = state.data.decisions.flatMap((d) => d.claims.map((c) => ({ ...c, item: d.id })));
  const written = all.filter((c) => c.drafted_by !== "rule");     // by an AI model or a person
  const byRule = all.filter((c) => c.drafted_by === "rule");      // deadlines and meetings read by fixed rules
  const held = written.filter((c) => !c.verified);
  const ruleHeld = byRule.filter((c) => !c.verified);
  const quotes = all.flatMap((c) => c.sources).length;

  const rows = all.map((c) => `
    <tr class="${c.verified ? "" : "needs-check"}">
      <td>${esc(c.item)}</td>
      <td>${esc(c.text)}${c.planted ? ` <em>(Planted on purpose to test the check.)</em>` : ""}</td>
      <td>${c.sources.map((s) => `“${esc(s.quote)}” ${s.verified ? "" : "<strong>Not found in the record.</strong>"}`).join("<br>")}</td>
      <td>${c.verified ? "Shown" : "Held back"}${c.drafted_by === "rule" ? "<br><small>Read by rules</small>" : ""}</td>
    </tr>`).join("");

  view.innerHTML = `
    <section class="method">
      <h1>How we check what you read here</h1>
      <p class="lede">A summary that gets a decision wrong is worse than no summary. So nothing reaches a resident on trust.</p>

      <ol class="steps">
        <li><strong>Copy the record.</strong> We save the words of the City's public notice (from City open data) or of an item page a person saved, with the date we copied them.</li>
        <li><strong>Draft.</strong> An AI model or a staff member writes each plain sentence and must paste the exact words from the record that back it up.
          Deadlines and meeting dates in notices are read by fixed rules instead, which also keep the City's exact sentence.</li>
        <li><strong>Check, without AI.</strong> A short program looks for those exact words in the saved record. If they are not there, the sentence is held back. A deadline is shown only when its date is written in the record. It is never worked out from a meeting date.</li>
        <li><strong>Show the proof.</strong> Every sentence has a Source button with the City's words and a link.</li>
      </ol>

      <p class="tally"><strong>${written.length - held.length} of ${written.length}</strong> written sentences passed and are shown.
        <strong>${held.length}</strong> held back. Separately, <strong>${byRule.length - ruleHeld.length} of ${byRule.length}</strong>
        deadline and meeting sentences read by rules passed. <strong>${quotes}</strong> quotes checked across
        <strong>${state.data.decisions.length}</strong> real decisions.</p>

      <h2>What this does not do</h2>
      <ul>
        <li>The check proves the quoted words exist. It cannot prove a sentence is a fair or complete reading of them. A person should still review each one.</li>
        <li>These pages are not the official record. If they differ from the City's page, the City's page is right.</li>
        <li>Records are copied on a date. A scheduled job reads City open data again every few hours and re-runs the check; each decision shows when it was last checked. Between checks, the City's record may already have changed.</li>
        <li>Public notices in City open data do not give an agenda item number. A notice is joined to another item only when both share a planning application number, so a notice card does not show the later decision.</li>
        <li>Recorded votes come from the 2022 to 2026 Council term's voting record, and only for items with an agenda item number.</li>
        <li>French sentences are machine translations and have not been reviewed.</li>
        <li>Ward outlines on the map are simplified. Near a boundary, check your ward with the City.</li>
      </ul>

      ${dataSources()}
      ${checks()}

      <h2>Every sentence, for staff review</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Item</th><th>Plain sentence</th><th>Words from the record</th><th>Status</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>`;
}
