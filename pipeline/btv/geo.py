"""geo.py - which ward is a point in? The same method as web/js/geo.js, in Python.

web/data/wards.txt has one ward per line:   code|name|x,y x,y ...
with longitude = x / 1000 - 80 and latitude = y / 1000 + 43 (written by fetch_wards.py).
The outlines are simplified to about 100 metres, so a point right on a ward
boundary could be placed in the neighbouring ward.
"""

from pathlib import Path

WARDS_FILE = Path(__file__).resolve().parent.parent.parent / "web" / "data" / "wards.txt"


def parse_wards(text: str) -> list[dict]:
    wards = []
    for line in text.strip().splitlines():
        code, name, points = line.split("|")
        ring = []
        for pair in points.split():
            x, y = pair.split(",")
            ring.append((int(x) / 1000 - 80, int(y) / 1000 + 43))     # (lon, lat)
        wards.append({"code": code, "name": name, "ring": ring})
    return wards


def point_in_ring(lon: float, lat: float, ring: list) -> bool:
    """Ray casting: draw a line east from the point and count the outline edges it
    crosses. An odd count means the point is inside."""
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def ward_at(lon: float, lat: float, wards: list[dict]) -> dict | None:
    """{"code", "name"} of the ward holding the point, or None if it is outside every ward."""
    for ward in wards:
        if point_in_ring(lon, lat, ward["ring"]):
            return {"code": ward["code"], "name": ward["name"]}
    return None


def load_wards(path: Path = WARDS_FILE) -> list[dict]:
    return parse_wards(path.read_text(encoding="utf-8")) if path.exists() else []
