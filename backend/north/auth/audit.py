"""Append-only audit log (the table refuses UPDATE and DELETE)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from north.repository.models import AuditEntry, User


def record(session: Session, action: str, *, actor: User | str, target: str | None = None,
           ip: str | None = None, **detail: Any) -> None:
    """Add an entry to the caller's transaction (it commits with the change it describes)."""
    if isinstance(actor, User):
        session.add(AuditEntry(actor_id=actor.id, actor=actor.username, action=action,
                               target=target, detail=detail, ip=ip))
    else:
        session.add(AuditEntry(actor=actor, action=action, target=target, detail=detail, ip=ip))
