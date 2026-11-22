"""US ingestion helpers: CSV reading, the US country row and its subdivisions.

The generic machinery (source files, runs, idempotency, history, reconciliation) lives in
``north.ingest.common`` and is re-exported here for the US steps.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path

from sqlalchemy.orm import Session

from north.ingest.common import (  # noqa: F401  (re-exported for the US steps)
    RunContext,
    StepResult,
    log,
    run_step,
    sha256_file,
    sha256_files,
)
from north.ingest.us.states import STATE_NAMES
from north.ingest.us.zipguard import check_member
from north.repository.models import Country, Subdivision

COUNTRY = "US"


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


