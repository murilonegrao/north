"""Versioned reference data from ``data/reference/``: the CIP 2020 -> ISCED-F 2013 map (R9)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from north.ingest.us.common import read_csv_rows
from north.ingest.us.ipeds import ensure_cip
from north.repository.models import Classification, ClassificationMap

ISCED_SCHEME = "isced_f_2013"
COLUMNS = ("cip_code", "cip_title", "isced_f_code", "isced_f_title", "origin", "partial",
           "notes")
# CSV "official" = pair copied from the Statistics Canada concordance (R9: derived_official).
ORIGIN = {"official": "derived_official", "proposed": "proposed"}


def load_cip_isced(session: Session, path: Path) -> dict[str, int]:
    rows = 0
    for r in read_csv_rows(path, columns=COLUMNS):
        rows += 1
        cip = ensure_cip(session, r["cip_code"], r["cip_title"], authoritative=False)
        isced = session.scalar(select(Classification).where(
            Classification.scheme == ISCED_SCHEME, Classification.code == r["isced_f_code"]))
        if isced is None:
            isced = Classification(scheme=ISCED_SCHEME, code=r["isced_f_code"],
                                   title=r["isced_f_title"])
            session.add(isced)
            session.flush()
        m = session.get(ClassificationMap, (cip.id, isced.id))
        if m is None:
            m = ClassificationMap(from_id=cip.id, to_id=isced.id, origin="proposed")
            session.add(m)
        m.origin = ORIGIN.get(r["origin"], r["origin"])
        m.partial = r["partial"].strip().lower() == "true"
        m.notes = r["notes"] or None
    session.commit()
    return {"rows": rows}
