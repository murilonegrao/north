"""Irish rules module (record 0008/T2, T5, T6, C2; BR-18, BR-21). Pure."""

from __future__ import annotations

from north.domain.cefr import bands_up_to, rank
from north.domain.countries import rules_for
from north.domain.countries.ie import rules
from north.domain.criteria import Outcome, Profile, TravellingParty


def _auth(scheme: str, status: str = "confirmed_official", authorized: bool = True) -> dict:
    return {"value": {"scheme": scheme, "authorized": authorized}, "status": status,
            "source_kind": "uploaded_file", "source_url": "https://example.org/list",
            "verified_at": "2026-11-22"}


def test_authorization_on_a_list_passes() -> None:
    ilep = rules.authorization(_auth("ie_ilep"))
    assert ilep.outcome == Outcome.PASS and ilep.rule_keys == ("ie.ilep_end",)
    trusted = rules.authorization(_auth("ie_trusted"))
    assert trusted.outcome == Outcome.PASS and trusted.rule_keys == ()


def test_not_found_on_the_lists_is_undetermined_never_fail() -> None:
    for value in (None, {}, {"value": None, "status": "unknown"}, _auth("sevp")):
        assert rules.authorization(value).outcome == Outcome.UNDETERMINED
    # Only a curator-confirmed negative fails (C1).
    negative = _auth("ie_ilep", status="confirmed_negative", authorized=False)
    assert rules.authorization(negative).outcome == Outcome.FAIL


def test_family_criterion_follows_the_travelling_party() -> None:
    family = Profile(dependents=2)  # default: alone for courses, with the family for degrees
    assert rules.family("language_course", family).outcome == Outcome.PASS
    fail = rules.family("degree", family)
    assert fail.outcome == Outcome.FAIL and fail.rule_keys == ("ie.stamp2_no_dependants",)
    together = Profile(dependents=2, travelling_party=TravellingParty(
        language_course="with_family"))
    assert rules.family("language_course", together).outcome == Outcome.FAIL
    assert rules.family("degree", Profile(dependents=0)).outcome == Outcome.PASS


def test_rules_are_dated_and_sourced() -> None:
    for rule in rules.RULES.values():
        assert rule.source_url.startswith("https://www.irishimmigration.ie/")
        assert rule.checked_on == "2026-11-22"
    stay = rules.english_course_stay()
    assert stay["ie.english_course_min_weeks"]["params"] == {"weeks": 25}
    assert stay["ie.english_course_months"]["params"] == {"months_per_course": 8,
                                                          "max_courses": 3}
    assert stay["ie.work_hours"]["params"]["term_hours_per_week"] == 20
    assert stay["ie.work_hours"]["params"]["holiday_hours_per_week"] == 40


def test_registry_exposes_ireland_through_the_common_interface() -> None:
    ie = rules_for("ie")
    assert ie.currency == "EUR" and ie.cities_unique and ie.stem_rule_key is None
    assert ie.subdivision_id("D") == "IE-D" and "CO" in ie.subdivisions
    assert [n["code"] for n in ie.authorization_notes("ie_ilep")] == ["ie.ilep_end"]
    assert ie.authorization_notes("ie_trusted") == []
    assert rules_for("US").authorization_notes("sevp") == []


def test_cefr_bands() -> None:
    assert bands_up_to("A1") == ("A0", "A1")
    assert bands_up_to("B1") == ("A0", "A1", "A2", "B1")
    assert rank("A0") < rank("C2")
