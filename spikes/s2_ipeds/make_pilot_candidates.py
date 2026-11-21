"""Build docs/methodology/pilot-candidates.csv: 20 CANDIDATE Texas master's programs for the
manual pilot. Nothing here is verified; it only says that IPEDS reports master's completions
for this UNITID x CIP. A program name, F-1 eligibility, delivery mode etc. still need checking.

Selection was made by hand (list below) for variety: public/private, institution size,
the three CIP families, all with master's completions > 0 in AY2023-24.

Usage (from the project root):
  uv run --with pandas --with openpyxl python -I spikes/s2_ipeds/make_pilot_candidates.py \
      spikes/s2_ipeds/out/tx_masters_target_ipeds.csv \
      spikes/s1_scorecard/out/tx_masters_target_scorecard.csv \
      spikes/_raw/ipeds/C2024_A_Dict.zip \
      docs/methodology/pilot-candidates.csv
"""
import io
import sys
import zipfile

import pandas as pd

IPEDS, SC, CDICT, OUT = sys.argv[1:5]

PICKS = [  # (UNITID, CIP6)
    ("228787", "11.0101"), ("228769", "11.0101"), ("227216", "11.0103"), ("228778", "11.0101"),
    ("227757", "11.0101"), ("223232", "11.0701"), ("224226", "11.0401"), ("226091", "11.0701"),
    ("224147", "11.0101"), ("461795", "11.0701"), ("225511", "11.1003"), ("226833", "11.0101"),
    ("228149", "11.0701"),
    ("229115", "30.7001"), ("228723", "30.7001"), ("228246", "30.7001"), ("227216", "30.7001"),
    ("229814", "52.1201"), ("229063", "52.1201"), ("229027", "52.1207"),
]
SIZE = {"1": "Under 1,000", "2": "1,000-4,999", "3": "5,000-9,999", "4": "10,000-19,999",
        "5": "20,000 and above"}
DIST = {"0": "not reported", "1": "no credential fully online", "2": "some fully online",
        "3": "all can be fully online"}

ip = pd.read_csv(IPEDS, dtype=str, keep_default_na=False)
sc = pd.read_csv(SC, dtype=str, keep_default_na=False)
with zipfile.ZipFile(CDICT) as z:
    f = pd.read_excel(io.BytesIO(z.read(z.namelist()[0])), "Frequencies", dtype=str)
titles = {}
for _, r in f[f["VarName"] == "CIPCODE"].iterrows():
    code = r["CodeValue"]
    if "." in code:
        a, b = code.split(".")
        titles[f"{int(a):02d}.{b.ljust(4, '0')[:4]}"] = r["ValueLabel"].strip()

rows = []
for i, (u, cip) in enumerate(PICKS, 1):
    m = ip[(ip["UNITID"] == u) & (ip["CIPCODE"] == cip)]
    assert len(m) == 1, (u, cip)
    r = m.iloc[0]
    s = sc[(sc["UNITID"] == u) & (sc["CIPCODE"] == cip.replace(".", "")[:4])]
    rows.append({
        "candidate_id": f"TX-{i:02d}",
        "unitid": u,
        "opeid": r["OPEID"],
        "institution_name_ipeds": r["INSTNM"],
        "institution_name_scorecard": s["INSTNM"].iloc[0] if len(s) else "",
        "city": r["CITY"],
        "control": r["control_label"],
        "size_category": SIZE.get(r["INSTSIZE"], ""),
        "cip_family": r["family"],
        "cip6": cip,
        "cip6_title": titles.get(cip, ""),
        "masters_completions_2023_24": r["completions_total"],
        "nonresident_completions_2023_24": r["completions_nonresident"],
        "grad_tuition_out_of_state_2023_24_usd": r["TUITION7"],
        "scorecard_distance_hint": DIST.get(s["DISTANCE"].iloc[0], "") if len(s) else "",
        "website": r["WEBADDR"],
        "verification_status": "candidate_unverified",
        "source": "IPEDS C2024_A + HD2024 + IC2023_AY; Scorecard FoS 2026-10-15",
    })
pd.DataFrame(rows).to_csv(OUT, index=False)
print(pd.DataFrame(rows)[["candidate_id", "institution_name_ipeds", "cip6", "control", "size_category"]].to_string(index=False))
