"""S-3 check: compare the parsed DHS STEM list with the official CIP 2020 table (NCES).

Usage:
    python3 -I spikes/s3_dhs_stem/check_against_cip2020.py \
        data/reference/dhs-stem-list-2024-07-22.csv spikes/_raw/nces_cip/CIPCode2020.csv

Checks: every listed code exists in CIP 2020; titles match (ignoring a trailing
period); and for the whole-series designations (14, 26, 27, 40) how many CIP 2020
6-digit codes are not printed in the PDF (they are STEM anyway, by the series rule).
"""
import csv
import re
import sys


def clean(code: str) -> str:
    return re.sub(r'^="?|"$', "", code.strip())


stem = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
cip = {}
with open(sys.argv[2], encoding="utf-8-sig", errors="replace") as f:
    for r in csv.DictReader(f):
        cip[clean(r["CIPCode"])] = r["CIPTitle"].strip()

missing = [s["cip_code"] for s in stem if s["cip_code"] not in cip and s["level"] == "6"]
heading = [s["cip_code"] for s in stem if s["level"] != "6"]
title_diff = [(s["cip_code"], s["title"], cip[s["cip_code"]]) for s in stem
              if s["level"] == "6" and s["cip_code"] in cip
              and s["title"].rstrip(".").strip().lower() != cip[s["cip_code"]].rstrip(".").strip().lower()]
listed = {s["cip_code"] for s in stem}
six = [c for c in cip if re.fullmatch(r"\d{2}\.\d{4}", c)]
print(f"stem rows={len(stem)}  6-digit rows={len(stem) - len(heading)}  headings={len(heading)}")
print(f"CIP 2020 6-digit codes={len(six)}")
print(f"6-digit codes not in CIP 2020: {missing}")
print(f"title differences: {len(title_diff)}")
for t in title_diff[:20]:
    print("  ", t)
for series in ("14", "26", "27", "40"):
    all6 = [c for c in six if c.startswith(series + ".")]
    not_printed = [c for c in all6 if c not in listed]
    print(f"series {series}: CIP 2020 has {len(all6)} 6-digit codes, PDF prints {len(all6) - len(not_printed)}, not printed {len(not_printed)} {not_printed[:10]}")
