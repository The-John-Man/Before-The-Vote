// time.js — date helpers. No libraries.
// Dates in the data are either a full moment ("2026-11-16T09:30:00-05:00")
// or a day with no known time ("2024-07-09"). Both are handled here.

const DAY = 24 * 60 * 60 * 1000;
const HOUR = 60 * 60 * 1000;
const TORONTO = { timeZone: "America/Toronto" };

const isDayOnly = (value) => value.length === 10;

// Turn either form into a Date. A day-only value becomes noon Toronto time,
// so it can never slip to the day before in another time zone.
export function toDate(value) {
  return new Date(isDayOnly(value) ? value + "T12:00:00-05:00" : value);
}

// "16 November 2026" or "16 November 2026, 9:30 a.m." depending on what is known.
export function formatWhen(value, locale = "en-CA") {
  const options = { ...TORONTO, day: "numeric", month: "long", year: "numeric" };
  if (!isDayOnly(value)) Object.assign(options, { hour: "numeric", minute: "2-digit" });
  return toDate(value).toLocaleString(locale, options);
}

// Has this day arrived yet, as seen from the moment `at`?
export function reached(dayValue, at) {
  return Boolean(dayValue) && new Date(dayValue.slice(0, 10) + "T00:00:00-05:00") <= at;
}

// The last minute of a day, used when replaying a decision "as of" a stop.
export function endOfDay(dayValue) {
  return new Date(dayValue.slice(0, 10) + "T23:59:00-05:00");
}

// Time until a moment, as { open, big } for the board. open=false once it has passed.
export function countdown(value, now) {
  // A day with no known time counts down to the START of that day: the safe reading
  // is "act before the day of the meeting".
  const target = isDayOnly(value) ? new Date(value + "T00:00:00-05:00") : toDate(value);
  const ms = target - now;
  if (ms <= 0) return { open: false, big: "Closed" };
  const days = Math.floor(ms / DAY);
  const hours = Math.floor(ms / HOUR);
  return { open: true, big: days >= 2 ? days + " days" : hours >= 1 ? hours + " hours" : "Under 1 hour" };
}
