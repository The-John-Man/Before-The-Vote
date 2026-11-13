"""fetch_wards.py - download Toronto's ward boundaries and write web/data/wards.txt.

Run from the pipeline folder:   python fetch_wards.py

NOT YET RUN from this script (the build machine had no internet access). The
wards.txt in the repo was produced on 13 Nov 2026 with the same steps but a
coarser setting, so its outlines are rough (points about 600 m apart). Running
this gives finer outlines.

Source: City of Toronto Open Data, "City Wards", WGS84 GeoJSON,
Open Government Licence - Toronto.

File format, one ward per line:   code|name|x,y x,y x,y ...
where longitude = x / 1000 - 80  and  latitude = y / 1000 + 43.
Whole numbers keep the file small enough to read by eye.
"""

import json
import math
import urllib.request
from pathlib import Path

URL = ("https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/5e7a8234-f805-43ac-820f-03d7c360b588/"
       "resource/737b29e0-8329-4260-b6af-21555ab24f28/download/city-wards-data-4326.geojson")
OUTPUT = Path(__file__).resolve().parent.parent / "web" / "data" / "wards.txt"
TOLERANCE = 0.002   # degrees, about 200 m: skip points closer than this to the last kept point


def simplify(ring: list) -> list:
    kept = [ring[0]]
    for point in ring:
        if math.dist(point[:2], kept[-1][:2]) >= TOLERANCE:
            kept.append(point)
    return kept


def ward_line(feature: dict) -> str:
    geometry = feature["geometry"]
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    outer = max((polygon[0] for polygon in polygons), key=len)   # biggest outline, ignore small islands
    points = " ".join(f"{round((lon + 80) * 1000)},{round((lat - 43) * 1000)}" for lon, lat, *_ in simplify(outer))
    properties = feature["properties"]
    return f"{properties['AREA_SHORT_CODE']}|{properties['AREA_NAME']}|{points}"


def main():
    with urllib.request.urlopen(URL, timeout=60) as response:
        features = json.load(response)["features"]
    OUTPUT.write_text("\n".join(sorted(ward_line(f) for f in features)) + "\n", encoding="utf-8")
    print(f"Wrote {len(features)} wards to {OUTPUT}")


if __name__ == "__main__":
    main()
