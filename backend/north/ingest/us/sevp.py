"""SEVP certified school list -> ``campuses.intl_authorization`` (record 0002/R5, K7).

1. A campus whose ``sevp_campus_code`` is known is matched by that code.
2. Otherwise an exact normalized name + city match (one SEVP campus, code not taken) is
   accepted automatically and the code is stored on the campus.
3. Anything else becomes a reconciliation task with candidates; nothing is written.
A campus matched before but missing now gets a task and keeps its value ("never not
certified"). The 12-character SEVP school code is not unique and is never an identifier.
Name-to-name matching is a US-specific exception and stays in this module.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from north.domain.verified import Status
from north.ingest.us.common import RunContext, StepResult, run_step, subdivision_id
from north.ingest.us.sevp_pdf import (
    SevpCampus,
    check_rows,
    date_from_filename,
    parse_pdf,
    read_csv,
)
from north.repository.models import Campus, Institution

DOWNLOAD_PAGE = "https://studyinthestates.dhs.gov/school-search"

STOP = {"the", "inc", "llc", "corp", "corporation", "dba", "of", "at", "in", "campus", "main",
        "and"}
ABBR = {"univ": "university", "u": "university", "coll": "college", "cc": "community college",
        "comm": "community", "tech": "technology", "inst": "institute",
        "intl": "international", "ctr": "center", "sch": "school", "schl": "school",
        "sci": "science", "sciences": "science", "hlth": "health", "med": "medical",
        "ft": "fort", "mt": "mount", "saint": "st"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks: list[str] = []
    for t in s.split():
        toks.extend(ABBR.get(t, t).split())
    return " ".join(t for t in toks if t not in STOP)


def norm_city(s: str) -> str:
    return norm(s).replace("saint ", "st ")


def _strip_place(name: str, city: str, state: str) -> str:
    out = f" {name} "
    if city:
        out = out.replace(f" {city} ", " ")
    out = out.replace(f" {state.lower()} ", " ")
    return " ".join(out.split())


def _variants(raws: Iterable[str], city: str, state: str) -> set[str]:
    names = {norm(r) for r in raws}
    names |= {norm(re.split(r"[(,]", r)[0]) for r in raws}
    names |= {_strip_place(n, city, state) for n in list(names)}
    return {n for n in names if n}


def campus_names(c: SevpCampus) -> set[str]:
    """Names that identify this SEVP campus itself (not the school it belongs to)."""
    return _variants([c.campus_name], norm(c.city), c.state)


def sevp_names(c: SevpCampus) -> set[str]:
    raws = [c.school_name, c.campus_name, f"{c.school_name} {c.campus_name}"]
    return _variants(raws, norm(c.city), c.state)


def ipeds_names(name: str) -> set[str]:
    return {n for n in (norm(name), norm(name.split("-")[0])) if n}


def _similarity(a: str, b: str) -> float:
    return 100 * difflib.SequenceMatcher(None, " ".join(sorted(a.split())),
                                         " ".join(sorted(b.split()))).ratio()


def candidates_for(names: set[str], city: str, sevp: Iterable[tuple[SevpCampus, set[str], str]],
                   limit: int = 3) -> list[dict]:
    """Best SEVP suggestions for a campus (exact name in another city, or similar names)."""
    scored = []
    for c, c_names, c_city in sevp:
        best = max((100.0 if a == b else _similarity(a, b)) for a in names for b in c_names)
        if best >= 80:
            scored.append((best, c_city == city, c))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [{"sevp_campus_code": c.campus_code, "school_name": c.school_name,
             "campus_name": c.campus_name, "city": c.city, "state": c.state, "f_1": c.f_1,
             "score": round(score, 1), "same_city": same}
            for score, same, c in scored[:limit]]


def ingest_sevp(session: Session, path: Path, state: str = "TX") -> StepResult:
    """``path`` is the official PDF, or the CSV derived from it by the spike parser."""
    state = state.upper()
    is_pdf = path.suffix.lower() == ".pdf"
    version = date_from_filename(path) or path.stem

    def work(ctx: RunContext) -> None:
        if is_pdf:
            rows, updated = parse_pdf(path)
            if updated and updated != ctx.source_file.file_version:
                ctx.source_file.file_version = updated
        else:
            rows = list(read_csv(path))
            check_rows(rows)
        list_date = ctx.source_file.file_version
        ctx.counts["rows"] = len(rows)
        in_state = [r for r in rows if r.state == state]
        ctx.counts["sevp_campuses_in_state"] = len(in_state)
        by_code = {r.campus_code: r for r in rows}
        prepared = [(r, sevp_names(r), norm_city(r.city)) for r in in_state]
        # Two exact indexes: by the campus's own name (strong), and by any name variant
        # including the school name shared by every campus of a school (weak).
        strong: dict[tuple[str, str], list[SevpCampus]] = defaultdict(list)
        weak: dict[tuple[str, str], list[SevpCampus]] = defaultdict(list)
        for r, names, city in prepared:
            for n in names:
                weak[(n, city)].append(r)
            for n in campus_names(r):
                strong[(n, city)].append(r)

        campuses = session.execute(
            select(Campus, Institution).join(Institution)
            .where(Institution.subdivision_id == subdivision_id(state))
            .order_by(Institution.id, Campus.id)).all()
        taken = {c.sevp_campus_code for c, _ in campuses if c.sevp_campus_code}
        for campus, inst in campuses:
            ctx.counts["campuses"] += 1
            subject = {"institution_id": inst.id, "campus_id": campus.id,
                       "name": campus.name, "city": campus.city}
            names, city = ipeds_names(campus.name), norm_city(campus.city or "")
            if campus.sevp_campus_code:
                match = by_code.get(campus.sevp_campus_code)
                if match is None:
                    ctx.task("sevp_missing",
                             f"{inst.id} {campus.name}: campus code {campus.sevp_campus_code} "
                             f"is not in the SEVP list of {list_date}; value kept",
                             [subject])
                    continue
                how = "campus code"
            else:
                free: dict[str, SevpCampus] = {}
                hits: dict[str, SevpCampus] = {}
                for idx in (strong, weak):
                    hits = {r.campus_code: r for n in names for r in idx.get((n, city), [])}
                    free = {k: v for k, v in hits.items() if k not in taken}
                    if free:
                        break
                if len(free) != 1:
                    why = ("several exact name + city matches" if len(free) > 1 else
                           "matching campus code already linked to another campus" if hits else
                           "no exact name + city match")
                    ctx.task("sevp_match", f"{inst.id} {campus.name} ({campus.city}): {why}",
                             [subject, *candidates_for(names, city, prepared)])
                    continue
                match = next(iter(free.values()))
                ctx.set_attr(campus, "sevp_campus_code", match.campus_code,
                             f"campus[{campus.id}].sevp_campus_code")
                taken.add(match.campus_code)
                how = "exact name and city"
                ctx.counts["matched_exact"] += 1
            ctx.counts["matched"] += 1
            # Only an explicit "N" is a negative (BR-02); anything but Y/N is unknown.
            if match.f_1 not in ("Y", "N"):
                ctx.task("sevp_flag",
                         f"{inst.id} {campus.name}: F-1 flag {match.f_1!r} for campus code "
                         f"{match.campus_code} in the SEVP list of {list_date}; not written",
                         [subject, {"sevp_campus_code": match.campus_code, "f_1": match.f_1}])
                ctx.counts["f1_flag_unknown"] += 1
                continue
            authorized = match.f_1 == "Y"
            new = ctx.vv({"scheme": "sevp", "authorized": authorized},
                         Status.CONFIRMED_OFFICIAL if authorized else Status.CONFIRMED_NEGATIVE,
                         evidence=f"SEVP certified school list {list_date}: {match.school_name}"
                                  f" / {match.campus_name}, {match.city} {match.state}, "
                                  f"F-1 {match.f_1} (matched by {how})")
            ctx.put(campus, "intl_authorization", new, f"campus[{campus.id}].intl_authorization")
            ctx.counts["authorized" if authorized else "not_authorized_f1"] += 1
        session.flush()

    return run_step(session, source="sevp_csl", files=[path], file_version=version,
                    source_url=DOWNLOAD_PAGE, scope=subdivision_id(state), work=work)
