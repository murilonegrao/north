"""Job kinds and schedules, declared in code by country modules (P8: the core names none).

Each module listed in PLUGINS exposes `KINDS` (list of JobKind), `SCHEDULES` (list of
ScheduleSpec) and `overview(session) -> dict`. Kinds run in the worker; the web process
imports them only to list and validate them, so heavy imports stay inside `run`.
"""

from __future__ import annotations

import datetime as dt
import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from north.jobs.context import JobContext

PLUGINS = ("north.ingest.us.jobs", "north.ingest.ie.jobs")


@dataclass(frozen=True)
class Param:
    name: str
    kind: str  # "text" or "bool"
    default: Any
    help: str = ""


@dataclass(frozen=True)
class JobKind:
    name: str
    title: str
    description: str
    run: Callable[[JobContext, dict[str, Any]], dict[str, Any]]
    # Returns the normalized parameters or raises ValueError (shown to the user).
    validate: Callable[[dict[str, Any]], dict[str, Any]] = lambda p: {}
    params: tuple[Param, ...] = ()
    min_role: str = "curator"
    # False: started by the system (an upload), not offered in the "run" menu.
    manual: bool = True

    def public(self) -> dict[str, Any]:
        return {"name": self.name, "title": self.title, "description": self.description,
                "min_role": self.min_role, "manual": self.manual,
                "params": [p.__dict__ for p in self.params]}


@dataclass(frozen=True)
class ScheduleSpec:
    id: str
    kind: str
    every_hours: int
    params: dict[str, Any] = field(default_factory=dict)
    # First run after a fresh install, from "now".
    first_run: Callable[[dt.datetime], dt.datetime] = lambda now: now


def next_weekday_at(weekday: int, hour: int) -> Callable[[dt.datetime], dt.datetime]:
    """Monday is 0. The next such day at hour:00 UTC strictly after now."""
    def first(now: dt.datetime) -> dt.datetime:
        day = now.astimezone(dt.UTC).replace(hour=hour, minute=0, second=0, microsecond=0)
        day += dt.timedelta(days=(weekday - day.weekday()) % 7)
        return day if day > now else day + dt.timedelta(days=7)
    return first


@cache
def plugins() -> tuple[ModuleType, ...]:
    return tuple(importlib.import_module(name) for name in PLUGINS)


def kinds() -> dict[str, JobKind]:
    return {k.name: k for p in plugins() for k in p.KINDS}


def schedules() -> list[ScheduleSpec]:
    return [s for p in plugins() for s in p.SCHEDULES]


def overview(session: Any) -> dict[str, Any]:
    return {p.COUNTRY: p.overview(session) for p in plugins()}


def upload_kind() -> dict[str, str]:
    """Country code -> name of the kind that accepts an uploaded file."""
    return {p.COUNTRY: p.UPLOAD_KIND for p in plugins()}
