"""IPEDS (NCES): HD directory, C_A completions, IC_AY graduate charges (record 0002/R3, K6).

Processed in this order for a state: HD, then C_A, then IC_AY. Each file keeps its own year in
``source_files.file_version`` (e.g. HD2024, C2024_A, IC2023_AY).
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from north.domain.countries.us.cip import cip_family, normalize_cip
from north.domain.countries.us.stem import program_flags
from north.domain.verified import Status
from north.ingest.us.common import (
    COUNTRY,
    RunContext,
    StepResult,
    ensure_subdivision,
    read_csv_rows,
    run_step,
    subdivision_id,
)
from north.ingest.us.eligibility import recompute_stem_eligibilities
from north.ingest.us.xlsx import value_labels
from north.repository.models import (
    Campus,
    Classification,
    Institution,
    InstitutionIdentifier,
    Locality,
    Program,
    ProgramClassification,
)

DOWNLOAD_PAGE = "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx"
FILE_URL = "https://nces.ed.gov/ipeds/datacenter/data/{name}.zip"

# HD CONTROL codes (HD dictionary).
CONTROL = {"1": "public", "2": "private_nonprofit", "3": "private_for_profit"}
# HD HLOFFER 7, 8, 9: highest offering is a master's degree or above.
GRAD_HLOFFER = {"7", "8", "9"}
# C_A AWLEVEL 7 = "Master's degree" (C<year>_A dictionary, Frequencies sheet).
AWLEVEL_MASTERS = "7"
MASTERS_LABEL = "Master's degree"
DEGREE = "Master's"
# Contract v0.1 §4: a code, translated by the UI ("institution-wide average for graduate
# students, not this program's price").
NOTE_TUITION = "institution_wide_average"

# Only these HD columns are read; the file also names the chief administrator (CHFNM), which
# North never stores.
HD_COLUMNS = ("UNITID", "INSTNM", "CITY", "STABBR", "CONTROL", "OPEID", "WEBADDR", "HLOFFER",
              "SECTOR", "CYACTIVE", "COUNTYCD", "COUNTYNM", "LATITUDE", "LONGITUD")


def find_file(directory: Path, pattern: str) -> Path:
    """Newest file in ``directory`` whose stem matches ``pattern`` (e.g. ``HD(\\d{4})``)."""
    rx = re.compile(rf"^{pattern}$", re.I)
    found = []
    for p in directory.iterdir():
        if p.suffix.lower() in (".zip", ".csv") and (m := rx.match(p.stem)):
            found.append((m.group(1), p.suffix.lower() == ".zip", p))
    if not found:
        raise FileNotFoundError(f"no file matching {pattern} in {directory}")
    return max(found)[2]


def file_version(path: Path) -> str:
    return path.stem.upper().replace("_RV", "")


def academic_year(version: str) -> str:
    """C2024_A -> "2023-24" (completions of the academic year ending in 2024)."""
    m = re.search(r"(\d{4})", version)
    if not m:
        return version
    end = int(m.group(1))
    return f"{end - 1}-{str(end)[2:]}"


def _project(row: dict[str, str], columns: tuple[str, ...]) -> dict[str, str]:
    return {c: row.get(c, "") for c in columns}


def _website(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    return raw if re.match(r"^https?://", raw, re.I) else f"https://{raw}"


def _host(url: str | None) -> str | None:
    if not url:
        return None
    host = (urlsplit(url).hostname or "").lower()
    return host.removeprefix("www.") or None


def _set_website(ctx: RunContext, inst: Institution, new: str | None, field_path: str) -> None:
    """The HD file is the source of truth for the website (applied and logged), but a change of
    host is not routine (a merger, a typo, a hijacked domain): a curator reviews it."""
    old = inst.website
    if old is not None and _host(old) != _host(new):
        ctx.task("website_changed",
                 f"{field_path}: host changed from {_host(old)} to {_host(new)}; review",
                 [{"institution_id": inst.id, "old": old, "new": new}])
    ctx.set_attr(inst, "website", new, field_path)


def _float(raw: str) -> float | None:
    try:
        return float(raw)
    except ValueError:
        return None


def institutions_in_state(session: Session, state: str) -> dict[str, Institution]:
    """UNITID -> institution, for the institutions of a state."""
    rows = session.execute(
        select(InstitutionIdentifier.value, Institution)
        .join(Institution, Institution.id == InstitutionIdentifier.institution_id)
        .where(InstitutionIdentifier.scheme == "unitid",
               Institution.subdivision_id == subdivision_id(state)))
    return {unitid: inst for unitid, inst in rows}


def main_campus(session: Session, institution_id: str) -> Campus | None:
    return session.scalar(select(Campus).where(Campus.institution_id == institution_id)
                          .order_by(Campus.id).limit(1))


def _identifier(ctx: RunContext, inst: Institution, scheme: str, value: str) -> None:
    session = ctx.session
    existing = session.scalar(select(InstitutionIdentifier).where(
        InstitutionIdentifier.scheme == scheme, InstitutionIdentifier.value == value))
    if existing is not None:
        if existing.institution_id != inst.id:
            ctx.task("identifier_conflict",
                     f"{scheme} {value} belongs to {existing.institution_id}, file says {inst.id}",
                     [{"scheme": scheme, "value": value, "institution_id": inst.id}])
        return
    old = session.scalar(select(InstitutionIdentifier).where(
        InstitutionIdentifier.institution_id == inst.id, InstitutionIdentifier.scheme == scheme))
    path = f"institution[{inst.id}].identifiers.{scheme}"
    if old is not None:
        ctx.log_change(path, old.value, value)
        old.value = value
    else:
        ctx.log_change(path, None, value)
        session.add(InstitutionIdentifier(institution_id=inst.id, scheme=scheme, value=value))
    session.flush()


def _locality(ctx: RunContext, code: str, name: str) -> Locality | None:
    if not re.fullmatch(r"\d{5}", code):
        return None
    loc = ctx.session.scalar(select(Locality).where(
        Locality.country_code == COUNTRY, Locality.scheme == "us_county_fips",
        Locality.code == code))
    if loc is None:
        loc = Locality(country_code=COUNTRY, scheme="us_county_fips", code=code, name=name)
        ctx.session.add(loc)
        ctx.session.flush()
        ctx.counts["localities_created"] += 1
    elif name and loc.name != name:
        loc.name = name
    return loc


# --------------------------------------------------------------------------- HD


def ingest_hd(session: Session, path: Path, state: str = "TX") -> StepResult:
    """Institutions, identifiers (unitid, opeid), main campus and county locality."""
    state = state.upper()
    version = file_version(path)

    def work(ctx: RunContext) -> None:
        ensure_subdivision(session, state)
        for raw in read_csv_rows(path):
            ctx.counts["rows"] += 1
            r = _project(raw, HD_COLUMNS)
            if r["STABBR"] != state or r["CYACTIVE"] != "1":
                continue
            if r["HLOFFER"] not in GRAD_HLOFFER or r["SECTOR"] == "0":
                continue
            unitid = r["UNITID"]
            if not unitid.isdigit():
                ctx.errors.append(f"bad UNITID {unitid!r}")
                continue
            inst = session.get(Institution, unitid)
            if inst is None:
                inst = Institution(id=unitid, subdivision_id=subdivision_id(state),
                                   name=r["INSTNM"], carnegie_classification={
                                       "value": None, "status": str(Status.UNKNOWN)})
                session.add(inst)
                ctx.log_change(f"institution[{unitid}].name", None, r["INSTNM"])
                session.flush()
                ctx.counts["institutions_created"] += 1
            p = f"institution[{unitid}]"
            ctx.set_attr(inst, "name", r["INSTNM"], f"{p}.name")
            ctx.set_attr(inst, "city", r["CITY"] or None, f"{p}.city")
            ctx.set_attr(inst, "control", CONTROL.get(r["CONTROL"]), f"{p}.control")
            _set_website(ctx, inst, _website(r["WEBADDR"]), f"{p}.website")
            ctx.set_attr(inst, "subdivision_id", subdivision_id(state), f"{p}.subdivision_id")
            ctx.counts["institutions"] += 1
            _identifier(ctx, inst, "unitid", unitid)
            opeid = r["OPEID"].strip()
            if re.fullmatch(r"\d{8}", opeid):
                _identifier(ctx, inst, "opeid", opeid)

            loc = _locality(ctx, r["COUNTYCD"], r["COUNTYNM"])
            campus = main_campus(session, unitid)
            if campus is None:
                campus = Campus(institution_id=unitid, name=r["INSTNM"],
                                intl_authorization={"value": None,
                                                    "status": str(Status.UNKNOWN)})
                session.add(campus)
                session.flush()
                ctx.counts["campuses_created"] += 1
            cp = f"campus[{campus.id}]"
            ctx.set_attr(campus, "name", r["INSTNM"], f"{cp}.name")
            ctx.set_attr(campus, "city", r["CITY"] or None, f"{cp}.city")
            ctx.set_attr(campus, "locality_id", loc.id if loc else None, f"{cp}.locality_id")
            lat, lon = _float(r["LATITUDE"]), _float(r["LONGITUD"])
            if campus.latitude is None or float(campus.latitude) != lat:
                campus.latitude = lat
            if campus.longitude is None or float(campus.longitude) != lon:
                campus.longitude = lon
        session.flush()

    return run_step(session, source="ipeds_hd", files=[path], file_version=version,
                    source_url=DOWNLOAD_PAGE, file_source_url=FILE_URL.format(name=version),
                    scope=subdivision_id(state), work=work)


# --------------------------------------------------------------------------- C_A


def official_cip_title(title: str) -> str:
    """CIP 2020 titles end with a period ("Computer Science.")."""
    title = title.strip()
    return title if title.endswith(".") else f"{title}."


def program_title(cip_title: str) -> str:
    return cip_title.strip().rstrip(".")


def ensure_cip(session: Session, code: str, title: str | None,
               authoritative: bool = True) -> Classification:
    """Get or create a CIP 2020 classification.

    Titles from US files (IPEDS dictionary, DHS list) are authoritative and replace others;
    titles from the reference map (CIP Canada for some codes) only fill a missing one.
    """
    c = session.scalar(select(Classification).where(Classification.scheme == "cip2020",
                                                     Classification.code == code))
    if c is None:
        c = Classification(scheme="cip2020", code=code,
                           title=official_cip_title(title) if title else code)
        session.add(c)
        session.flush()
    elif title and (c.title == code or authoritative):
        c.title = official_cip_title(title)
    return c


def program_id(unitid: str, cip: str) -> str:
    return f"{unitid}-{cip.replace('.', '')}"


def ingest_c_a(session: Session, path: Path, state: str = "TX",
               dictionary: Path | None = None) -> StepResult:
    """Programs per UNITID x 6-digit CIP, master's level, in the scope families."""
    state = state.upper()
    version = file_version(path)
    year = academic_year(version)

    def work(ctx: RunContext) -> None:
        labels: dict[str, dict[str, str]] = {}
        if dictionary is not None:
            labels = value_labels(dictionary)
            got = labels.get("AWLEVEL", {}).get(AWLEVEL_MASTERS, "")
            if got.strip().lower() != MASTERS_LABEL.lower():
                raise ValueError(f"AWLEVEL {AWLEVEL_MASTERS} is {got!r} in the dictionary, "
                                 f"expected {MASTERS_LABEL!r}")
        else:
            ctx.errors.append("no dictionary: CIP titles taken from existing classifications")
        cip_titles = labels.get("CIPCODE", {})

        insts = institutions_in_state(session, state)
        # [total, nonresident] per (UNITID, CIP6); None once any contributing cell is
        # missing or unparsable (".", empty, absent column): never summed as 0 (BR-02).
        totals: dict[tuple[str, str], list[int | None]] = defaultdict(lambda: [0, 0])
        for r in read_csv_rows(path):
            ctx.counts["rows"] += 1
            if r.get("AWLEVEL") != AWLEVEL_MASTERS or r.get("UNITID") not in insts:
                continue
            try:
                cip = normalize_cip(r.get("CIPCODE", ""))
            except ValueError:
                continue  # 99 = grand total
            if cip_family(cip) is None:
                continue
            t = totals[(r["UNITID"], cip)]
            for i, column in enumerate(("CTOTALT", "CNRALT")):
                v = _int(r.get(column))
                t[i] = None if t[i] is None or v is None else t[i] + v

        for (unitid, cip), (total, nonresident) in sorted(totals.items()):
            inst = insts[unitid]
            campus = main_campus(session, inst.id)
            if campus is None:
                ctx.errors.append(f"{unitid}: no campus")
                continue
            cls = ensure_cip(session, cip, cip_titles.get(cip))
            pid = program_id(unitid, cip)
            prog = session.get(Program, pid)
            if prog is None:
                prog = Program(id=pid, campus_id=campus.id, name=program_title(cls.title),
                               degree=DEGREE, flags=[], immigration={}, academic={}, cost={},
                               funding={}, admissions={}, career={}, family={})
                session.add(prog)
                session.flush()
                ctx.log_change("name", None, prog.name, pid)
                ctx.counts["programs_created"] += 1
            ctx.counts["programs"] += 1
            ctx.counts[f"programs_family_{cip_family(cip)}"] += 1
            ctx.set_attr(prog, "campus_id", campus.id, "campus_id", pid)
            ctx.set_attr(prog, "degree", DEGREE, "degree", pid)
            if prog.academic.get("title_source", "cip_title") == "cip_title":
                ctx.set_attr(prog, "name", program_title(cls.title), "name", pid)
                prog.academic = {**prog.academic, "title_source": "cip_title"}
            ctx.set_attr(prog, "flags", program_flags(cip), "flags", pid)

            pc = session.get(ProgramClassification, (pid, cls.id))
            new_pc = ctx.vv({"scheme": "cip2020", "code": cip},
                            evidence=f"{version} UNITID {unitid} CIPCODE {cip} AWLEVEL 7")
            if pc is None:
                for other in session.scalars(select(ProgramClassification).where(
                        ProgramClassification.program_id == pid,
                        ProgramClassification.is_primary.is_(True))):
                    other.is_primary = False
                pc = ProgramClassification(program_id=pid, classification_id=cls.id,
                                           is_primary=True, verified=None)
                session.add(pc)
            ctx.put(pc, "verified", new_pc, "primary_classification", program_id=pid)
            if total is None:
                completions = ctx.vv(None, Status.UNKNOWN, evidence="")
                ctx.counts["programs_unknown_completions"] += 1
            elif nonresident is None:
                completions = ctx.vv(
                    {"total": total, "nonresident": None, "year": year},
                    evidence=f"{version} CTOTALT (AWLEVEL 7, majors 1 and 2); CNRALT missing "
                             f"or not reported, nonresident count unknown")
                ctx.counts["programs_unknown_nonresident"] += 1
            else:
                completions = ctx.vv(
                    {"total": total, "nonresident": nonresident, "year": year},
                    evidence=f"{version} CTOTALT, CNRALT (AWLEVEL 7, majors 1 and 2)")
            ctx.put(prog, "academic", completions, "academic.completions",
                    key=("completions",), program_id=pid)
            if total == 0:
                ctx.counts["programs_zero_completions"] += 1
        session.flush()
        n = recompute_stem_eligibilities(session, author=ctx.author, counts=ctx.counts,
                                         subdivision_id=subdivision_id(state))
        ctx.counts["eligibilities_computed"] += n

    return run_step(session, source="ipeds_c_a", files=[path], file_version=version,
                    source_url=DOWNLOAD_PAGE, file_source_url=FILE_URL.format(name=version),
                    scope=subdivision_id(state), work=work)


def _int(raw: str | None) -> int | None:
    """An IPEDS count; None when the cell is missing, empty, "." or not a number."""
    if raw is None:
        return None
    raw = raw.strip()
    if not raw or raw == ".":
        return None
    try:
        return int(float(raw))
    except (ValueError, OverflowError):
        return None


# --------------------------------------------------------------------------- IC_AY


def ingest_ic_ay(session: Session, path: Path, state: str = "TX") -> StepResult:
    """``TUITION7`` -> ``cost.graduate_tuition_nonresident`` on every program of the institution."""
    state = state.upper()
    version = file_version(path)

    def work(ctx: RunContext) -> None:
        insts = institutions_in_state(session, state)
        tuition: dict[str, int | None] = {}
        for r in read_csv_rows(path):
            ctx.counts["rows"] += 1
            if r.get("UNITID") in insts:
                raw = r.get("TUITION7", "")
                try:
                    v = float(raw)
                except ValueError:
                    v = None  # "." = not applicable / missing
                tuition[r["UNITID"]] = round(v) if v and v > 0 else None
        for unitid, inst in insts.items():
            amount = tuition.get(unitid)
            if amount is None:
                new = ctx.vv(None, Status.UNKNOWN, evidence="", note_code=NOTE_TUITION)
                ctx.counts["institutions_without_tuition"] += 1
            else:
                new = ctx.vv({"amount": amount, "currency": "USD"},
                             evidence=f"{version} TUITION7", note_code=NOTE_TUITION)
                ctx.counts["institutions_with_tuition"] += 1
            progs = session.scalars(select(Program).join(Campus).where(
                Campus.institution_id == inst.id))
            for prog in progs:
                ctx.put(prog, "cost", new, "cost.graduate_tuition_nonresident",
                        key=("graduate_tuition_nonresident",), program_id=prog.id)
                ctx.counts["programs_updated"] += 1
        session.flush()

    return run_step(session, source="ipeds_ic_ay", files=[path], file_version=version,
                    source_url=DOWNLOAD_PAGE, file_source_url=FILE_URL.format(name=version),
                    scope=subdivision_id(state), work=work)


def ingest_ipeds_dir(session: Session, directory: Path, state: str = "TX") -> list[StepResult]:
    """HD, then C_A (with its dictionary when present), then IC_AY, from one directory."""
    hd = find_file(directory, r"HD(\d{4})")
    ca = find_file(directory, r"C(\d{4})_A")
    ic = find_file(directory, r"IC(\d{4})_AY")
    try:
        ca_dict: Path | None = find_file(directory, r"C(\d{4})_A_Dict")
    except FileNotFoundError:
        ca_dict = None
    if ca_dict is None:
        xs = [p for p in directory.iterdir() if re.match(r"^c\d{4}_a_dict\.(zip|xlsx)$",
                                                         p.name, re.I)]
        ca_dict = xs[0] if xs else None
    return [ingest_hd(session, hd, state), ingest_c_a(session, ca, state, ca_dict),
            ingest_ic_ay(session, ic, state)]
