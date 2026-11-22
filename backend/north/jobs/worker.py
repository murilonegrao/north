"""The worker: `python -m north.jobs.worker`.

One process, one job at a time (the parsers are CPU and memory bound). Each loop: enqueue due
schedules, claim the oldest queued job, run it with a heartbeat thread, record the outcome.
SIGTERM (a deploy) cancels the running job at its next checkpoint, so it ends as "cancelled"
instead of being killed half way; a job left "running" by a crash is reaped as "failed".
"""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import socket
import threading
import time
import traceback

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from north.auth.service import purge_old_attempts
from north.jobs import queue, registry
from north.jobs.context import JobCancelled, JobContext, JobLogHandler, result_status
from north.settings import get_settings

log = logging.getLogger("north.worker")

IDLE_SLEEP = 5.0
HEARTBEAT_EVERY = 15.0
HOUSEKEEPING_EVERY = 3600.0
WORKER_APP = "north-worker"  # also read by north.api.admin.overview


def worker_sessionmaker() -> sessionmaker[Session]:
    """Connections named north-worker, so the admin can see that the worker is up."""
    url = get_settings().database_url
    if not url:
        raise SystemExit("NORTH_DATABASE_URL is not set")
    engine = create_engine(url, pool_pre_ping=True,
                           connect_args={"application_name": WORKER_APP})
    return sessionmaker(bind=engine, expire_on_commit=False)


class Worker:
    def __init__(self, sessions: sessionmaker[Session] | None = None) -> None:
        self.sessions = sessions or worker_sessionmaker()
        self.name = f"{socket.gethostname()}:{os.getpid()}"
        self.stop = threading.Event()
        self.current: JobContext | None = None
        self._last_housekeeping = 0.0

    # ------------------------------------------------------------------ lifecycle

    def request_stop(self, *_: object) -> None:
        log.info("stop requested; the running job is cancelled at its next checkpoint")
        self.stop.set()
        if self.current is not None:
            self.current.cancel.set()

    def run_forever(self) -> None:
        with self.sessions() as db:
            queue.sync_schedules(db)
            queue.reap_stale(db)
        log.info("worker %s ready; job kinds: %s", self.name, ", ".join(registry.kinds()))
        while not self.stop.is_set():
            if not self.tick():
                self.stop.wait(IDLE_SLEEP)

    def tick(self) -> bool:
        """One loop iteration; True when a job ran."""
        with self.sessions() as db:
            queue.run_due_schedules(db)
            if time.monotonic() - self._last_housekeeping > HOUSEKEEPING_EVERY:
                queue.reap_stale(db)
                purge_old_attempts(db)
                self._last_housekeeping = time.monotonic()
            job = queue.claim(db, self.name)
            if job is None:
                return False
            job_id, kind, params = job.id, job.kind, dict(job.params)
            requested_by = job.requested_by
        self.run_job(job_id, kind, params, requested_by)
        return True

    # ------------------------------------------------------------------ one job

    def run_job(self, job_id: int, kind: str, params: dict, requested_by: int | None) -> str:
        settings = get_settings()
        ctx = JobContext(job_id=job_id, sessions=self.sessions, raw_dir=settings.raw_dir,
                         incoming_dir=settings.incoming_dir, requested_by=requested_by)
        self.current = ctx
        if self.stop.is_set():
            ctx.cancel.set()
        beat_stop = threading.Event()
        beat = threading.Thread(target=self._beat, args=(ctx, beat_stop), daemon=True)
        beat.start()
        handler = JobLogHandler(ctx)
        north_log = logging.getLogger("north")
        north_log.addHandler(handler)
        status, result, error = "failed", {}, None
        started = time.monotonic()
        try:
            spec = registry.kinds().get(kind)
            if spec is None:
                raise ValueError(f"unknown job kind {kind!r} (removed from the code?)")
            ctx.log(f"start {kind} {params or ''}".rstrip())
            result = spec.run(ctx, params) or {}
            status = result_status(result)
        except JobCancelled:
            status, error = "cancelled", "cancelled while running"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            tb = traceback.format_exc(limit=8)
            with contextlib.suppress(BaseException):  # the outcome below is what matters
                ctx.log(tb)
        finally:
            north_log.removeHandler(handler)
            beat_stop.set()
            beat.join(timeout=5)
            self.current = None
        secs = round(time.monotonic() - started, 1)
        try:
            ctx.cancel.clear()
            ctx.log(f"end {status} in {secs}s" + (f": {error}" if error else ""))
        finally:
            ctx.close()
        with self.sessions() as db:
            queue.finish(db, job_id, status, result=result, error=error)
        log.info("job %s %s %s in %ss", job_id, kind, status, secs)
        return status

    def _beat(self, ctx: JobContext, stop: threading.Event) -> None:
        with self.sessions() as db:
            while not stop.wait(HEARTBEAT_EVERY):
                try:
                    if queue.heartbeat(db, ctx.job_id):
                        ctx.cancel.set()
                except Exception:  # a database blip must not kill the job
                    db.rollback()
                    log.exception("heartbeat failed for job %s", ctx.job_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    w = Worker()
    signal.signal(signal.SIGTERM, w.request_stop)
    signal.signal(signal.SIGINT, w.request_stop)
    w.run_forever()


if __name__ == "__main__":
    main()

