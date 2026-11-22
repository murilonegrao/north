"""S-7: Irish lists of programmes eligible for a study permission (Stamp 2).

Two official lists, same 15-column layout:
  * ILEP, Interim List of Eligible Programmes (Immigration Service Delivery,
    Department of Justice). Closed to new providers; being replaced by TrustEd.
  * TrustEd Ireland "List of Eligible Programmes" (QQI). Despite the file name
    ("he-list") it also carries Foundation and English language programmes.
"Eligible programmes will not appear on both lists" (both official pages).

Download (only if the file is not there yet; generic user agent, robots.txt
crawl-delay of 10 s on irishimmigration.ie is respected):

    python3 -I spikes/s7_ie_lists/profile_ie_lists.py --download \
        --raw-dir spikes/_raw --out-dir spikes/s7_ie_lists/out

Profile only (files already present):

    uv run --with openpyxl python -I spikes/s7_ie_lists/profile_ie_lists.py \
        --raw-dir spikes/_raw --out-dir spikes/s7_ie_lists/out

Personal data: columns "Contact Email", "Contact Telephone" and "Contact Name"
are never printed or written; only their fill rate is reported. The output
CSV (written to <raw-dir>/ie_derived/, not committed) keeps only
non-personal columns. "Addresss" (sic) is an institutional
postal address; only the derived city/county is written out.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import time
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

UA = "north-research-spike"

ILEP_PAGE = (
    "https://www.irishimmigration.ie/coming-to-study-in-ireland/"
    "what-are-my-study-options/a-third-level-course-or-a-language-course/"
)
ILEP_XLSX = (
    "https://www.irishimmigration.ie/wp-content/uploads/2026/09/"
    "Interim-List-of-Eligible-Programmes-updated-22-September-2026.xlsx"
)
TRUSTED_PAGE = "https://www.trustedireland.ie/check-eligible-courses-for-study-visas"
TRUSTED_XLSX = (
    "https://www.trustedireland.ie/sites/default/files/2026-02/"
    "trusted-ireland-he-list-of-eligible-programmes.xlsx"
)
TRUSTED_PROVIDER_PAGES = {
    "el_institutions.html": "https://www.trustedireland.ie/trusted-providers/english-language-education-institutions",
    "he_institutions_p0.html": "https://www.trustedireland.ie/trusted-providers/higher-education-institutions",
    "he_institutions_p1.html": "https://www.trustedireland.ie/trusted-providers/higher-education-institutions?page=1",
    "he_institutions_p2.html": "https://www.trustedireland.ie/trusted-providers/higher-education-institutions?page=2",
}

PERSONAL = {"contact email", "contact telephone", "contact name"}

COUNTIES = [
    "Dublin",
    "Cork",
    "Galway",
    "Limerick",
    "Waterford",
    "Kildare",
    "Meath",
    "Wicklow",
    "Louth",
    "Kerry",
    "Clare",
    "Tipperary",
    "Wexford",
    "Kilkenny",
    "Carlow",
    "Laois",
    "Offaly",
    "Westmeath",
    "Longford",
    "Roscommon",
    "Sligo",
    "Leitrim",
    "Mayo",
    "Donegal",
    "Cavan",
    "Monaghan",
]
# Towns that appear in addresses without the county name.
TOWN_COUNTY = {
    "maynooth": "Kildare",
    "athlone": "Westmeath",
    "dundalk": "Louth",
    "tralee": "Kerry",
    "letterkenny": "Donegal",
    "carlow": "Carlow",
    "thurles": "Tipperary",
    "dun laoghaire": "Dublin",
    "dún laoghaire": "Dublin",
    "blackrock": "Dublin",
    "dalkey": "Dublin",
    "sandyford": "Dublin",
    "swords": "Dublin",
    "tallaght": "Dublin",
    "blanchardstown": "Dublin",
    "bray": "Wicklow",
    "ennis": "Clare",
    "castlebar": "Mayo",
    "moylish": "Limerick",
    "clonmel": "Tipperary",
    "drogheda": "Louth",
}
# Eircode routing keys of County Dublin (D01-D24, D6W and the county keys).
DUBLIN_KEYS = {f"D{n:02d}" for n in range(1, 25)} | {
    "D6W",
    "A94",
    "A96",
    "K32",
    "K34",
    "K36",
    "K45",
    "K56",
    "K67",
    "K78",
}

AWARD_PATTERNS = [
    ("doctorate", r"\b(phd|ph\.d|doctor|doctorate|dprof|md\b|dba\b|edd|dclinpsych|dmus|dpsych)"),
    (
        "master",
        r"\b(master|msc|m\.sc|ma\b|mba|mbs|meng|mph|mres|llm|mphil|med\b|march|mfa|mlitt|mmus|msw|mst|mtech|mpharm|mbus|m\.a\.)",
    ),
    (
        "postgraduate_diploma",
        r"(postgraduate diploma|post graduate diploma|pgdip|pg dip|graduate diploma|higher diploma|h\.?dip|professional diploma|pme\b)",
    ),
    (
        "postgraduate_certificate",
        r"(postgraduate certificate|post graduate certificate|pgcert|pg cert|graduate certificate)",
    ),
    (
        "bachelor_honours",
        r"(bachelor.*hon|\(hons\)|honours|b\.?a\.? ?\(?hons|bsc ?\(?hons|mb ?bch|bds\b|bcl\b|llb\b|beng\b|bmus)",
    ),
    ("bachelor_ordinary", r"(bachelor|\bba\b|\bbsc\b|\bbbs\b|\bbcomm|\bbeng\b|b\.?sc|b\.?a\b)"),
    ("higher_certificate", r"higher certificate"),
    ("certificate_diploma_other", r"(certificate|diploma|cert\b)"),
]


def norm(s: object) -> str:
    if s is None:
        return ""
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    t = t.replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def clean(s: object) -> str:
    return "" if s is None else re.sub(r"\s+", " ", str(s)).strip()


def fetch(url: str, dest: Path, delay: float) -> None:
    if dest.exists():
        print(f"present: {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
        print(
            f"GET {url} -> {resp.status}, {len(data)} bytes, "
            f"Last-Modified {resp.headers.get('Last-Modified')}"
        )
    dest.write_bytes(data)
    time.sleep(delay)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_list(path: Path) -> tuple[str, list[str], list[dict]]:
    import openpyxl  # imported here so --download works without it

    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    title = clean(rows[0][0])
    header = [clean(h) for h in rows[1]]
    data = []
    for r in rows[2:]:
        if not any(c not in (None, "") for c in r):
            continue
        data.append({header[i]: r[i] for i in range(len(header))})
    return title, header, data


def county_of(address: str) -> str:
    a = address
    m = re.search(r"\b([AC-FHKNPRTV-Y]\d{2}|D6W)\s?[0-9AC-FHKNPRTV-Y]{4}\b", a.upper())
    if m and m.group(1) in DUBLIN_KEYS:
        return "Dublin"
    if re.search(r"\bdublin\b|\bd\s?\d{1,2}\b", a, re.I):
        return "Dublin"
    for c in COUNTIES:
        if re.search(rf"\b{c}\b", a, re.I):
            return c
    low = a.lower()
    for town, c in TOWN_COUNTY.items():
        if town in low:
            return c
    return "unknown"


def nfq(value: object) -> str:
    v = clean(value)
    m = re.fullmatch(r"(?:level\s*)?(\d{1,2})\b.*", v, re.I)
    if m and 1 <= int(m.group(1)) <= 10:
        return m.group(1)
    if v.lower() in ("n/a", "na", "not applicable"):
        return "n/a"
    return "other:" + (v[:30] if v else "(empty)")


def award_kind(award_title: str, programme_title: str, ptype: str) -> str:
    if ptype.lower().startswith("english"):
        return "english_language"
    if ptype.lower().startswith("foundation"):
        return "foundation"
    if ptype.lower().startswith("professional"):
        return "professional"
    for text in (award_title, programme_title):
        t = text.lower()
        for kind, pat in AWARD_PATTERNS:
            if re.search(pat, t):
                return kind
    return "unclassified"


def duration(value: object) -> tuple[str, float | None]:
    v = clean(value).lower()
    if not v or v in ("n/a", "na", "not applicable"):
        return ("none", None)
    if "research" in v:
        return ("research", None)
    m = re.search(r"(\d+(?:\.\d+)?)\s*ects", v) or re.fullmatch(r"(\d+(?:\.\d+)?)", v)
    if m:
        return ("ects", float(m.group(1)))
    m = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(weeks?|wks?)", v) or re.search(r"^(\d+)\s*\+", v)
    if m:
        return ("weeks", float(m.group(1)))
    return ("other", None)


def ptype_norm(v: object) -> str:
    t = norm(v)
    if "english" in t:
        return "English Language"
    if "foundation" in t:
        return "Foundation"
    if "professional" in t:
        return "Professional"
    if "non" in t and "major" in t:
        return "Higher education - Non-major award"
    if "major" in t:
        return "Higher education - Major award"
    return clean(v) or "(empty)"


def provider_key(name: str) -> str:
    t = norm(name)
    t = re.sub(r"\b(the|ltd|limited|t a|dac|clg|teoranta)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def profile(name: str, title: str, header: list[str], data: list[dict]) -> dict:
    ref_col = header[0]
    out: dict = {"title": title, "rows": len(data), "header": header}
    out["fill_rate"] = {h: sum(1 for r in data if clean(r.get(h))) for h in header}
    for r in data:
        r["_type"] = ptype_norm(r.get("Programme Type"))
        r["_nfq"] = nfq(r.get("NFQ Level"))
        r["_county"] = county_of(clean(r.get("Addresss")))
        r["_award"] = award_kind(
            clean(r.get("Award Title")), clean(r.get("Programme Title")), r["_type"]
        )
        r["_dur_unit"], r["_dur"] = duration(r.get("Duration (ECTS /Weeks per year)"))
        ref = clean(r.get(ref_col))
        r["_ref"] = ref
        m = re.fullmatch(r"(TE)?(\d{4})/(\d{4})", ref)
        r["_prov_code"] = (m.group(1) or "") + m.group(2) if m else ""
    out["programme_type_raw"] = Counter(clean(r.get("Programme Type")) for r in data).most_common()
    out["programme_type"] = Counter(r["_type"] for r in data).most_common()
    out["nfq_level"] = Counter(r["_nfq"] for r in data).most_common()
    out["nfq_by_type"] = {
        t: Counter(r["_nfq"] for r in data if r["_type"] == t).most_common()
        for t in sorted({r["_type"] for r in data})
    }
    out["award_kind"] = Counter(r["_award"] for r in data).most_common()
    out["award_kind_by_nfq"] = {
        lv: Counter(r["_award"] for r in data if r["_nfq"] == lv).most_common()
        for lv in sorted({r["_nfq"] for r in data})
    }
    out["awarding_body_top20"] = Counter(clean(r.get("Awarding Body")) for r in data).most_common(
        20
    )
    out["awarding_body_distinct"] = len({clean(r.get("Awarding Body")) for r in data})
    out["duration_unit"] = Counter(r["_dur_unit"] for r in data).most_common()
    out["duration_ects"] = Counter(r["_dur"] for r in data if r["_dur_unit"] == "ects").most_common(
        10
    )

    providers = defaultdict(list)
    for r in data:
        providers[clean(r.get("Provider"))].append(r)
    out["providers"] = len(providers)
    out["providers_by_type"] = {
        t: len({p for p, rs in providers.items() if any(x["_type"] == t for x in rs)})
        for t in sorted({r["_type"] for r in data})
    }
    out["rows_per_provider_top15"] = sorted(
        ((p, len(rs)) for p, rs in providers.items()), key=lambda x: -x[1]
    )[:15]
    out["county_rows"] = Counter(r["_county"] for r in data).most_common()
    prov_county = {
        p: Counter(x["_county"] for x in rs).most_common(1)[0][0] for p, rs in providers.items()
    }
    out["county_providers"] = Counter(prov_county.values()).most_common()
    out["dublin"] = {
        t: {
            "rows": sum(1 for r in data if r["_type"] == t and r["_county"] == "Dublin"),
            "rows_total": sum(1 for r in data if r["_type"] == t),
            "providers": len(
                {
                    clean(r.get("Provider"))
                    for r in data
                    if r["_type"] == t and r["_county"] == "Dublin"
                }
            ),
            "providers_total": len({clean(r.get("Provider")) for r in data if r["_type"] == t}),
        }
        for t in sorted({r["_type"] for r in data})
    }

    # Identifiers
    refs = [r["_ref"] for r in data]
    out["ref_pattern"] = Counter(
        re.sub(r"\d", "9", x) if x else "(empty)" for x in refs
    ).most_common(8)
    dup = [k for k, v in Counter(refs).items() if v > 1 and k]
    out["ref_duplicates"] = {
        "distinct_duplicated": len(dup),
        "rows_involved": sum(Counter(refs)[k] for k in dup),
        "examples": dup[:5],
    }
    code_names = defaultdict(set)
    name_codes = defaultdict(set)
    for r in data:
        if r["_prov_code"]:
            code_names[r["_prov_code"]].add(clean(r.get("Provider")))
            name_codes[clean(r.get("Provider"))].add(r["_prov_code"])
    out["provider_codes"] = len(code_names)
    out["codes_with_several_names"] = {k: sorted(v) for k, v in code_names.items() if len(v) > 1}
    out["names_with_several_codes"] = {k: sorted(v) for k, v in name_codes.items() if len(v) > 1}

    # English language detail
    el = [r for r in data if r["_type"] == "English Language"]
    out["english"] = {
        "rows": len(el),
        "providers": len({clean(r.get("Provider")) for r in el}),
        "weeks": Counter(r["_dur"] for r in el if r["_dur_unit"] == "weeks").most_common(8),
        "duration_unit": Counter(r["_dur_unit"] for r in el).most_common(),
        "hours_per_week_top": Counter(norm(r.get("Hours per week")) for r in el).most_common(8),
        "entry_level_top": Counter(clean(r.get("Entry Level")) for r in el).most_common(8),
        "awarding_body_top": Counter(clean(r.get("Awarding Body")) for r in el).most_common(10),
    }
    return out


def parse_provider_page(path: Path) -> list[str]:
    t = path.read_text(encoding="utf-8", errors="replace")
    names = re.findall(r"<h[23][^>]*>\s*([^<]+?)\s*</h[23]>", t)
    skip = {"TrustEd Main Menu", "TrustEd Breadcrumb", "Help", "Sitemap"}
    seen: list[str] = []
    for n in names:
        n = html.unescape(n).strip()
        if n not in skip and n not in seen:
            seen.append(n)
    return seen


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--download", action="store_true")
    a = ap.parse_args()
    ilep_path = a.raw_dir / "ilep" / ILEP_XLSX.rsplit("/", 1)[1]
    tr_dir = a.raw_dir / "trusted_ie"
    tr_path = tr_dir / TRUSTED_XLSX.rsplit("/", 1)[1]

    if a.download:
        fetch(ILEP_XLSX, ilep_path, delay=10)  # robots.txt Crawl-delay: 10
        fetch(TRUSTED_XLSX, tr_path, delay=1)
        for fname, url in TRUSTED_PROVIDER_PAGES.items():
            fetch(url, tr_dir / fname, delay=1)
        return

    a.out_dir.mkdir(parents=True, exist_ok=True)
    result: dict = {"files": {}}
    lists = {}
    for key, path, url, page in (
        ("ilep", ilep_path, ILEP_XLSX, ILEP_PAGE),
        ("trusted", tr_path, TRUSTED_XLSX, TRUSTED_PAGE),
    ):
        title, header, data = read_list(path)
        result["files"][key] = {
            "url": url,
            "page": page,
            "file": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        result[key] = profile(key, title, header, data)
        lists[key] = data

    # Overlap between the two lists
    def pkey(r: dict) -> tuple[str, str]:
        return (provider_key(clean(r.get("Provider"))), norm(r.get("Programme Title")))

    ik = {pkey(r) for r in lists["ilep"]}
    tk = {pkey(r) for r in lists["trusted"]}
    ip = {provider_key(clean(r.get("Provider"))) for r in lists["ilep"]}
    tp = {provider_key(clean(r.get("Provider"))) for r in lists["trusted"]}
    both_prov = sorted(ip & tp)
    result["overlap"] = {
        "provider_plus_title_keys": {
            "ilep": len(ik),
            "trusted": len(tk),
            "both": len(ik & tk),
            "examples": sorted(ik & tk)[:10],
        },
        "providers": {
            "ilep": len(ip),
            "trusted": len(tp),
            "both": len(both_prov),
            "names": both_prov,
        },
        "provider_type_in_each": {
            p: {
                "ilep": sorted(
                    {
                        r["_type"]
                        for r in lists["ilep"]
                        if provider_key(clean(r.get("Provider"))) == p
                    }
                ),
                "trusted": sorted(
                    {
                        r["_type"]
                        for r in lists["trusted"]
                        if provider_key(clean(r.get("Provider"))) == p
                    }
                ),
            }
            for p in both_prov
        },
    }
    # Same provider: does the TrustEd code keep the ILEP number?
    codes = {}
    for k in ("ilep", "trusted"):
        for r in lists[k]:
            if r["_prov_code"]:
                codes.setdefault(provider_key(clean(r.get("Provider"))), {}).setdefault(
                    k, set()
                ).add(r["_prov_code"])
    result["overlap"]["codes_of_shared_providers"] = {
        p: {k: sorted(v) for k, v in codes.get(p, {}).items()} for p in both_prov
    }

    # TrustEd provider web pages vs the xlsx
    pages = {}
    for kind, files in (
        ("english", ["el_institutions.html"]),
        (
            "higher_education",
            ["he_institutions_p0.html", "he_institutions_p1.html", "he_institutions_p2.html"],
        ),
    ):
        names: list[str] = []
        for f in files:
            p = tr_dir / f
            if p.exists():
                names += [n for n in parse_provider_page(p) if n not in names]
        pages[kind] = names
    xlsx_prov = {
        provider_key(clean(r.get("Provider"))): clean(r.get("Provider")) for r in lists["trusted"]
    }
    result["trusted_pages"] = {
        k: {
            "count": len(v),
            "names": v,
            "in_xlsx": [n for n in v if provider_key(n) in xlsx_prov],
            "not_in_xlsx_by_name": [n for n in v if provider_key(n) not in xlsx_prov],
        }
        for k, v in pages.items()
    }
    result["trusted_xlsx_providers"] = sorted(set(xlsx_prov.values()))
    result["trusted_xlsx_english_providers"] = sorted(
        {clean(r.get("Provider")) for r in lists["trusted"] if r["_type"] == "English Language"}
    )

    # Non-personal CSV of both lists, for later joins
    cols = [
        "list",
        "programme_ref",
        "provider_code",
        "programme_type",
        "provider",
        "county",
        "programme_title",
        "awarding_body",
        "award_title",
        "award_kind",
        "nfq_level",
        "duration_raw",
        "duration_unit",
        "duration_value",
        "hours_per_week",
        "entry_level",
        "exit_level",
    ]
    derived = a.raw_dir / "ie_derived"  # large file: kept out of git
    derived.mkdir(parents=True, exist_ok=True)
    with (derived / "ie_eligible_programmes.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for k in ("ilep", "trusted"):
            for r in lists[k]:
                assert not any(norm(h) in {norm(x) for x in PERSONAL} for h in cols)
                w.writerow(
                    [
                        k,
                        r["_ref"],
                        r["_prov_code"],
                        r["_type"],
                        clean(r.get("Provider")),
                        r["_county"],
                        clean(r.get("Programme Title")),
                        clean(r.get("Awarding Body")),
                        clean(r.get("Award Title")),
                        r["_award"],
                        r["_nfq"],
                        clean(r.get("Duration (ECTS /Weeks per year)")),
                        r["_dur_unit"],
                        r["_dur"] if r["_dur"] is not None else "",
                        clean(r.get("Hours per week")),
                        clean(r.get("Entry Level")),
                        clean(r.get("Exit Level")),
                    ]
                )

    (a.out_dir / "ie_lists_summary.json").write_text(
        json.dumps(result, indent=1, ensure_ascii=False, default=str), encoding="utf-8"
    )
    for k in ("ilep", "trusted"):
        p = result[k]
        print(f"== {k}: {p['rows']} rows, {p['providers']} providers | {p['title']}")
        print("  type:", p["programme_type"])
        print("  nfq:", p["nfq_level"])
        print("  award:", p["award_kind"])
        print("  dublin:", p["dublin"])
        print("  county providers:", p["county_providers"][:8])
        print(
            "  ref patterns:", p["ref_pattern"], "dups:", p["ref_duplicates"]["distinct_duplicated"]
        )
    print(
        "overlap:",
        {k: v for k, v in result["overlap"]["provider_plus_title_keys"].items() if k != "examples"},
        result["overlap"]["providers"]["both"],
    )
    print(
        "trusted pages:",
        {k: (v["count"], len(v["in_xlsx"])) for k, v in result["trusted_pages"].items()},
    )


if __name__ == "__main__":
    main()
