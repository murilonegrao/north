"""Spike S-6: HUD Fair Market Rents for Texas.

Source: HUD's official FeatureServer on ArcGIS Online (HUD org, item
12d2516901f947b5bb4da4e780e35f07). huduser.gov answers scripted clients with an
AWS WAF JavaScript challenge (HTTP 202, empty body), and the HUD User API needs
a token (HTTP 403 without one).

The script:
1. downloads the layer metadata and every FMR area with ", TX" in its name;
2. downloads the Census 2024 Gazetteer places file for TX, to get the official
   internal point of each city;
3. links city -> FMR area by point-in-polygon (ArcGIS spatial query);
4. prints the FMRs (0-4 bedrooms) of the matched areas.

Usage: python3 -I spikes/s6_hud/fmr_tx.py <raw_dir>
Example: python3 -I spikes/s6_hud/fmr_tx.py spikes/_raw/hud_fmr
Standard library only. Downloaded files are read as data, never executed.
"""

import csv
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "north-research-spike"
LAYER = ("https://services.arcgis.com/VTyQ9soqVukalItT/arcgis/rest/services/"
         "Fair_Market_Rents/FeatureServer/0")
GAZ = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
       "2024_Gazetteer/2024_gaz_place_48.txt")
# Cities with large universities (exact place name in the Gazetteer).
CITIES = ["Austin city", "Houston city", "Dallas city", "San Antonio city",
          "College Station city"]

_last = {}


def get(url, params=None):
    """GET with a generic UA and at most 1 request per second per host."""
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    host = urllib.parse.urlparse(url).netloc
    wait = 1.1 - (time.monotonic() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    _last[host] = time.monotonic()
    return body


def main(raw_dir):
    raw = Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    gaz_dir = raw.parent / "census_gazetteer"
    gaz_dir.mkdir(parents=True, exist_ok=True)

    meta = json.loads(get(LAYER, {"f": "json"}))
    (raw / "layer_meta.json").write_text(json.dumps(meta, indent=1))
    last_edit = dt.datetime.fromtimestamp(
        meta["editingInfo"]["dataLastEditDate"] / 1000, dt.timezone.utc)
    print(f"layer: {meta['name']}; data last edited: {last_edit:%Y-%m-%d}")

    q = json.loads(get(LAYER + "/query", {
        "where": "FMR_AREANAME LIKE '%, TX%'", "outFields": "*",
        "returnGeometry": "false", "orderByFields": "FMR_AREANAME",
        "f": "json"}))
    (raw / "tx_areas.json").write_text(json.dumps(q, indent=1))
    tx = [f["attributes"] for f in q["features"]]
    print(f"Texas FMR areas: {len(tx)}")

    gaz_path = gaz_dir / "2024_gaz_place_48.txt"
    if not gaz_path.exists():
        gaz_path.write_bytes(get(GAZ))
    with gaz_path.open(encoding="latin-1") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    rows = [{k.strip(): (v or "").strip() for k, v in r.items()} for r in rows]
    by_name = {r["NAME"]: r for r in rows}

    out = []
    for city in CITIES:
        g = by_name[city]
        lat, lon = g["INTPTLAT"], g["INTPTLONG"]
        hit = json.loads(get(LAYER + "/query", {
            "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint",
            "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
            "outFields": "FMR_CODE,FMR_AREANAME,FMR_0BDR,FMR_1BDR,FMR_2BDR,"
                         "FMR_3BDR,FMR_4BDR",
            "returnGeometry": "false", "f": "json"}))
        for f in hit["features"]:
            a = f["attributes"]
            out.append({"city": city, "place_geoid": g["GEOID"],
                        "intptlat": lat, "intptlong": lon, **a})
    (raw / "tx_city_points.json").write_text(json.dumps(out, indent=1))

    print()
    print("| city (Census place) | FMR area | FMR_CODE | 0BR | 1BR | 2BR | 3BR | 4BR |")
    print("|---|---|---|---|---|---|---|---|")
    for r in out:
        print(f"| {r['city']} | {r['FMR_AREANAME']} | {r['FMR_CODE']} | "
              f"{r['FMR_0BDR']} | {r['FMR_1BDR']} | {r['FMR_2BDR']} | "
              f"{r['FMR_3BDR']} | {r['FMR_4BDR']} |")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "spikes/_raw/hud_fmr")
