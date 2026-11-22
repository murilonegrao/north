"""Private institution contacts from official files (record 0009). Shared by every country.

A source's run replaces that source's ``institution_contacts`` rows for the institutions it
covers, so only the latest file's contacts are kept. Contacts never go to a VerifiedValue,
evidence, a field change, a task, the run counts or a log line; ``Person`` hides its values
from ``repr`` so a traceback or a log of the object leaks nothing.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import delete
from sqlalchemy.orm import Session

from north.repository.models import InstitutionContact


@dataclass(frozen=True)
class Person:
    institution_id: str
    name: str = field(default="", repr=False)
    title: str = field(default="", repr=False)
    email: str = field(default="", repr=False)
    phone: str = field(default="", repr=False)

    def __bool__(self) -> bool:  # a role title alone is not a contact
        return bool(self.name or self.email or self.phone)


def replace_contacts(session: Session, *, source: str, source_file_id: int,
                     people: Iterable[Person], institution_ids: Iterable[str] | None) -> None:
    """Delete ``source``'s rows for ``institution_ids`` (every institution when None), then
    store the distinct non-empty ``people``."""
    stmt = delete(InstitutionContact).where(InstitutionContact.source == source)
    if institution_ids is not None:
        stmt = stmt.where(InstitutionContact.institution_id.in_(list(institution_ids)))
    session.execute(stmt)
    seen: set[tuple[str, str, str, str, str]] = set()
    for p in people:
        key = (p.institution_id, p.name, p.title, p.email.lower(), p.phone)
        if not p or key in seen:
            continue
        seen.add(key)
        session.add(InstitutionContact(
            institution_id=p.institution_id, source=source, source_file_id=source_file_id,
            name=p.name or None, title=p.title or None, email=p.email or None,
            phone=p.phone or None))
    session.flush()
