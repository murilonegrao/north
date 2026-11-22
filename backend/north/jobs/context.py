"""What a running job sees: its parameters, directories, a logger and the cancel signal."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from north.jobs import queue


class JobCancelled(BaseException):
    """Raised at the next checkpoint after a cancel request (or a worker shutdown)."""


class NeedsSetting(Exception):
    pass


@dataclass
class JobContext:
    job_id: int
    sessions: sessionmaker[Session]
    raw_dir: Path | None
    incoming_dir: Path | None
    requested_by: int | None = None
    cancel: threading.Event = field(default_factory=threading.Event)
    _log_db: Session | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def log(self, line: str) -> None:
        """A progress line for the admin; also a cancel checkpoint."""
        with self._lock:
            if self._log_db is None:
                self._log_db = self.sessions()
            for part in str(line).splitlines() or [""]:
                queue.append_log(self._log_db, self.job_id, part)
        self.checkpoint()

    def checkpoint(self) -> None:
        if self.cancel.is_set():
            raise JobCancelled()

    def raw(self) -> Path:
        if self.raw_dir is None:
            raise NeedsSetting("NORTH_RAW_DIR is not set for the worker")
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        return self.raw_dir

    def incoming(self) -> Path:
        if self.incoming_dir is None:
            raise NeedsSetting("NORTH_INCOMING_DIR is not set for the worker")
        return self.incoming_dir

    def close(self) -> None:
        if self._log_db is not None:
            self._log_db.close()


class JobLogHandler(logging.Handler):
    """Copies records of the north.* loggers into the job log while the job runs."""

    def __init__(self, ctx: JobContext) -> None:
        super().__init__(level=logging.INFO)
        self.ctx = ctx
        self.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            with self.ctx._lock:
                if self.ctx._log_db is None:
                    self.ctx._log_db = self.ctx.sessions()
                queue.append_log(self.ctx._log_db, self.ctx.job_id, self.format(record))
        except Exception:  # logging must never break the job
            self.handleError(record)


def result_status(result: dict[str, Any]) -> str:
    return "attention" if result.get("needs_attention") else "succeeded"
