// util.js — helpers shared by every screen.

import { state } from "./state.js";
import { reached, countdown, formatWhen } from "./time.js";

// Make text safe to place inside HTML. Everything from the data goes through this.
export function esc(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

// How decided is this item at the moment `at`?
// The brief asks us to keep three things apart: what staff recommend, what a
// committee recommends, and what Council decides. We look at the latest stage
// that has happened and say which of the three it is.
export function statusAt(decision, at) {
  const happened = decision.stages.filter((s) => reached(s.date, at));
  const last = happened[happened.length - 1];
  if (last?.key === "notice") {
    return { level: "proposed", short: "City notice", text: "The City has posted a public notice. Nothing is decided yet." };
  }
  if (!last || last.body === "staff") {
    const what = last?.result ? `City staff ${last.result}.` : "City staff have reported.";
    return { level: "proposed", short: "Staff recommendation", text: `${what} Nothing is decided yet.` };
  }
  if (last.body === "committee") {
    return last.result
      ? { level: "committee", short: "Committee recommendation", text: `${last.label} ${last.result}. City Council has not voted.` }
      : { level: "committee", short: "At committee", text: `${last.label} has met. The result is not loaded yet.` };
  }
  return last.result
    ? { level: "decided", short: "Decided by Council", text: `City Council ${last.result}.` }
    : { level: "decided", short: "At Council", text: "City Council has considered this. The result is not loaded yet." };
}

// The next moment a resident can act, and how sure we are about it.
//   kind "deadline": a cut-off written in the City's own notice
//   kind "meeting":  no written cut-off; this is when the meeting starts
export function actBy(decision, now) {
  const say = decision.say;
  const value = say.deadline ?? say.meeting;
  if (!value) return { open: false, big: "No date", small: "No date found in the record", kind: "none" };
  const left = countdown(value, now);
  const kind = say.deadline ? "deadline" : "meeting";
  if (!left.open) return { ...left, kind, value, small: "since " + formatWhen(value) };
  return {
    ...left, kind, value,
    small: kind === "deadline" ? "left to have your say" : (value.length === 10 ? "until the day of the meeting" : "until the meeting") + ". No written deadline posted",
  };
}

// Only sentences that passed the quote check are ever shown to residents.
export function shownClaims(decision, at) {
  return decision.claims.filter((c) => {
    if (!c.verified) return false;
    if (!c.stage) return true;
    const stage = decision.stages.find((s) => s.key === c.stage);
    return !stage || reached(stage.date, at);
  });
}

// When this item was last compared with the City's record, from status.json.
// "checked" says what was compared: a saved item page, a public notice, or recorded votes.
// Returns null when no automatic check has run (for example, a local build).
export function lastCheck(decision) {
  const check = state.status?.items?.[decision.id];
  if (!check) return null;
  const when = formatWhen(check.checked_at).replace(/\.$/, ""); // "6:34 p.m." would end in two dots
  const what = { notice: "the City's public notice (open data)", votes: "the City's voting record (open data)" }[check.checked]
    ?? "the City's page";
  return check.ok
    ? { ok: true, text: `${check.checked === "votes" ? "Recorded votes checked" : "Checked"} against ${what} ${when}.` }
    : { ok: false, text: `The latest automatic check could not reach ${what} (${when}). What you see is from the last copy that worked.` };
}

// The newest "what changed" entry, if it is from the last 7 days.
export function recentUpdate(decision, now) {
  const latest = decision.updates?.[0];
  if (!latest) return null;
  const days = (now - new Date(latest.date + "T12:00:00-05:00")) / 86400000;
  return days <= 7 && days >= -1 ? latest : null;
}

// The sentence in the chosen language, falling back to English.
export function claimText(claim, lang) {
  return lang === "fr" && claim.fr ? claim.fr : claim.text;
}
