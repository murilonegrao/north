"""S-2 fallback: fetch IPEDS data for one state from the Urban Institute Education Data Portal.

Why: nces.ed.gov (IPEDS Data Center) reset or timed out every connection during the spike
(2026-11-20/21), so the original C/HD/IC files could not be downloaded. The Urban portal
republishes IPEDS (third-party mirror; see docs/sources/ipeds.md).

Usage (from the project root):
  python3 -I spikes/s2_ipeds/fetch_urban_ipeds.py spikes/_raw/ipeds/urban 48 2023

Arguments: output dir, state FIPS (48 = Texas), year (Urban "year" = fall of the academic
year, so 2023 = AY2023-24 = IPEDS completions collected in 2024-25).

Saves the raw JSON pages exactly as received. Nothing from the responses is executed.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

OUT, FIPS, YEAR = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://educationdata.urban.org/api/v1/college-university/ipeds"

QUERIES = {
    # award_level 9 = "Master's degree" in Urban's recode (IPEDS AWLEVEL 7);
    # race=99 and sex=99 = totals.
    "completions_cip6_masters": f"{BASE}/completions-cip-6/{YEAR}/?fips={FIPS}&award_level=9&race=99&sex=99",
    # level_of_study 2 = Graduate; tuition_type 3 = in state, 4 = out of state.
    "tuition_graduate": f"{BASE}/academic-year-tuition/{YEAR}/?fips={FIPS}&level_of_study=2",
    "directory": f"{BASE}/directory/{YEAR}/?fips={FIPS}",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "north-research-spike"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except Exception as e:  # network errors: retry with backoff
            print(f"retry {attempt + 1} {url}: {e}", file=sys.stderr)
            time.sleep(10 * (attempt + 1))
    raise SystemExit(f"failed: {url}")


for name, url in QUERIES.items():
    rows, page, nxt = [], 1, url
    while nxt:
        data = fetch(nxt)
        rows.extend(data.get("results", []))
        nxt = data.get("next")
        page += 1
        time.sleep(1)
    out = OUT / f"{name}_{FIPS}_{YEAR}.json"
    out.write_text(json.dumps({"source_url": url, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                               "count": len(rows), "results": rows}))
    print(name, len(rows), "rows ->", out)
