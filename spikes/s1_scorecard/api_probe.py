"""S-1: minimal probe of the College Scorecard API for Texas master's programs.

Confirms that the API exposes programs.cip_4_digit with credential.level = 5 and
counts how many TX schools/programs it returns for the target CIP families.

Usage (from the project root; the key is read from the environment, never printed):
  set -a; . ./.env; set +a
  python3 -I spikes/s1_scorecard/api_probe.py spikes/_raw/scorecard/api

Falls back to DEMO_KEY when NORTH_API_DATA_GOV_KEY is not set. Makes one call per page
(TX returned 411 schools on 2026-11-21; per_page=100 -> 5 calls).
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
KEY = os.environ.get("NORTH_API_DATA_GOV_KEY") or "DEMO_KEY"
BASE = "https://api.data.gov/ed/collegescorecard/v1/schools"
FIELDS = ",".join([
    "id", "school.name", "school.city", "school.ownership", "school.state",
    "programs.cip_4_digit.code", "programs.cip_4_digit.title",
    "programs.cip_4_digit.credential.level", "programs.cip_4_digit.counts.ipeds_awards2",
    "programs.cip_4_digit.earnings.1_yr.overall_median_earnings",
])


def get(page):
    q = {"school.state": "TX", "fields": FIELDS, "per_page": 100, "page": page,
         "all_programs_nested": "true", "api_key": KEY}
    req = urllib.request.Request(BASE + "?" + urllib.parse.urlencode(q),
                                 headers={"User-Agent": "north-research-spike"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def family(code):
    c = (code or "").replace(".", "")
    if c.startswith("11"):
        return "11.xx"
    if c.startswith("5212"):
        return "52.12"
    if c.startswith("3070"):
        return "30.70"
    return None


results, page = [], 0
while True:
    data = get(page)
    results.extend(data.get("results", []))
    meta = data.get("metadata", {})
    if (page + 1) * meta.get("per_page", 100) >= meta.get("total", 0):
        break
    page += 1
    time.sleep(1)

# Raw response saved without the key (the key is only in the request URL, never stored).
(OUT / "tx_schools_programs.json").write_text(json.dumps({"metadata": meta, "results": results}))

progs, schools = [], set()
for s in results:
    for p in s.get("latest.programs.cip_4_digit") or s.get("programs.cip_4_digit") or []:
        lvl = (p.get("credential") or {}).get("level")
        f = family(p.get("code"))
        if lvl == 5 and f:
            progs.append((s.get("id"), p.get("code"), f))
            schools.add(s.get("id"))
summary = {"api_total_tx_schools": meta.get("total"), "pages_called": page + 1,
           "tx_masters_target_programs": len(progs), "tx_masters_target_institutions": len(schools),
           "by_family": {f: sum(1 for x in progs if x[2] == f) for f in ("11.xx", "52.12", "30.70")},
           "result_keys_sample": sorted(results[0].keys()) if results else []}
(OUT / "summary_api.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
