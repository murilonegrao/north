"""DAPIP export -> ``institutions.accreditation`` (record 0002/R10, A15, A16).

Only institutional accreditation counts: ``AccreditationRecords.ProgramName ==
"Institutional Accreditation"`` with no end date and status "Accredited". The join is by UNITID,
then by the 8-digit OPEID, then by the parent's 6-digit OPEID (branch campuses of chains).

Contacts (record 0009): ``InstitutionCampus.csv`` names administrators (AdminName,
AdminPhone, AdminEmail). They are read in a separate projection and stored only in the private
``institution_contacts`` table, per institution (an institution's own rows and its locations,
by ``ParentDapipId``); this run replaces the DAPIP contacts of the institutions it covers. The
address, general phone and fax columns are never read. Nothing of this reaches a value,
evidence, a field change, a task or a log.
"""

from __future__ import annotations

import datetime as dt
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from north.domain.verified import Status
from north.ingest.contacts import Person, replace_contacts
from north.ingest.us.common import RunContext, StepResult, read_csv_rows, run_step, subdivision_id
from north.repository.models import Institution, InstitutionIdentifier

DOWNLOAD_PAGE = "https://ope.ed.gov/dapip/#/download-data-files"
INSTITUTIONAL = "Institutional Accreditation"
CAMPUS_FILE, RECORDS_FILE = "InstitutionCampus.csv", "AccreditationRecords.csv"
CAMPUS_COLUMNS = ("DapipId", "OpeId", "IpedsUnitIds", "LocationType")
CONTACT_COLUMNS = ("DapipId", "ParentDapipId", "AdminName", "AdminEmail", "AdminPhone")
RECORD_COLUMNS = ("DapipId", "AgencyName", "ProgramName", "AccreditationStatus",
                  "AccreditationEndDate")
# The seven former regional commissions, shown by their usual short names. "Regional" itself is
# never shown (R10); any other recognized accreditor is shown by its DAPIP name.
SHORT_NAMES = {
    "Middle States Commission on Higher Education": "MSCHE",
    "New England Commission of Higher Education": "NECHE",
    "Higher Learning Commission": "HLC",
    "Northwest Commission on Colleges and Universities": "NWCCU",
    "Southern Association of Colleges and Schools Commission on Colleges d.b.a. Commission on "
    "Colleges and Universities": "SACSCOC",
    "WASC Senior College and University Commission": "WSCUC",
    "Accrediting Commission for Community and Junior Colleges": "ACCJC",
}


def _inputs(path: Path) -> tuple[list[Path], Path, str | None, str | None]:
    """(files to hash, container, campus member, records member) for a zip or a directory."""
    if path.is_dir():
        files = [path / CAMPUS_FILE, path / RECORDS_FILE]
        return files, path, None, None
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    def member(name: str) -> str:
        return next(n for n in names if n.rsplit("/", 1)[-1].lower() == name.lower())
    return [path], path, member(CAMPUS_FILE), member(RECORDS_FILE)


def _version(path: Path, files: list[Path]) -> str:
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(path))
    if m:
        return m.group(0)
    newest = max(f.stat().st_mtime for f in files)
    return dt.datetime.fromtimestamp(newest, dt.UTC).date().isoformat()


def ingest_dapip(session: Session, path: Path, state: str = "TX") -> StepResult:
    """``path`` is the DAPIP zip as downloaded or a directory with the extracted CSVs."""
    state = state.upper()
    files, container, campus_member, records_member = _inputs(path)
    version = _version(path, files)

    def read(name: str, member: str | None, cols: tuple[str, ...]):
        return read_csv_rows(container / name if member is None else container, member, cols)

    def work(ctx: RunContext) -> None:
        by_unitid: dict[str, list[str]] = defaultdict(list)
        by_opeid: dict[str, list[str]] = defaultdict(list)
        by_ope6: dict[str, list[str]] = defaultdict(list)
        for r in read(CAMPUS_FILE, campus_member, CAMPUS_COLUMNS):
            ctx.counts["rows"] += 1
            if r["LocationType"] != "Institution":
                continue
            for u in r["IpedsUnitIds"].split(","):
                if u.strip():
                    by_unitid[u.strip()].append(r["DapipId"])
            ope = r["OpeId"].strip()
            if re.fullmatch(r"\d{8}", ope):
                by_opeid[ope].append(r["DapipId"])
                by_ope6[ope[:6]].append(r["DapipId"])
        # Administrators by the DAPIP id of their institution (a location counts for its parent).
        admins: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        for r in read(CAMPUS_FILE, campus_member, CONTACT_COLUMNS):
            admins[r["ParentDapipId"] or r["DapipId"]].append(
                (r["AdminName"], r["AdminEmail"], r["AdminPhone"]))
        people: list[Person] = []
        current: dict[str, list[dict[str, str]]] = defaultdict(list)
        for r in read(RECORDS_FILE, records_member, RECORD_COLUMNS):
            ctx.counts["accreditation_rows"] += 1
            if r["ProgramName"] == INSTITUTIONAL and not r["AccreditationEndDate"]:
                current[r["DapipId"]].append(r)

        insts = session.scalars(select(Institution).where(
            Institution.subdivision_id == subdivision_id(state)).order_by(Institution.id)).all()
        for inst in insts:
            ids = {i.scheme: i.value for i in inst.identifiers}
            subject = {"institution_id": inst.id, "name": inst.name}
            unitid, opeid = ids.get("unitid", ""), ids.get("opeid", "")
            join, dapip_ids = "unitid", by_unitid.get(unitid, [])
            if not dapip_ids and opeid:
                join, dapip_ids = "opeid", by_opeid.get(opeid, [])
            if not dapip_ids and opeid:
                join, dapip_ids = "parent opeid", by_ope6.get(opeid[:6], [])
            ctx.counts["institutions"] += 1
            path_ = f"institution[{inst.id}].accreditation"
            if not dapip_ids:
                ctx.counts["not_joined"] += 1
                ctx.task("dapip_match", f"{inst.id} {inst.name}: no DAPIP row by UNITID or OPEID",
                         [subject])
                ctx.put(inst, "accreditation", ctx.vv(None, Status.UNKNOWN, evidence=""), path_)
                continue
            ctx.counts[f"joined_by_{join.replace(' ', '_')}"] += 1
            people += [Person(inst.id, name=n, email=e, phone=ph)
                       for d in dict.fromkeys(dapip_ids) for n, e, ph in admins.get(d, [])]
            if join != "parent opeid" and len(set(dapip_ids)) == 1:
                _dapip_identifier(ctx, inst, dapip_ids[0])
            recs = [x for d in dict.fromkeys(dapip_ids) for x in current.get(d, [])]
            accredited = sorted({x["AgencyName"] for x in recs
                                 if x["AccreditationStatus"] == "Accredited"})
            if not accredited:
                statuses = sorted({x["AccreditationStatus"] for x in recs}) or ["none current"]
                ctx.counts["no_current_institutional"] += 1
                ctx.task("accreditation_review",
                         f"{inst.id} {inst.name}: DAPIP has no current institutional "
                         f"accreditation with status Accredited ({', '.join(statuses)})",
                         [{**subject, "dapip_ids": sorted(set(dapip_ids)), "join": join}])
                ctx.put(inst, "accreditation", ctx.vv(None, Status.UNKNOWN, evidence=""), path_)
                continue
            names = [SHORT_NAMES.get(a, a) for a in accredited]
            new = ctx.vv({"accreditor": "; ".join(names), "scheme": "us_ed_recognized",
                          "institutional": True},
                         evidence=f"DAPIP {version}: {INSTITUTIONAL}, "
                                  f"{'; '.join(accredited)}, status Accredited "
                                  f"(joined by {join})")
            ctx.put(inst, "accreditation", new, path_)
            ctx.counts["accredited"] += 1
        replace_contacts(session, source="dapip", source_file_id=ctx.source_file.id,
                         people=people, institution_ids=[i.id for i in insts])
        session.flush()

    return run_step(session, source="dapip", files=files, file_version=version,
                    source_url=DOWNLOAD_PAGE, scope=subdivision_id(state), work=work)


def _dapip_identifier(ctx: RunContext, inst: Institution, dapip_id: str) -> None:
    s = ctx.session
    taken = s.scalar(select(InstitutionIdentifier).where(
        InstitutionIdentifier.scheme == "dapip", InstitutionIdentifier.value == dapip_id))
    if taken is not None:
        return
    mine = s.scalar(select(InstitutionIdentifier).where(
        InstitutionIdentifier.institution_id == inst.id, InstitutionIdentifier.scheme == "dapip"))
    ctx.log_change(f"institution[{inst.id}].identifiers.dapip",
                   mine.value if mine else None, dapip_id)
    if mine is not None:
        mine.value = dapip_id
    else:
        s.add(InstitutionIdentifier(institution_id=inst.id, scheme="dapip", value=dapip_id))
    s.flush()
