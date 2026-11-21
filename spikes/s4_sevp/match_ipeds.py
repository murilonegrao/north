"""S-4: match SEVP certified schools to IPEDS institutions (UNITID) for one state.

SEVP publishes no UNITID/OPEID, so the match uses normalized name + city + state.

Usage:
    uv run --with rapidfuzz python -I spikes/s4_sevp/match_ipeds.py \
        --sevp spikes/_raw/sevp/derived/sevp-certified-schools-2026-11-18.csv \
        --hd spikes/_raw/ipeds/extracted/HD2024.csv \
        --state TX --out-dir spikes/s4_sevp/out

Tiers (in rank order; best one wins, per IPEDS institution):
  exact            normalized name equal AND normalized city equal
  approximate      fuzzy name score >= 90 with same city, or >= 95 any city,
                   or one name is a prefix (>= 20 chars) of the other with the
                   same city (SEVP names are truncated at the printed cell width)
  exact_name_only  normalized name equal, city differs (same state)
  none             nothing above

Two universes are measured:
  ipeds_grad   IPEDS active institutions whose highest offering is master's or
               above (HLOFFER 7, 8, 9), excluding administrative units (SECTOR 0):
               the institutions North cares about
  sevp_schools SEVP school codes with at least one campus in the state
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from rapidfuzz import fuzz

STOP = {"the", "inc", "llc", "corp", "corporation", "dba", "of", "at", "in", "campus", "main", "and"}
ABBR = {"univ": "university", "u": "university", "coll": "college", "cc": "community college",
        "comm": "community", "tech": "technology", "inst": "institute", "intl": "international",
        "ctr": "center", "sch": "school", "schl": "school", "sci": "science", "sciences": "science",
        "hlth": "health", "med": "medical", "ft": "fort", "mt": "mount"}
GRAD_HLOFFER = {"7", "8", "9"}
TRUNC_MIN = 20
# A close name in the same city beats an identical name in another city
# (e.g. a system with campuses listed under the HQ city).
RANK = {"exact": 3, "approximate": 2, "exact_name_only": 1, "none": 0}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = []
    for t in s.split():
        t = ABBR.get(t, t)
        toks.extend(t.split())
    return " ".join(t for t in toks if t not in STOP)


def norm_city(s: str) -> str:
    return norm(s).replace("saint ", "st ")


def strip_place(name: str, city: str, state: str) -> str:
    """Drop the campus city and the state abbreviation from a SEVP name
    ("St. Mary's Univ. of San Antonio, TX" -> "st marys university")."""
    out = f" {name} "
    if city:
        out = out.replace(f" {city} ", " ")
    out = out.replace(f" {state.lower()} ", " ")
    return " ".join(out.split())


def sevp_names(r: dict) -> list[str]:
    names = {norm(r["school_name"]), norm(r["campus_name"]), norm(r["school_name"] + " " + r["campus_name"])}
    # "Foo University (Waco, Texas)" / "Austin College, Sherman TX" style suffixes
    for raw in (r["school_name"], r["campus_name"]):
        names.add(norm(re.split(r"[(,]", raw)[0]))
    city = norm(r["city"])
    names |= {strip_place(n, city, r["state"]) for n in list(names)}
    return [n for n in names if n]


def ipeds_names(r: dict) -> list[str]:
    names = {norm(r["INSTNM"]), norm(r["INSTNM"].split("-")[0])}
    for a in re.split(r"[|,;]", r.get("IALIAS", "")):
        if len(a.strip()) > 3:
            names.add(norm(a))
    return [n for n in names if n]


def best_match(i_names: list[str], i_city: str, cands: list[dict]) -> tuple[str, float, dict | None]:
    best = ("none", 0.0, None)
    rank = RANK
    for c in cands:
        same_city = c["_city"] == i_city
        for sn in c["_names"]:
            for iname in i_names:
                if sn == iname:
                    tier, score = ("exact" if same_city else "exact_name_only"), 100.0
                else:
                    score = fuzz.token_sort_ratio(sn, iname)
                    short, long_ = sorted((sn, iname), key=len)
                    prefix = len(short) >= TRUNC_MIN and long_.startswith(short) and same_city
                    if (score >= 90 and same_city) or score >= 95 or prefix:
                        tier = "approximate"
                        score = max(score, 90.0) if prefix else score
                    else:
                        tier = "none"
                if (rank[tier], score) > (rank[best[0]], best[1]):
                    best = (tier, score, c)
    return best


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sevp", type=Path, required=True)
    ap.add_argument("--hd", type=Path, required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()

    sevp = [r for r in csv.DictReader(a.sevp.open(encoding="utf-8")) if r["state"] == a.state]
    for r in sevp:
        r["_names"], r["_city"] = sevp_names(r), norm_city(r["city"])
    with a.hd.open(encoding="utf-8-sig", errors="replace") as f:
        hd = [r for r in csv.DictReader(f) if r["STABBR"] == a.state and r["CYACTIVE"] == "1"]
    # SECTOR 0 = administrative unit (system offices): not a school a student enrolls in.
    grad = [r for r in hd if r["HLOFFER"] in GRAD_HLOFFER and r["SECTOR"] != "0"]

    # Universe 1: IPEDS graduate institutions -> SEVP
    out_rows, tiers = [], Counter()
    matched_campus_codes = set()
    for r in grad:
        tier, score, c = best_match(ipeds_names(r), norm_city(r["CITY"]), sevp)
        tiers[tier] += 1
        if c and tier != "none":
            matched_campus_codes.add(c["campus_code"])
        out_rows.append({
            "unitid": r["UNITID"], "opeid": r["OPEID"].strip(), "instnm": r["INSTNM"], "city": r["CITY"],
            "hloffer": r["HLOFFER"], "tier": tier, "score": round(score, 1),
            "sevp_school": c["school_name"] if c and tier != "none" else "",
            "sevp_campus": c["campus_name"] if c and tier != "none" else "",
            "sevp_city": c["city"] if c and tier != "none" else "",
            "sevp_campus_code": c["campus_code"] if c and tier != "none" else "",
            "best_candidate_if_none": f'{c["school_name"]} / {c["campus_name"]} ({c["city"]}) {score:.0f}' if c and tier == "none" else "",
        })

    # Universe 2: SEVP school codes in the state -> any active IPEDS institution in the state
    by_school: dict[str, list[dict]] = defaultdict(list)
    for r in sevp:
        by_school[r["school_code"]].append(r)
    hd_prepped = [{**r, "_names": ipeds_names(r), "_city": norm_city(r["CITY"])} for r in hd]
    s_tiers, s_rows = Counter(), []
    for code, campuses in sorted(by_school.items()):
        best = ("none", 0.0, None, None)
        rank = RANK
        for camp in campuses:
            tier, score, h = best_match(camp["_names"], camp["_city"], hd_prepped)
            if (rank[tier], score) > (rank[best[0]], best[1]):
                best = (tier, score, h, camp)
        tier, score, h, camp = best
        camp = camp or campuses[0]
        s_tiers[tier] += 1
        s_rows.append({"school_code": code, "school_name": campuses[0]["school_name"], "campuses_in_state": len(campuses),
                       "tier": tier, "score": round(score, 1),
                       "unitid": h["UNITID"] if h and tier != "none" else "",
                       "instnm": h["INSTNM"] if h and tier != "none" else "",
                       "ipeds_hloffer": h["HLOFFER"] if h and tier != "none" else ""})

    a.out_dir.mkdir(parents=True, exist_ok=True)
    p1 = a.out_dir / f"{a.state.lower()}_ipeds_grad_to_sevp.csv"
    with p1.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(out_rows, key=lambda x: (RANK[x["tier"]], x["instnm"])))
    p2 = a.out_dir / f"{a.state.lower()}_sevp_schools_to_ipeds.csv"
    with p2.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(s_rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(s_rows)

    summary = {
        "state": a.state,
        "sevp_file": str(a.sevp), "ipeds_file": str(a.hd),
        "sevp_campuses_in_state": len(sevp), "sevp_school_codes_in_state": len(by_school),
        "ipeds_active_in_state": len(hd), "ipeds_grad_in_state": len(grad),
        "ipeds_grad_to_sevp": dict(tiers),
        "ipeds_grad_to_sevp_pct": {k: round(100 * v / len(grad), 1) for k, v in tiers.items()},
        "sevp_schools_to_ipeds": dict(s_tiers),
        "sevp_schools_to_ipeds_pct": {k: round(100 * v / len(by_school), 1) for k, v in s_tiers.items()},
    }
    (a.out_dir / f"{a.state.lower()}_match_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
