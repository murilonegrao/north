"""Programs API, contract v0.4 (docs/api/programs-v0.md).

Filters, facets and sort keys are SQLAlchemy expressions over the JSONB VerifiedValues; JSON
paths and user values are bound parameters, never formatted into SQL. Facets reuse the very
predicates of the filters, so a count always equals the length of the filtered list.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.exceptions import RequestValidationError
from pydantic import StringConstraints
from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.elements import ColumnElement

from north.api import schemas as s
from north.domain.cefr import BANDS, bands_up_to
from north.domain.countries import (
    DEFAULT_COUNTRY,
    CountryRules,
    country_of_subdivision,
    is_country,
    rules_for,
)
from north.repository.db import session_scope
from north.repository.models import (
    Campus,
    Classification,
    ClassificationMap,
    EligibilityRule,
    IngestionRun,
    Institution,
    InstitutionIdentifier,
    Program,
    ProgramClassification,
    ProgramEligibility,
    ProgramIdentifier,
    SourceFile,
    Subdivision,
)

router = APIRouter(prefix="/api", tags=["programs"])
DB = Annotated[Session, Depends(session_scope)]

NOT_YET_COLLECTED = {
    "degree": ["admissions.english", "admissions.deadlines", "admissions.other_field_accepted",
               "funding", "cost.program_tuition", "immigration.i20_issued_for_program"],
    # Record 0008/T13: price and start dates come from the school's own site (FR-13).
    "language_course": ["language_course.price", "language_course.start_dates"],
}
KINDS: tuple[str, ...] = ("degree", "language_course")
EXAMS: tuple[str, ...] = ("ielts", "cambridge", "trinity", "languagecert", "toefl", "pte",
                          "duolingo", "tie", "other")
COURSE_FACTS = ("cefr_entry", "cefr_exit", "exam", "weeks", "hours_per_week", "price")
UNKNOWN: dict[str, Any] = {"value": None, "status": "unknown"}
NOTE_TUITION = "institution_wide_average"


# Free-text parameters never carry NUL (PostgreSQL rejects it in text: 422, never 500).
NO_NUL = r"^[^\x00]*$"
# US `<unitid>-<cip6>`, Ireland `ie-ilep-0018-0001`: lower-case words joined by dashes.
PROGRAM_ID = r"^[a-z0-9]{1,12}(?:-[a-z0-9]{1,12}){1,5}$"
MAX_OFFSET = 100_000
MAX_SOURCES = 500


def _rules_for(country: str | None, state: str | None) -> CountryRules:
    """An explicit ``country`` wins; else the country of ``state``; else the default (US)."""
    if country:
        if not is_country(country):
            raise _invalid("country", "a country North covers (US, IE)", country)
        return rules_for(country)
    return rules_for(country_of_subdivision(state) if state else DEFAULT_COUNTRY)


def _in_scope(rules: CountryRules, state: str | None,
              kind: str | None = None) -> ColumnElement[bool]:
    """One subdivision, or the whole country when no state is given; optionally one kind."""
    where = (Institution.subdivision_id == rules.subdivision_id(state) if state
             else Institution.country_code == rules.code)
    return and_(where, Program.kind == kind) if kind else where


def _current_rule(db: Session, rules: CountryRules) -> EligibilityRule | None:
    if not rules.stem_rule_key:
        return None
    return db.scalar(
        select(EligibilityRule)
        .where(EligibilityRule.country_code == rules.code,
               EligibilityRule.key == rules.stem_rule_key)
        .order_by(EligibilityRule.published_on.desc().nulls_last(),
                  EligibilityRule.version.desc()).limit(1))


def _base(rule_id: int | None) -> tuple[Select[Any], Any]:
    pe = aliased(ProgramEligibility)
    join_pe = and_(pe.program_id == Program.id, pe.rule_id == (rule_id or -1))
    return (
        select(Program, Campus, Institution, Classification, pe)
        .join(Campus, Campus.id == Program.campus_id)
        .join(Institution, Institution.id == Campus.institution_id)
        # Outer joins: a language course has no CIP (record 0008/T13).
        .outerjoin(ProgramClassification, and_(ProgramClassification.program_id == Program.id,
                                               ProgramClassification.is_primary.is_(True)))
        .outerjoin(Classification,
                   Classification.id == ProgramClassification.classification_id)
        .outerjoin(pe, join_pe)
    ), pe


def _stem(pe: ProgramEligibility | None) -> dict[str, Any]:
    if pe is None or pe.result.get("status") == "unknown":
        return dict(UNKNOWN)
    r = pe.result
    return {**r, "value": {"eligible": r["value"], "rule_version": pe.rule_version,
                           "claim_mismatch": pe.claim_mismatch}}


def _status(v: dict[str, Any] | None) -> str:
    return (v or {}).get("status") or "unknown"


def _title_source(p: Program) -> str:
    return p.academic.get("title_source") or "cip_title"


def _state(inst: Institution) -> str | None:
    sid = inst.subdivision_id
    return CountryRules.local_subdivision(sid) if sid else None


def _tuition(p: Program) -> dict[str, Any]:
    if p.kind == "language_course":  # no institution-wide average for a course
        return {**UNKNOWN, "note_code": None}
    return p.cost.get("graduate_tuition_nonresident") or {**UNKNOWN, "note_code": NOTE_TUITION}


def _no_evidence(v: dict[str, Any]) -> dict[str, Any]:
    return {k: x for k, x in v.items() if k != "evidence"}


def _language_course(p: Program, evidence: bool) -> dict[str, Any] | None:
    """The course facts (v0.4): every one a VerifiedValue; lists omit ``evidence``."""
    if p.kind != "language_course":
        return None
    lc = p.language_course or {}
    out: dict[str, Any] = {}
    for key in COURSE_FACTS:
        v = lc.get(key) or dict(UNKNOWN)
        out[key] = v if evidence else _no_evidence(v)
    out["start_dates"] = [v if evidence else _no_evidence(v) for v in lc.get("start_dates") or []]
    return out


def _authorization(rules: CountryRules, p: Program, evidence: bool) -> dict[str, Any] | None:
    """The program-level authorization (record 0008/T5) with the rule notes of its scheme."""
    v = p.intl_authorization
    if not v:
        return dict(UNKNOWN, notes=[]) if p.kind == "language_course" else None
    scheme = (v.get("value") or {}).get("scheme")
    out = v if evidence else _no_evidence(v)
    return {**out, "notes": rules.authorization_notes(scheme) if scheme else []}


def _item(rules: CountryRules, p: Program, c: Campus, i: Institution,
          cls: Classification | None, pe: ProgramEligibility | None,
          evidence: bool = False) -> dict[str, Any]:
    tuition = _tuition(p)
    return {
        "id": p.id, "kind": p.kind, "country": i.country_code, "title": p.name,
        "title_source": _title_source(p), "degree": p.degree,
        "cip": {"code": cls.code, "title": cls.title, "family": rules.cip_family(cls.code)}
        if cls else None,
        "institution": {"id": i.id, "name": i.name, "control": i.control},
        "campus": {"city": c.city, "state": _state(i)},
        "stem_opt": _stem(pe),
        "flags": list(p.flags or []),
        "completions": p.academic.get("completions") or dict(UNKNOWN),
        "graduate_tuition_nonresident": tuition if evidence else _no_evidence(tuition),
        "sevp_status": _status(c.intl_authorization),
        "accreditation_status": _status(i.accreditation),
        "language_course": _language_course(p, evidence),
        "intl_authorization": _authorization(rules, p, evidence),
    }


# --------------------------------------------------------------------------- predicates

Control = Literal["public", "private_nonprofit", "private_for_profit"]
CONTROLS: tuple[str, ...] = ("public", "private_nonprofit", "private_for_profit")
SortKey = Literal["title", "institution", "city", "tuition", "graduates",
                  "nonresident_graduates", "nonresident_share"]
City = Annotated[str, StringConstraints(min_length=1, max_length=120, pattern=NO_NUL)]
MAX_TUITION = 1_000_000


def _vv_status(col: Any, *path: str) -> ColumnElement[Any]:
    """Status of the VerifiedValue at ``path`` in a JSONB column ('unknown' when absent)."""
    return func.coalesce(col[(*path, "status")].astext, "unknown")


def _tuition_amount() -> ColumnElement[Any]:
    return Program.cost[("graduate_tuition_nonresident", "value", "amount")].as_float()


def _completions(field: str) -> ColumnElement[Any]:
    """``completions.value.<field>``; NULL when the completions are unknown."""
    known = _vv_status(Program.academic, "completions") != "unknown"
    return case((known, Program.academic[("completions", "value", field)].as_float()),
                else_=None)


def _family_pred(rules: CountryRules, family: str) -> ColumnElement[bool]:
    prefix = rules.cip_families.get(family)
    if prefix is None:  # a family the country does not define matches nothing
        return Classification.id.is_(None)
    return Classification.code.startswith(prefix)


def _like_pattern(text: str) -> str:
    """``%text%`` with LIKE wildcards in ``text`` escaped, so they match literally."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _stem_pred(pe: Any, value: str) -> ColumnElement[bool]:
    status = pe.result["status"].astext
    if value == "unknown":
        return or_(pe.program_id.is_(None), status == "unknown")
    return and_(pe.program_id.is_not(None), status != "unknown",
                pe.result["value"].astext == ("true" if value == "eligible" else "false"))


def _sevp_pred(value: str) -> ColumnElement[bool]:
    status = _vv_status(Campus.intl_authorization)
    if value == "unknown":
        return status == "unknown"
    return and_(status == "confirmed_official",
                Campus.intl_authorization[("value", "authorized")].as_boolean().is_(True))


def _accredited_pred(value: str) -> ColumnElement[bool]:
    status = _vv_status(Institution.accreditation)
    if value == "unknown":
        return status == "unknown"
    return and_(status == "confirmed_official",
                Institution.accreditation[("value", "institutional")].as_boolean().is_(True))


def _graduates_pred(value: str) -> ColumnElement[bool]:
    total = _completions("total")
    # Unknown completions match neither value (BR-02: unknown is never negative).
    return total > 0 if value == "true" else total == 0


def _course_value(key: str) -> ColumnElement[Any]:
    """``language_course.<key>.value`` as text (NULL when unknown or not a course)."""
    return Program.language_course[(key, "value")].astext


def _exam_pred(value: str) -> ColumnElement[bool]:
    if value == "unknown":
        return and_(Program.kind == "language_course", _course_value("exam").is_(None))
    return _course_value("exam") == value


def _cefr_entry_pred(value: str) -> ColumnElement[bool]:
    if value == "unknown":
        return and_(Program.kind == "language_course", _course_value("cefr_entry").is_(None))
    return _course_value("cefr_entry") == value


def _hours() -> ColumnElement[Any]:
    return Program.language_course[("hours_per_week", "value")].as_float()


def _sort_expr(key: str) -> ColumnElement[Any]:
    if key == "title":
        return Program.name
    if key == "institution":
        return Institution.name
    if key == "city":
        return Campus.city
    if key == "tuition":
        return _tuition_amount()
    if key == "graduates":
        return _completions("total")
    if key == "nonresident_graduates":
        return _completions("nonresident")
    # nonresident_share: undefined (NULL, sorted last) when there are no graduates.
    return _completions("nonresident") / func.nullif(_completions("total"), 0)


def _invalid(field: str, msg: str, value: Any) -> RequestValidationError:
    return RequestValidationError([{"type": "value_error", "loc": ("query", field),
                                    "msg": msg, "input": value}])


STATE = Annotated[str | None, Query(pattern=r"^[A-Za-z]{1,3}$")]
COUNTRY = Annotated[str | None, Query(pattern=r"^[A-Za-z]{2}$")]
Kind = Literal["degree", "language_course"]
Exam = Literal["ielts", "cambridge", "trinity", "languagecert", "toefl", "pte", "duolingo",
               "tie", "other"]
Band = Literal["A0", "A1", "A2", "B1", "B2", "C1", "C2"]


@router.get("/programs", response_model=s.ProgramList)
def list_programs(
    db: DB,
    country: COUNTRY = None,
    state: STATE = None,
    kind: Kind | None = None,
    cip_family_: Annotated[list[Literal["11", "30.70", "30.71", "52.12"]] | None,
                           Query(alias="cip_family")] = None,
    stem: Literal["eligible", "not_eligible", "unknown"] | None = None,
    q: Annotated[str | None, Query(max_length=200, pattern=NO_NUL)] = None,
    control: Annotated[list[Control] | None, Query()] = None,
    city: Annotated[list[City] | None, Query(max_length=50)] = None,
    min_tuition: Annotated[float | None, Query(ge=0, le=MAX_TUITION)] = None,
    max_tuition: Annotated[float | None, Query(ge=0, le=MAX_TUITION)] = None,
    sevp: Literal["confirmed", "unknown"] | None = None,
    accredited: Literal["true", "unknown"] | None = None,
    has_graduates: Literal["true", "false"] | None = None,
    exam: Annotated[list[Exam] | None, Query()] = None,
    cefr_entry_max: Band | None = None,
    hours_min: Annotated[float | None, Query(ge=0, le=80)] = None,
    sort: SortKey = "title",
    order: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> dict[str, Any]:
    if min_tuition is not None and max_tuition is not None and max_tuition < min_tuition:
        raise _invalid("max_tuition", "max_tuition must be greater than or equal to min_tuition",
                       max_tuition)
    rules = _rules_for(country, state)
    rule = _current_rule(db, rules)
    stmt, pe = _base(rule.id if rule else None)
    stmt = stmt.where(_in_scope(rules, state, kind))
    if cip_family_:
        stmt = stmt.where(or_(*[_family_pred(rules, f) for f in cip_family_]))
    if stem:
        stmt = stmt.where(_stem_pred(pe, stem))
    if q and q.strip():
        like = _like_pattern(q.strip())
        stmt = stmt.where(or_(*[col.ilike(like, escape="\\") for col in (
            Institution.name, Campus.city, Classification.title, Program.name)]))
    if control:
        stmt = stmt.where(Institution.control.in_(control))
    if city:
        stmt = stmt.where(Campus.city.in_(city))
    if min_tuition is not None:
        stmt = stmt.where(_tuition_amount() >= min_tuition)
    if max_tuition is not None:
        stmt = stmt.where(_tuition_amount() <= max_tuition)
    if sevp:
        stmt = stmt.where(_sevp_pred(sevp))
    if accredited:
        stmt = stmt.where(_accredited_pred(accredited))
    if has_graduates:
        stmt = stmt.where(_graduates_pred(has_graduates))
    if exam:
        stmt = stmt.where(_course_value("exam").in_(exam))
    if cefr_entry_max:
        # Courses with an unknown entry level stay in the list, marked as unknown on the card:
        # an unknown level is not a level above the bound (BR-02).
        entry = _course_value("cefr_entry")
        stmt = stmt.where(or_(entry.in_(bands_up_to(cefr_entry_max)),
                              and_(Program.kind == "language_course", entry.is_(None))))
    if hours_min is not None:
        stmt = stmt.where(_hours() >= hours_min)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    key = _sort_expr(sort)
    primary = (key.desc() if order == "desc" else key.asc()).nulls_last()
    ties = [Program.id] if sort == "institution" else [Institution.name, Program.id]
    rows = db.execute(stmt.order_by(primary, *ties).limit(limit).offset(offset)).all()
    return {"total": total, "limit": limit, "offset": offset,
            "items": [_item(rules, *row) for row in rows]}


@router.get("/facets", response_model=s.Facets, tags=["programs"])
def facets(
    db: DB,
    country: COUNTRY = None,
    state: STATE = None,
    kind: Kind | None = None,
) -> dict[str, Any]:
    """Counts for the filter UI over every program of ``state`` (or of the whole country) and
    of ``kind`` when given; other filters are ignored. ``states`` always covers the whole
    country, so the state picker can offer every state that has programs."""
    rules = _rules_for(country, state)
    rule = _current_rule(db, rules)
    stmt, pe = _base(rule.id if rule else None)
    sub = stmt.where(_in_scope(rules, state, kind))
    count = func.count(Program.id)
    columns: dict[str, ColumnElement[Any]] = {"total": count}
    columns |= {f"cip_family:{f}": count.filter(_family_pred(rules, f))
                for f in rules.cip_families}
    columns |= {f"control:{c}": count.filter(Institution.control == c) for c in CONTROLS}
    columns |= {f"stem:{v}": count.filter(_stem_pred(pe, v))
                for v in ("eligible", "not_eligible", "unknown")}
    columns |= {f"sevp:{v}": count.filter(_sevp_pred(v)) for v in ("confirmed", "unknown")}
    columns |= {f"accredited:{v}": count.filter(_accredited_pred(v)) for v in ("true", "unknown")}
    columns |= {f"has_graduates:{v}": count.filter(_graduates_pred(v)) for v in ("true", "false")}
    amount = _tuition_amount()
    columns |= {"tuition:min": func.min(amount), "tuition:max": func.max(amount),
                "tuition:known": count.filter(amount.is_not(None))}
    columns |= {f"kind:{k}": count.filter(Program.kind == k) for k in KINDS}
    columns |= {f"exam:{e}": count.filter(_exam_pred(e)) for e in (*EXAMS, "unknown")}
    columns |= {f"cefr_entry:{b}": count.filter(_cefr_entry_pred(b))
                for b in (*BANDS, "unknown")}
    hours = _hours()
    courses = count.filter(Program.kind == "language_course")
    columns |= {"hours:min": func.min(hours), "hours:max": func.max(hours),
                "hours:known": count.filter(hours.is_not(None)), "hours:courses": courses}
    row = db.execute(sub.with_only_columns(*[c.label(f"c{n}") for n, c in
                                             enumerate(columns.values())])).one()
    got = dict(zip(columns, row, strict=True))
    out: dict[str, Any] = {"country": rules.code, "state": state.upper() if state else None,
                           "kind_scope": kind, "total": got["total"]}
    for group in ("cip_family", "control", "stem", "sevp", "accredited", "has_graduates",
                  "kind", "exam", "cefr_entry"):
        out[group] = {k.split(":", 1)[1]: v for k, v in got.items()
                      if k.startswith(f"{group}:")}
    # Cities only inside one state (across US states the same name is different places),
    # unless a city name is one place in the whole country (Ireland).
    cities = db.execute(sub.with_only_columns(Campus.city, count.label("n"))
                        .where(Campus.city.is_not(None))
                        .group_by(Campus.city).order_by(count.desc(), Campus.city)).all() \
        if state or rules.cities_unique else []
    out["cities"] = [{"city": c, "count": n} for c, n in cities]
    whole, _ = _base(rule.id if rule else None)
    states = db.execute(whole.where(_in_scope(rules, None, kind))
                        .join(Subdivision, Subdivision.id == Institution.subdivision_id)
                        .with_only_columns(Institution.subdivision_id, Subdivision.name,
                                           count.label("n"))
                        .group_by(Institution.subdivision_id, Subdivision.name)
                        .order_by(Subdivision.name)).all()
    out["states"] = [{"state": CountryRules.local_subdivision(sid), "name": name, "count": n}
                     for sid, name, n in states]
    lo, hi = got["tuition:min"], got["tuition:max"]
    out["tuition"] = {"min": _num(lo), "max": _num(hi), "known": got["tuition:known"],
                      "unknown": got["total"] - got["tuition:known"],
                      "currency": rules.currency}
    out["hours_per_week"] = {"min": _num(got["hours:min"]), "max": _num(got["hours:max"]),
                             "known": got["hours:known"],
                             "unknown": got["hours:courses"] - got["hours:known"]}
    return out


def _num(v: float | None) -> float | int | None:
    return None if v is None else int(v) if float(v).is_integer() else v


def _sources(db: Session, scopes: list[str], only: tuple[str, ...] | None,
             limit: int | None = None) -> list[dict]:
    """Latest succeeded file per source (with its row count), or every file when only=None."""
    stmt = (select(SourceFile, IngestionRun)
            .outerjoin(IngestionRun, and_(IngestionRun.source_file_id == SourceFile.id,
                                          IngestionRun.status == "succeeded"))
            .order_by(SourceFile.source, IngestionRun.finished_at.desc().nulls_last(),
                      SourceFile.uploaded_at.desc()))
    out: dict[tuple[str, str], dict] = {}
    for sf, run in db.execute(stmt):
        if only is not None and (run is None or sf.source not in only or run.scope not in scopes):
            continue
        key = (sf.source, "") if only is not None else (sf.source, sf.sha256)
        if key in out:
            continue
        rows = (run.counts or {}).get("rows") if run else None
        out[key] = {"source": sf.source, "file_version": sf.file_version, "sha256": sf.sha256,
                    "uploaded_at": sf.uploaded_at.isoformat().replace("+00:00", "Z"),
                    "rows": rows}
    if only is not None:
        order = {k: n for n, k in enumerate(only)}
        return sorted(out.values(), key=lambda d: order.get(d["source"], 99))
    return list(out.values())[:limit]


@router.get("/programs/{program_id}", response_model=s.ProgramDetail)
def get_program(program_id: Annotated[str, Path(pattern=PROGRAM_ID)],
                db: DB) -> dict[str, Any]:
    country = db.scalar(select(Institution.country_code)
                        .join(Campus, Campus.institution_id == Institution.id)
                        .join(Program, Program.campus_id == Campus.id)
                        .where(Program.id == program_id))
    if country is None or not is_country(country):
        raise HTTPException(status_code=404, detail="program not found")
    rules = rules_for(country)
    rule = _current_rule(db, rules)
    stmt, _ = _base(rule.id if rule else None)
    row = db.execute(stmt.where(Program.id == program_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")
    p, c, i, cls, pe = row
    item = _item(rules, p, c, i, cls, pe, evidence=True)
    isced = db.scalar(
        select(func.min(Classification.code))
        .join(ClassificationMap, ClassificationMap.to_id == Classification.id)
        .where(ClassificationMap.from_id == cls.id, Classification.scheme == "isced_f_2013")
    ) if cls else None
    program_ids = [{"scheme": sch, "value": val} for sch, val in db.execute(
        select(ProgramIdentifier.scheme, ProgramIdentifier.value)
        .where(ProgramIdentifier.program_id == p.id)
        .order_by(ProgramIdentifier.scheme, ProgramIdentifier.value)).all()]
    identifiers = dict(db.execute(select(InstitutionIdentifier.scheme, InstitutionIdentifier.value)
                                  .where(InstitutionIdentifier.institution_id == i.id)).all())
    loc = c.locality
    return {
        **item,
        "cip": {**item["cip"], "isced_f": isced} if item["cip"] else None,
        "identifiers": program_ids,
        "institution": {
            **item["institution"], "website": i.website, "identifiers": identifiers,
            "accreditation": i.accreditation or dict(UNKNOWN),
            "carnegie_classification": i.carnegie_classification or dict(UNKNOWN),
        },
        "campus": {
            **item["campus"],
            "locality": {"country": loc.country_code, "scheme": loc.scheme, "code": loc.code,
                         "name": loc.name} if loc else None,
            "sevp_campus_code": c.sevp_campus_code,
            "intl_authorization": c.intl_authorization or dict(UNKNOWN),
        },
        "not_yet_collected": NOT_YET_COLLECTED.get(p.kind, []),
        "sources": _sources(db, [s for s in (i.subdivision_id, rules.code) if s],
                            rules.program_sources),
    }


@router.get("/sources", response_model=list[s.SourceRef], tags=["sources"])
def list_sources(
    db: DB, limit: Annotated[int, Query(ge=1, le=MAX_SOURCES)] = 100,
) -> list[dict]:
    """Every uploaded file (latest first within each source), at most ``limit`` of them."""
    return _sources(db, [], None, limit)
