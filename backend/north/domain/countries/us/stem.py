"""Rule ``us.stem_opt``: is a 6-digit CIP on the DHS STEM Designated Degree Program List?

The rule version carries the listed 6-digit codes and the 2-digit series designated in full
(``params.whole_series``, record 0002/A14): any code in those series is eligible, even one
added to CIP after the list was printed. Result statuses follow BR-02 and R12: the list is an
official source, so a listed code is ``confirmed_official`` + true and an unlisted one is
``confirmed_negative`` + false. Without a rule or with an invalid code the answer is ``unknown``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from north.domain.countries.us.cip import is_cip6
from north.domain.verified import Status

RULE_KEY = "us.stem_opt"
FLAG_NO_STEM_OPT_EXTENSION = "no_stem_opt_extension"
# Record 0002/R1: no 52.12xx code is on the list; the card says so.
NO_EXTENSION_PREFIXES = ("52.12",)


@dataclass(frozen=True)
class StemRule:
    version: str
    codes: frozenset[str]
    whole_series: frozenset[str] = frozenset()

    @classmethod
    def build(cls, version: str, codes: Iterable[str],
              params: Mapping[str, Any] | None = None) -> StemRule:
        series = (params or {}).get("whole_series", [])
        return cls(version=version, codes=frozenset(codes), whole_series=frozenset(series))


@dataclass(frozen=True)
class StemResult:
    eligible: bool | None
    status: Status
    rule_version: str | None
    claim_mismatch: bool = False


def stem_opt_eligibility(cip: str, rule: StemRule | None,
                         claimed_by_program: bool | None = None) -> StemResult:
    """Eligibility of a 6-digit CIP under one rule version.

    ``claimed_by_program`` is ``immigration.stem_opt_claimed_by_program``; ``claim_mismatch``
    is true only when the program claims STEM and the CIP is confirmed not eligible (0002/A8).
    """
    if rule is None or not is_cip6(cip):
        return StemResult(None, Status.UNKNOWN, rule.version if rule else None)
    eligible = cip in rule.codes or cip[:2] in rule.whole_series
    status = Status.CONFIRMED_OFFICIAL if eligible else Status.CONFIRMED_NEGATIVE
    mismatch = bool(claimed_by_program) and not eligible
    return StemResult(eligible, status, rule.version, mismatch)


def program_flags(cip: str) -> list[str]:
    """Derived flags of a program from its primary CIP (record 0002/R1)."""
    if cip.startswith(NO_EXTENSION_PREFIXES):
        return [FLAG_NO_STEM_OPT_EXTENSION]
    return []
