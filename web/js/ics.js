// ics.js — builds a calendar reminder file (.ics) in the browser.
// The file is created and downloaded on the device. Nothing is sent to a server.

import { toDate } from "./time.js";

// 2026-11-16T14:30:00.000Z -> 20261116T143000Z (the format calendars expect)
function stamp(date) {
  return date.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
}

export function downloadReminder(decision, act) {
  const dayOnly = act.value.length === 10;       // the record gives a day but no time
  const end = toDate(act.value);
  const start = new Date(end.getTime() - 60 * 60 * 1000); // one hour before
  const day = act.value.slice(0, 10).replace(/-/g, "");
  const timing = dayOnly
    ? ["DTSTART;VALUE=DATE:" + day]               // an all-day entry on the meeting day
    : ["DTSTART:" + stamp(start), "DTEND:" + stamp(end)];
  const kind = act.kind === "deadline" ? "Last chance to comment"
    : dayOnly ? "Meeting day (time not posted, comment before this day)" : "Meeting starts (no written deadline posted)";
  const lines = [
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Before the Vote//CIVIC Hack 2026//EN",
    "BEGIN:VEVENT",
    "UID:" + decision.id + "@before-the-vote",
    "DTSTAMP:" + stamp(new Date()),
    ...timing,
    "SUMMARY:" + kind + ": " + decision.title_plain.replace(/[,;]/g, " "),
    "DESCRIPTION:Official record: " + decision.official_url,
    "END:VEVENT", "END:VCALENDAR",
  ];
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([lines.join("\r\n")], { type: "text/calendar" }));
  link.download = "have-your-say-" + decision.id + ".ics";
  link.click();
  URL.revokeObjectURL(link.href);
}
