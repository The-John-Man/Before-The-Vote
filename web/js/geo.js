// geo.js — "is this near me?" worked out on the device.
// The resident's location is compared with ward outlines and decision locations
// that are already in the page. It is never sent anywhere.

// wards.txt has one ward per line:  code|name|x,y x,y ...
// with longitude = x / 1000 - 80 and latitude = y / 1000 + 43.
export function parseWards(text) {
  return text.trim().split("\n").map((line) => {
    const [code, name, points] = line.split("|");
    const ring = points.split(" ").map((pair) => {
      const [x, y] = pair.split(",").map(Number);
      return [x / 1000 - 80, y / 1000 + 43]; // [lon, lat]
    });
    return { code, name, ring };
  });
}

// Ray casting: draw a line east from the point and count how many edges of the
// outline it crosses. An odd count means the point is inside.
export function pointInRing(lon, lat, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    const crosses = (yi > lat) !== (yj > lat) && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;
    if (crosses) inside = !inside;
  }
  return inside;
}

export function wardAt(lon, lat, wards) {
  return wards.find((ward) => pointInRing(lon, lat, ward.ring)) ?? null;
}

// Straight-line distance in kilometres (haversine formula).
export function distanceKm(a, b) {
  const rad = (degrees) => (degrees * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat);
  const dLon = rad(b.lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(h));
}

// Map drawing: longitude/latitude to flat x/y. At Toronto's latitude a degree of
// longitude is about 0.72 as wide as a degree of latitude, so we squeeze x by that.
const SQUEEZE = Math.cos((43.7 * Math.PI) / 180);
export function project(lon, lat) {
  return [(lon + 80) * 1000 * SQUEEZE, -(lat - 43) * 1000];
}
