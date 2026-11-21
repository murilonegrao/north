"""Convert the pilot spreadsheet (CSV, one row per program) into JSON documents valid against the schema.

The columns are not written by hand: they are derived from program.schema.json by walking
its dimensions, so the spreadsheet and the schema cannot drift apart.

Two modes:
- full (default): one complete program document per row (pilot-template.csv). Used for programs
  that official files do not cover (e.g. other countries).
- site-only (--site-only): only the fields that exist on the program's own site
  (pilot-site-template.csv, decision record 0004/O2), in a long format: one row per program and
  field, keyed by `program_id` (`<unitid>-<cip6 without dot>`, docs/api/programs-v0.md). Each
  program becomes a site patch that the backend merges onto the record ingested from official
  files. Format and merge rules: see SITE PATCH below.

Usage:
    uv run --with jsonschema schema/csv_to_json.py --print-header > docs/methodology/pilot-template.csv
    uv run --with jsonschema schema/csv_to_json.py --site-template docs/methodology/pilot-candidates.csv \
        > docs/methodology/pilot-site-template.csv
    uv run --with jsonschema schema/csv_to_json.py --print-header --site-only   # long-format header only
    uv run --with jsonschema schema/csv_to_json.py filled.csv --out out/
    uv run --with jsonschema schema/csv_to_json.py filled-site.csv --site-only --out out/
    uv run --with jsonschema schema/csv_to_json.py --self-test     # tests both modes

Filling conventions (details in docs/methodology/pilot-guide.md):
- all cells of a field empty              -> {value: null, status: unknown}
- verified_at empty but status filled     -> the row's collected_on column is used
- source_kind empty but status filled     -> "page" (R13); write official_list, correspondence or uploaded_file when it applies
- simple lists (e.g. start_terms): items separated by ";"; "[]" = empty list
- booleans: true/false, yes/no, 1/0
- list slots (funding.opportunities.N..., admissions.deadlines.N...) left entirely empty are dropped
- derived fields (in_strategy, flags) are not columns: the system computes them (0002/A11, R1)

Site-only (long) format: columns program_id, field, field_label, hint, value, status, source_kind,
source_url, evidence, verified_at, minutes_spent, remarks; one row per (program, field), pre-filled by
--site-template. Defaults (details in docs/methodology/pilot-guide.md):
- value and status empty                  -> field left out of the patch (status unknown only when written)
- value filled, status empty              -> reported_by_program; a yes/no field with "no" -> confirmed_negative
- source_kind empty                       -> "page"
- source_url empty                        -> the program's `program_page` row (not for correspondence or unknown)
- verified_at empty                       -> the program's `collected_on` row (required once anything is filled)
- compact values: money "75 [USD]"; rate "1450 [USD] credit_hour"; credits "30 [unit]";
  deadline "term|year|applicant|kind|date"; TOEFL sections "reading=20;writing=22"; lists "fall;spring"
- lists: admissions.deadlines[i] (one row per deadline) and funding.opportunities[i].<field>

SITE PATCH (output of --site-only, one file per program: <out>/<program_id>.json)

    {
      "format": "north.site_patch.v0",
      "schema_version": 0,
      "program_id": "228778-110701",
      "fields": {
        "name": "Master of Science in Computer Science",
        "official_url": "https://...",
        "modality": { VerifiedValue },
        "immigration.i20_issued_for_program": { VerifiedValue },
        "admissions.english.toefl_ibt_min": { VerifiedValue },
        "admissions.deadlines": [ VerifiedValue, ... ],
        "funding.opportunities": [ FundingOpportunity, ... ],
        ...
      }
    }

- Each key of `fields` is a dotted path into the program document of program.schema.json
  (`immigration.*` = the country module, e.g. $defs.immigration_us). Allowed keys are the merge
  units in site_units(); each value is valid against the schema node at that path
  (site_patch_schema() builds the JSON Schema of the whole patch).
- Merge rules for the backend (reference implementation: apply_site_patch):
  1. Find the ingested program whose id equals `program_id`. If there is none, do not create a
     program: open a reconciliation task.
  2. For each key, replace the whole value at that path. A VerifiedValue is replaced as a unit;
     the two lists (`admissions.deadlines`, `funding.opportunities`) are replaced as a whole,
     never appended item by item.
  3. A key that is absent leaves the stored value untouched. A patch never writes `unknown`,
     `false` or an empty list for a field nobody filled in (BR-02). A key whose value is
     `{status: unknown}` was written explicitly ("searched, not found", dated by verified_at):
     the backend stores it, but it never overwrites a stored value with a known status: the key
     is skipped and reported as a conflict (apply_site_patch returns the list).
  4. A patch never touches fields that come from official files (institution, campus,
     classifications, eligibilities, career, cost.rent_reference_monthly): those paths are not
     merge units, and a key outside site_units() rejects the whole patch.
  5. `name` replaces the CIP title (API `title_source` becomes `program_page`); a merged key
     leaves `not_yet_collected`.
  6. Applying the same patch twice gives the same record (idempotent). A newer patch for the
     same program replaces the keys it carries.
"""

from __future__ import annotations

import argparse
import copy
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

# Site-only mode (0004/O2): schema paths whose data exists only on the program's own site.
# Everything else (institution, campus, CIP, completions, STEM OPT, SEVP, accreditation,
# institution-wide tuition, Scorecard earnings, HUD rent) comes from official files.
# A path covers its whole subtree.
SITE_ONLY_INCLUDE = [
    "name",
    "official_url",
    "modality",
    "immigration.f1_compatible_modality",
    "immigration.i20_issued_for_program",  # DSO rule R11
    "immigration.cpt_available",
    "immigration.cpt_from_first_term",
    "immigration.internship",
    "immigration.stem_opt_claimed_by_program",
    "admissions.english",
    "admissions.accepts_other_undergrad_area",
    "admissions.prerequisites",
    "admissions.gre",
    "admissions.gmat",  # record 0005
    "admissions.min_gpa_4scale",
    "admissions.application_fee",
    "admissions.application_fee_waiver",  # record 0005
    "admissions.deadlines",  # each item with its own source (R18)
    "cost.tuition_international",
    "cost.fees",
    "cost.tuition_fees_program_total",
    "cost.i20_requirement_student",
    "cost.i20_requirement_per_dependent",
    "cost.student_health_insurance",
    "academic.credits_required",
    "academic.duration_months",
    "academic.start_terms",
    "academic.thesis_option",
    "funding",
    "family.family_housing_on_campus",
    "family.family_housing_rent",
    "family.dependent_insurance_available",
    "family.dependent_insurance_cost",
]
SITE_KEY = "program_id"
SITE_PATCH_FORMAT = "north.site_patch.v0"
PROGRAM_ID_PATTERN = r"^[0-9]{6}-[0-9]{6}$"  # <unitid>-<cip6 without dot>

# Long format of the site-only pilot: one row per (program, field).
LONG_COLUMNS = [SITE_KEY, "field", "field_label", "hint", "value", "status", "source_kind", "source_url",
                "evidence", "verified_at", "minutes_spent", "remarks"]
LONG_METHOD = ("minutes_spent", "remarks")  # kept in the spreadsheet, never written to the JSON
# Rows that are not VerifiedValues: value only, status and source columns are ignored.
PLAIN_ROWS = {"program_page": "official_url", "program_name": "name", "collected_on": "collected_on"}
LONG_SLOTS = {"admissions.deadlines": 2, "funding.opportunities": 2}  # pre-filled; up to SLOTS[...] accepted
YES_NO = "yes/no"
AMOUNT = "amount [currency], e.g. 75 (USD if no currency)"
RATE = "amount [currency] per; per = credit_hour, term, academic_year, calendar_year, month, program_total, one_time"
# (field, label, hint) in the order a person fills them. "{i}" = slot index, "{n}" = slot number (i + 1).
LONG_FIELDS = [
    ("program_page", "Program page", "URL of the program's own page (https://...); default source_url of this program's rows"),
    ("program_name", "Program name", "name as the page writes it, with the degree, e.g. Master of Science in Computer Science"),
    ("collected_on", "Collected on", "date you collected this program, YYYY-MM-DD; default verified_at of its rows"),
    ("modality", "Delivery mode", "in_person, hybrid or online"),
    ("immigration.f1_compatible_modality", "Format allows F-1 status", "yes/no (no = fully online or closed to F-1)"),
    ("immigration.i20_issued_for_program", "I-20 issued for this program",
     "yes/no; international office page or written reply = confirmed_official (R11)"),
    ("immigration.stem_opt_claimed_by_program", "Program says it is STEM", "yes/no: the program advertises STEM / STEM OPT"),
    ("admissions.english.toefl_ibt_accepted", "TOEFL iBT accepted", YES_NO),
    ("admissions.english.toefl_ibt_min", "TOEFL iBT minimum", "TOEFL iBT total, integer 0-120"),
    ("admissions.english.toefl_ibt_section_min", "TOEFL section minimums",
     "only the published ones, 0-30: reading=20;listening=20;speaking=22;writing=22"),
    ("admissions.english.ielts_academic_accepted", "IELTS Academic accepted", YES_NO),
    ("admissions.english.ielts_academic_min", "IELTS overall minimum", "IELTS overall band, number 0-9, e.g. 6.5"),
    ("admissions.english.ielts_band_min", "IELTS minimum per band", "minimum on each IELTS band, number 0-9, e.g. 6"),
    ("admissions.english.duolingo_accepted", "Duolingo accepted", YES_NO),
    ("admissions.english.duolingo_min", "Duolingo minimum", "Duolingo English Test score, integer 10-160"),
    ("admissions.english.pte_academic_accepted", "PTE Academic accepted", YES_NO),
    ("admissions.english.pte_academic_min", "PTE Academic minimum", "PTE Academic score, integer 10-90"),
    ("admissions.english.waiver_available", "English test waiver exists", YES_NO),
    ("admissions.english.waiver_criteria", "English waiver criteria", "short text: who is exempt"),
    ("admissions.english.conditional_admission", "Conditional admission (English later)", YES_NO),
    ("admissions.english.conditional_admission_details", "Conditional admission details",
     "short text, e.g. through the intensive English program"),
    ("admissions.accepts_other_undergrad_area", "Bachelor's in another field accepted", YES_NO),
    ("admissions.prerequisites", "Prerequisites", "short text: required courses or knowledge"),
    ("admissions.gre", "GRE", "required, optional, not_required or waivable"),
    ("admissions.gmat", "GMAT", "required, optional, not_required or waivable"),
    ("admissions.min_gpa_4scale", "Minimum GPA", "number on a 4.0 scale, e.g. 3.0"),
    ("admissions.application_fee", "Application fee", AMOUNT),
    ("admissions.application_fee_waiver", "Application fee waiver", "yes/no; conditions go in evidence"),
    ("admissions.deadlines[{i}]", "Deadline {n}",
     ("term|year|applicant|kind|date, e.g. fall|2027|international|final|2027-02-01; "
      "applicant = international, domestic, all; kind = priority, final, funding_consideration, rolling (date empty)")),
    ("academic.start_terms", "Start terms", "fall, winter, spring, summer separated by ;, e.g. fall;spring"),
    ("academic.credits_required", "Credits required",
     "number [unit], e.g. 30 (semester credit hours if no unit) or 45 us_quarter_credit_hour"),
    ("academic.duration_months", "Duration in months", "typical full-time duration, integer months, e.g. 24"),
    ("academic.thesis_option", "Thesis option", "thesis_only, non_thesis_only or both"),
    ("cost.tuition_international", "Tuition (international)", RATE + "; e.g. 1450 credit_hour"),
    ("cost.fees", "Mandatory fees", RATE + "; e.g. 1200 term"),
    ("cost.tuition_fees_program_total", "Tuition and fees, program total", AMOUNT + "; only if a total is published"),
    ("cost.student_health_insurance", "Student health insurance", RATE + "; e.g. 3200 academic_year"),
    ("cost.i20_requirement_student", "I-20 funds required, student", RATE + "; e.g. 42000 academic_year"),
    ("cost.i20_requirement_per_dependent", "I-20 funds per dependent", RATE + "; e.g. 6000 academic_year"),
    ("funding.available_to_masters", "Funding for master's students", YES_NO),
    ("funding.opportunities[{i}].type", "Funding {n}: type",
     "TA, RA, GA, fellowship, scholarship, tuition_waiver or other (no status needed)"),
    ("funding.opportunities[{i}].tuition_coverage", "Funding {n}: tuition covered", "full, partial or none"),
    ("funding.opportunities[{i}].stipend", "Funding {n}: stipend", RATE + "; e.g. 1800 month"),
    ("funding.opportunities[{i}].hours_per_week", "Funding {n}: hours per week", "number, e.g. 20"),
    ("funding.opportunities[{i}].open_to_international", "Funding {n}: open to international students", YES_NO),
    ("funding.opportunities[{i}].open_to_masters", "Funding {n}: open to master's students", YES_NO),
    ("funding.opportunities[{i}].availability", "Funding {n}: availability", "guaranteed, competitive or rare"),
    ("immigration.cpt_available", "CPT available", YES_NO),
    ("immigration.cpt_from_first_term", "Day-1 CPT", "yes/no: CPT allowed from the first term"),
    ("immigration.internship", "Internship", "required, optional or not_offered"),
    ("family.family_housing_on_campus", "Family housing on campus", YES_NO),
    ("family.family_housing_rent", "Family housing rent", RATE + "; e.g. 950 month"),
    ("family.dependent_insurance_available", "Health plan covers spouse and children", YES_NO),
    ("family.dependent_insurance_cost", "Health plan cost, family tier", RATE + "; e.g. 9000 academic_year"),
]


# ---------------------------------------------------------------- schema walk

class Walker:
    def __init__(self, schema: dict, country: str = "US", include: list[str] | None = None):
        self.schema = schema
        self.country = country
        self.include = include  # None = every field; otherwise only these paths (and their subtrees)
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

    def wanted(self, path: str) -> bool:
        if self.include is None:
            return True
        return any(path == p or path.startswith(p + ".") or p.startswith(path + ".") for p in self.include)

    def walk(self):
        for name, sub in self.schema["properties"].items():
            if name in SKIP or not self.wanted(name):
                continue
            if name == "immigration":
                sub = {"$ref": f"#/$defs/immigration_{self.country.lower()}"}
            self._walk(sub, name)
        return self

    def _walk(self, node: dict, path: str):
        if not self.wanted(path):
            return
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


# ---------------------------------------------------------------- site-only mode

def site_walker(schema: dict, country: str = "US") -> Walker:
    return Walker(schema, country, SITE_ONLY_INCLUDE).walk()


def site_header(schema: dict | None = None, country: str = "US") -> list[str]:
    """Header of the long-format site template."""
    return list(LONG_COLUMNS)


def long_rows_for_program(program_id: str) -> list[dict]:
    """Pre-filled rows of one program (LONG_SLOTS slots for each list)."""
    rows = []
    for field, label, hint in LONG_FIELDS:
        slot = next((k for k in LONG_SLOTS if field.startswith(k + "[")), None)
        for i in range(LONG_SLOTS[slot] if slot else 1):
            rows.append({c: "" for c in LONG_COLUMNS} | {
                SITE_KEY: program_id,
                "field": field.format(i=i),
                "field_label": label.format(n=i + 1),
                "hint": hint,
            })
    return rows


def site_template(candidates_csv: str) -> str:
    """Long template pre-filled for each candidate (columns unitid and cip6 of pilot-candidates.csv)."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=LONG_COLUMNS, lineterminator="\n")
    w.writeheader()
    seen = set()
    for cand in csv.DictReader(io.StringIO(candidates_csv)):
        pid = f"{cand['unitid'].strip()}-{cand['cip6'].strip().replace('.', '')}"
        if pid in seen:
            continue
        seen.add(pid)
        w.writerows(long_rows_for_program(pid))
    return buf.getvalue()


def long_to_wide_path(field: str) -> str:
    """admissions.deadlines[0] -> admissions.deadlines.0"""
    return field.replace("[", ".").replace("]", "")


def _amount(tok: str, where: str) -> str:
    tok = tok.replace("$", "").replace(",", "")
    try:
        float(tok)
    except ValueError:
        raise ValueError(f"{where}: invalid amount {tok!r}") from None
    return tok


def parse_long_value(raw: str, parts: list[str], where: str) -> dict[str, str]:
    """Compact value -> {wide column suffix: raw text}. parts = the sub-columns of the value in wide mode."""
    if not parts:
        return {"value": raw}
    if set(parts) in ({"amount", "currency"}, {"amount", "currency", "per"}, {"amount", "unit"}):
        toks = raw.split()
        out = {"amount": _amount(toks[0], where)} if toks else {}
        rest = toks[1:]
        if "currency" in parts:
            out["currency"] = rest.pop(0) if rest and rest[0].isupper() and len(rest[0]) == 3 else "USD"
        if "per" in parts:
            if len(rest) != 1:
                raise ValueError(f"{where}: expected 'amount [currency] per', got {raw!r}")
            out["per"] = rest[0]
        elif "unit" in parts:
            out["unit"] = rest.pop(0) if rest else "us_semester_credit_hour"
        if ("per" not in parts and rest) or not toks:
            raise ValueError(f"{where}: cannot read {raw!r}")
        return {f"value.{k}": v for k, v in out.items()}
    if parts == ["term", "term_year", "applicant", "kind", "date"]:
        items = [x.strip() for x in raw.split("|")]
        if len(items) == 4:
            items.append("")  # rolling, no date
        if len(items) != 5:
            raise ValueError(f"{where}: expected term|year|applicant|kind|date, got {raw!r}")
        return {f"value.{k}": v for k, v in zip(parts, items) if v}
    out = {}
    for pair in raw.replace(",", ";").split(";"):
        if not pair.strip():
            continue
        key, sep, val = pair.partition("=")
        if not sep or key.strip() not in parts:
            raise ValueError(f"{where}: expected key=value with key in {parts}, got {pair!r}")
        out[f"value.{key.strip()}"] = val.strip()
    return out


def site_units(walker: Walker) -> list[str]:
    """Merge units: the keys of a site patch. Each column belongs to the shortest prefix that is a
    VerifiedValue or a list of objects; plain fields (name, official_url) are their own unit."""
    containers = set(walker.vv_paths) | set(walker.slot_paths)
    units: list[str] = []
    for path, _ in walker.columns:
        parts = path.split(".")
        unit = next((".".join(parts[:i]) for i in range(1, len(parts) + 1) if ".".join(parts[:i]) in containers), path)
        if unit not in units:
            units.append(unit)
    return units


def schema_node(schema: dict, path: str, country: str = "US") -> dict:
    """Schema node of a dotted document path (no list indexes)."""
    walker = Walker(schema, country)
    node = schema
    for i, part in enumerate(path.split(".")):
        if i == 0 and part == "immigration":
            node = walker._lookup(f"#/$defs/immigration_{country.lower()}")
            continue
        node = walker.resolve(node)["properties"][part]
    return node


def site_patch_schema(schema: dict, country: str = "US") -> dict:
    """JSON Schema of a site patch: the envelope plus, for each merge unit, the program schema node at that path."""
    units = site_units(site_walker(schema, country))
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "North site patch (site-only pilot fields for one ingested program)",
        "$defs": schema["$defs"],
        "type": "object",
        "additionalProperties": False,
        "required": ["format", "schema_version", "program_id", "fields"],
        "properties": {
            "format": {"const": SITE_PATCH_FORMAT},
            "schema_version": {"const": 0},
            "program_id": {"type": "string", "pattern": PROGRAM_ID_PATTERN},
            "fields": {
                "type": "object",
                "additionalProperties": False,
                "properties": {u: schema_node(schema, u, country) for u in units},
            },
        },
    }


def is_unfilled(value) -> bool:
    if value is None or value == [] or value == {}:
        return True
    return isinstance(value, dict) and value.get("status") == "unknown" and value.get("value") is None


def long_program_to_wide(rows: list[tuple[int, dict]], walker: Walker) -> tuple[dict, set[str], list[str]]:
    """Long rows of one program -> (wide row for row_to_doc, units written as explicit unknown, errors)."""
    cols = dict(walker.columns)
    vv_paths = set(walker.vv_paths)
    plain = set(cols)
    wide: dict[str, str] = {}
    explicit_unknown: set[str] = set()
    errors: list[str] = []
    seen: dict[str, int] = {}

    def get(r: dict, k: str) -> str:
        return (r.get(k) or "").strip()

    page = collected = ""
    for _, r in rows:
        if get(r, "field") == "program_page":
            page = get(r, "value")
        if get(r, "field") == "collected_on":
            collected = get(r, "value")

    for rownum, r in rows:
        field = get(r, "field")
        where = f"row {rownum} ({field})"
        filled = {k: get(r, k) for k in ("value", "status", "source_kind", "source_url", "evidence", "verified_at")}
        if field in seen and any(filled.values()):
            errors.append(f"{where}: field repeated (row {seen[field]})")
            continue
        seen.setdefault(field, rownum)
        if field in PLAIN_ROWS:
            if filled["value"]:
                wide[PLAIN_ROWS[field]] = filled["value"]
            continue
        path = long_to_wide_path(field)
        if path not in vv_paths:
            if path in plain and path.endswith((".type", ".name")):  # funding opportunity type/name
                if filled["value"]:
                    wide[path] = filled["value"]
                continue
            errors.append(f"{where}: unknown field")
            continue
        value, status = filled["value"], filled["status"]
        if not value and not status:
            if any(filled.values()):
                errors.append(f"{where}: source or evidence without a value; leave the row empty or write status unknown")
            continue  # not collected: left out of the patch
        parts = [c[len(path) + 7:] for c in cols if c.startswith(path + ".value.")]
        if value:
            try:
                for suffix, raw in parse_long_value(value, parts, where).items():
                    wide[f"{path}.{suffix}"] = raw
            except ValueError as exc:
                errors.append(str(exc))
                continue
        if not status:
            is_no = not parts and cols[f"{path}.value"]["kind"] == "bool" and value.lower() in FALSE
            status = "confirmed_negative" if is_no else "reported_by_program"
        if status == "unknown":
            if path.startswith("admissions.deadlines."):
                errors.append(f"{where}: a deadline is never unknown; leave the row empty")
                continue
            if value:
                errors.append(f"{where}: status unknown with a value")
                continue
            explicit_unknown.add(path)
        wide[f"{path}.status"] = status
        kind = filled["source_kind"]
        if kind:
            wide[f"{path}.source_kind"] = kind
        url = filled["source_url"] or ("" if status == "unknown" or kind == "correspondence" else page)
        if url:
            wide[f"{path}.source_url"] = url
        if filled["evidence"]:
            wide[f"{path}.evidence"] = filled["evidence"]
        verified = filled["verified_at"] or collected
        if verified:
            wide[f"{path}.verified_at"] = verified
    if any(k != "official_url" and k != "name" for k in wide) and not collected:
        errors.append(f"row {rows[0][0]}: the collected_on row is required once anything is filled in")
    if collected:
        wide["collected_on"] = collected
    return wide, explicit_unknown, errors


def convert_site(csv_text: str, schema: dict, country: str = "US"):
    """Long-format site CSV -> [(first row number, patch or None, errors or None)].
    A program with nothing filled in gives (row, None, None) and is skipped."""
    walker = site_walker(schema, country)
    units = site_units(walker)
    validator = Draft202012Validator(site_patch_schema(schema, country))
    reader = csv.DictReader(io.StringIO(csv_text))
    missing = [c for c in ("program_id", "field", "value", "status") if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"not a long-format site CSV: missing columns {missing}")
    programs: dict[str, list[tuple[int, dict]]] = {}
    for i, row in enumerate(reader, start=2):
        if not any((v or "").strip() for v in row.values() if isinstance(v, str)):
            continue
        programs.setdefault((row.get(SITE_KEY) or "").strip(), []).append((i, row))
    results = []
    for pid, rows in programs.items():
        first = rows[0][0]
        if not any((r.get(k) or "").strip() for _, r in rows for k in ("value", "status")):
            results.append((first, None, None))
            continue
        wide, explicit_unknown, errors = long_program_to_wide(rows, walker)
        if errors:
            results.append((first, None, [f"{pid}: {e}" for e in errors]))
            continue
        try:
            doc = row_to_doc(wide, walker, first)
        except ValueError as exc:
            results.append((first, None, [f"{pid}: {exc}"]))
            continue
        fields = {}
        for unit in units:
            value = get_path(doc, unit)
            if not is_unfilled(value) or unit in explicit_unknown:
                fields[unit] = value
        patch = {"format": SITE_PATCH_FORMAT, "schema_version": 0, "program_id": pid, "fields": fields}
        errs = [
            f"{pid}: {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
            for e in sorted(validator.iter_errors(patch), key=lambda e: list(map(str, e.absolute_path)))
        ]
        results.append((first, patch, errs))
    return results


def _is_known_vv(value) -> bool:
    return isinstance(value, dict) and value.get("status") not in (None, "unknown")


def _is_unknown_vv(value) -> bool:
    return isinstance(value, dict) and "status" in value and value.get("status") == "unknown"


def apply_site_patch(record: dict, patch: dict, schema: dict, country: str = "US") -> tuple[dict, list[dict]]:
    """Reference merge (see SITE PATCH in the module docstring).

    Returns (new record, conflicts). A key whose incoming value has status `unknown` is skipped
    when the stored value has a known status (rule 3: unknown never overwrites a known value);
    each skipped key is reported in `conflicts` as {"field", "stored", "incoming"} so the backend
    can open a reconciliation task.
    """
    units = set(site_units(site_walker(schema, country)))
    if patch.get("format") != SITE_PATCH_FORMAT:
        raise ValueError(f"not a site patch: {patch.get('format')!r}")
    if record.get("id") != patch["program_id"]:
        raise ValueError(f"patch for {patch['program_id']} applied to {record.get('id')}")
    bad = sorted(set(patch["fields"]) - units)
    if bad:
        raise ValueError(f"keys outside the site-only merge units: {bad}")
    out = copy.deepcopy(record)
    conflicts: list[dict] = []
    for key, value in patch["fields"].items():
        stored = get_path(out, key)
        if _is_unknown_vv(value) and _is_known_vv(stored):
            conflicts.append({"field": key, "stored": copy.deepcopy(stored), "incoming": copy.deepcopy(value)})
            continue
        set_path(out, key, copy.deepcopy(value))
    return out, conflicts


# ---------------------------------------------------------------- self-test

def self_test_full(schema: dict) -> int:
    """One fictitious valid row and invalid rows (missing source, deadline without source, R12)."""
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


# Fictitious filled values for the long-format self-test: field -> (value, status, source_kind, source_url, evidence, verified_at)
SITE_TEST_VALUES = {
    "program_page": ("https://example.edu/msds",),
    "program_name": ("Master of Science in Data Science (FICTITIOUS)",),
    "collected_on": ("2026-11-21",),
    "modality": ("in_person",),
    "immigration.i20_issued_for_program": (
        "yes", "confirmed_official", "correspondence", "",
        'Written reply from the international office, 2026-11-20: "The program is eligible for an I-20."', "2026-11-20"),
    "immigration.cpt_from_first_term": ("no", "", "", "https://example.edu/isss/cpt"),
    "admissions.english.toefl_ibt_accepted": ("yes",),
    "admissions.english.toefl_ibt_min": ("80", "", "", "https://example.edu/msds/admissions", "minimum TOEFL iBT score of 80"),
    "admissions.english.toefl_ibt_section_min": ("reading=20;writing=22",),
    "admissions.english.pte_academic_accepted": ("no",),
    "admissions.gre": ("", "unknown"),  # searched, not found
    "admissions.gmat": ("not_required",),
    "admissions.application_fee": ("$75",),
    "admissions.application_fee_waiver": ("no", "confirmed_negative", "", "https://example.edu/graduate-school/apply"),
    "admissions.deadlines[0]": ("fall|2027|international|final|2027-02-01", "", "", "https://example.edu/msds/deadlines"),
    "admissions.deadlines[1]": ("fall|2027|all|funding_consideration|2027-01-15", "", "", "https://example.edu/graduate-school/funding"),
    "academic.start_terms": ("fall;spring",),
    "academic.credits_required": ("30",),
    "cost.tuition_international": ("1,450 credit_hour", "", "", "https://example.edu/bursar/rates"),
    "cost.student_health_insurance": ("3200 USD academic_year",),
    "funding.available_to_masters": ("yes",),
    "funding.opportunities[0].type": ("TA",),
    "funding.opportunities[0].tuition_coverage": ("partial",),
    "funding.opportunities[0].hours_per_week": ("20",),
    "family.family_housing_on_campus": ("yes", "", "", "https://example.edu/housing/family"),
}
_LONG_FILL = ("value", "status", "source_kind", "source_url", "evidence", "verified_at")


def _long_csv(programs: dict[str, dict[str, tuple]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=LONG_COLUMNS)
    w.writeheader()
    for pid, values in programs.items():
        for row in long_rows_for_program(pid):
            row.update(zip(_LONG_FILL, values.get(row["field"], ())))
            w.writerow(row)
    return buf.getvalue()


def self_test_site(schema: dict) -> int:
    """Long-format site mode: template coverage, one valid program (+ merge onto the full example), invalid programs."""
    passed = True
    walker = site_walker(schema)
    rows = long_rows_for_program("000000-307001")
    fields = [r["field"] for r in rows]
    covered = {long_to_wide_path(f) for f in fields}
    wanted = {p for p in walker.vv_paths if not p.startswith(tuple(f"{k}." for k in LONG_SLOTS))}
    assert wanted <= covered, sorted(wanted - covered)
    assert all(r["field_label"] and r["hint"] for r in rows)
    assert len(fields) == len(set(fields))
    assert set(SITE_TEST_VALUES) <= set(fields), set(SITE_TEST_VALUES) - set(fields)
    print(f"ok   long site template: every site-only VerifiedValue has a row with label and hint ({len(rows)} rows per program)")

    good = dict(SITE_TEST_VALUES)
    bad_deadline = {k: v for k, v in good.items() if k != "program_page"}  # no default source left (R18, NFR-01)
    bad_deadline["admissions.deadlines[0]"] = ("fall|2027|international|final|2027-02-01",)
    bad_polarity = good | {"admissions.english.pte_academic_accepted": ("no", "reported_by_program")}
    bad_value = good | {"cost.tuition_international": ("1450",)}  # missing `per`
    no_date = {k: v for k, v in good.items() if k != "collected_on"}
    text = _long_csv({
        "000000-307001": good,
        "000000-307002": bad_deadline,
        "000000-307003": bad_polarity,
        "000000-307004": bad_value,
        "000000-307005": no_date,
        "228778-11.0701": good,  # cip6 must have no dot
        "000000-110701": {},  # untouched pre-filled program
    })
    ok_row, r_deadline, r_polarity, r_value, r_date, r_id, r_blank = convert_site(text, schema)

    if ok_row[2]:
        print("FAIL: the valid long-format program produced errors:", *ok_row[2], sep="\n  ")
        passed = False
    else:
        patch = ok_row[1]
        f = patch["fields"]
        assert patch["program_id"] == "000000-307001" and patch["format"] == SITE_PATCH_FORMAT
        assert f["name"].startswith("Master of Science") and f["official_url"] == "https://example.edu/msds"
        assert f["modality"]["status"] == "reported_by_program"  # default status
        assert f["modality"]["source_url"] == "https://example.edu/msds"  # default source = program page
        assert f["modality"]["source_kind"] == "page" and f["modality"]["verified_at"] == "2026-11-21"
        i20 = f["immigration.i20_issued_for_program"]
        assert i20["source_url"] is None and i20["verified_at"] == "2026-11-20" and i20["value"] is True
        cpt = f["immigration.cpt_from_first_term"]
        assert cpt["value"] is False and cpt["status"] == "confirmed_negative"  # "no" defaults to confirmed_negative
        assert f["admissions.english.toefl_ibt_min"]["value"] == 80
        assert f["admissions.english.toefl_ibt_section_min"]["value"] == {
            "reading": 20, "listening": None, "speaking": None, "writing": 22}
        assert f["admissions.gre"]["status"] == "unknown" and f["admissions.gre"]["verified_at"] == "2026-11-21"
        assert f["admissions.application_fee"]["value"] == {"amount": 75, "currency": "USD"}
        assert f["admissions.application_fee_waiver"]["value"] is False
        assert f["admissions.gmat"]["value"] == "not_required"
        assert f["cost.tuition_international"]["value"] == {"amount": 1450, "currency": "USD", "per": "credit_hour"}
        assert f["academic.credits_required"]["value"] == {"amount": 30, "unit": "us_semester_credit_hour"}
        assert f["academic.start_terms"]["value"] == ["fall", "spring"]
        assert [d["value"]["kind"] for d in f["admissions.deadlines"]] == ["final", "funding_consideration"]
        assert f["funding.opportunities"][0]["stipend"]["status"] == "unknown"
        assert len(f["funding.opportunities"]) == 1  # the empty second slot is dropped
        assert "admissions.english.duolingo_min" not in f  # empty row: left out, never unknown by default
        assert not any(k.startswith(("institution", "campus", "classifications")) for k in f)
        print(f"ok   valid long-format program -> patch valid ({len(f)} fields; defaults for status, source, date)")

        base = json.loads((SCHEMA_PATH.parent / "examples" / "program.example.json").read_text(encoding="utf-8"))
        base["id"] = patch["program_id"]  # ingested programs are keyed <unitid>-<cip6>
        merged, conflicts = apply_site_patch(base, patch, schema)
        errs = [f"{'/'.join(map(str, e.absolute_path))}: {e.message}"
                for e in Draft202012Validator(schema).iter_errors(merged)]
        if errs:
            print("FAIL: merged record is invalid:", *errs, sep="\n  ")
            passed = False
        else:
            assert merged["admissions"]["english"]["duolingo_min"] == base["admissions"]["english"]["duolingo_min"]
            assert merged["institution"] == base["institution"]
            assert len(merged["admissions"]["deadlines"]) == 2  # list replaced, not appended
            assert apply_site_patch(merged, patch, schema)[0] == merged  # idempotent
            print("ok   patch merged onto a full record -> record valid; absent keys untouched; idempotent")
            # admissions.gre is an explicit unknown in the patch and known in the example record:
            # the stored value is kept and the key comes back as a conflict.
            if merged["admissions"]["gre"] != base["admissions"]["gre"] or [c["field"] for c in conflicts] != ["admissions.gre"]:
                print("FAIL: an incoming unknown overwrote a known value or was not reported:", conflicts)
                passed = False
            else:
                print("ok   incoming unknown over a known value: skipped and reported as a conflict")
            base_unknown = copy.deepcopy(base)
            base_unknown["admissions"]["gre"] = {"value": None, "status": "unknown"}
            merged_unknown, conflicts_unknown = apply_site_patch(base_unknown, patch, schema)
            assert merged_unknown["admissions"]["gre"] == f["admissions.gre"] and not conflicts_unknown
            print("ok   incoming unknown over an unknown value: stored (dated), no conflict")
        try:
            apply_site_patch(base, patch | {"fields": {"campus.city": "X"}}, schema)
            print("FAIL: a patch touching an official-file field was accepted")
            passed = False
        except ValueError:
            print("ok   patch touching an official-file field rejected")

    for label, row in (
        ("no program page and a deadline without source_url (R18)", r_deadline),
        ("reported_by_program + false (R12)", r_polarity),
        ("rate without per", r_value),
        ("no collected_on row", r_date),
        ("program_id with a dotted CIP", r_id),
    ):
        if not row[2]:
            print(f"FAIL: the long-format '{label}' program passed")
            passed = False
        else:
            print(f"ok   invalid long-format program rejected ({label}):", row[2][0][:150])
            if row is r_deadline:
                assert any("admissions.deadlines/0/source_url" in e for e in row[2]), row[2]
    if r_blank[1] is None and r_blank[2] is None:
        print("ok   untouched pre-filled program skipped")
    else:
        print("FAIL: an untouched pre-filled program was not skipped")
        passed = False
    return 0 if passed else 1


def self_test(schema: dict) -> int:
    print("full mode")
    a = self_test_full(schema)
    print("site-only mode")
    b = self_test_site(schema)
    return a or b


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", help="filled-in spreadsheet")
    ap.add_argument("--out", default="out", help="output folder for the JSON files")
    ap.add_argument("--country", default="US")
    ap.add_argument("--print-header", action="store_true", help="print the spreadsheet header (template)")
    ap.add_argument("--site-only", action="store_true",
                    help="site-only pilot (long format, one row per program and field): header or conversion "
                         "to site patches (0004/O2)")
    ap.add_argument("--site-template", metavar="CANDIDATES_CSV",
                    help="print the pre-filled long site template for the candidates (columns unitid, cip6)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    if args.print_header:
        cols = site_header() if args.site_only else header(schema, args.country)
        csv.writer(sys.stdout, lineterminator="\n").writerow(cols)
        return 0
    if args.site_template:
        sys.stdout.write(site_template(Path(args.site_template).read_text(encoding="utf-8-sig")))
        return 0
    if args.self_test:
        return self_test(schema)
    if not args.csv:
        ap.error("pass a CSV, --print-header or --self-test")

    text = Path(args.csv).read_text(encoding="utf-8-sig")
    results = (convert_site if args.site_only else convert)(text, schema, args.country)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    failed = skipped = 0
    for rownum, doc, errs in results:
        if doc is None and errs is None:
            skipped += 1
            continue
        if errs:
            failed += 1
            print(f"{'program at row' if args.site_only else 'row'} {rownum}: INVALID")
            for e in errs:
                print(f"  - {e}")
            continue
        target = out / f"{doc['program_id'] if args.site_only else doc['id']}.json"
        target.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{'program at row' if args.site_only else 'row'} {rownum}: ok -> {target}")
    print(f"{len(results) - failed - skipped} valid, {failed} invalid"
          + (f", {skipped} skipped (nothing filled in)" if skipped else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
