"""Jobs (run, follow, cancel) and schedules (pause, resume, run now)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from north.api.admin.deps import Admin, Curator, Viewer
from north.auth import audit, service
from north.jobs import queue, registry
from north.repository.models import Job, JobLog, Schedule, User

router = APIRouter()


def job_view(job: Job, users: dict[int, str]) -> dict[str, Any]:
    kind = registry.kinds().get(job.kind)
    return {"id": job.id, "kind": job.kind, "title": kind.title if kind else job.kind,
            "params": job.params, "status": job.status, "error": job.error,
            "requested_by": users.get(job.requested_by) if job.requested_by else None,
            "schedule_id": job.schedule_id, "created_at": job.created_at,
            "started_at": job.started_at, "finished_at": job.finished_at,
            "heartbeat_at": job.heartbeat_at, "cancel_requested": job.cancel_requested,
            "log_lines": job.log_lines}


def usernames(db: Any, ids: set[int | None]) -> dict[int, str]:
    ids.discard(None)
    if not ids:
        return {}
    return dict(db.execute(select(User.id, User.username).where(User.id.in_(ids))).all())


def recent_jobs(db: Any, limit: int, status: str | None = None,
                before: int | None = None) -> list[dict[str, Any]]:
    stmt = select(Job).order_by(Job.id.desc()).limit(limit)
    if status:
        stmt = stmt.where(Job.status == status)
    if before:
        stmt = stmt.where(Job.id < before)
    jobs = db.scalars(stmt).all()
    users = usernames(db, {j.requested_by for j in jobs})
    return [job_view(j, users) for j in jobs]


@router.get("/job-kinds")
def job_kinds(auth: Viewer) -> object:
    rank = service.RANK[auth.user.role]
    return [k.public() | {"allowed": rank >= service.RANK[k.min_role]}
            for k in registry.kinds().values() if k.manual]


@router.get("/jobs")
def list_jobs(auth: Viewer, status: str | None = None,
              limit: int = Query(50, ge=1, le=200), before: int | None = None) -> object:
    return recent_jobs(auth.db, limit, status, before)


class NewJob(BaseModel):
    kind: str = Field(max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)


def _enqueue(auth: Any, kind: str, params: dict[str, Any], **kw: Any) -> object:
    spec = registry.kinds().get(kind)
    if spec is None or not spec.manual:
        raise HTTPException(404, "unknown job kind")
    if service.RANK[auth.user.role] < service.RANK[spec.min_role]:
        raise HTTPException(403, "your role does not allow this")
    try:
        job = queue.enqueue(auth.db, kind, params, actor=auth.user, ip=auth.ip, **kw)
    except queue.AlreadyActive as e:
        return JSONResponse({"detail": str(e), "job_id": e.job.id}, status_code=409)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    return JSONResponse(jsonable_encoder(job_view(job, {auth.user.id: auth.user.username})),
                        status_code=201)


@router.post("/jobs")
def create_job(body: NewJob, auth: Curator) -> object:
    return _enqueue(auth, body.kind, body.params)


@router.get("/jobs/{job_id}")
def get_job(job_id: int, auth: Viewer, after: int = Query(0, ge=0)) -> object:
    job = auth.db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    logs = auth.db.execute(select(JobLog.id, JobLog.at, JobLog.line)
                           .where(JobLog.job_id == job_id, JobLog.id > after)
                           .order_by(JobLog.id).limit(1000)).all()
    view = job_view(job, usernames(auth.db, {job.requested_by}))
    return view | {"result": job.result,
                   "logs": [{"id": i, "at": at, "line": line} for i, at, line in logs]}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int, auth: Curator) -> object:
    job = auth.db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "no such job")
    queue.request_cancel(auth.db, job, actor=auth.user, ip=auth.ip)
    return job_view(job, usernames(auth.db, {job.requested_by}))


# ----------------------------------------------------------------------------- schedules


def schedule_view(row: Schedule) -> dict[str, Any]:
    kind = registry.kinds().get(row.kind)
    return {"id": row.id, "kind": row.kind, "title": kind.title if kind else row.kind,
            "params": row.params, "every_hours": row.every_hours, "paused": row.paused,
            "next_run_at": row.next_run_at, "last_job_id": row.last_job_id}


@router.get("/schedules")
def list_schedules(auth: Viewer) -> object:
    return [schedule_view(r) for r in auth.db.scalars(select(Schedule).order_by(Schedule.id))]


class SchedulePatch(BaseModel):
    paused: bool


@router.patch("/schedules/{schedule_id}")
def patch_schedule(schedule_id: str, body: SchedulePatch, auth: Admin) -> object:
    row = auth.db.get(Schedule, schedule_id)
    if row is None:
        raise HTTPException(404, "no such schedule")
    if row.paused != body.paused:
        row.paused = body.paused
        audit.record(auth.db, "schedule_paused" if body.paused else "schedule_resumed",
                     actor=auth.user, target=f"schedule:{row.id}", ip=auth.ip)
        auth.db.commit()
    return schedule_view(row)


@router.post("/schedules/{schedule_id}/run")
def run_schedule(schedule_id: str, auth: Curator) -> object:
    row = auth.db.get(Schedule, schedule_id)
    if row is None:
        raise HTTPException(404, "no such schedule")
    return _enqueue(auth, row.kind, dict(row.params), schedule_id=row.id)
