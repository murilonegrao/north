"""Derived ``program_eligibilities`` for ``us.stem_opt`` (BR-03, record 0002/A8).

Recomputed for every US program whenever a rule version or a program's primary CIP changes.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from north.domain.countries.us.stem import RULE_KEY, StemRule, stem_opt_eligibility
from north.domain.verified import SourceKind, Status, verified
from north.repository.models import (
    Campus,
    Classification,
    EligibilityRule,
    EligibilityRuleCode,
    FieldChange,
    Institution,
    Program,
    ProgramClassification,
    ProgramEligibility,
    Subdivision,
)

COUNTRY = "US"


def current_rule(session: Session) -> EligibilityRule | None:
    return session.scalar(
        select(EligibilityRule)
        .where(EligibilityRule.country_code == COUNTRY, EligibilityRule.key == RULE_KEY)
        .order_by(EligibilityRule.published_on.desc().nulls_last(),
                  EligibilityRule.version.desc())
        .limit(1))


def load_stem_rule(session: Session, rule: EligibilityRule) -> StemRule:
    codes = session.scalars(
        select(Classification.code)
        .join(EligibilityRuleCode, EligibilityRuleCode.classification_id == Classification.id)
        .where(EligibilityRuleCode.rule_id == rule.id))
    return StemRule.build(rule.version, codes, rule.params)


def _evidence(cip: str, rule: StemRule, eligible: bool) -> str:
    name = f"DHS STEM Designated Degree Program List {rule.version}"
    if cip in rule.codes:
        return f"{name}: {cip} is listed"
    if eligible:
        return f"{name}: series {cip[:2]} is designated in full"
    return f"{name}: {cip} is not listed"


def _strip(v: dict[str, Any]) -> dict[str, Any]:
    return {k: x for k, x in v.items() if k != "verified_at"}


def recompute_stem_eligibilities(session: Session, *, author: str,
                                 counts: Counter[str] | None = None) -> int:
    """Recompute the eligibility of every US program under the current rule version."""
    rule = current_rule(session)
    if rule is None:
        return 0
    stem = load_stem_rule(session, rule)
    today = dt.date.today().isoformat()
    rows = session.execute(
        select(Program, Classification.code)
        .join(ProgramClassification, ProgramClassification.program_id == Program.id)
        .join(Classification, Classification.id == ProgramClassification.classification_id)
        .join(Campus, Campus.id == Program.campus_id)
        .join(Institution, Institution.id == Campus.institution_id)
        .join(Subdivision, Subdivision.id == Institution.subdivision_id)
        .where(ProgramClassification.is_primary.is_(True),
               Classification.scheme == "cip2020", Subdivision.country_code == COUNTRY))
    n = 0
    for prog, cip in rows:
        claimed = (prog.immigration.get("stem_opt_claimed_by_program") or {}).get("value")
        res = stem_opt_eligibility(cip, stem, claimed if isinstance(claimed, bool) else None)
        if res.status == Status.UNKNOWN:
            result: dict[str, Any] = verified(None, Status.UNKNOWN)
        else:
            result = verified(res.eligible, res.status, source_kind=SourceKind.OFFICIAL_LIST,
                              source_url=rule.source_url,
                              evidence=_evidence(cip, stem, bool(res.eligible)),
                              verified_at=today)
        pe = session.get(ProgramEligibility, (prog.id, rule.id))
        old = pe.result if pe else None
        if pe is None:
            pe = ProgramEligibility(program_id=prog.id, rule_id=rule.id, result=result,
                                    rule_version=rule.version,
                                    claim_mismatch=res.claim_mismatch)
            session.add(pe)
        else:
            pe.result, pe.claim_mismatch = result, res.claim_mismatch
            pe.computed_at = dt.datetime.now(dt.UTC)
        if old is None or _strip(old) != _strip(result):
            session.add(FieldChange(program_id=prog.id, field_path=f"eligibility[{RULE_KEY}]",
                                    old_value=old, new_value=result, author=author))
            if counts is not None:
                counts["field_changes"] += 1
        if counts is not None:
            counts[f"stem_{'unknown' if res.eligible is None else res.eligible}"] += 1
        n += 1
    session.flush()
    return n
