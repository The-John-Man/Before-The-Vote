// state.js — the few things the site remembers while it is open.
// All of it lives in this one object in the browser's memory. Nothing is saved
// to disk, put in a cookie, or sent anywhere. Closing the tab forgets it.

export const state = {
  now: new Date(),   // "today". Can be overridden for testing with ?asof=2024-07-01
  testDate: null,    // the ?asof value, if one was given
  ward: null,        // ward code the resident picked, e.g. "04"
  me: null,          // { lat, lon } from the device, only if the resident asked
  lens: null,        // "rent", "drive"... which sentences to bring forward
  lang: "en",        // "en" or "fr"
  data: null,        // decisions.json
  wards: [],         // parsed wards.txt
};

// Testing aid: add ?asof=YYYY-MM-DD to the address to see the site as of that day.
const asof = new URLSearchParams(location.search).get("asof");
if (/^\d{4}-\d{2}-\d{2}$/.test(asof ?? "")) {
  state.now = new Date(asof + "T12:00:00-05:00");
  state.testDate = asof;
}
