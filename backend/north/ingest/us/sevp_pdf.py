"""Parser for the SEVP Certified School List PDF (port of ``spikes/s4_sevp/parse_sevp_pdf.py``).

The only bulk file SEVP publishes is a PDF printed from Excel ("Microsoft: Print To PDF"),
so long names are truncated at the cell border. Columns are split by content-stream order
(school run, campus run, F, M, city; the state is the 2 characters before the 15-character
campus code), and overflow is clipped at the next column, as the printed page shows it.
"""

from __future__ import annotations

import csv
import datetime as dt
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

CODE_RE = re.compile(r"^[A-Z]{3}214[FM]\d{8}$")
# Column limits in PDF points, measured on the 2026-11-18 file.
CAMPUS_MIN, CAMPUS_X, CITY_MIN, STATE_MIN, CODE_MIN = 243, 245.9, 414, 487, 512
NOISE_RE = re.compile(r"SEVP Certified Schools|SCHOOL NAME|^Updated|^[A-Z][a-z]+ \d{1,2}, \d{4}$"
                      r"|^Page \d+ of \d+$")
UPDATED_RE = re.compile(r"Updated\s+([A-Z][a-z]+ \d{1,2}, \d{4})")
FILENAME_DATE_RE = re.compile(r"(\d{1,2})-(\d{1,2})-(\d{2,4})")
LINE_TOL = 2.0
COLUMNS = ("school_name", "campus_name", "f_1", "m_1", "city", "state", "campus_code")
# Limits for an uploaded file (FR-26): the 2026-11-18 list has 151 pages and about 1.5 MB.
MAX_PDF_BYTES = 100 << 20
MAX_PDF_PAGES = 1000
# Rows whose F/M flags are not Y/N tolerated before the whole file is refused (also 1%).
MAX_BAD_FLAG_ROWS = 3


@dataclass(frozen=True)
class SevpCampus:
    school_name: str
    campus_name: str
    f_1: str
    m_1: str
    city: str
    state: str
    campus_code: str


def _text_of(chars: list[dict]) -> str:
    out: list[str] = []
    prev = None
    for c in sorted(chars, key=lambda c: c["x0"]):
        if prev is not None and c["x0"] - prev["x1"] > 1.2 and not out[-1].endswith(" "):
            out.append(" ")
        out.append(c["text"])
        prev = c
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _split_tail(tail: list[dict]) -> dict[str, str]:
    code = "".join(c["text"] for c in tail[-15:])
    st = "".join(c["text"] for c in tail[-17:-15])
    if CODE_RE.match(code) and re.fullmatch(r"[A-Z]{2}", st):
        return {"city": _text_of([c for c in tail[:-17] if c["x1"] <= STATE_MIN + 1]),
                "state": st, "campus_code": code}
    return {"city": _text_of([c for c in tail if CITY_MIN <= c["x0"] < STATE_MIN]),
            "state": _text_of([c for c in tail if STATE_MIN <= c["x0"] < CODE_MIN]),
            "campus_code": _text_of([c for c in tail if c["x0"] >= CODE_MIN])}


def _split_line(chars: list[dict]) -> dict[str, str]:
    chars = [c for c in chars if c["text"].strip()]
    flag_i = None
    for i in range(len(chars) - 1):
        a, b = chars[i], chars[i + 1]
        nxt = chars[i + 2] if i + 2 < len(chars) else None
        if (a["text"] in "YN" and b["text"] in "YN" and 380 <= a["x0"] < 398
                and 398 <= b["x0"] < CITY_MIN and (nxt is None or nxt["x0"] >= CITY_MIN)):
            flag_i = i
    f = m = ""
    clip = CITY_MIN
    if flag_i is not None:
        f, m = chars[flag_i]["text"], chars[flag_i + 1]["text"]
        clip = chars[flag_i]["x0"]
        head, tail = chars[:flag_i], chars[flag_i + 2:]
    else:
        city_idx = next((i for i, c in enumerate(chars) if c["x0"] >= CITY_MIN), len(chars))
        head, tail = chars[:city_idx], chars[city_idx:]
    cut = len(head)
    for i in range(1, len(head)):
        if abs(head[i]["x0"] - CAMPUS_X) < 0.3:
            cut = i
            break
    school, campus = head[:cut], head[cut:]
    return {"school_name": _text_of([c for c in school if c["x1"] <= CAMPUS_MIN + 1]),
            "campus_name": _text_of([c for c in campus if c["x1"] <= clip + 1]),
            "f_1": f, "m_1": m, **_split_tail(tail)}


def _lines_of(page) -> list[list[dict]]:
    indexed = list(enumerate(page.chars))
    groups: list[list[tuple[int, dict]]] = []
    for i, c in sorted(indexed, key=lambda t: (t[1]["top"], t[0])):
        if groups and abs(groups[-1][0][1]["top"] - c["top"]) <= LINE_TOL:
            groups[-1].append((i, c))
        else:
            groups.append([(i, c)])
    return [[c for _, c in sorted(g, key=lambda t: t[0])] for g in groups]


def parse_pdf(path: Path) -> tuple[list[SevpCampus], str | None]:
    """All campuses of the list and the "Updated <date>" of the page header (ISO), if found."""
    import pdfplumber  # heavy import, only when a PDF is parsed

    size = path.stat().st_size
    if size > MAX_PDF_BYTES:
        raise ValueError(f"{path.name}: {size} bytes, over the {MAX_PDF_BYTES} byte limit")
    rows: list[dict[str, str]] = []
    updated: str | None = None
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) > MAX_PDF_PAGES:
            raise ValueError(f"{path.name}: {len(pdf.pages)} pages, over the {MAX_PDF_PAGES} "
                             f"page limit")
        pending: list[dict[str, str]] = []
        for n, page in enumerate(pdf.pages):
            if n == 0:
                m = UPDATED_RE.search(page.extract_text() or "")
                if m:
                    updated = dt.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
            for line in _lines_of(page):
                full = _text_of(line)
                if not full or NOISE_RE.search(full):
                    continue
                parts = _split_line(line)
                if CODE_RE.match(parts["campus_code"]):
                    for p in pending:  # wrapped text printed above the row
                        for k in ("school_name", "campus_name", "city"):
                            if p[k]:
                                parts[k] = (p[k] + " " + parts[k]).strip()
                    pending = []
                    rows.append(parts)
                else:
                    pending.append(parts)
            page.flush_cache()
    campuses = [SevpCampus(**{k: r[k] for k in COLUMNS}) for r in rows]
    check_rows(campuses)
    return campuses, updated


def check_rows(campuses: list[SevpCampus]) -> None:
    """Reject a list whose shape is wrong (PDF layout change, a hand-edited or truncated CSV).

    A few rows with an F/M flag other than Y/N are data, not a layout change: they pass here
    and the ingestion treats their flag as unknown. Many such rows mean the columns moved.
    """
    if not campuses:
        raise ValueError("no campus rows found; has the PDF layout changed?")
    codes = [c.campus_code for c in campuses]
    if len(set(codes)) != len(codes):
        raise ValueError("duplicate campus codes; has the PDF layout changed?")
    bad_codes = sum(1 for code in codes if not CODE_RE.match(code))
    if bad_codes:
        raise ValueError(f"{bad_codes} rows with a malformed campus code; has the layout changed?")
    bad_states = sum(1 for c in campuses if not re.fullmatch(r"[A-Z]{2}", c.state))
    if bad_states:
        raise ValueError(f"{bad_states} rows with a malformed state; has the layout changed?")
    bad = sum(1 for c in campuses if c.f_1 not in ("Y", "N") or c.m_1 not in ("Y", "N"))
    if bad > max(MAX_BAD_FLAG_ROWS, len(campuses) // 100):
        raise ValueError(f"{bad} rows without F/M flags; has the PDF layout changed?")


def read_csv(path: Path) -> Iterator[SevpCampus]:
    """Rows of the CSV written by the spike parser (same columns)."""
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            yield SevpCampus(**{k: (r.get(k) or "").strip() for k in COLUMNS})


def date_from_filename(path: Path) -> str | None:
    """certified-school-list-11-18-26.pdf -> 2026-11-18; also ISO dates in the name."""
    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", path.name)
    if iso:
        return iso.group(0)
    m = FILENAME_DATE_RE.search(path.name)
    if not m:
        return None
    month, day, year = (int(x) for x in m.groups())
    year = year + 2000 if year < 100 else year
    try:
        return dt.date(year, month, day).isoformat()
    except ValueError:
        return None
