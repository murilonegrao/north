"""S-8: every award level and every field in the US official sources.

Counts, for Texas and nationally, IPEDS programs (UNITID x CIP6) by award level for
North's current tech CIPs and for all CIPs; nonresident graduates by level; the
College Scorecard Field of Study rows and earnings suppression by credential level;
the ESL CIP codes in IPEDS; and language-school signals in the parsed SEVP list.

Usage (from the project root):
  uv run --with pandas,openpyxl python -I spikes/s8_us_levels/analyze_levels.py \
      spikes/_raw spikes/s8_us_levels/out

Inputs (all git-ignored, already downloaded by earlier spikes):
  ipeds/C2024_A.zip, ipeds/C2024_A_Dict.zip, ipeds/HD2024.zip, ipeds/IC2023_AY.zip,
  ipeds/IC2023_AY_Dict.zip, scorecard/fos/Most-Recent-Cohorts-Field-of-Study.csv,
  scorecard/inst/Most-Recent-Cohorts-Institution.csv,
  sevp/derived/sevp-certified-schools-2026-11-18.csv (output of spikes/s4_sevp).
Nothing from the downloads is executed; files are read as data only.
"""
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

RAW, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
STATE = "TX"
res = {}


def read_zip_csv(path):
    with zipfile.ZipFile(path) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        pick = sorted(csvs, key=lambda n: ("_rv" not in n.lower(), n))[0]
        with z.open(pick) as f:
            df = pd.read_csv(f, dtype=str, keep_default_na=False, encoding="utf-8-sig",
                             encoding_errors="replace")
    df.columns = [c.strip().upper() for c in df.columns]
    return df.apply(lambda s: s.str.strip()), pick


def read_zip_xlsx(path, sheet):
    with zipfile.ZipFile(path) as z:
        name = [n for n in z.namelist() if n.lower().endswith(".xlsx")][0]
        return pd.read_excel(io.BytesIO(z.read(name)), sheet_name=sheet, dtype=str)


def num(s):
    # "" and "." are "not reported" (BR-02): they become NaN, never 0.
    return pd.to_numeric(s.replace({"": None, ".": None}), errors="coerce")


def is_tech(cip):
    c = cip.replace(".", "")
    return c.startswith("11") or c.startswith("5212") or c.startswith("3070") or c.startswith("3071")


# ---------------------------------------------------------------- IPEDS dictionary
freq = read_zip_xlsx(RAW / "ipeds/C2024_A_Dict.zip", "Frequencies")
freq.columns = [c.strip() for c in freq.columns]
aw = freq[freq["VarName"].str.strip().str.upper() == "AWLEVEL"]
AWLABEL = {str(r["CodeValue"]).strip(): str(r["ValueLabel"]).strip() for _, r in aw.iterrows()}
res["awlevel_dictionary_C2024_A"] = AWLABEL

# ---------------------------------------------------------------- IPEDS completions
c, cfile = read_zip_csv(RAW / "ipeds/C2024_A.zip")
hd, hfile = read_zip_csv(RAW / "ipeds/HD2024.zip")
res["files"] = {"completions": cfile, "directory": hfile}
res["completions_rows_total"] = len(c)
res["awlevel_values_in_data"] = c["AWLEVEL"].value_counts().sort_index().to_dict()

c = c[c["CIPCODE"] != "99"].copy()  # 99 = grand total row
c["CTOTALT_N"] = num(c["CTOTALT"])
c["CNRALT_N"] = num(c["CNRALT"])
c = c.merge(hd[["UNITID", "STABBR"]], on="UNITID", how="left")
c["TECH"] = c["CIPCODE"].map(is_tech)

# One program = UNITID x CIP6 x AWLEVEL; first and second majors are summed.
prog = (c.groupby(["UNITID", "STABBR", "CIPCODE", "AWLEVEL", "TECH"], dropna=False)
        .agg(ctotal=("CTOTALT_N", lambda s: s.sum(min_count=1)),
             cnral=("CNRALT_N", lambda s: s.sum(min_count=1)))
        .reset_index())
(RAW / "ipeds/derived").mkdir(exist_ok=True)
prog.to_csv(RAW / "ipeds/derived/ipeds_programs_all_levels.csv.gz", index=False, compression="gzip")


def level_table(df):
    rows = []
    for lv, g in df.groupby("AWLEVEL"):
        rows.append({
            "awlevel": lv,
            "label": AWLABEL.get(lv, "?"),
            "programs": len(g),
            "with_completions_gt0": int((g["ctotal"] > 0).sum()),
            "with_completions_0": int((g["ctotal"] == 0).sum()),
            "completions_unknown": int(g["ctotal"].isna().sum()),
            "institutions": g["UNITID"].nunique(),
            "completions": int(g["ctotal"].sum()),
            "nonresident": int(g["cnral"].sum()),
        })
    out = pd.DataFrame(rows)
    out["nonresident_pct"] = (100 * out["nonresident"] / out["completions"].where(out["completions"] > 0)).round(1)
    return out.sort_values("awlevel", key=lambda s: s.astype(int))


tx = prog[prog["STABBR"] == STATE]
tables = {
    "tx_tech": level_table(tx[tx["TECH"]]),
    "tx_all": level_table(tx),
    "us_tech": level_table(prog[prog["TECH"]]),
    "us_all": level_table(prog),
}
for k, t in tables.items():
    t.to_csv(OUT / f"levels_{k}.csv", index=False)
    res[f"levels_{k}"] = t.to_dict(orient="records")
res["totals"] = {k: {"programs": int(t["programs"].sum()),
                     "with_completions_gt0": int(t["with_completions_gt0"].sum()),
                     "institutions": int((tx if k.startswith("tx") else prog)
                                         .pipe(lambda d: d[d["TECH"]] if k.endswith("tech") else d)
                                         ["UNITID"].nunique())}
                 for k, t in tables.items()}
res["us_distinct_cip6_reported"] = int(prog["CIPCODE"].nunique())
res["us_institutions_reporting"] = int(prog["UNITID"].nunique())
res["unitid_without_state"] = int(prog["STABBR"].isna().sum())

# Programs whose CIP6 is on the DHS STEM list (S-3 output, in the repository).
STEM_CSV = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("data/reference/dhs-stem-list-2024-07-22.csv")
stem = set(pd.read_csv(STEM_CSV, dtype=str).query("level == '6'")["cip_code"])
prog["STEM"] = prog["CIPCODE"].isin(stem)
res["dhs_stem_programs"] = {
    "stem_list_codes": len(stem),
    "us": int(prog["STEM"].sum()), "tx": int((prog["STEM"] & (prog["STABBR"] == STATE)).sum()),
    "us_awlevel18": int((prog["STEM"] & (prog["AWLEVEL"] == "18")).sum()),
}

# ESL-related CIP codes in completions. 16.1701 is ESL for credit (new in CIP 2020);
# 32.01xx are "not valid for IPEDS reporting" per the CIP 2020 definitions.
esl = prog[prog["CIPCODE"].str.match(r"^(16\.17|32\.)")]
res["esl_cip_rows"] = {
    "us_by_cip_level": esl.groupby(["CIPCODE", "AWLEVEL"]).size().reset_index(name="programs")
                          .to_dict(orient="records"),
    "us_completions": int(esl["ctotal"].sum()),
    "us_nonresident": int(esl["cnral"].sum()),
    "tx_programs": int((esl["STABBR"] == STATE).sum()),
}

# ---------------------------------------------------------------- IC_AY by level
ay, ayfile = read_zip_csv(RAW / "ipeds/IC2023_AY.zip")
res["files"]["ic_ay"] = ayfile
ay = ay.merge(hd[["UNITID", "STABBR"]], on="UNITID", how="left")
aytx = ay[ay["STABBR"] == STATE]
fill = {}
for col in ["CHG3AY3", "TUITION3", "TUITION7", "OSPROF3", "OSPROF6", "OSPROF9"]:
    if col in ay.columns:
        v = num(aytx[col])
        fill[col] = {"tx_rows": len(aytx), "with_value": int(v.notna().sum())}
res["ic_ay_tx_fill"] = fill

# ---------------------------------------------------------------- Scorecard FoS
fos = pd.read_csv(RAW / "scorecard/fos/Most-Recent-Cohorts-Field-of-Study.csv", dtype=str,
                  keep_default_na=False, encoding="utf-8-sig",
                  usecols=["UNITID", "CIPCODE", "CREDLEV", "CREDDESC", "IPEDSCOUNT2",
                           "EARN_MDN_1YR", "EARN_MDN_4YR", "DISTANCE"])
inst = pd.read_csv(RAW / "scorecard/inst/Most-Recent-Cohorts-Institution.csv", dtype=str,
                   keep_default_na=False, encoding="utf-8-sig", usecols=["UNITID", "STABBR"])
fos = fos.merge(inst, on="UNITID", how="left")
fos["TECH"] = fos["CIPCODE"].map(is_tech)


def fos_table(df):
    rows = []
    for (lv, desc), g in df.groupby(["CREDLEV", "CREDDESC"]):
        e1 = g["EARN_MDN_1YR"]
        rows.append({"credlev": lv, "creddesc": desc, "rows": len(g),
                     "institutions": g["UNITID"].nunique(),
                     "earn1_value": int((~e1.isin(["PS", "NA", ""])).sum()),
                     "earn1_PS": int((e1 == "PS").sum()),
                     "earn1_NA": int(e1.isin(["NA", ""]).sum())})
    out = pd.DataFrame(rows)
    out["earn1_suppressed_pct"] = (100 * out["earn1_PS"] / out["rows"]).round(1)
    out["earn1_value_pct"] = (100 * out["earn1_value"] / out["rows"]).round(1)
    return out.sort_values("credlev", key=lambda s: s.astype(int))


ftx = fos[fos["STABBR"] == STATE]
for k, df in {"tx_all": ftx, "tx_tech": ftx[ftx["TECH"]], "us_all": fos}.items():
    t = fos_table(df)
    t.to_csv(OUT / f"scorecard_{k}.csv", index=False)
    res[f"scorecard_{k}"] = t.to_dict(orient="records")
res["scorecard_rows_total"] = len(fos)

# ---------------------------------------------------------------- SEVP language schools
sevp = pd.read_csv(RAW / "sevp/derived/sevp-certified-schools-2026-11-18.csv", dtype=str,
                   keep_default_na=False)
LANG = re.compile(r"\b(?:english|language|languages|esl|els|intensive|linguistic|toefl|lingua|idioma)\b", re.I)
sevp["lang_name"] = (sevp["school_name"] + " " + sevp["campus_name"]).str.contains(LANG)
fm = lambda d: (d["f_1"] + "/" + d["m_1"]).value_counts().to_dict()
res["sevp"] = {
    "campuses": len(sevp),
    "f_m_split": fm(sevp),
    "name_keyword_campuses_us": int(sevp["lang_name"].sum()),
    "name_keyword_school_codes_us": int(sevp.loc[sevp["lang_name"], "school_code"].nunique()),
    "name_keyword_f_m_us": fm(sevp[sevp["lang_name"]]),
    "tx_campuses": int((sevp["state"] == STATE).sum()),
    "name_keyword_campuses_tx": int((sevp["lang_name"] & (sevp["state"] == STATE)).sum()),
    "name_keyword_f_m_tx": fm(sevp[sevp["lang_name"] & (sevp["state"] == STATE)]),
}
hd_lang = hd[hd["INSTNM"].str.contains(LANG)]
res["ipeds_hd_language_name_hits"] = hd_lang[["UNITID", "INSTNM", "STABBR"]].to_dict(orient="records")
sevp[sevp["lang_name"] & (sevp["state"] == STATE)][
    ["school_name", "campus_name", "f_1", "m_1", "city", "campus_code"]
].to_csv(OUT / "sevp_tx_language_name_hits.csv", index=False)

(OUT / "summary_levels.json").write_text(json.dumps(res, indent=2, default=str))
for k, t in tables.items():
    print(f"\n== IPEDS {k}\n{t.to_string(index=False)}")
for k in ["scorecard_tx_all", "scorecard_tx_tech", "scorecard_us_all"]:
    print(f"\n== {k}\n{pd.DataFrame(res[k]).to_string(index=False)}")
print(json.dumps({k: res[k] for k in ["totals", "us_distinct_cip6_reported", "us_institutions_reporting",
                                      "unitid_without_state", "awlevel_values_in_data", "esl_cip_rows",
                                      "ic_ay_tx_fill", "dhs_stem_programs", "sevp", "ipeds_hd_language_name_hits", "scorecard_rows_total"]}, indent=1, default=str))
