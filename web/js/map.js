// map.js — the ward map, drawn as plain SVG from wards.txt.
// No map library and no map tiles, so no outside server learns which part of
// the city a resident is looking at. Every ward is a real button: it works with
// a keyboard and is announced by screen readers.

import { esc } from "./util.js";
import { project } from "./geo.js";
import { state } from "./state.js";

function outline(ring) {
  return "M" + ring.map(([lon, lat]) => project(lon, lat).map((n) => n.toFixed(1)).join(",")).join("L") + "Z";
}

export function mapSvg(wards, decisions, openIds) {
  if (!wards.length) return "";
  const points = wards.flatMap((w) => w.ring.map(([lon, lat]) => project(lon, lat)));
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  const pad = 6;
  const box = [Math.min(...xs) - pad, Math.min(...ys) - pad,
               Math.max(...xs) - Math.min(...xs) + 2 * pad, Math.max(...ys) - Math.min(...ys) + 2 * pad];

  const shapes = wards.map((ward) => {
    const count = decisions.filter((d) => d.ward?.code === ward.code).length;
    const label = `Ward ${Number(ward.code)}, ${ward.name}, ${count} decision${count === 1 ? "" : "s"}`;
    return `<path class="ward ${state.ward === ward.code ? "is-picked" : ""} ${count ? "has-items" : ""}"
      d="${outline(ward.ring)}" data-ward="${esc(ward.code)}" role="button" tabindex="0"
      aria-pressed="${state.ward === ward.code}" aria-label="${esc(label)}"><title>${esc(label)}</title></path>`;
  });

  const pins = decisions.filter((d) => d.place).map((d) => {
    const [x, y] = project(d.place.lon, d.place.lat);
    return `<circle class="pin ${openIds.has(d.id) ? "is-open" : ""}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5"></circle>`;
  });

  let you = "";
  if (state.me) {
    const [x, y] = project(state.me.lon, state.me.lat);
    you = `<circle class="you" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4"></circle>`;
  }

  return `<svg class="ward-map" viewBox="${box.map((n) => n.toFixed(1)).join(" ")}" role="group"
    aria-label="Map of Toronto's 25 wards. Choose a ward to see its decisions.">${shapes.join("")}${pins.join("")}${you}</svg>`;
}

// Call after the SVG is on the page. onPick receives the ward code.
export function wireMap(root, onPick) {
  root.querySelectorAll(".ward").forEach((shape) => {
    const pick = () => onPick(shape.dataset.ward);
    shape.addEventListener("click", pick);
    shape.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); pick(); }
    });
  });
}
