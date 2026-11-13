// app.js — starting point. Loads the data once, then shows the right screen.
//
// The site is static: it reads files made by the Python pipeline
// (data/decisions.json, data/wards.txt, and data/status.json when the scheduled
// refresh has run). There is no server and no database.
//
// Screens are chosen by the part of the address after "#":
//   #/              the board of decisions and the ward map
//   #/d/<id>        one decision
//   #/poster/<id>   a one-page notice to print
//   #/method        how sentences are checked, and the full list for staff

import { state } from "./state.js";
import { parseWards } from "./geo.js";
import { renderBoard } from "./board.js";
import { renderDecision } from "./decision.js";
import { renderPoster } from "./poster.js";
import { renderMethod } from "./method.js";

const view = document.getElementById("view");

function findDecision(id) {
  return state.data.decisions.find((d) => d.id === decodeURIComponent(id));
}

function route() {
  speechSynthesis?.cancel(); // stop any read-aloud from the last screen
  const hash = location.hash || "#/";
  const [, screen, id] = hash.split("/");
  const decision = id ? findDecision(id) : null;

  if (screen === "d" && decision) renderDecision(view, decision);
  else if (screen === "poster" && decision) renderPoster(view, decision);
  else if (screen === "method") renderMethod(view);
  else if (screen === "d" || screen === "poster") {
    view.innerHTML = `<p class="empty">We could not find that decision. <a href="#/">See all decisions</a></p>`;
  } else renderBoard(view);

  document.body.classList.toggle("is-poster", screen === "poster");
  view.focus();
  window.scrollTo(0, 0);
}

async function start() {
  try {
    const [data, wardsText, status] = await Promise.all([
      fetch("data/decisions.json").then((r) => r.json()),
      fetch("data/wards.txt").then((r) => (r.ok ? r.text() : "")), // the map is optional
      fetch("data/status.json").then((r) => (r.ok ? r.json() : null)).catch(() => null), // only after a refresh
    ]);
    state.data = data;
    state.status = status;
    state.wards = wardsText ? parseWards(wardsText) : [];
    if (state.testDate) {
      document.getElementById("test-banner").hidden = false;
      document.getElementById("test-date").textContent = state.testDate;
    }
    window.addEventListener("hashchange", route);
    route();
  } catch (error) {
    view.innerHTML = `<p class="empty">The decision list did not load. Check that web/data/decisions.json exists, then refresh.</p>`;
    console.error(error);
  }
}

start();
