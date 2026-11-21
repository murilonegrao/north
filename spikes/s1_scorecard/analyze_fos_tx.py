"""S-1: College Scorecard master's-by-program (Field of Study) coverage in Texas.

Usage (from the project root):
  uv run --with pandas python -I spikes/s1_scorecard/analyze_fos_tx.py \
      spikes/_raw/scorecard/fos/Most-Recent-Cohorts-Field-of-Study.csv \
      spikes/_raw/scorecard/inst/Most-Recent-Cohorts-Institution.csv \
      spikes/s1_scorecard/out

Input files are untrusted data: they are only parsed as CSV, nothing in them is executed.
"""
import json
import sys
from pathlib import Path

import pandas as pd

FOS, INST, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)

COLS = ["UNITID", "OPEID6", "INSTNM", "CONTROL", "MAIN", "CIPCODE", "CIPDESC",
        "CREDLEV", "CREDDESC", "IPEDSCOUNT1", "IPEDSCOUNT2", "DISTANCE",
        "EARN_COUNT_WNE_1YR", "EARN_MDN_1YR", "EARN_MDN_4YR", "EARN_MDN_5YR",
        "EARN_MDN_HI_1YR", "EARN_MDN_HI_2YR", "DEBT_ALL_STGP_EVAL_MDN", "DEBT_ALL_STGP_EVAL_N"]

fos = pd.read_csv(FOS, usecols=COLS, dtype=str, keep_default_na=False)
inst = pd.read_csv(INST, usecols=["UNITID", "STABBR", "CITY", "INSTNM"], dtype=str,
                   keep_default_na=False).rename(columns={"INSTNM": "INSTNM_INST"})

res = {"fos_rows_total": len(fos),
       "credlev_values": fos["CREDLEV"].value_counts().to_dict(),
       "cipcode_lengths": {str(k): v for k, v in fos["CIPCODE"].str.len().value_counts().items()},
       "cipcode_examples": fos["CIPCODE"].head(5).tolist()}

# The FoS file has no state column: join with the institution file on UNITID.
df = fos.merge(inst, on="UNITID", how="left")
res["fos_rows_without_institution_match"] = int(df["STABBR"].isna().sum() + df["STABBR"].eq("").sum())

ms = df[(df["STABBR"] == "TX") & (df["CREDLEV"] == "5")].copy()  # CREDLEV 5 = Master's Degree
res["tx_masters_rows_all_cips"] = len(ms)
res["tx_masters_institutions_all_cips"] = ms["UNITID"].nunique()


def family(c):
    # FoS CIPCODE is 4 digits without a dot (e.g. "1107").
    c = c.replace(".", "")
    if c.startswith("11"):
        return "11.xx computing"
    if c.startswith("5212"):
        return "52.12 information systems"
    if c.startswith("3070"):
        return "30.70 data science"
    return None


def status(v):
    # In the 2026 FoS file missing values are "NA" and privacy suppression is "PS"
    # (older releases used "NULL" and "PrivacySuppressed").
    if v in ("", "NA") or v.upper() == "NULL":
        return "null"
    if v in ("PS", "PrivacySuppressed"):
        return "suppressed"
    return "value"


ms["family"] = ms["CIPCODE"].map(family)
target = ms[ms["family"].notna()].copy()

metric_cols = ["EARN_MDN_1YR", "EARN_MDN_4YR", "EARN_MDN_5YR", "EARN_MDN_HI_1YR", "EARN_MDN_HI_2YR",
               "DEBT_ALL_STGP_EVAL_MDN", "IPEDSCOUNT1", "IPEDSCOUNT2"]
by_family = {}
for f, g in list(target.groupby("family")) + [("TOTAL", target)]:
    d = {"programs": len(g), "institutions": g["UNITID"].nunique(),
         "by_control": g["CONTROL"].value_counts().to_dict(),
         "cips": g["CIPCODE"].value_counts().to_dict(),
         "distance": g["DISTANCE"].value_counts().to_dict()}
    for c in metric_cols:
        d[c] = g[c].map(status).value_counts().to_dict()
    by_family[f] = d
res["tx_masters_by_family"] = by_family
res["distinct_non_numeric_values"] = sorted(
    {v for c in metric_cols for v in target[c].unique() if not v.replace(".", "").isdigit()})

# National baseline: master's in the same CIP families, all states.
nat = df[(df["CREDLEV"] == "5") & df["CIPCODE"].map(family).notna()]
res["national_masters_target"] = {
    "programs": len(nat),
    "EARN_MDN_1YR": nat["EARN_MDN_1YR"].map(status).value_counts().to_dict()}

target.sort_values(["family", "INSTNM", "CIPCODE"]).to_csv(OUT / "tx_masters_target_scorecard.csv", index=False)
(OUT / "summary_scorecard.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
print(json.dumps(res, indent=2, ensure_ascii=False))
