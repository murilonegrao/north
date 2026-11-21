"""Validate program documents against program.schema.json.

Usage:
    uv run --with jsonschema schema/validate.py                 # validates examples/*.json + negative cases
    uv run --with jsonschema schema/validate.py file.json ...   # validates the given files

The negative cases build broken copies of the example in memory and check that the
schema rejects each one. Exit code 0 only if every valid file passes and every
negative case fails.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).parent
SCHEMA = json.loads((HERE / "program.schema.json").read_text(encoding="utf-8"))
EXAMPLE = HERE / "examples" / "program.example.json"


def errors(doc: dict) -> list[str]:
    v = Draft202012Validator(SCHEMA)
    return [
        f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
        for e in sorted(v.iter_errors(doc), key=lambda e: list(map(str, e.absolute_path)))
    ]


def negative_cases(base: dict):
    """(name, mutation) pairs. Each mutation must make the document invalid."""

    def confirmed_without_source(d):
        vv = d["eligibilities"][0]["result"]
        vv["status"] = "confirmed_official"
        vv["source_url"] = None

    def reported_without_source(d):
        del d["admissions"]["english"]["toefl_ibt_min"]["source_url"]

    def confirmed_without_date(d):
        d["campus"]["intl_authorization"]["verified_at"] = None

    def unknown_with_value(d):
        d["career"]["placement_rate_pct"]["value"] = 90

    def extracted_without_evidence(d):
        d["immigration"]["cpt_available"]["evidence"] = None

    def negative_without_source(d):
        d["family"]["childcare_on_campus"]["source_url"] = None

    def negative_on_numeric_field(d):
        # R12: "test not accepted" is <test>_accepted = false, never a negative minimum
        d["admissions"]["english"]["pte_academic_min"] = {
            "value": None, "status": "confirmed_negative", "source_kind": "page",
            "source_url": "https://example.edu/graduate-school/english-requirements",
            "evidence": "PTE Academic is not accepted.", "verified_at": "2026-11-21",
        }

    def negative_on_enum_field(d):
        vv = d["admissions"]["gre"]
        vv["status"] = "confirmed_negative"
        vv["value"] = "not_required"

    def official_false(d):
        # R12: a confirmed "no" is always confirmed_negative
        vv = d["family"]["childcare_on_campus"]
        vv["status"] = "reported_by_program"

    def sevp_not_authorized_as_official(d):
        d["campus"]["intl_authorization"]["value"]["authorized"] = False

    def asserted_without_source_kind(d):
        del d["modality"]["source_kind"]

    def page_without_url(d):
        d["modality"]["source_url"] = None  # source_kind = page, so the URL is required

    def correspondence_without_date(d):
        d["immigration"]["i20_issued_for_program"]["verified_at"] = None

    def email_in_evidence(d):
        d["immigration"]["i20_issued_for_program"]["evidence"] = "Reply from jane.doe@example.edu: eligible."

    def deadline_item_without_source(d):
        del d["admissions"]["deadlines"][0]["source_url"]

    def deadline_item_unknown(d):
        d["admissions"]["deadlines"].append(
            {"value": None, "status": "unknown", "source_kind": None, "source_url": None, "evidence": None, "verified_at": None}
        )

    def sevp_code_as_identifier(d):
        d["institution"]["identifiers"].append({"scheme": "sevp_campus", "value": "EXA000F00000000"})

    def campus_without_locality(d):
        del d["campus"]["locality"]

    def program_with_free_text_campus(d):
        d["campus"] = "Main Campus"

    def confirmed_with_null_value(d):
        d["modality"]["value"] = None

    def money_without_currency(d):
        del d["cost"]["fees"]["value"]["currency"]

    def bad_status(d):
        d["modality"]["status"] = "verified"

    def two_primary_classifications(d):
        d["classifications"].append(copy.deepcopy(d["classifications"][0]))

    def unknown_us_immigration_key(d):
        d["immigration"]["h1b_lottery_odds"] = {"value": None, "status": "unknown"}

    def generic_country_non_vv(d):
        d["country"] = "CA"
        d["subdivision"] = "CA-ON"
        d["immigration"] = {"pgwp_eligible": True}  # must be a VerifiedValue

    return [
        ("confirmed_official without source_url", confirmed_without_source),
        ("reported_by_program without source_url", reported_without_source),
        ("confirmed_official without verified_at", confirmed_without_date),
        ("unknown with a value", unknown_with_value),
        ("extracted_unverified without evidence", extracted_without_evidence),
        ("confirmed_negative without source_url", negative_without_source),
        ("confirmed_negative on a numeric field (R12)", negative_on_numeric_field),
        ("confirmed_negative on an enum field (R12)", negative_on_enum_field),
        ("reported_by_program + false instead of confirmed_negative (R12)", official_false),
        ("confirmed_official + authorized=false instead of confirmed_negative (R12)", sevp_not_authorized_as_official),
        ("asserting status without source_kind (R13)", asserted_without_source_kind),
        ("source_kind page without source_url", page_without_url),
        ("correspondence without verified_at (0002/A4/R13)", correspondence_without_date),
        ("email address in evidence (R13)", email_in_evidence),
        ("deadline item without source_url (R18)", deadline_item_without_source),
        ("deadline item with status unknown (R18)", deadline_item_unknown),
        ("SEVP code as institution identifier (0002/A15)", sevp_code_as_identifier),
        ("campus without locality (R17)", campus_without_locality),
        ("free-text campus (R17)", program_with_free_text_campus),
        ("asserting status with null value", confirmed_with_null_value),
        ("Money without currency", money_without_currency),
        ("status outside the BR-02 enum", bad_status),
        ("two primary classifications", two_primary_classifications),
        ("unknown key in immigration_us", unknown_us_immigration_key),
        ("country without module, non-VerifiedValue value", generic_country_non_vv),
    ]


def positive_cases(base: dict):
    """(name, document) pairs built from the example that must stay valid."""
    out = []

    d = copy.deepcopy(base)
    d["immigration"]["i20_issued_for_program"].update(source_kind="correspondence", source_url=None)
    out.append(("correspondence without source_url (R13)", d))

    d = copy.deepcopy(base)
    d["campus"]["intl_authorization"].update(
        value={"scheme": "sevp", "authorized": False}, status="confirmed_negative", evidence=None
    )
    out.append(("campus not SEVP-certified as confirmed_negative + authorized=false (R12)", d))

    d = copy.deepcopy(base)
    d["institution"]["accreditation"].update(value=False, status="confirmed_negative", source_kind="uploaded_file")
    out.append(("accreditation false + confirmed_negative (R10/R12)", d))

    d = copy.deepcopy(base)
    d["admissions"]["deadlines"] = []
    out.append(("no deadline recorded (empty list)", d))
    return out


def main(argv: list[str]) -> int:
    Draft202012Validator.check_schema(SCHEMA)
    files = [Path(a) for a in argv] or sorted((HERE / "examples").glob("*.json"))
    ok = True
    for f in files:
        errs = errors(json.loads(f.read_text(encoding="utf-8")))
        if errs:
            ok = False
            print(f"FAIL  {f}")
            for e in errs:
                print(f"      - {e}")
        else:
            print(f"ok    {f} is valid")

    if not argv:
        base = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        # a country without a module, with VerifiedValues only, must be accepted
        generic = copy.deepcopy(base)
        generic.update(country="CA", subdivision="CA-ON")
        generic["immigration"] = {"pgwp_eligible": {"value": None, "status": "unknown"}}
        if errors(generic):
            ok = False
            print("FAIL  country without module (CA) with VerifiedValues was rejected:", errors(generic)[0])
        else:
            print("ok    country without module (CA) with VerifiedValues accepted")
        for name, doc in positive_cases(base):
            errs = errors(doc)
            if errs:
                ok = False
                print(f"FAIL  rejected but should be valid: {name}  [{errs[0]}]")
            else:
                print(f"ok    accepted: {name}")
        for name, mutate in negative_cases(base):
            doc = copy.deepcopy(base)
            mutate(doc)
            errs = errors(doc)
            if errs:
                print(f"ok    rejected: {name}  [{errs[0]}]")
            else:
                ok = False
                print(f"FAIL  accepted but should be invalid: {name}")
    print("ALL PASSED" if ok else "THERE ARE FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
