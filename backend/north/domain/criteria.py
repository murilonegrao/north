"""Criterion results shared by the country modules (UML §2, BR-02, record 0008/T2).

A criterion is evaluated for one program and one profile. ``undetermined`` is the result of
missing data and never excludes a program by itself; only ``fail`` does (BR-02).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


class Outcome(StrEnum):
    PASS = "pass"
    PASS_WITH_CAVEAT = "pass_with_caveat"
    UNDETERMINED = "undetermined"
    FAIL = "fail"


@dataclass(frozen=True)
class Criterion:
    key: str  # e.g. "authorization", "family"
    outcome: Outcome
    reason: str  # a code the UI translates, never UI text
    rule_keys: tuple[str, ...] = ()  # migration rules cited (with their source and check date)


Party = Literal["alone", "with_family"]


@dataclass(frozen=True)
class TravellingParty:
    """Who travels, per program kind (record 0008/T2). Defaults: alone for a language course,
    with the family for a degree."""

    language_course: Party = "alone"
    degree: Party = "with_family"

    def for_kind(self, kind: str) -> Party:
        return self.language_course if kind == "language_course" else self.degree


@dataclass(frozen=True)
class Profile:
    """The parts of the profile the country criteria read (more fields arrive with FR-04)."""

    dependents: int = 0
    travelling_party: TravellingParty = field(default_factory=TravellingParty)
