"""Providers and their private contacts (record 0009), admin only.

The list shows each institution of a country with how many contacts are stored, never the
contacts themselves. Reading one institution's contacts is a separate request, written to the
audit log (who, which institution, when; never the values). Nothing here is public.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from sqlalchemy import func, select

from north.api.admin.deps import Admin
from north.auth import audit
from north.repository.models import (
    Campus,
    Institution,
    InstitutionContact,
    InstitutionIdentifier,
    Program,
    SourceFile,
)

router = APIRouter(prefix="/institutions")
INSTITUTION_ID = r"^[a-z0-9][a-z0-9-]{0,39}$"


@router.get("")
def list_institutions(auth: Admin,
                      country: Annotated[str, Query(pattern=r"^[A-Za-z]{2}$")] = "IE") -> object:
    programs = (select(Campus.institution_id, func.count(Program.id).label("n"))
                .join(Program, Program.campus_id == Campus.id)
                .group_by(Campus.institution_id).subquery())
    contacts = (select(InstitutionContact.institution_id, func.count().label("n"))
                .group_by(InstitutionContact.institution_id).subquery())
    rows = auth.db.execute(
        select(Institution.id, Institution.name, Institution.subdivision_id,
               func.coalesce(programs.c.n, 0), func.coalesce(contacts.c.n, 0))
        .outerjoin(programs, programs.c.institution_id == Institution.id)
        .outerjoin(contacts, contacts.c.institution_id == Institution.id)
        .where(Institution.country_code == country.upper())
        .order_by(Institution.name, Institution.id)).all()
    ids: dict[str, dict[str, str]] = {}
    for iid, scheme, value in auth.db.execute(
            select(InstitutionIdentifier.institution_id, InstitutionIdentifier.scheme,
                   InstitutionIdentifier.value)
            .join(Institution, Institution.id == InstitutionIdentifier.institution_id)
            .where(Institution.country_code == country.upper())):
        ids.setdefault(iid, {})[scheme] = value
    return [{"id": iid, "name": name, "subdivision": sub, "programs": n_prog,
             "contacts": n_contacts, "identifiers": ids.get(iid, {})}
            for iid, name, sub, n_prog, n_contacts in rows]


@router.get("/{institution_id}/contacts")
def institution_contacts(auth: Admin,
                         institution_id: Annotated[str, Path(pattern=INSTITUTION_ID)]) -> object:
    inst = auth.db.get(Institution, institution_id)
    if inst is None:
        raise HTTPException(404, "no such institution")
    rows = auth.db.execute(
        select(InstitutionContact, SourceFile.source, SourceFile.file_version)
        .join(SourceFile, SourceFile.id == InstitutionContact.source_file_id)
        .where(InstitutionContact.institution_id == institution_id)
        .order_by(SourceFile.source, InstitutionContact.id)).all()
    audit.record(auth.db, "institution_contacts_read", actor=auth.user, target=institution_id,
                 ip=auth.ip, count=len(rows))
    auth.db.commit()
    return {"institution": {"id": inst.id, "name": inst.name},
            "contacts": [{"name": c.name, "title": c.title, "email": c.email, "phone": c.phone,
                          "source": source, "file_version": version,
                          "seen_at": c.seen_at.isoformat()}
                         for c, source, version in rows]}
