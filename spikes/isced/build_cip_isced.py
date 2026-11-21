"""Build data/reference/cip-isced-f.csv for the in-scope CIP 2020 codes
(11.xxxx, 52.12xx, 30.70xx).

Inputs (all downloaded beforehand, read as data, never executed):
  1. Statistics Canada, CIP Canada 2016 -> ISCED-F 2013 concordance (CSV).
     This is the only official CIP -> ISCED-F table found. It is the Canadian
     interpretation, at the 6-digit CIP / 4-digit ISCED-F level.
  2. Statistics Canada, CIP Canada 2021 v1.0 structure (CSV). CIP Canada 2021
     was harmonized with the US CIP 2020; it gives the list of 6-digit codes in
     scope and a fallback title.
  3. data/reference/dhs-stem-list-2024-07-22.csv (from spike S-3). It quotes the
     US CIP 2020 titles for the codes on the DHS STEM list. Used for cip_title.

Rules:
  - A code that exists in the StatCan 2016 concordance keeps the StatCan pairs
    verbatim: origin = official.
  - A code that is new in CIP 2020 / CIP Canada 2021 gets a curated pair from
    PROPOSALS below: origin = proposed, with a justification in notes.
  - "*" on the StatCan ISCED-F code means the CIP class is only a portion of the
    ISCED-F class. It goes to the `partial` column.

Usage:
  python3 -I spikes/isced/build_cip_isced.py <statcan_concordance.csv> \
      <cip_canada_2021_structure.csv> <dhs_stem_list.csv> <out.csv>
"""

import csv
import sys

STATCAN_URL = ("https://www.statcan.gc.ca/sites/default/files/documents/"
               "cip2016-isced-f-2013-eng.csv")
CIP2021_URL = ("https://www.statcan.gc.ca/en/statistical-programs/document/"
               "cip-cpe-2021-structure-v1-eng.csv")
SCOPE = ("11.", "52.12", "30.70")

# Curated proposals for codes absent from the StatCan 2016 concordance.
# (isced_f_code, partial, justification). These are NOT official.
PROPOSALS = {
    "11.0105": ("0613", True,
                "Proposed. New in CIP 2020 under 11.01 (computing, general). "
                "Designing technology around users is part of software and "
                "applications development and analysis. Alternative: 0688, "
                "since StatCan maps the related 30.3101 Human computer "
                "interaction to 0388."),
    "11.0204": ("0613", True,
                "Proposed. New in CIP 2020 under 11.02 (programming). StatCan "
                "maps every other 11.02xx code (11.0201, 11.0202, 11.0203, "
                "11.0299) to 0613*."),
    "11.0205": ("0613", True,
                "Proposed. New in CIP 2020 under 11.02 (programming). Same "
                "reasoning as 11.0204: StatCan maps all 11.02xx codes to 0613*."),
    "11.0902": ("0612", True,
                "Proposed. Cloud computing is infrastructure design and "
                "administration; StatCan maps network/system administration "
                "codes (11.1001, 11.1002) to 0612*. Alternative: 0619, the "
                "StatCan pair of its parent 11.0901."),
    "11.0999": ("0619", True,
                "Proposed. Residual 'other' code of 11.09; follows the StatCan "
                "pair of 11.0901 (0619*)."),
    "30.7001": ("0688", True,
                "Proposed. Data science combines statistics (0542) and computing "
                "(06). ISCED-F puts programmes with no dominant field in the "
                "x88 inter-disciplinary class; StatCan maps the similar 30.3001 "
                "Computational science to 0688*. Alternative: 0542 Statistics "
                "or 0588. Choosing 0688 keeps it under broad field 06 (ICT)."),
    "30.7099": ("0688", True,
                "Proposed. Residual 'other' code of 30.70; follows 30.7001."),
}


def read_csv(path, encodings=("utf-8-sig", "cp1252")):
    for enc in encodings:
        try:
            with open(path, encoding=enc, newline="") as fh:
                return list(csv.DictReader(fh))
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"cannot decode {path}")


def main(statcan_path, cip2021_path, dhs_path, out_path):
    conc = read_csv(statcan_path)
    struct = read_csv(cip2021_path)
    dhs = read_csv(dhs_path)

    isced_titles = {}
    pairs = {}
    titles_2016 = {}
    for r in conc:
        code = r["CIP Canada 2016 Code"].strip()
        isced = r["ISCED-F 2013 Code"].strip()
        isced_titles[isced.rstrip("*")] = r["ISCED-F 2013 Title"].strip()
        titles_2016[code] = r["CIP Canada 2016 Title"].strip()
        pairs.setdefault(code, []).append(
            (isced.rstrip("*"), isced.endswith("*"),
             r["Explanatory Notes"].strip()))

    us_titles = {r["cip_code"].strip(): r["title"].strip().rstrip(".")
                 for r in dhs if r.get("level", "6") == "6"}
    scope = [(r["Code"].strip(), r["Class title"].strip(), r["Superscript"])
             for r in struct
             if r["Level"] == "3" and r["Code"].startswith(SCOPE)]

    out = []
    for code, ca_title, sup in scope:
        if sup.strip() == "CAN":
            continue  # Canada-only class, not in the US CIP 2020
        if code in us_titles:
            title, tnote = us_titles[code], ""
        else:
            title = ca_title
            tnote = ("cip_title from CIP Canada 2021 (code not on the DHS STEM "
                     "list); confirm against NCES CIP 2020. ")
        if code in pairs:
            for isced, partial, expl in pairs[code]:
                note = tnote + "Pair copied from the StatCan CIP Canada 2016 "
                note += "concordance; the code also exists in CIP 2020."
                if titles_2016[code].lower() != ca_title.lower():
                    note += (f" CIP Canada 2016 title was '{titles_2016[code]}'.")
                if expl:
                    note += f" StatCan note: {expl}."
                out.append([code, title, isced, isced_titles[isced], "official",
                            STATCAN_URL, str(partial).lower(), note])
        elif code in PROPOSALS:
            isced, partial, why = PROPOSALS[code]
            if isced not in isced_titles:
                raise SystemExit(f"ISCED-F code {isced} has no title in source")
            out.append([code, title, isced, isced_titles[isced], "proposed",
                        "north curation; ISCED-F title from " + STATCAN_URL,
                        str(partial).lower(), tnote + why])
        else:
            raise SystemExit(f"no mapping for {code} {title}")

    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cip_code", "cip_title", "isced_f_code", "isced_f_title",
                    "origin", "source", "partial", "notes"])
        w.writerows(out)
    n_off = sum(1 for r in out if r[4] == "official")
    print(f"{len(out)} rows ({n_off} official, {len(out) - n_off} proposed) "
          f"for {len({r[0] for r in out})} CIP codes -> {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
