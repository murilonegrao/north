"""What the admin home shows: counts, files in use, worker health, recent jobs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select, text

from north.api.admin.deps import Viewer
from north.api.admin.jobs import recent_jobs, schedule_view
from north.jobs import registry
from north.repository.models import EmailOutbox, IngestionRun, Job, Schedule, SourceFile

router = APIRouter()

WORKER_APP = "north-worker"  # application_name set by north.jobs.worker


def worker_status(db: Any) -> dict[str, Any]:
    """Connections the worker holds (it names them with application_name), and the last
    heartbeat of a running job. Idle workers hold a connection only while polling."""
    connected = db.scalar(text("select count(*) from pg_stat_activity "
                               "where application_name = :name"), {"name": WORKER_APP}) or 0
    last_beat = db.scalar(select(func.max(Job.heartbeat_at)))
    last_claim = db.scalar(select(func.max(Job.started_at)))
    return {"connected": connected > 0, "last_heartbeat_at": last_beat,
            "last_job_started_at": last_claim}


def mail_status(db: Any) -> dict[str, Any]:
    """The outbox seen from the web process (only the worker knows the SMTP settings): what
    waits, what failed lately, the last error."""
    def count(*where: Any) -> int:
        return db.scalar(select(func.count()).select_from(EmailOutbox).where(*where)) or 0

    day = func.now() - text("interval '1 day'")
    last_problem = db.scalars(select(EmailOutbox).where(EmailOutbox.last_error.is_not(None))
                              .order_by(EmailOutbox.id.desc()).limit(1)).first()
    return {
        "queued": count(EmailOutbox.status == "queued"),
        "failed_24h": count(EmailOutbox.status.in_(("failed", "expired")),
                            EmailOutbox.created_at > day),
        "sent_24h": count(EmailOutbox.status == "sent", EmailOutbox.sent_at > day),
        "last_sent_at": db.scalar(select(func.max(EmailOutbox.sent_at))),
        "last_error": (None if last_problem is None or last_problem.status == "sent"
                       else last_problem.last_error),
    }


@router.get("/overview")
def overview(auth: Viewer) -> object:
    db = auth.db
    attention = db.scalar(select(func.count()).select_from(Job)
                          .where(Job.status.in_(("attention", "failed")))) or 0
    return {
        "countries": registry.overview(db),
        "worker": worker_status(db),
        "mail": mail_status(db),
        "jobs": recent_jobs(db, 8),
        "jobs_needing_attention": attention,
        "schedules": [schedule_view(r) for r in db.scalars(select(Schedule).order_by(Schedule.id))],
    }


@router.get("/source-files")
def source_files(auth: Viewer, limit: int = Query(100, ge=1, le=500)) -> object:
    db = auth.db
    files = db.scalars(select(SourceFile).order_by(SourceFile.id.desc()).limit(limit)).all()
    runs: dict[int, list[dict[str, Any]]] = {}
    if files:
        for r in db.scalars(select(IngestionRun)
                            .where(IngestionRun.source_file_id.in_([f.id for f in files]))
                            .order_by(IngestionRun.id)):
            runs.setdefault(r.source_file_id, []).append(
                {"scope": r.scope, "status": r.status, "finished_at": r.finished_at,
                 "errors": len(r.errors or [])})
    return [{"id": f.id, "source": f.source, "file_version": f.file_version,
             "sha256": f.sha256, "original_name": f.original_name, "size_bytes": f.size_bytes,
             "source_url": f.source_url, "uploaded_at": f.uploaded_at,
             "runs": runs.get(f.id, [])} for f in files]
