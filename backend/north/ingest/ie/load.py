"""ILEP and TrustEd Ireland lists -> English-course programs (record 0008, FR-30, FR-31, BR-18).

One step per uploaded file (source ``ie_ilep`` or ``ie_trusted``, scope ``IE``), idempotent on
the file hash (NFR-03). For each English-language row:

1. The program is found by its list reference (``program_identifiers``: ``ie_ilep_ref`` or
   ``ie_trusted_ref``). A new reference is linked to a program of the *other* list when the
   provider number and the normalized title match exactly and that program has no reference
   in this list yet (the ILEP -> TrustEd move, T6); otherwise a new program is created.
2. The provider is the institution ``ie-<provider number>`` (identifier ``ie_provider_no``);
   the campus is the provider's town (or no town when the address names several, or none).
3. Course facts (CEFR entry/exit, exam, weeks, hours/week) are ``confirmed_official`` from the
   uploaded file, raw text as evidence; unreadable text is ``unknown`` with the raw text.
4. ``programs.intl_authorization`` = {scheme ie_ilep | ie_trusted, authorized: true}. Once a
   programme has a TrustEd reference, the TrustEd authorization is kept.

Contacts (record 0009): the contact name, email and phone of each loaded row are stored only
in ``institution_contacts``, one row per distinct contact of an institution, and only for the
latest file of each source (this run replaces the source's previous rows). They never reach a
program, a VerifiedValue, evidence, a field change, a task, the run counts or a log line.

A programme that disappears from its list keeps its values and gets a reconciliation task
(``ie_list_move`` for ILEP, ``ie_list_missing`` for TrustEd) unless it already moved; nothing
is ever set to ``confirmed_negative`` here (BR-18, C1). Higher-education, foundation and
professional rows are counted and skipped (slice E3).
"""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from north.domain.countries.ie.places import COUNTIES
from north.domain.countries.ie.rules import SCHEME_ILEP, SCHEME_TRUSTED
from north.domain.verified import Status, verified
from north.ingest.common import RunContext, StepResult, run_step
from north.ingest.contacts import Person, replace_contacts
from north.ingest.ie.lists import Contact, ListRow, file_version, read_list
from north.ingest.ie.parse import (
    ExamMap,
    Place,
    norm_title,
    parse_cefr,
    parse_hours,
    parse_ref,
    parse_weeks,
    place_of,
    scrub,
)
from north.repository.models import (
    Campus,
    Country,
    Institution,
    InstitutionIdentifier,
    Locality,
    Program,
    ProgramIdentifier,
    ReconciliationTask,
    Subdivision,
)

COUNTRY = "IE"
SCOPE = "IE"
KIND = "language_course"
PROVIDER_SCHEME = "ie_provider_no"
LOCALITY_SCHEME = "ie_county"
HERE = Path(__file__).resolve()


@dataclass(frozen=True)
class ListSpec:
    source: str
    label: str
    ref_scheme: str
    auth_scheme: str
    id_prefix: str
    page: str  # the official page that links the file (K10)
    trusted: bool
    left_task: str


ILEP = ListSpec(
    source="ie_ilep", label="ILEP", ref_scheme="ie_ilep_ref", auth_scheme=SCHEME_ILEP,
    id_prefix="ie-ilep", trusted=False, left_task="ie_list_move",
    page="https://www.irishimmigration.ie/coming-to-study-in-ireland/what-are-my-study-options/"
         "a-third-level-course-or-a-language-course/")
TRUSTED = ListSpec(
    source="ie_trusted", label="TrustEd Ireland", ref_scheme="ie_trusted_ref",
    auth_scheme=SCHEME_TRUSTED, id_prefix="ie-trusted", trusted=True,
    left_task="ie_list_missing",
    page="https://www.trustedireland.ie/check-eligible-courses-for-study-visas")
LISTS = {s.source: s for s in (ILEP, TRUSTED)}
REF_SCHEMES = (ILEP.ref_scheme, TRUSTED.ref_scheme)


def reference_dir() -> Path:
    """data/reference: NORTH_REFERENCE_DIR, the source tree, or the image (/app/data)."""
    env = os.environ.get("NORTH_REFERENCE_DIR")
    if env:
        return Path(env)
    for candidate in (HERE.parents[4] / "data" / "reference",
                      HERE.parents[3] / "data" / "reference"):
        if candidate.is_dir():
            return candidate
    return HERE.parents[4] / "data" / "reference"


def default_exam_csv() -> Path:
    return reference_dir() / "ie_exam_names.csv"


# --------------------------------------------------------------------------- places


def ensure_country(session: Session) -> None:
    if session.get(Country, COUNTRY) is None:
        session.add(Country(code=COUNTRY, name="Ireland", currency="EUR", rules_module="ie"))
        session.flush()


def _subdivision(session: Session, county: str | None) -> str | None:
    if county is None:
        return None
    sid = f"{COUNTRY}-{county}"
    if session.get(Subdivision, sid) is None:
        session.add(Subdivision(id=sid, country_code=COUNTRY, name=COUNTIES[county],
                                coverage_status="in_progress"))
        session.flush()
    return sid


def _locality(session: Session, county: str | None) -> Locality | None:
    if county is None:
        return None
    code = f"{COUNTRY}-{county}"
    loc = session.scalar(select(Locality).where(
        Locality.country_code == COUNTRY, Locality.scheme == LOCALITY_SCHEME,
        Locality.code == code))
    if loc is None:
        loc = Locality(country_code=COUNTRY, scheme=LOCALITY_SCHEME, code=code,
                       name=COUNTIES[county])
        session.add(loc)
        session.flush()
    return loc


# --------------------------------------------------------------------------- values


def _evidence(spec: ListSpec, version: str, row: ListRow, column: str, raw: str) -> str:
    return scrub(f'{spec.label} {version}, {row.ref}: {column} "{raw}"')


def course_values(ctx: RunContext, spec: ListSpec, version: str, row: ListRow,
                  exams: ExamMap) -> dict[str, dict[str, Any]]:
    """The five list facts of a course as VerifiedValues (unknown keeps the raw text)."""
    def vv(value: Any, column: str, raw: str) -> dict[str, Any]:
        evidence = _evidence(spec, version, row, column, raw)
        if value is None:
            return verified(None, Status.UNKNOWN, evidence=evidence if raw else None)
        return ctx.vv(value, evidence=evidence)

    entry, _ = parse_cefr(row.entry)
    _, exit_ = parse_cefr(row.exit)
    exam = exams.code(row.awarding_body) if row.awarding_body else None
    if row.awarding_body and exam is None:
        ctx.counts["exam_unmapped"] += 1
        if row.awarding_body not in ctx.errors:
            ctx.errors.append(f"awarding body not in ie_exam_names.csv: {row.awarding_body}")
    exam_raw = row.awarding_body + (f" / award: {row.award_title}" if row.award_title else "")
    return {
        "cefr_entry": vv(entry, "Entry Level", row.entry),
        "cefr_exit": vv(exit_, "Exit Level", row.exit),
        "exam": vv(exam, "Awarding Body", exam_raw if row.awarding_body else ""),
        "weeks": vv(parse_weeks(row.duration), "Duration", row.duration),
        "hours_per_week": vv(parse_hours(row.hours), "Hours per week", row.hours),
    }


# --------------------------------------------------------------------------- the step


@dataclass
class _Known:
    """A language-course program already in the database, for matching."""

    id: str
    provider_no: str
    title_key: str
    refs: dict[str, str]  # scheme -> value


def _known_programs(session: Session) -> dict[str, _Known]:
    rows = session.execute(
        select(Program.id, Program.name, Institution.id, ProgramIdentifier.scheme,
               ProgramIdentifier.value)
        .join(Campus, Campus.id == Program.campus_id)
        .join(Institution, Institution.id == Campus.institution_id)
        .outerjoin(ProgramIdentifier, ProgramIdentifier.program_id == Program.id)
        .where(Institution.country_code == COUNTRY, Program.kind == KIND)).all()
    out: dict[str, _Known] = {}
    for pid, name, inst_id, scheme, value in rows:
        k = out.setdefault(pid, _Known(pid, inst_id.removeprefix("ie-"), norm_title(name), {}))
        if scheme in REF_SCHEMES:
            k.refs[scheme] = value
    return out


def _open_task_for(session: Session, kind: str, program_id: str) -> bool:
    return session.scalar(select(ReconciliationTask.id).where(
        ReconciliationTask.kind == kind, ReconciliationTask.resolved.is_(False),
        ReconciliationTask.candidates.contains([{"program_id": program_id}])).limit(1)) is not None


def _row_subject(row: ListRow) -> dict[str, Any]:
    """Non-personal fields of a row, for reconciliation tasks."""
    return {"ref": row.ref, "provider": row.provider, "title": row.title, "line": row.line}


def ingest_list(session: Session, path: Path, source: str,
                exam_csv: Path | None = None) -> StepResult:
    """Load one ILEP (``source='ie_ilep'``) or TrustEd (``'ie_trusted'``) XLSX file."""
    spec = LISTS[source]
    exams = ExamMap.load(exam_csv or default_exam_csv())
    listed = read_list(path)
    version = file_version(path.name, listed.title)

    def work(ctx: RunContext) -> None:
        ensure_country(session)
        rows = listed.rows
        ctx.counts["rows"] = len(rows)
        english: list[tuple[ListRow, Any]] = []
        file_refs: set[str] = set()
        for row in rows:
            ref = parse_ref(row.ref)
            if ref is not None:
                file_refs.add(ref.value)
            if row.kind != "english":
                ctx.counts[f"skipped_{row.kind}"] += 1
                continue
            ctx.counts["english_rows"] += 1
            if ref is None or ref.trusted != spec.trusted:
                ctx.counts["bad_ref"] += 1
                ctx.task("ie_bad_ref", f"{spec.label} {version} line {row.line}: reference "
                         f"{row.ref!r} is not in the list's format; row not loaded",
                         [_row_subject(row)])
                continue
            english.append((row, ref))

        known = _known_programs(session)
        by_ref = {(s, v): k.id for k in known.values() for s, v in k.refs.items()}

        # A reference used twice in the file: the row whose title matches the program that
        # already holds the reference keeps it, else the first row; the others need a person.
        groups: dict[str, list[tuple[ListRow, Any]]] = defaultdict(list)
        for row, ref in english:
            groups[ref.value].append((row, ref))
        kept: list[tuple[ListRow, Any]] = []
        for value, group in groups.items():
            keeper = group[0]
            holder = known.get(by_ref.get((spec.ref_scheme, value), ""))
            if holder is not None:
                keeper = next((g for g in group if norm_title(g[0].title) == holder.title_key),
                              keeper)
            kept.append(keeper)
            for other in group:
                if other is keeper:
                    continue
                ctx.counts["duplicate_ref_rows"] += 1
                ctx.task("ie_duplicate_ref",
                         f"{spec.label} {version}: reference {value} is used by more than one "
                         f"row; '{other[0].title}' was not loaded",
                         [_row_subject(other[0]), _row_subject(keeper[0])])

        # Providers: one institution per provider number; county only when every row agrees.
        places = {row.line: place_of(row.address) for row, _ in kept}
        by_provider: dict[str, list[ListRow]] = defaultdict(list)
        for row, ref in kept:
            by_provider[ref.provider_no].append(row)
        institutions: dict[str, Institution] = {}
        for no, prow in sorted(by_provider.items()):
            counties = {places[r.line].county for r in prow}
            county = counties.pop() if len(counties) == 1 else None
            institutions[no] = _institution(ctx, no, prow, county)

        campuses: dict[tuple[str, str | None, str | None], Campus] = {}
        for row, ref in sorted(kept, key=lambda t: t[1].value):
            place = places[row.line]
            if place.city is None:
                ctx.counts["city_unknown"] += 1
            key = (ref.provider_no, place.city, place.county)
            if key not in campuses:
                campuses[key] = _campus(ctx, institutions[ref.provider_no], place)
            _program(ctx, spec, version, row, ref, campuses[key], known, by_ref, exams)

        _replace_contacts(ctx, spec, [(ref.provider_no, listed.contacts.get(row.line))
                                      for row, ref in kept])

        # Programmes of this list that are not in the file any more.
        for k in sorted(known.values(), key=lambda k: k.id):
            value = k.refs.get(spec.ref_scheme)
            if value is None or value in file_refs:
                continue
            if not spec.trusted and TRUSTED.ref_scheme in k.refs:
                ctx.counts["moved_to_trusted"] += 1
                continue
            ctx.counts["left_list"] += 1
            if _open_task_for(session, spec.left_task, k.id):
                continue
            others = [{"program_id": o.id, "refs": o.refs} for o in known.values()
                      if o.provider_no == k.provider_no and o.id != k.id
                      and spec.ref_scheme not in o.refs][:10]
            ctx.task(spec.left_task,
                     f"{k.id}: reference {value} is not in the {spec.label} list of {version};"
                     " values kept (never 'not eligible' automatically)",
                     [{"program_id": k.id, "ref": value}, *others])
        session.flush()

    return run_step(session, source=spec.source, files=[path], file_version=version,
                    source_url=spec.page, scope=SCOPE, work=work)


def _replace_contacts(ctx: RunContext, spec: ListSpec,
                      pairs: list[tuple[str, Contact | None]]) -> None:
    """Keep only this file's contacts for this source (record 0009: data minimization)."""
    replace_contacts(ctx.session, source=spec.source, source_file_id=ctx.source_file.id,
                     institution_ids=None,
                     people=[Person(f"ie-{no}", name=c.name, email=c.email, phone=c.phone)
                             for no, c in pairs if c])


def _institution(ctx: RunContext, no: str, rows: list[ListRow],
                 county: str | None) -> Institution:
    session = ctx.session
    iid = f"ie-{no}"
    inst = session.get(Institution, iid)
    name = Counter(r.provider for r in rows).most_common(1)[0][0]
    sid = _subdivision(session, county)
    if inst is None:
        inst = Institution(id=iid, country_code=COUNTRY, subdivision_id=sid, name=name,
                           accreditation=None, carnegie_classification=None)
        session.add(inst)
        ctx.log_change(f"institution[{iid}].name", None, name)
        ctx.counts["institutions_created"] += 1
    elif inst.subdivision_id is None and sid is not None:
        ctx.set_attr(inst, "subdivision_id", sid, f"institution[{iid}].subdivision_id")
    if session.scalar(select(InstitutionIdentifier.id).where(
            InstitutionIdentifier.scheme == PROVIDER_SCHEME,
            InstitutionIdentifier.value == no)) is None:
        session.add(InstitutionIdentifier(institution_id=iid, scheme=PROVIDER_SCHEME, value=no))
    session.flush()
    return inst


def _campus(ctx: RunContext, inst: Institution, place: Place) -> Campus:
    session = ctx.session
    loc = _locality(session, place.county)
    stmt = select(Campus).where(Campus.institution_id == inst.id)
    stmt = stmt.where(Campus.city == place.city if place.city else Campus.city.is_(None))
    stmt = stmt.where(Campus.locality_id == loc.id if loc else Campus.locality_id.is_(None))
    campus = session.scalars(stmt.order_by(Campus.id).limit(1)).first()
    if campus is None:
        campus = Campus(institution_id=inst.id, name=inst.name, city=place.city,
                        locality_id=loc.id if loc else None)
        session.add(campus)
        session.flush()
        ctx.log_change(f"campus[{campus.id}].city", None, place.city)
    return campus


def _program(ctx: RunContext, spec: ListSpec, version: str, row: ListRow, ref: Any,
             campus: Campus, known: dict[str, _Known], by_ref: dict[tuple[str, str], str],
             exams: ExamMap) -> None:
    session = ctx.session
    other = TRUSTED if spec is ILEP else ILEP
    pid = by_ref.get((spec.ref_scheme, ref.value))
    if pid is None:
        title_key = norm_title(row.title)
        matches = [k for k in known.values()
                   if k.provider_no == ref.provider_no and k.title_key == title_key
                   and other.ref_scheme in k.refs and spec.ref_scheme not in k.refs]
        if len(matches) == 1:
            pid = matches[0].id
            ctx.counts[f"linked_to_{other.source}"] += 1
        elif len(matches) > 1:
            ctx.task("ie_list_move",
                     f"{spec.label} {ref.value}: several {other.label} programmes of provider "
                     f"{ref.provider_no} have the same title; loaded as a new programme",
                     [_row_subject(row), *[{"program_id": m.id, "refs": m.refs}
                                           for m in matches]])
    prog = session.get(Program, pid) if pid else None
    values = course_values(ctx, spec, version, row, exams)
    if prog is None:
        pid = _new_id(session, spec, ref)
        prog = Program(id=pid, campus_id=campus.id, name=row.title, degree=KIND, kind=KIND,
                       flags=[], language_course={"price": verified(None, Status.UNKNOWN),
                                                  "start_dates": []})
        session.add(prog)
        session.flush()
        ctx.log_change("name", None, row.title, program_id=pid)
        ctx.counts["programs_created"] += 1
        known[pid] = _Known(pid, ref.provider_no, norm_title(row.title), {})
    else:
        ctx.set_attr(prog, "name", row.title, "name", program_id=pid)
        ctx.set_attr(prog, "campus_id", campus.id, "campus_id", program_id=pid)
        ctx.counts["programs_updated"] += 1
    if (spec.ref_scheme, ref.value) not in by_ref:
        session.add(ProgramIdentifier(program_id=pid, scheme=spec.ref_scheme, value=ref.value))
        ctx.log_change(f"identifier.{spec.ref_scheme}", None, ref.value, program_id=pid)
        by_ref[(spec.ref_scheme, ref.value)] = pid
        known[pid].refs[spec.ref_scheme] = ref.value
    for key, new in values.items():
        if new["status"] == Status.UNKNOWN:
            ctx.counts[f"{key}_unknown"] += 1
        ctx.put(prog, "language_course", new, f"language_course.{key}", key=(key,),
                program_id=pid)
    current = (prog.intl_authorization or {}).get("value") or {}
    if not spec.trusted and current.get("scheme") == SCHEME_TRUSTED:
        ctx.counts["kept_trusted_authorization"] += 1  # moved: TrustEd is the successor
        return
    auth = ctx.vv({"scheme": spec.auth_scheme, "authorized": True},
                  evidence=f"{spec.label} {version}: programme {ref.value}")
    ctx.put(prog, "intl_authorization", auth, "intl_authorization", program_id=pid)


def _new_id(session: Session, spec: ListSpec, ref: Any) -> str:
    base = f"{spec.id_prefix}-{ref.provider_no}-{ref.programme_no}"
    pid, n = base, 1
    while session.get(Program, pid) is not None:
        n += 1
        pid = f"{base}-{n}"
    return pid
