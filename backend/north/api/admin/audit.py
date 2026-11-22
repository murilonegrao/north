"""Audit log, newest first (admin only)."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from north.api.admin.deps import Admin
from north.repository.models import AuditEntry

router = APIRouter()


@router.get("/audit")
def audit_log(auth: Admin, limit: int = Query(100, ge=1, le=500),
              before: int | None = None) -> object:
    stmt = select(AuditEntry).order_by(AuditEntry.id.desc()).limit(limit)
    if before:
        stmt = stmt.where(AuditEntry.id < before)
    return [{"id": e.id, "at": e.at, "actor": e.actor, "action": e.action, "target": e.target,
             "detail": e.detail, "ip": e.ip} for e in auth.db.scalars(stmt)]
