"""S-7b: Ireland in the European Qualifications Dataset Register (QDR).

QQI publishes the Irish Register of Qualifications (IRQ) to the EU QDR; the EU
republishes it as open data (data.europa.eu dataset "european-learning-data",
licence COM_REUSE). irq.ie itself has robots.txt "Disallow: /", so the EU
bulk file is the only scripted route to IRQ data.

Download (one request; JSON-LD zips were empty on 2026-11-22, Turtle had data):

    curl -sL -A north-research-spike -o spikes/_raw/qdr_ie/irl-ttl_1.zip \
      'https://europa.eu/europass/qdr/open-data/dcat/download?url=http://data.europa.eu/snb/data/downloadable/country/irl/ttl/irl-ttl_1.zip'
    python3 -I -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" \
      spikes/_raw/qdr_ie/irl-ttl_1.zip spikes/_raw/qdr_ie/extracted

Profile:

    uv run --with rdflib python -I spikes/s7_ie_lists/profile_qdr_ie.py \
      --ttl-dir spikes/_raw/qdr_ie/extracted \
      --ie-csv spikes/_raw/ie_derived/ie_eligible_programmes.csv \
      --out-dir spikes/s7_ie_lists/out

Only organisations (legal names) and programmes are read; the files carry no
person data that this script writes out.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from rdflib import RDF, Graph, URIRef
from rdflib.namespace import DCTERMS, FOAF, SKOS

ELM = "http://data.europa.eu/snb/model/ontology/"
ADMS_ID = URIRef("http://www.w3.org/ns/adms#identifier")
ROV_LEGAL = URIRef("http://www.w3.org/ns/regorg#legalName")


def e(name: str) -> URIRef:
    return URIRef(ELM + name)


def norm(s: object) -> str:
    t = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    t = t.replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", t)).strip()


def tail(u: object) -> str:
    return str(u).rstrip("/").rsplit("/", 1)[-1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ttl-dir", type=Path, required=True)
    ap.add_argument("--ie-csv", type=Path)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()

    los: dict[str, dict] = {}
    quals: dict[str, dict] = defaultdict(dict)
    orgs: dict[str, str] = {}
    idents: dict[str, tuple[str, str]] = {}
    urls: dict[str, str] = {}
    addresses: dict[str, str] = {}
    locations: dict[str, str] = {}
    awarding_opp_body: dict[str, str] = {}

    files = sorted(a.ttl_dir.glob("*.ttl"))
    for f in files:
        g = Graph()
        g.parse(f, format="turtle")
        for s, _, o in g.triples((None, SKOS.notation, None)):
            idents[str(s)] = (str(o), str(getattr(o, "datatype", "") or ""))
        for s, _, o in g.triples((None, e("contentUrl"), None)):
            urls[str(s)] = str(o)
        for s, _, o in g.triples((None, ROV_LEGAL, None)):
            orgs[str(s)] = str(o)
        for s, _, o in g.triples((None, e("fullAddress"), None)):
            addresses[str(s)] = str(g.value(o, e("noteLiteral")) or o)
        for s, _, o in g.triples((None, e("address"), None)):
            locations[str(s)] = str(o)
        for s, _, o in g.triples((None, e("awardingBody"), None)):
            awarding_opp_body[str(s)] = str(o)
        for s in g.subjects(RDF.type, e("LearningOpportunity")):
            los[str(s)] = {
                "title": str(g.value(s, DCTERMS.title) or ""),
                "status": str(g.value(s, e("status")) or ""),
                "modified": str(g.value(s, DCTERMS.modified) or ""),
                "spec": str(g.value(s, e("learningAchievementSpecification")) or ""),
                "provider": str(g.value(s, e("providedBy")) or ""),
                "location": str(g.value(s, e("location")) or ""),
                "identifier": str(g.value(s, ADMS_ID) or ""),
                "homepage": str(g.value(s, FOAF.homepage) or ""),
                "predicates": sorted({tail(p) for p in g.predicates(s, None)}),
            }
        for s in g.subjects(RDF.type, e("Qualification")):
            q = quals[str(s)]
            for key, pred in (
                ("title", DCTERMS.title),
                ("eqf", e("EQFLevel")),
                ("nqf", e("NQFLevel")),
                ("isced", e("ISCEDFCode")),
                ("identifier", ADMS_ID),
                ("awarding", e("awardingOpportunity")),
            ):
                v = g.value(s, pred)
                if v is not None:
                    q[key] = str(v)
            q.setdefault("predicates", set()).update(tail(p) for p in g.predicates(s, None))
        print(f"parsed {f.name}: {len(los)} LOs, {len(quals)} quals so far")

    def ident(u: str) -> str:
        return idents.get(u, ("", ""))[0]

    def qual_awarding(q: dict) -> str:
        body = awarding_opp_body.get(q.get("awarding", ""), "")
        return orgs.get(body, "")

    res: dict = {"files": len(files)}
    res["learning_opportunities"] = len(los)
    res["lo_status"] = Counter(x["status"] for x in los.values()).most_common()
    res["lo_predicates"] = Counter(p for x in los.values() for p in x["predicates"]).most_common()
    res["lo_modified_year"] = Counter(x["modified"][:4] for x in los.values()).most_common()
    res["lo_homepage_urls_top"] = Counter(
        urls.get(x["homepage"], "(none)") for x in los.values()
    ).most_common(5)
    res["lo_identifier_examples"] = [ident(x["identifier"]) for x in list(los.values())[:8]]
    res["lo_identifier_datatype"] = Counter(
        idents.get(x["identifier"], ("", ""))[1] for x in los.values()
    ).most_common(5)
    res["lo_with_location_address"] = sum(
        1 for x in los.values() if addresses.get(locations.get(x["location"], ""))
    )

    full_quals = {k: v for k, v in quals.items() if "nqf" in v}
    res["qualification_nodes"] = len(quals)
    res["qualifications_with_nqf"] = len(full_quals)
    res["qual_predicates"] = Counter(
        p for v in quals.values() for p in v["predicates"]
    ).most_common()
    res["nqf_level"] = Counter(tail(v["nqf"]) for v in full_quals.values()).most_common()
    res["nqf_uri_examples"] = sorted({v["nqf"] for v in full_quals.values()})[:12]
    res["eqf_level_all_quals"] = Counter(
        tail(v.get("eqf", "")) for v in quals.values()
    ).most_common()
    res["isced_f_all_quals"] = Counter(
        tail(v.get("isced", "")) for v in quals.values()
    ).most_common(15)
    res["isced_f_digits"] = Counter(
        len(tail(v.get("isced", ""))) for v in quals.values()
    ).most_common()
    res["awarding_body_top"] = Counter(qual_awarding(v) for v in full_quals.values()).most_common(
        25
    )

    # LOs joined to their qualification (the spec node)
    joined = []
    for k, x in los.items():
        q = quals.get(x["spec"], {})
        joined.append(
            {
                "lo": tail(k),
                "status": x["status"],
                "title": x["title"],
                "provider": orgs.get(x["provider"], ""),
                "lo_ref": ident(x["identifier"]),
                "eqf": tail(q.get("eqf", "")),
                "nqf_concept": tail(q.get("nqf", "")),
                "isced_f": tail(q.get("isced", "")),
                "qual_title": q.get("title", ""),
                "spec_ref": ident(q.get("identifier", "")),
            }
        )
    rel = [j for j in joined if j["status"] == "released"]
    res["released"] = len(rel)
    res["released_eqf"] = Counter(j["eqf"] for j in rel).most_common()
    res["released_nqf_concept"] = Counter(j["nqf_concept"] for j in rel).most_common()
    # NQF concept labels are not in the dump; show the most common words of the
    # qualification titles per concept so the NFQ level can be inferred.
    words = defaultdict(Counter)
    for v in full_quals.values():
        t = norm(v.get("title", ""))
        words[(tail(v["nqf"]), tail(v.get("eqf", "")))].update(
            w
            for w in (
                "honours",
                "higher diploma",
                "higher certificate",
                "ordinary",
                "master",
                "doctor",
                "postgraduate",
                "advanced certificate",
                "certificate",
                "bachelor",
                "minor",
                "special purpose",
            )
            if w in t
        )
    res["nqf_concept_title_words"] = {
        f"{k[0]} (EQF {k[1]})": c.most_common(6) for k, c in sorted(words.items())
    }
    res["released_eqf_6_8"] = sum(1 for j in rel if j["eqf"] in ("6", "7", "8"))
    res["released_isced_broad"] = Counter(j["isced_f"][:2] for j in rel).most_common()
    res["released_providers"] = len({j["provider"] for j in rel})
    res["released_providers_top25"] = Counter(j["provider"] for j in rel).most_common(25)
    res["released_with_isced"] = sum(1 for j in rel if j["isced_f"])

    # Overlap with the immigration lists, by normalized provider-free title
    if a.ie_csv and a.ie_csv.exists():
        ie = list(csv.DictReader(a.ie_csv.open(encoding="utf-8")))
        titles = defaultdict(set)
        for j in rel:
            titles[norm(j["title"])].add(j["provider"])
        for lst in ("ilep", "trusted"):
            rows = [r for r in ie if r["list"] == lst and r["programme_type"].startswith("Higher")]
            hit = sum(1 for r in rows if norm(r["programme_title"]) in titles)
            res[f"title_match_{lst}_he"] = {"rows": len(rows), "title_found_in_qdr": hit}
        el = [r for r in ie if r["programme_type"] == "English Language"]
        res["english_in_qdr_by_title"] = {
            "ie_rows": len(el),
            "found": sum(1 for r in el if norm(r["programme_title"]) in titles),
        }

    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / "qdr_ie_summary.json").write_text(
        json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8"
    )
    derived = a.ttl_dir.parent / "derived"  # large file: kept out of git
    derived.mkdir(parents=True, exist_ok=True)
    with (derived / "qdr_ie_learning_opportunities.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        w = csv.DictWriter(fh, fieldnames=list(joined[0].keys()))
        w.writeheader()
        w.writerows(joined)
    for k, v in res.items():
        if not isinstance(v, list) or len(v) < 30:
            print(k, ":", v)


if __name__ == "__main__":
    main()
