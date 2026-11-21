"""Shared ingestion machinery: source files, runs, idempotency, history, reconciliation.

Every step takes file paths (the FR-26 upload flow will call the same functions with the
stored upload). A step registers a ``source_files`` row (unique on source + sha256) and an
``ingestion_runs`` row; a succeeded run for the same file and scope makes the step a no-op
(NFR-03). Values are written as VerifiedValues; each change gets a ``field_changes`` row with
author ``ingest:<source>``. Ingestion never overwrites a curated value and never turns a known
value into unknown: it opens a reconciliation task instead (UML 5.1).
"""

from __future__ import annotations

import copy
import csv
import datetime as dt
import hashlib
import io
import logging
import zipfile
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from north.domain.verified import SourceKind, Status, is_curated, verified
from north.ingest.us.states import STATE_NAMES
from north.ingest.us.zipguard import check_member
from north.repository.models import (
    Country,
    FieldChange,
    IngestionRun,
    ReconciliationTask,
    SourceFile,
    Subdivision,
)

log = logging.getLogger("north.ingest")

COUNTRY = "US"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_files(paths: Sequence[Path]) -> str:
    """Hash of several files (a directory upload): sha256 over "name sha256" lines, sorted."""
    lines = sorted(f"{p.name} {sha256_file(p)}" for p in paths)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def read_csv_rows(path: Path, member: str | None = None,
                  columns: Iterable[str] | None = None) -> Iterator[dict[str, str]]:
    """Rows of a CSV file or of a CSV inside a zip, with stripped keys and values.

    Keys are upper-cased only when ``columns`` is None (IPEDS); ``columns`` projects each row
    to a whitelist at read time, so other columns (personal data) never leave this function.
    Downloaded files are data: nothing in them is executed.
    """
    keep = list(columns) if columns is not None else None
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            name = member or pick_csv_member(z.namelist())
            check_member(z, name)  # size and compression ratio (zip bombs, FR-26 uploads)
            with z.open(name) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
                yield from _rows(text, keep)
    else:
        with path.open(encoding="utf-8-sig", errors="replace", newline="") as text:
            yield from _rows(text, keep)


def pick_csv_member(names: Iterable[str]) -> str:
    csvs = [n for n in names if n.lower().endswith(".csv")]
    if not csvs:
        raise ValueError("no CSV inside the zip")
    # Some IPEDS zips ship a revised "_rv" file next to the original; prefer it.
    return sorted(csvs, key=lambda n: ("_rv" not in n.lower(), n))[0]


def _rows(text: io.TextIOBase, keep: list[str] | None) -> Iterator[dict[str, str]]:
    reader = csv.reader(text)
    header = [h.strip() for h in next(reader)]
    if keep is None:
        header = [h.upper() for h in header]
        for row in reader:
            yield {k: v.strip() for k, v in zip(header, row, strict=False)}
        return
    missing = [c for c in keep if c not in header]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    idx = [(c, header.index(c)) for c in keep]
    for row in reader:
        yield {c: (row[i].strip() if i < len(row) else "") for c, i in idx}


def ensure_country(session: Session) -> Country:
    country = session.get(Country, COUNTRY)
    if country is None:
        country = Country(code=COUNTRY, name="United States", currency="USD", rules_module="us")
        session.add(country)
        session.flush()
    return country


def subdivision_id(state: str) -> str:
    return f"{COUNTRY}-{state.upper()}"


def ensure_subdivision(session: Session, state: str) -> Subdivision:
    ensure_country(session)
    sid = subdivision_id(state)
    sub = session.get(Subdivision, sid)
    if sub is None:
        sub = Subdivision(id=sid, country_code=COUNTRY, name=STATE_NAMES.get(state.upper(), state),
                          coverage_status="in_progress")
        session.add(sub)
        session.flush()
    return sub


def _strip_volatile(v: Any) -> Any:
    if isinstance(v, dict) and "verified_at" in v:
        return {k: x for k, x in v.items() if k != "verified_at"}
    return v


@dataclass
class RunContext:
    session: Session
    source: str
    run: IngestionRun
    source_file: SourceFile
    source_url: str
    counts: Counter[str] = field(default_factory=Counter)
    errors: list[str] = field(default_factory=list)

    @property
    def author(self) -> str:
        return f"ingest:{self.source}"

    @property
    def today(self) -> str:
        return dt.date.today().isoformat()

    def vv(self, value: Any, status: Status = Status.CONFIRMED_OFFICIAL, *, evidence: str,
           source_url: str | None = None, **extra: Any) -> dict[str, Any]:
        """VerifiedValue taken from this run's uploaded file (K10: URL of the download page)."""
        if status == Status.UNKNOWN:
            return verified(None, Status.UNKNOWN, **extra)
        return verified(value, status, source_kind=SourceKind.UPLOADED_FILE,
                        source_url=source_url or self.source_url, evidence=evidence,
                        verified_at=self.today, **extra)

    def log_change(self, field_path: str, old: Any, new: Any,
                   program_id: str | None = None) -> bool:
        """Add a field_changes row when the value changed (re-verification is not a change)."""
        if _strip_volatile(old) == _strip_volatile(new):
            return False
        self.session.add(FieldChange(program_id=program_id, field_path=field_path,
                                     old_value=old, new_value=new, author=self.author))
        self.counts["field_changes"] += 1
        return True

    def task(self, kind: str, reason: str, candidates: list[Any] | None = None) -> None:
        self.session.add(ReconciliationTask(run_id=self.run.id, kind=kind, reason=reason,
                                            candidates=candidates or []))
        self.counts[f"tasks_{kind}"] += 1

    def set_attr(self, obj: Any, attr: str, new: Any, field_path: str,
                 program_id: str | None = None) -> None:
        """Set a plain column and log the change."""
        old = getattr(obj, attr)
        if old != new:
            self.log_change(field_path, old, new, program_id)
            setattr(obj, attr, new)

    def put(self, obj: Any, attr: str, new: dict[str, Any], field_path: str, *,
            key: Sequence[str] = (), program_id: str | None = None) -> bool:
        """Write a VerifiedValue at ``obj.attr[key...]`` with the protection rules.

        Returns True when the stored value was written.
        """
        root = copy.deepcopy(getattr(obj, attr))
        if key:
            node = root if isinstance(root, dict) else {}
            root = node
            for k in key[:-1]:
                node = node.setdefault(k, {})
            current = node.get(key[-1])
        else:
            current = root
        if is_curated(current) and _strip_volatile(current) != _strip_volatile(new):
            self.task("value_conflict",
                      f"{field_path}: curated value kept; {self.source} reports a different one",
                      [{"field_path": field_path, "current": current, "reported": new}])
            return False
        if (new.get("status") == Status.UNKNOWN and isinstance(current, dict)
                and current.get("status") not in (None, Status.UNKNOWN)):
            self.task("value_missing",
                      f"{field_path}: {self.source} no longer supports the stored value; kept",
                      [{"field_path": field_path, "current": current}])
            return False
        self.log_change(field_path, current, new, program_id)
        if key:
            node[key[-1]] = new
            setattr(obj, attr, root)
        else:
            setattr(obj, attr, new)
        return True


@dataclass
class StepResult:
    source: str
    status: str  # succeeded, skipped, failed
    file_version: str
    sha256: str
    counts: dict[str, int]
    errors: list[str]

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def run_step(session: Session, *, source: str, files: Sequence[Path], file_version: str,
             source_url: str, scope: str, work: Callable[[RunContext], None],
             file_source_url: str | None = None) -> StepResult:
    """Register the file, skip if already ingested for this scope, run ``work`` atomically."""
    files = [Path(f) for f in files]
    for f in files:
        if not f.is_file():
            raise FileNotFoundError(f)
    digest = sha256_file(files[0]) if len(files) == 1 else sha256_files(files)
    sf = session.scalar(select(SourceFile).where(SourceFile.source == source,
                                                 SourceFile.sha256 == digest))
    if sf is None:
        sf = SourceFile(source=source, sha256=digest, file_version=file_version,
                        original_name=files[0].name if len(files) == 1 else
                        ",".join(sorted(f.name for f in files)),
                        storage_path=None, size_bytes=sum(f.stat().st_size for f in files),
                        source_url=file_source_url or source_url)
        session.add(sf)
        session.flush()
    done = session.scalar(select(IngestionRun).where(
        IngestionRun.source_file_id == sf.id, IngestionRun.scope == scope,
        IngestionRun.status == "succeeded"))
    if done is not None:
        session.commit()
        return StepResult(source, "skipped", sf.file_version, digest, dict(done.counts), [])
    run = IngestionRun(source_file_id=sf.id, scope=scope, status="running")
    session.add(run)
    session.commit()
    run_id, sf_id = run.id, sf.id

    ctx = RunContext(session=session, source=source, run=run, source_file=sf,
                     source_url=source_url)
    try:
        work(ctx)
        run.status = "succeeded"
        run.counts = dict(ctx.counts)
        run.errors = ctx.errors
        run.finished_at = dt.datetime.now(dt.UTC)
        session.commit()
        status = "succeeded"
    except Exception as exc:  # the run is closed as failed and can be repeated
        session.rollback()
        log.exception("ingestion of %s failed", source)
        failed = session.get(IngestionRun, run_id)
        assert failed is not None
        failed.status = "failed"
        failed.errors = [*ctx.errors, f"{type(exc).__name__}: {exc}"]
        failed.finished_at = dt.datetime.now(dt.UTC)
        session.commit()
        ctx.errors = failed.errors
        status = "failed"
    sf = session.get(SourceFile, sf_id)
    return StepResult(source, status, sf.file_version if sf else file_version, digest,
                      dict(ctx.counts), list(ctx.errors))
