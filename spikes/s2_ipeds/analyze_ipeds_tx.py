"""S-2: IPEDS master's completions in Texas (UNITID x 6-digit CIP x AWLEVEL 7),
graduate tuition (IC_AY), comparison with the Scorecard FoS list, and a cross-check
against the Urban Institute mirror.

Usage (from the project root, after download_ipeds.sh, fetch_urban_ipeds.py and the S-1 script):
  uv run --with pandas python -I spikes/s2_ipeds/analyze_ipeds_tx.py \
      spikes/_raw/ipeds spikes/s1_scorecard/out/tx_masters_target_scorecard.csv spikes/s2_ipeds/out

Reads the CSVs straight out of the NCES zip files; nothing from the downloads is executed.
Files used: C2024_A (completions AY2023-24), HD2024 (directory), IC2023_AY (charges 2023-24).
"""
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

RAW, SC, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)

CONTROL = {"1": "Public", "2": "Private nonprofit", "3": "Private for-profit"}
# INSTSIZE labels from HD2024 dictionary / Urban codebook (same coding).
INSTSIZE = {"1": "Under 1,000", "2": "1,000-4,999", "3": "5,000-9,999", "4": "10,000-19,999",
            "5": "20,000 and above"}


def read_zip_csv(name):
    with zipfile.ZipFile(RAW / f"{name}.zip") as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        # Some IPEDS zips ship a revised "_rv" file next to the original; prefer it.
        pick = sorted(csvs, key=lambda n: ("_rv" not in n.lower(), n))[0]
        with z.open(pick) as f:
            df = pd.read_csv(f, dtype=str, keep_default_na=False, encoding="utf-8-sig", encoding_errors="replace")
    df.columns = [c.strip().upper() for c in df.columns]
    return df.apply(lambda s: s.str.strip()), pick


def family(cip):
    c = cip.replace(".", "")
    if c.startswith("11"):
        return "11.xx computing"
    if c.startswith("5212"):
        return "52.12 information systems"
    if c.startswith("3070"):
        return "30.70 data science"
    return None


def num(s):
    return pd.to_numeric(s, errors="coerce")


res = {}
c, cfile = read_zip_csv("C2024_A")
hd, hfile = read_zip_csv("HD2024")
ay, ayfile = read_zip_csv("IC2023_AY")
res["files"] = {"completions": cfile, "directory": hfile, "ic_ay": ayfile}
res["completions_rows_total"] = len(c)

# AWLEVEL 7 = "Master's degree" (C2024_A dictionary, Frequencies sheet).
c = c[(c["AWLEVEL"] == "7") & (c["CIPCODE"] != "99")].copy()
for col in ("CTOTALT", "CNRALT"):
    c[col] = num(c[col]).fillna(0).astype(int)
c["first"] = c["MAJORNUM"].eq("1")
agg = (c.groupby(["UNITID", "CIPCODE"])
         .apply(lambda g: pd.Series({
             "completions_total": int(g["CTOTALT"].sum()),
             "completions_first_major": int(g.loc[g["first"], "CTOTALT"].sum()),
             "completions_nonresident": int(g["CNRALT"].sum())}), include_groups=False)
         .reset_index())
hd = hd[["UNITID", "INSTNM", "CITY", "STABBR", "CONTROL", "OPEID", "WEBADDR", "INSTSIZE", "CYACTIVE",
         "LATITUDE", "LONGITUD"]]
m = agg.merge(hd, on="UNITID", how="left")
tx = m[m["STABBR"] == "TX"].copy()
tx["family"] = tx["CIPCODE"].map(family)
res["tx_masters_all_cips"] = {"unitid_cip6_rows": len(tx), "institutions": tx["UNITID"].nunique()}

t = tx[tx["family"].notna()].copy()
t["cip4"] = t["CIPCODE"].str.replace(".", "", regex=False).str[:4]
t["control_label"] = t["CONTROL"].map(CONTROL)
t["size_label"] = t["INSTSIZE"].map(INSTSIZE)

# Graduate tuition, 2023-24 (IC2023_AY): TUITION6 in-state, TUITION7 out-of-state, FEE6/FEE7 fees.
tcols = ["TUITION6", "FEE6", "TUITION7", "FEE7", "HRCHG7"]
t = t.merge(ay[["UNITID"] + tcols], on="UNITID", how="left")


def tstatus(v):
    if pd.isna(v) or v in ("", "."):
        return "missing"
    x = pd.to_numeric(v, errors="coerce")
    return "value" if pd.notna(x) and x > 0 else "zero_or_not_applicable"


by_family = {}
for f, g in list(t.groupby("family")) + [("TOTAL", t)]:
    inst = g.drop_duplicates("UNITID")
    by_family[f] = {
        "programs_unitid_cip6": len(g),
        "programs_unitid_cip6_with_completions": int((g["completions_total"] > 0).sum()),
        "programs_unitid_cip4": g[["UNITID", "cip4"]].drop_duplicates().shape[0],
        "institutions": g["UNITID"].nunique(),
        "institutions_by_control": inst["control_label"].value_counts().to_dict(),
        "cip6": g["CIPCODE"].value_counts().to_dict(),
        "completions_total": int(g["completions_total"].sum()),
        "completions_nonresident": int(g["completions_nonresident"].sum()),
        "grad_tuition_out_of_state_TUITION7": inst["TUITION7"].map(tstatus).value_counts().to_dict(),
    }
res["tx_masters_by_family"] = by_family

# Comparison with Scorecard FoS (4-digit CIP, CREDLEV 5).
sc = pd.read_csv(SC, dtype=str, keep_default_na=False)
sc_keys = set(zip(sc["UNITID"], sc["CIPCODE"]))
ip_keys = set(zip(t["UNITID"], t["cip4"]))
pos = t[t["completions_total"] > 0]
ip_pos = set(zip(pos["UNITID"], pos["cip4"]))
names = dict(zip(t["UNITID"], t["INSTNM"]))
names.update(dict(zip(sc["UNITID"], sc["INSTNM"])))
res["compare_scorecard_vs_ipeds_unitid_cip4"] = {
    "scorecard_rows": len(sc_keys), "ipeds_rows": len(ip_keys), "ipeds_rows_with_completions": len(ip_pos),
    "in_both": len(sc_keys & ip_keys),
    "only_scorecard": sorted([u, cp, names.get(u, "")] for u, cp in sc_keys - ip_keys),
    "only_ipeds": sorted([u, cp, names.get(u, "")] for u, cp in ip_keys - sc_keys),
    "scorecard_institutions": sc["UNITID"].nunique(), "ipeds_institutions": t["UNITID"].nunique(),
    "cip6_per_unitid_cip4_max": int(t.groupby(["UNITID", "cip4"]).size().max()),
    "unitid_cip4_with_more_than_one_cip6": int((t.groupby(["UNITID", "cip4"]).size() > 1).sum()),
}

# Does Scorecard IPEDSCOUNT2 (AY2023-24) equal the NCES C2024_A sum per UNITID x CIP4?
ic4 = t.groupby(["UNITID", "cip4"])["completions_total"].sum()
sc2 = sc.set_index(["UNITID", "CIPCODE"])["IPEDSCOUNT2"]
sc2 = pd.to_numeric(sc2, errors="coerce")
jj = pd.concat([ic4.rename("nces"), sc2.rename("scorecard")], axis=1, join="inner").dropna()
res["compare_ipedscount2_vs_c2024"] = {"pairs_compared": len(jj),
                                        "equal": int((jj["nces"] == jj["scorecard"]).sum())}

# Cross-check with the Urban mirror (same AY2023-24), if it was fetched.
urban = RAW / "urban" / "completions_cip6_masters_48_2023.json"
if urban.exists():
    u = pd.DataFrame(json.loads(urban.read_text())["results"])
    u = u[u["cipcode_6digit"] != 99]
    u["cip"] = u["cipcode_6digit"].astype(int).map(lambda x: f"{x:06d}")
    u["cip"] = u["cip"].str[:2].str.lstrip("0").str.zfill(2) + "." + u["cip"].str[2:]
    u["family"] = u["cip"].map(family)
    u = u[u["family"].notna()]
    ug = u.groupby(["unitid", "cip"])["awards_6digit"].sum()
    ig = t.assign(u=t["UNITID"].astype(int)).groupby(["u", "CIPCODE"])["completions_total"].sum()
    j = pd.concat([ug.rename("urban"), ig.rename("nces")], axis=1)
    res["urban_crosscheck"] = {"pairs_urban": len(ug), "pairs_nces": len(ig),
                               "pairs_matching_exactly": int((j["urban"] == j["nces"]).sum()),
                               "sum_urban": int(ug.sum()), "sum_nces": int(ig.sum())}

t.sort_values(["family", "INSTNM", "CIPCODE"]).to_csv(OUT / "tx_masters_target_ipeds.csv", index=False)
(OUT / "summary_ipeds.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
print(json.dumps(res, indent=2, ensure_ascii=False))
