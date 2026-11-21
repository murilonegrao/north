"""Programs API, contract v0.2 (docs/api/programs-v0.md).

Filters, facets and sort keys are SQLAlchemy expressions over the JSONB VerifiedValues; JSON
paths and user values are bound parameters, never formatted into SQL. Facets reuse the very
predicates of the filters, so a count always equals the length of the filtered list.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from pydantic import StringConstraints
from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.elements import ColumnElement

from north.api import schemas as s
from north.domain.countries.us.cip import FAMILIES, cip_family
from north.domain.countries.us.stem import RULE_KEY
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
    SourceFile,
)

router = APIRouter(prefix="/api", tags=["programs"])
DB = Annotated[Session, Depends(session_scope)]

NOT_YET_COLLECTED = [
    "admissions.english", "admissions.deadlines", "admissions.other_field_accepted",
    "funding", "cost.program_tuition", "immigration.i20_issued_for_program",
]
# Source files behind a program's values (contract v0.1 §5 ids).
PROGRAM_SOURCES = ("ipeds_hd", "ipeds_c_a", "ipeds_ic_ay", "dhs_stem_list", "sevp_csl", "dapip")
UNKNOWN: dict[str, Any] = {"value": None, "status": "unknown"}
NOTE_TUITION = "institution_wide_average"


def _current_rule(db: Session, country: str = "US") -> EligibilityRule | None:
    return db.scalar(
        select(EligibilityRule)
        .where(EligibilityRule.country_code == country, EligibilityRule.key == RULE_KEY)
        .order_by(EligibilityRule.published_on.desc().nulls_last(),
                  EligibilityRule.version.desc()).limit(1))


def _base(rule_id: int | None) -> tuple[Select[Any], Any]:
    pe = aliased(ProgramEligibility)
    join_pe = and_(pe.program_id == Program.id, pe.rule_id == (rule_id or -1))
    return (
        select(Program, Campus, Institution, Classification, pe)
        .join(Campus, Campus.id == Program.campus_id)
        .join(Institution, Institution.id == Campus.institution_id)
        .join(ProgramClassification, and_(ProgramClassification.program_id == Program.id,
                                          ProgramClassification.is_primary.is_(True)))
        .join(Classification, Classification.id == ProgramClassification.classification_id)
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


def _state(inst: Institution) -> str:
    return inst.subdivision_id.split("-", 1)[-1]


def _list_tuition(p: Program) -> dict[str, Any]:
    """The detail's tuition VerifiedValue without ``evidence`` (v0.2 §1)."""
    t = p.cost.get("graduate_tuition_nonresident") or {**UNKNOWN, "note_code": NOTE_TUITION}
    return {k: v for k, v in t.items() if k != "evidence"}


def _item(p: Program, c: Campus, i: Institution, cls: Classification,
          pe: ProgramEligibility | None) -> dict[str, Any]:
    return {
        "id": p.id, "title": p.name, "title_source": _title_source(p), "degree": p.degree,
        "cip": {"code": cls.code, "title": cls.title, "family": cip_family(cls.code)},
        "institution": {"id": i.id, "name": i.name, "control": i.control},
        "campus": {"city": c.city, "state": _state(i)},
        "stem_opt": _stem(pe),
        "flags": list(p.flags or []),
        "completions": p.academic.get("completions") or dict(UNKNOWN),
        "graduate_tuition_nonresident": _list_tuition(p),
        "sevp_status": _status(c.intl_authorization),
        "accreditation_status": _status(i.accreditation),
    }


# --------------------------------------------------------------------------- predicates

Control = Literal["public", "private_nonprofit", "private_for_profit"]
CONTROLS: tuple[str, ...] = ("public", "private_nonprofit", "private_for_profit")
SortKey = Literal["title", "institution", "city", "tuition", "graduates",
                  "nonresident_graduates", "nonresident_share"]
City = Annotated[str, StringConstraints(min_length=1, max_length=120)]
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


def _family_pred(family: str) -> ColumnElement[bool]:
    return Classification.code.startswith(FAMILIES[family])


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


@router.get("/programs", response_model=s.ProgramList)
def list_programs(
    db: DB,
    state: Annotated[str, Query(pattern=r"^[A-Za-z]{2}$")] = "TX",
    cip_family_: Annotated[list[Literal["11", "30.70", "30.71", "52.12"]] | None,
                           Query(alias="cip_family")] = None,
    stem: Literal["eligible", "not_eligible", "unknown"] | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    control: Annotated[list[Control] | None, Query()] = None,
    city: Annotated[list[City] | None, Query(max_length=50)] = None,
    min_tuition: Annotated[float | None, Query(ge=0, le=MAX_TUITION)] = None,
    max_tuition: Annotated[float | None, Query(ge=0, le=MAX_TUITION)] = None,
    sevp: Literal["confirmed", "unknown"] | None = None,
    accredited: Literal["true", "unknown"] | None = None,
    has_graduates: Literal["true", "false"] | None = None,
    sort: SortKey = "title",
    order: Literal["asc", "desc"] = "asc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    if min_tuition is not None and max_tuition is not None and max_tuition < min_tuition:
        raise _invalid("max_tuition", "max_tuition must be greater than or equal to min_tuition",
                       max_tuition)
    rule = _current_rule(db)
    stmt, pe = _base(rule.id if rule else None)
    stmt = stmt.where(Institution.subdivision_id == f"US-{state.upper()}")
    if cip_family_:
        stmt = stmt.where(or_(*[_family_pred(f) for f in cip_family_]))
    if stem:
        stmt = stmt.where(_stem_pred(pe, stem))
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Institution.name.ilike(like), Campus.city.ilike(like),
                              Classification.title.ilike(like), Program.name.ilike(like)))
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
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    key = _sort_expr(sort)
    primary = (key.desc() if order == "desc" else key.asc()).nulls_last()
    ties = [Program.id] if sort == "institution" else [Institution.name, Program.id]
    rows = db.execute(stmt.order_by(primary, *ties).limit(limit).offset(offset)).all()
    return {"total": total, "limit": limit, "offset": offset,
            "items": [_item(*row) for row in rows]}


@router.get("/facets", response_model=s.Facets, tags=["programs"])
def facets(
    db: DB,
    state: Annotated[str, Query(pattern=r"^[A-Za-z]{2}$")] = "TX",
) -> dict[str, Any]:
    """Counts for the filter UI over every program of ``state`` (other filters ignored)."""
    rule = _current_rule(db)
    stmt, pe = _base(rule.id if rule else None)
    sub = stmt.where(Institution.subdivision_id == f"US-{state.upper()}")
    count = func.count(Program.id)
    columns: dict[str, ColumnElement[Any]] = {"total": count}
    columns |= {f"cip_family:{f}": count.filter(_family_pred(f)) for f in FAMILIES}
    columns |= {f"control:{c}": count.filter(Institution.control == c) for c in CONTROLS}
    columns |= {f"stem:{v}": count.filter(_stem_pred(pe, v))
                for v in ("eligible", "not_eligible", "unknown")}
    columns |= {f"sevp:{v}": count.filter(_sevp_pred(v)) for v in ("confirmed", "unknown")}
    columns |= {f"accredited:{v}": count.filter(_accredited_pred(v)) for v in ("true", "unknown")}
    columns |= {f"has_graduates:{v}": count.filter(_graduates_pred(v)) for v in ("true", "false")}
    amount = _tuition_amount()
    columns |= {"tuition:min": func.min(amount), "tuition:max": func.max(amount),
                "tuition:known": count.filter(amount.is_not(None))}
    row = db.execute(sub.with_only_columns(*[c.label(f"c{n}") for n, c in
                                             enumerate(columns.values())])).one()
    got = dict(zip(columns, row, strict=True))
    out: dict[str, Any] = {"state": state.upper(), "total": got["total"]}
    for group in ("cip_family", "control", "stem", "sevp", "accredited", "has_graduates"):
        out[group] = {k.split(":", 1)[1]: v for k, v in got.items()
                      if k.startswith(f"{group}:")}
    cities = db.execute(sub.with_only_columns(Campus.city, count.label("n"))
                        .where(Campus.city.is_not(None))
                        .group_by(Campus.city).order_by(count.desc(), Campus.city)).all()
    out["cities"] = [{"city": c, "count": n} for c, n in cities]
    lo, hi = got["tuition:min"], got["tuition:max"]
    out["tuition"] = {"min": _num(lo), "max": _num(hi), "known": got["tuition:known"],
                      "unknown": got["total"] - got["tuition:known"], "currency": "USD"}
    return out


def _num(v: float | None) -> float | int | None:
    return None if v is None else int(v) if float(v).is_integer() else v


def _sources(db: Session, scopes: list[str], only: tuple[str, ...] | None) -> list[dict]:
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
    return list(out.values())


@router.get("/programs/{program_id}", response_model=s.ProgramDetail)
def get_program(program_id: str, db: DB) -> dict[str, Any]:
    rule = _current_rule(db)
    stmt, _ = _base(rule.id if rule else None)
    row = db.execute(stmt.where(Program.id == program_id)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="program not found")
    p, c, i, cls, pe = row
    item = _item(p, c, i, cls, pe)
    isced = db.scalar(
        select(func.min(Classification.code))
        .join(ClassificationMap, ClassificationMap.to_id == Classification.id)
        .where(ClassificationMap.from_id == cls.id, Classification.scheme == "isced_f_2013"))
    identifiers = dict(db.execute(select(InstitutionIdentifier.scheme, InstitutionIdentifier.value)
                                  .where(InstitutionIdentifier.institution_id == i.id)).all())
    loc = c.locality
    tuition = p.cost.get("graduate_tuition_nonresident") or {**UNKNOWN, "note_code": NOTE_TUITION}
    return {
        **item,
        "cip": {**item["cip"], "isced_f": isced},
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
        "graduate_tuition_nonresident": tuition,
        "not_yet_collected": NOT_YET_COLLECTED,
        "sources": _sources(db, [i.subdivision_id, "US"], PROGRAM_SOURCES),
    }


@router.get("/sources", response_model=list[s.SourceRef], tags=["sources"])
def list_sources(db: DB) -> list[dict]:
    return _sources(db, [], None)
