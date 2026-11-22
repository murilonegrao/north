"""Postgres job queue: enqueue, claim (FOR UPDATE SKIP LOCKED), finish, cancel, reap.

No broker: jobs are rows, transactional with the data they change and covered by backups.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from north.auth import audit
from north.jobs import registry
from north.repository.models import Job, JobLog, Schedule, User

ACTIVE = ("queued", "running")
FINAL = ("succeeded", "attention", "failed", "cancelled")
MAX_LOG_LINES = 5000
MAX_LINE = 2000
STALE_AFTER = dt.timedelta(minutes=5)


class AlreadyActive(Exception):
    def __init__(self, job: Job) -> None:
        super().__init__(f"job {job.id} of this kind is already {job.status}")
        self.job = job


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def active_of_kind(db: Session, kind: str) -> Job | None:
    return db.scalar(select(Job).where(Job.kind == kind, Job.status.in_(ACTIVE))
                     .order_by(Job.id).limit(1))


def enqueue(db: Session, kind: str, params: dict[str, Any] | None, *,
            actor: User | str, schedule_id: str | None = None, ip: str | None = None,
            allow_parallel: bool = False) -> Job:
    """Validate and queue. One active job per kind unless allow_parallel (uploads)."""
    spec = registry.kinds().get(kind)
    if spec is None:
        raise ValueError(f"unknown job kind {kind!r}")
    clean = spec.validate(dict(params or {}))
    if not allow_parallel and (busy := active_of_kind(db, kind)) is not None:
        raise AlreadyActive(busy)
    job = Job(kind=kind, params=clean, schedule_id=schedule_id,
              requested_by=actor.id if isinstance(actor, User) else None)
    db.add(job)
    db.flush()
    audit.record(db, "job_enqueued", actor=actor, target=f"job:{job.id}", ip=ip, kind=kind,
                 params=clean)
    db.commit()
    return job


def claim(db: Session, worker: str) -> Job | None:
    job = db.scalar(select(Job).where(Job.status == "queued", Job.run_after <= now())
                    .order_by(Job.id).limit(1).with_for_update(skip_locked=True))
    if job is None:
        db.rollback()
        return None
    t = now()
    job.status, job.started_at, job.heartbeat_at, job.worker = "running", t, t, worker
    db.commit()
    return job


def append_log(db: Session, job_id: int, line: str) -> None:
    """One line, committed at once so the admin sees progress. Capped per job."""
    n = db.execute(update(Job).where(Job.id == job_id).values(log_lines=Job.log_lines + 1)
                   .returning(Job.log_lines)).scalar_one()
    if n <= MAX_LOG_LINES:
        db.add(JobLog(job_id=job_id, line=line[:MAX_LINE]))
    elif n == MAX_LOG_LINES + 1:
        db.add(JobLog(job_id=job_id, line=f"[log capped at {MAX_LOG_LINES} lines]"))
    db.commit()


def heartbeat(db: Session, job_id: int) -> bool:
    """Refresh the heartbeat; True when someone asked to cancel."""
    row = db.execute(update(Job).where(Job.id == job_id).values(heartbeat_at=now())
                     .returning(Job.cancel_requested)).scalar_one_or_none()
    db.commit()
    return bool(row)


def finish(db: Session, job_id: int, status: str, *, result: dict[str, Any] | None = None,
           error: str | None = None) -> None:
    assert status in FINAL
    job = db.get(Job, job_id)
    assert job is not None
    job.status, job.finished_at = status, now()
    job.result = result or {}
    job.error = error[:4000] if error else None
    db.commit()


def request_cancel(db: Session, job: Job, *, actor: User, ip: str | None = None) -> Job:
    if job.status == "queued":
        job.status, job.finished_at, job.error = "cancelled", now(), "cancelled before start"
    elif job.status == "running":
        job.cancel_requested = True
    else:
        return job
    audit.record(db, "job_cancel", actor=actor, target=f"job:{job.id}", ip=ip)
    db.commit()
    return job


def reap_stale(db: Session) -> int:
    """Running jobs whose worker stopped beating (a crash or a kill) become failed."""
    rows = db.execute(update(Job).where(Job.status == "running",
                                        Job.heartbeat_at < now() - STALE_AFTER)
                      .values(status="failed", finished_at=now(),
                              error="the worker stopped while running this job")
                      .returning(Job.id)).scalars().all()
    db.commit()
    return len(rows)


# ----------------------------------------------------------------------------- schedules


def sync_schedules(db: Session) -> None:
    """Create rows for schedules declared in code; code owns kind, params and interval,
    the row keeps paused and next_run_at. Rows no longer declared are deleted."""
    specs = {s.id: s for s in registry.schedules()}
    t = now()
    for row in db.scalars(select(Schedule)):
        if row.id not in specs:
            db.delete(row)
    for spec in specs.values():
        row = db.get(Schedule, spec.id)
        if row is None:
            db.add(Schedule(id=spec.id, kind=spec.kind, params=spec.params,
                            every_hours=spec.every_hours, next_run_at=spec.first_run(t)))
        else:
            row.kind, row.params, row.every_hours = spec.kind, spec.params, spec.every_hours
    db.commit()


def run_due_schedules(db: Session) -> list[int]:
    """Enqueue every due schedule once; a kind already active is skipped, not stacked."""
    t = now()
    due = db.scalars(select(Schedule).where(Schedule.paused.is_(False),
                                            Schedule.next_run_at <= t)
                     .with_for_update(skip_locked=True)).all()
    created = []
    for row in due:
        step = dt.timedelta(hours=row.every_hours)
        while row.next_run_at <= t:
            row.next_run_at += step
        if active_of_kind(db, row.kind) is None:
            job = Job(kind=row.kind, params=row.params, schedule_id=row.id)
            db.add(job)
            db.flush()
            row.last_job_id = job.id
            audit.record(db, "job_enqueued", actor="scheduler", target=f"job:{job.id}",
                         kind=row.kind, schedule=row.id)
            created.append(job.id)
    db.commit()
    return created
