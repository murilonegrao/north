"""S-5: DAPIP (Database of Accredited Postsecondary Institutions and Programs).

Download (no key; the ope.ed.gov/dapip "Download Data Files" page calls this):
    curl -A north-research-spike -X POST -H 'Content-Type: application/json' \
      --data-raw '{"CSVChecked":true,"ExcelChecked":false}' \
      -o spikes/_raw/dapip/DAPIPData-<date>.zip \
      https://ope.ed.gov/dapip/api/downloadFiles/accreditationDataFiles

Usage:
    python3 -I spikes/s5_dapip/analyze_dapip.py \
        --dapip-dir spikes/_raw/dapip/extracted \
        --hd spikes/_raw/ipeds/extracted/HD2024.csv --state TX \
        --out-dir spikes/s5_dapip/out

What it measures:
  * join keys: DAPIP InstitutionCampus has OpeId and IpedsUnitIds (UNITID list)
  * current institutional accreditation per institution: AccreditationRecords
    rows with ProgramName == "Institutional Accreditation" and no
    AccreditationEndDate
  * "regional" = one of the 7 former regional commissions (ED dropped the
    regional/national distinction in its 2020 rules; DAPIP has no such flag)
  * coverage for IPEDS graduate institutions of one state (HLOFFER 7-9, SECTOR != 0)

The InstitutionCampus file also carries administrator names, phones and e-mails.
This script never writes those columns out.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path

REGIONAL = {
    "Middle States Commission on Higher Education": "MSCHE",
    "New England Commission of Higher Education": "NECHE",
    "Higher Learning Commission": "HLC",
    "Northwest Commission on Colleges and Universities": "NWCCU",
    "Southern Association of Colleges and Schools Commission on Colleges d.b.a. Commission on Colleges and Universities": "SACSCOC",
    "WASC Senior College and University Commission": "WSCUC",
    "Accrediting Commission for Community and Junior Colleges": "ACCJC",
}
INSTITUTIONAL = "Institutional Accreditation"


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_date(s: str) -> dt.date | None:
    s = s.strip()
    if not s:
        return None
    return dt.datetime.strptime(s.split(" ")[0], "%m/%d/%Y").date()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dapip-dir", type=Path, required=True)
    ap.add_argument("--hd", type=Path, required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()

    inst = read(a.dapip_dir / "InstitutionCampus.csv")
    recs = read(a.dapip_dir / "AccreditationRecords.csv")
    actions_header = (a.dapip_dir / "AccreditationActions.csv").open(encoding="utf-8-sig").readline().strip()

    loc_types = Counter(r["LocationType"] for r in inst)
    top = [r for r in inst if r["LocationType"] == "Institution"]
    with_unitid = [r for r in top if r["IpedsUnitIds"].strip()]
    with_opeid = [r for r in top if r["OpeId"].strip()]
    multi_unitid = [r for r in top if "," in r["IpedsUnitIds"]]

    by_unitid: dict[str, list[dict]] = defaultdict(list)
    for r in top:
        for u in r["IpedsUnitIds"].split(","):
            if u.strip():
                by_unitid[u.strip()].append(r)

    by_ope6: dict[str, list[dict]] = defaultdict(list)
    for r in top:
        if r["OpeId"].strip():
            by_ope6[r["OpeId"].strip()[:6]].append(r)

    current_inst: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        if r["ProgramName"] == INSTITUTIONAL and not r["AccreditationEndDate"].strip():
            current_inst[r["DapipId"]].append(r)

    with a.hd.open(encoding="utf-8-sig", errors="replace") as f:
        hd = [r for r in csv.DictReader(f)
              if r["STABBR"] == a.state and r["CYACTIVE"] == "1" and r["HLOFFER"] in {"7", "8", "9"} and r["SECTOR"] != "0"]

    rows, cov = [], Counter()
    for h in hd:
        d = by_unitid.get(h["UNITID"], [])
        opeid_hit = [r for r in top if r["OpeId"].strip() and r["OpeId"].strip() == h["OPEID"].strip()]
        join = "unitid" if d else ""
        if not d:
            # Fallback: branch campuses of multi-state chains often have no UNITID in
            # DAPIP; inherit from the parent institution with the same 6-digit OPEID.
            ope6 = h["OPEID"].strip()[:6]
            d = by_ope6.get(ope6, []) if ope6 and not ope6.startswith("-") else []
            join = "opeid6_parent" if d else "none"
        accs = [x for r in d for x in current_inst.get(r["DapipId"], [])]
        regional = sorted({REGIONAL[x["AgencyName"]] for x in accs if x["AgencyName"] in REGIONAL})
        others = sorted({x["AgencyName"] for x in accs if x["AgencyName"] not in REGIONAL})
        statuses = sorted({x["AccreditationStatus"] for x in accs})
        cov[f"join_{join}"] += 1
        cov["joined_by_opeid" if opeid_hit else "not_joined_by_opeid"] += 1
        cov["has_current_institutional" if accs else "no_current_institutional"] += 1
        cov["has_regional" if regional else "no_regional"] += 1
        rows.append({
            "unitid": h["UNITID"], "opeid_ipeds": h["OPEID"].strip(), "instnm": h["INSTNM"],
            "join": join,
            "dapip_ids": ";".join(r["DapipId"] for r in d),
            "dapip_opeid": ";".join(r["OpeId"] for r in d),
            "regional_accreditor": ";".join(regional),
            "other_institutional_accreditors": ";".join(others),
            "status": ";".join(statuses),
            "next_review": ";".join(sorted({x["ReviewDate"].split(" ")[0] for x in accs if x["ReviewDate"].strip()})),
        })

    a.out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = a.out_dir / f"{a.state.lower()}_ipeds_grad_accreditation.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    upd = [parse_date(r["UpdateDate"]) for r in inst if r["UpdateDate"].strip()]
    summary = {
        "files": {
            "InstitutionCampus.csv": {"rows": len(inst), "columns": list(inst[0].keys())},
            "AccreditationRecords.csv": {"rows": len(recs), "columns": list(recs[0].keys())},
            "AccreditationActions.csv": {"columns": actions_header.split(",")},
        },
        "location_types": dict(loc_types),
        "institutions": len(top),
        "institutions_with_unitid": len(with_unitid),
        "institutions_with_opeid": len(with_opeid),
        "institutions_with_multiple_unitids": len(multi_unitid),
        "latest_update_date": max(upd).isoformat() if upd else None,
        "accreditation_status_values": dict(Counter(r["AccreditationStatus"] for r in recs)),
        "records_institutional_current": sum(len(v) for v in current_inst.values()),
        "institutions_with_current_institutional": sum(1 for r in top if r["DapipId"] in current_inst),
        "current_institutional_by_agency_top15": Counter(
            x["AgencyName"] for v in current_inst.values() for x in v).most_common(15),
        f"{a.state}_ipeds_grad": len(hd),
        f"{a.state}_coverage": dict(cov),
    }
    (a.out_dir / "dapip_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    for r in rows:
        if not r["regional_accreditor"]:
            print("no regional:", r["unitid"], r["instnm"], "|", r["join"], "|", r["other_institutional_accreditors"] or "-", "|", r["dapip_ids"] or "-")


if __name__ == "__main__":
    main()
