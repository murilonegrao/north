"""Convert the pilot spreadsheet (CSV, one row per program) into JSON documents valid against the schema.

The columns are not written by hand: they are derived from program.schema.json by walking
its dimensions, so the spreadsheet and the schema cannot drift apart.

Usage:
    uv run --with jsonschema schema/csv_to_json.py --print-header > docs/methodology/pilot-template.csv
    uv run --with jsonschema schema/csv_to_json.py filled.csv --out out/
    uv run --with jsonschema schema/csv_to_json.py --self-test

Filling conventions (details in docs/methodology/pilot-guide.md):
- all cells of a field empty              -> {value: null, status: unknown}
- verified_at empty but status filled     -> the row's collected_on column is used
- source_kind empty but status filled     -> "page" (R13); write official_list, correspondence or uploaded_file when it applies
- simple lists (e.g. start_terms): items separated by ";"; "[]" = empty list
- booleans: true/false, yes/no, 1/0
- list slots (funding.opportunities.N..., admissions.deadlines.N...) left entirely empty are dropped
- derived fields (in_strategy, flags) are not columns: the system computes them (0002/A11, R1)
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).with_name("program.schema.json")
VV_REF = "#/$defs/VerifiedValue"
VV_META = ("status", "source_kind", "source_url", "evidence", "verified_at")

# How many slots each list of objects gets in the spreadsheet.
SLOTS = {
    "institution.identifiers": 3,
    "classifications": 1,
    "eligibilities": 1,
    "funding.opportunities": 3,
    "admissions.deadlines": 3,
}
# Document fields that do not become columns (constants, generated or derived).
SKIP = {"schema_version", "updated_at", "in_strategy", "flags"}
# Pilot method columns: they stay in the spreadsheet and are not written to the JSON.
METHOD_COLUMNS = ["collected_on", "where_found", "minutes_spent", "remarks"]


# ---------------------------------------------------------------- schema walk

class Walker:
    def __init__(self, schema: dict, country: str = "US"):
        self.schema = schema
        self.country = country
        self.columns: list[tuple[str, dict]] = []  # (path, leaf info)
        self.vv_paths: list[str] = []
        self.slot_paths: list[str] = []
        self.value_object_props: list[tuple[str, list[str]]] = []  # objects inside a ".value"

    def resolve(self, node: dict) -> dict:
        while "$ref" in node and set(node) - {"description", "$comment"} == {"$ref"}:
            node = self._lookup(node["$ref"])
        return node

    def _lookup(self, ref: str) -> dict:
        assert ref.startswith("#/"), ref
        cur = self.schema
        for part in ref[2:].split("/"):
            cur = cur[part]
        return cur

    def is_vv(self, node: dict) -> dict | None:
        """If the node is a typed VerifiedValue, return the schema of its `value`."""
        node = self.resolve(node)
        if node is self._lookup(VV_REF):
            return {}
        all_of = node.get("allOf") or []
        if all_of and all_of[0].get("$ref") == VV_REF:
            value = {}
            for part in all_of[1:]:
                value = part.get("properties", {}).get("value", value)
            return value
        return None

    def non_null(self, node: dict) -> dict:
        node = self.resolve(node)
        if "anyOf" in node:
            # null and `false` (the R12 "no" of a yes/no-with-details field, e.g. accreditation)
            # do not become columns
            options = [
                self.resolve(o) for o in node["anyOf"]
                if self.resolve(o).get("type") != "null" and self.resolve(o).get("const") is not False
            ]
            assert len(options) == 1, node
            return self.non_null(options[0])
        return node

    def walk(self):
        for name, sub in self.schema["properties"].items():
            if name in SKIP:
                continue
            if name == "immigration":
                sub = {"$ref": f"#/$defs/immigration_{self.country.lower()}"}
            self._walk(sub, name)
        return self

    def _walk(self, node: dict, path: str):
        value_schema = self.is_vv(node)
        if value_schema is not None:
            self.vv_paths.append(path)
            self._walk_value(value_schema, f"{path}.value")
            for meta in VV_META:
                self.columns.append((f"{path}.{meta}", {"kind": "str"}))
            return
        node = self.non_null(node)
        if node.get("type") == "object" and "properties" in node:
            if ".value." in f"{path}.":  # object inside a value (e.g. a deadline item)
                self.value_object_props.append((path, list(node["properties"])))
            for name, sub in node["properties"].items():
                self._walk(sub, f"{path}.{name}")
            return
        if node.get("type") == "array":
            items = self.non_null(node["items"])
            if items.get("type") == "object" or self.is_vv(items) is not None:
                self.slot_paths.append(path)
                for i in range(SLOTS.get(path, 1)):
                    self._walk(items, f"{path}.{i}")
                return
            self.columns.append((path, {"kind": "list", "item": leaf_kind(items)}))
            return
        self.columns.append((path, {"kind": leaf_kind(node)}))

    def _walk_value(self, node: dict, path: str):
        node = self.non_null(node) if node else {}
        if node.get("type") == "object" and "properties" in node:
            self.value_object_props.append((path, list(node["properties"])))
            for name, sub in node["properties"].items():
                self._walk(sub, f"{path}.{name}")
            return
        if node.get("type") == "array":
            self._walk(node, path)
            return
        self.columns.append((path, {"kind": leaf_kind(node)}))


def leaf_kind(node: dict) -> str:
    types = node.get("type")
    if types is None and "enum" in node:
        vals = {type(v).__name__ for v in node["enum"] if v is not None}
        return "int" if vals == {"int"} else "str"
    if isinstance(types, str):
        types = [types]
    types = [t for t in (types or ["string"]) if t != "null"]
    if "integer" in types:
        return "int"
    if "number" in types:
        return "number"
    if "boolean" in types:
        return "bool"
    return "str"


# ---------------------------------------------------------------- conversion

TRUE = {"true", "yes", "y", "1"}
FALSE = {"false", "no", "n", "0"}


def coerce(raw: str, info: dict, where: str):
    raw = raw.strip()
    kind = info["kind"]
    if kind == "list":
        if raw == "[]":
            return []
        return [coerce(x, {"kind": info["item"]}, where) for x in raw.split(";") if x.strip()]
    try:
        if kind == "int":
            return int(raw)
        if kind == "number":
            n = float(raw)
            return int(n) if n.is_integer() else n
    except ValueError:
        raise ValueError(f"{where}: invalid number: {raw!r}") from None
    if kind == "bool":
        low = raw.lower()
        if low in TRUE:
            return True
        if low in FALSE:
            return False
        raise ValueError(f"{where}: invalid boolean: {raw!r}")
    return raw


def set_path(doc: dict, path: str, value):
    parts = path.split(".")
    cur = doc
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        nxt = None if last else parts[i + 1]
        key = int(part) if part.isdigit() else part
        if isinstance(cur, list):
            while len(cur) <= key:
                cur.append(None)
            if last:
                cur[key] = value
            else:
                if cur[key] is None:
                    cur[key] = [] if nxt.isdigit() else {}
                cur = cur[key]
        else:
            if last:
                cur[key] = value
            else:
                if key not in cur:
                    cur[key] = [] if nxt.isdigit() else {}
                cur = cur[key]


def get_path(doc, path: str):
    cur = doc
    for part in path.split("."):
        if cur is None:
            return None
        if part.isdigit():
            idx = int(part)
            cur = cur[idx] if isinstance(cur, list) and idx < len(cur) else None
        else:
            cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


def row_to_doc(row: dict, walker: Walker, rownum: int) -> dict:
    doc: dict = {"schema_version": 0}
    errors = []
    for path, info in walker.columns:
        raw = (row.get(path) or "").strip()
        if raw == "":
            continue
        try:
            set_path(doc, path, coerce(raw, info, f"row {rownum}, {path}"))
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError("; ".join(errors))

    collected = (row.get("collected_on") or "").strip() or None

    # 1. Lists of objects: drop empty slots. A list inside `value` that ends up
    #    empty becomes null: nobody filled it in.
    for slot in sorted(walker.slot_paths, key=len, reverse=True):
        parent_path, _, leaf = slot.rpartition(".")
        parent = get_path(doc, parent_path) if parent_path else doc
        if not isinstance(parent, dict) or not isinstance(parent.get(leaf), list):
            continue
        parent[leaf] = [x for x in parent[leaf] if x not in (None, {}, [])]
        if not parent[leaf] and leaf == "value":
            parent[leaf] = None

    # 2. Partially filled objects inside `value` (e.g. a deadline item): missing properties become null
    #    (the schema complains if the property does not accept null, e.g. currency).
    for obj_path, props in walker.value_object_props:
        obj = get_path(doc, obj_path)
        if isinstance(obj, dict):
            for prop in props:
                obj.setdefault(prop, None)

    # 3. VerifiedValues: apply defaults and a minimal consistency check (the schema does the rest).
    for vv in sorted(walker.vv_paths, key=lambda p: p.count("."), reverse=True):
        in_slot = any(part.isdigit() for part in vv.split("."))
        parent_path, _, leaf = vv.rpartition(".")
        parent = get_path(doc, parent_path) if parent_path else doc
        if parent is None:
            if in_slot:
                continue  # slot that does not exist
            set_path(doc, vv, {})
            parent = get_path(doc, parent_path)
        if isinstance(parent, list):  # the slot itself is a VerifiedValue (e.g. a deadline item)
            idx = int(leaf)
            if idx >= len(parent) or not isinstance(parent[idx], dict):
                continue
            node = parent[idx]
        else:
            node = parent.get(leaf)
            node = node if isinstance(node, dict) else {}
        status = node.get("status")
        value = node.get("value")
        has_value = value is not None and value != {}
        if not status:
            if has_value or node.get("source_url") or node.get("source_kind"):
                raise ValueError(f"row {rownum}, {vv}: value or source filled in without a status")
            status = "unknown"
        new_vv = {
            "value": value if has_value else None,
            "status": status,
            "source_kind": node.get("source_kind") or ("page" if status != "unknown" else None),
            "source_url": node.get("source_url"),
            "evidence": node.get("evidence"),
            "verified_at": node.get("verified_at") or (collected if status != "unknown" else None),
        }
        if isinstance(parent, list):
            parent[int(leaf)] = new_vv
        else:
            parent[leaf] = new_vv

    # 4. Lists of objects outside `value` with no slot filled in.
    for slot in walker.slot_paths:
        parent_path, _, leaf = slot.rpartition(".")
        if leaf == "value" or any(part.isdigit() for part in slot.split(".")):
            continue
        parent = get_path(doc, parent_path) if parent_path else doc
        if isinstance(parent, dict):
            parent.setdefault(leaf, [])
    return doc


def convert(csv_text: str, schema: dict, country: str = "US"):
    walker = Walker(schema, country).walk()
    validator = Draft202012Validator(schema)
    results = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for i, row in enumerate(reader, start=2):  # row 1 = header
        if not any((v or "").strip() for v in row.values()):
            continue
        try:
            doc = row_to_doc(row, walker, i)
        except ValueError as exc:
            results.append((i, None, [str(exc)]))
            continue
        errs = [
            f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
            for e in sorted(validator.iter_errors(doc), key=lambda e: list(map(str, e.absolute_path)))
        ]
        results.append((i, doc, errs))
    return results


def header(schema: dict, country: str = "US") -> list[str]:
    walker = Walker(schema, country).walk()
    return [p for p, _ in walker.columns] + METHOD_COLUMNS


# ---------------------------------------------------------------- self-test

def self_test(schema: dict) -> int:
    """One fictitious valid row and one invalid row (confirmed_official without a source)."""
    cols = header(schema)
    good = {c: "" for c in cols}
    good.update({
        "id": "example-state-university-ms-data-science",
        "is_fictitious": "true",
        "country": "US",
        "subdivision": "US-TX",
        "institution.id": "example-state-university",
        "institution.name": "Example State University (FICTITIOUS)",
        "institution.city": "Exampleville",
        "institution.control": "public",
        "institution.identifiers.0.scheme": "unitid",
        "institution.identifiers.0.value": "000000",
        "institution.accreditation.value.accreditor": "Fictitious Recognized Accreditor",
        "institution.accreditation.value.scheme": "us_ed_recognized",
        "institution.accreditation.value.institutional": "true",
        "institution.accreditation.status": "confirmed_official",
        "institution.accreditation.source_kind": "uploaded_file",
        "institution.accreditation.source_url": "https://example.org/dapip-export",
        "campus.name": "Main Campus",
        "campus.city": "Exampleville",
        "campus.locality.country": "US",
        "campus.locality.scheme": "us_county_fips",
        "campus.locality.code": "00000",
        "campus.intl_authorization.value.scheme": "sevp",
        "campus.intl_authorization.value.authorized": "true",
        "campus.intl_authorization.status": "confirmed_official",
        "campus.intl_authorization.source_kind": "official_list",
        "campus.intl_authorization.source_url": "https://example.org/sevp-list",
        "name": "Master of Science in Data Science (FICTITIOUS)",
        "degree": "MS",
        "classifications.0.is_primary": "true",
        "classifications.0.code.value.scheme": "cip2020",
        "classifications.0.code.value.code": "30.7001",
        "classifications.0.code.status": "confirmed_official",
        "classifications.0.code.source_kind": "official_list",
        "classifications.0.code.source_url": "https://example.org/ipeds",
        "eligibilities.0.rule_key": "us.stem_opt",
        "eligibilities.0.rule_version": "2024-07-22",
        "eligibilities.0.result.value": "true",
        "eligibilities.0.result.status": "confirmed_official",
        "eligibilities.0.result.source_kind": "official_list",
        "eligibilities.0.result.source_url": "https://example.org/dhs-stem-list",
        "modality.value": "in_person",
        "modality.status": "reported_by_program",
        "modality.source_url": "https://example.edu/msds",
        "immigration.i20_issued_for_program.value": "true",
        "immigration.i20_issued_for_program.status": "confirmed_official",
        "immigration.i20_issued_for_program.source_kind": "correspondence",
        "immigration.i20_issued_for_program.evidence": "Written reply from the international office: eligible for an I-20.",
        "admissions.english.pte_academic_accepted.value": "false",
        "admissions.english.pte_academic_accepted.status": "confirmed_negative",
        "admissions.english.pte_academic_accepted.source_url": "https://example.edu/msds/admissions",
        "admissions.english.toefl_ibt_min.value": "80",
        "admissions.english.toefl_ibt_min.status": "reported_by_program",
        "admissions.english.toefl_ibt_min.source_url": "https://example.edu/msds/admissions",
        "admissions.english.toefl_ibt_min.evidence": "minimum TOEFL iBT score of 80",
        "academic.start_terms.value": "fall;spring",
        "academic.start_terms.status": "reported_by_program",
        "academic.start_terms.source_url": "https://example.edu/msds",
        "funding.opportunities.0.type": "TA",
        "funding.opportunities.0.tuition_coverage.value": "full",
        "funding.opportunities.0.tuition_coverage.status": "reported_by_program",
        "funding.opportunities.0.tuition_coverage.source_url": "https://example.edu/msds/funding",
        "admissions.deadlines.0.value.term": "fall",
        "admissions.deadlines.0.value.term_year": "2027",
        "admissions.deadlines.0.value.applicant": "international",
        "admissions.deadlines.0.value.kind": "final",
        "admissions.deadlines.0.value.date": "2027-02-01",
        "admissions.deadlines.0.status": "reported_by_program",
        "admissions.deadlines.0.source_url": "https://example.edu/msds/deadlines",
        "admissions.deadlines.2.value.term": "fall",
        "admissions.deadlines.2.value.term_year": "2027",
        "admissions.deadlines.2.value.applicant": "all",
        "admissions.deadlines.2.value.kind": "funding_consideration",
        "admissions.deadlines.2.value.date": "2027-01-15",
        "admissions.deadlines.2.status": "reported_by_program",
        "admissions.deadlines.2.source_url": "https://example.edu/graduate-school/funding",
        "collected_on": "2026-11-21",
        "where_found": "program site",
        "minutes_spent": "35",
        "remarks": "fictitious test row",
    })
    bad = dict(good)
    bad["id"] = "example-state-university-ms-bad"
    bad["eligibilities.0.result.source_url"] = ""  # confirmed_official without a source
    bad2 = dict(good)
    bad2["id"] = "example-state-university-ms-bad-deadline"
    bad2["admissions.deadlines.0.source_url"] = ""  # deadline item without a source (R18)
    bad3 = dict(good)
    bad3["id"] = "example-state-university-ms-bad-polarity"
    bad3["admissions.english.pte_academic_accepted.status"] = "reported_by_program"  # R12: a "no" must be confirmed_negative

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    w.writerow(good)
    w.writerow(bad)
    w.writerow(bad2)
    w.writerow(bad3)
    ok_row, bad_row, bad_row2, bad_row3 = convert(buf.getvalue(), schema)
    passed = True
    if ok_row[2]:
        print("FAIL: the valid row produced errors:", *ok_row[2], sep="\n  ")
        passed = False
    else:
        doc = ok_row[1]
        assert doc["admissions"]["english"]["toefl_ibt_min"]["value"] == 80
        assert doc["admissions"]["english"]["toefl_ibt_min"]["verified_at"] == "2026-11-21"
        assert doc["admissions"]["gre"]["status"] == "unknown"
        assert doc["academic"]["start_terms"]["value"] == ["fall", "spring"]
        assert len(doc["funding"]["opportunities"]) == 1
        assert doc["funding"]["opportunities"][0]["stipend"]["status"] == "unknown"
        deadlines = doc["admissions"]["deadlines"]
        assert len(deadlines) == 2, deadlines  # the empty middle slot is dropped
        assert deadlines[1]["value"]["kind"] == "funding_consideration"
        assert deadlines[0]["source_kind"] == "page"  # default
        i20 = doc["immigration"]["i20_issued_for_program"]
        assert i20["source_kind"] == "correspondence" and i20["source_url"] is None
        assert doc["admissions"]["english"]["pte_academic_accepted"]["value"] is False
        assert "in_strategy" not in doc and "flags" not in doc
        assert doc["campus"]["locality"]["code"] == "00000"
        print("ok   valid row -> JSON valid against the schema")
    for label, row in (
        ("confirmed_official without source", bad_row),
        ("deadline item without source", bad_row2),
        ("reported_by_program + false", bad_row3),
    ):
        if not row[2]:
            print(f"FAIL: the '{label}' row passed")
            passed = False
        else:
            print(f"ok   invalid row rejected ({label}):", row[2][0])
    print(f"     ({len(cols)} columns in the spreadsheet)")
    return 0 if passed else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", help="filled-in spreadsheet")
    ap.add_argument("--out", default="out", help="output folder for the JSON files")
    ap.add_argument("--country", default="US")
    ap.add_argument("--print-header", action="store_true", help="print the spreadsheet header (template)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    if args.print_header:
        csv.writer(sys.stdout, lineterminator="\n").writerow(header(schema, args.country))
        return 0
    if args.self_test:
        return self_test(schema)
    if not args.csv:
        ap.error("pass a CSV, --print-header or --self-test")

    results = convert(Path(args.csv).read_text(encoding="utf-8-sig"), schema, args.country)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    failed = 0
    for rownum, doc, errs in results:
        if errs:
            failed += 1
            print(f"row {rownum}: INVALID")
            for e in errs:
                print(f"  - {e}")
            continue
        target = out / f"{doc['id']}.json"
        target.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"row {rownum}: ok -> {target}")
    print(f"{len(results) - failed} valid, {failed} invalid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
