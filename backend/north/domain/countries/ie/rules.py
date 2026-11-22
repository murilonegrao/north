"""Irish migration rules and criteria (record 0008/T2, T5, T6, C2; BR-18, BR-21). Pure.

Rules are data with their source and check date (``docs/sources/ireland-immigration-rules.md``,
read on 2026-11-22). They become ``migration_rules`` rows when that table exists; until then the
API reads them from here through the country registry.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from north.domain.criteria import Criterion, Outcome, Profile

CHECKED_ON = "2026-11-22"
ISD_COURSE = ("https://www.irishimmigration.ie/coming-to-study-in-ireland/what-are-my-study-"
              "options/a-third-level-course-or-a-language-course/")
ISD_ILEP = ("https://www.irishimmigration.ie/coming-to-study-in-ireland/what-are-my-study-"
            "options/interim-list-of-eligible-programmes-ilep/")
ISD_PLAN = ("https://www.irishimmigration.ie/coming-to-study-in-ireland/what-are-my-study-"
            "options/planning-to-study-in-ireland/")
ISD_FAQ = ("https://www.irishimmigration.ie/coming-to-study-in-ireland/frequently-asked-"
           "questions-for-students/")
ISD_FRP = ("https://www.irishimmigration.ie/wp-content/uploads/2026/06/"
           "Family-Reunification-Policy-12-June-2026.pdf")

SCHEME_ILEP = "ie_ilep"
SCHEME_TRUSTED = "ie_trusted"
SCHEMES = (SCHEME_ILEP, SCHEME_TRUSTED)


@dataclass(frozen=True)
class MigrationRule:
    key: str
    params: Mapping[str, Any]
    source_url: str
    checked_on: str = CHECKED_ON
    applies_to_schemes: tuple[str, ...] = field(default=())

    def note(self) -> dict[str, Any]:
        """The rule as a note attached to a served value (the UI translates ``code``)."""
        return {"code": self.key, "params": dict(self.params), "source_url": self.source_url,
                "checked_on": self.checked_on}


RULES: dict[str, MigrationRule] = {r.key: r for r in (
    # T6: "ILEP will continue in operation until the decisions from the second TrustEd
    # application are announced which is scheduled for the end of 2026".
    MigrationRule("ie.ilep_end", {"ends": "after_second_trusted_round", "scheduled": "2026-12"},
                  ISD_ILEP, applies_to_schemes=(SCHEME_ILEP,)),
    # BR-21: an English course on the lists runs at least 25 weeks and gives up to 8 months of
    # Stamp 2; at most three such courses (two years of English in total).
    MigrationRule("ie.english_course_min_weeks", {"weeks": 25}, ISD_COURSE),
    MigrationRule("ie.english_course_months", {"months_per_course": 8, "max_courses": 3},
                  ISD_PLAN),
    MigrationRule("ie.work_hours", {"term_hours_per_week": 20, "holiday_hours_per_week": 40,
                                    "holidays": ["06-01/09-30", "12-15/01-15"]}, ISD_PLAN),
    # T2: students on Stamp 2 are ineligible sponsors (Family Reunification Policy §5.4),
    # except PhD students and recognised scholarship holders (Stamp 2A, no work).
    MigrationRule("ie.stamp2_no_dependants", {"exceptions": ["phd", "isd_scholarship"]},
                  ISD_FRP),
)}


def rule_notes(scheme: str) -> list[dict[str, Any]]:
    """Notes to show next to an authorization of ``scheme`` (e.g. the ILEP end, T6)."""
    return [r.note() for r in RULES.values() if scheme in r.applies_to_schemes]


def english_course_stay() -> dict[str, Any]:
    """The stay facts of an English course (BR-21), each with its source and check date."""
    keys = ("ie.english_course_min_weeks", "ie.english_course_months", "ie.work_hours")
    return {k: RULES[k].note() for k in keys}


def authorization(intl_authorization: Mapping[str, Any] | None) -> Criterion:
    """Programme on ILEP or TrustEd -> pass. Not found -> undetermined, never fail (BR-18):
    absence from a list is not a "no" until a curator confirms it (C1)."""
    vv = intl_authorization or {}
    value = vv.get("value") or {}
    if (vv.get("status") == "confirmed_official" and value.get("scheme") in SCHEMES
            and value.get("authorized") is True):
        rules = ("ie.ilep_end",) if value["scheme"] == SCHEME_ILEP else ()
        return Criterion("authorization", Outcome.PASS, f"listed_{value['scheme']}", rules)
    if vv.get("status") == "confirmed_negative":
        return Criterion("authorization", Outcome.FAIL, "confirmed_not_listed")
    return Criterion("authorization", Outcome.UNDETERMINED, "not_found_on_lists")


def family(kind: str, profile: Profile) -> Criterion:
    """T2: the family criterion uses the dependents only when the party for this kind travels
    with the family. On Stamp 2 dependants are not allowed, so that is a fail citing the rule.
    (NFQ 10 research degrees, pass_with_caveat, arrive with Irish higher education, E3.)"""
    party = profile.travelling_party.for_kind(kind)
    if party == "alone" or profile.dependents == 0:
        return Criterion("family", Outcome.PASS, "travelling_alone")
    return Criterion("family", Outcome.FAIL, "stamp2_no_dependants", ("ie.stamp2_no_dependants",))
