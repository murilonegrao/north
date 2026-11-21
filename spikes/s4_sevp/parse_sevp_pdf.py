"""S-4: parse the SEVP Certified School List PDF into CSV.

The only bulk file SEVP publishes is a PDF ("Download Certified School List" on
https://studyinthestates.dhs.gov/school-search). It is an Excel sheet printed
with "Microsoft: Print To PDF", so long names are truncated at the cell border.

Usage:
    uv run --with pdfplumber python -I spikes/s4_sevp/parse_sevp_pdf.py \
        spikes/_raw/sevp/certified-school-list-11-18-26.pdf \
        spikes/_raw/sevp/derived/sevp-certified-schools-2026-11-18.csv

Columns: school_name, campus_name, f_1, m_1, city, state, campus_code, school_code
  campus_code  = SEVIS code printed in the PDF (e.g. DAL214F00932000)
  school_code  = first 12 characters of campus_code (inferred; the last 3 digits
                 number the campus, 000 being the first one)
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import pdfplumber

CODE_RE = re.compile(r"^[A-Z]{3}214[FM]\d{8}$")
# Column limits in PDF points, measured on the 2026-11-18 file.
CAMPUS_MIN, CAMPUS_X, CITY_MIN, STATE_MIN, CODE_MIN = 243, 245.9, 414, 487, 512
NOISE_RE = re.compile(r"SEVP Certified Schools|SCHOOL NAME|^Updated|^[A-Z][a-z]+ \d{1,2}, \d{4}$|^Page \d+ of \d+$")
LINE_TOL = 2.0


def text_of(chars: list[dict]) -> str:
    """Rebuild text from chars, inserting a space where there is a visual gap."""
    out, prev = [], None
    for c in sorted(chars, key=lambda c: c["x0"]):
        if prev is not None and c["x0"] - prev["x1"] > 1.2 and not out[-1].endswith(" "):
            out.append(" ")
        out.append(c["text"])
        prev = c
    return re.sub(r"\s+", " ", "".join(out)).strip()


def split_line(chars: list[dict]) -> dict:
    """Split one printed row into columns.

    `chars` must be in content-stream order. Excel prints each cell as a run, in
    column order, and does not clip overflowing text in a way pdfplumber sees, so
    a long campus name can run over the F/M columns (and a long city under ST).
    Columns are therefore cut by stream order, and overflow is clipped at the
    next column, which reproduces what the printed page shows.
    """
    chars = [c for c in chars if c["text"].strip()]
    # Flags: a Y/N pair at the F/M columns, followed by the first CITY char.
    # Take the last such pair, because overflowing campus text can sit there too.
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
    # The campus run starts exactly at the campus column's left edge (x=245.9);
    # an overflowing school name does not land on that exact position.
    cut = len(head)
    for i in range(1, len(head)):
        c, prev = head[i], head[i - 1]
        if abs(c["x0"] - CAMPUS_X) < 0.3:
            cut = i
            break
    school, campus = head[:cut], head[cut:]
    return {
        "school_name": text_of([c for c in school if c["x1"] <= CAMPUS_MIN + 1]),
        "campus_name": text_of([c for c in campus if c["x1"] <= clip + 1]),
        "f_1": f,
        "m_1": m,
        **split_tail(tail),
    }


def split_tail(tail: list[dict]) -> dict:
    """CITY, ST, CAMPUS CODE by stream order: the code is the last 15 chars and
    the state the 2 chars before it; a long city name can run under ST, so the
    city is clipped at the ST column."""
    code = "".join(c["text"] for c in tail[-15:])
    st = "".join(c["text"] for c in tail[-17:-15])
    if CODE_RE.match(code) and re.fullmatch(r"[A-Z]{2}", st):
        return {
            "city": text_of([c for c in tail[:-17] if c["x1"] <= STATE_MIN + 1]),
            "state": st,
            "campus_code": code,
        }
    return {  # fallback by position
        "city": text_of([c for c in tail if CITY_MIN <= c["x0"] < STATE_MIN]),
        "state": text_of([c for c in tail if STATE_MIN <= c["x0"] < CODE_MIN]),
        "campus_code": text_of([c for c in tail if c["x0"] >= CODE_MIN]),
    }


def lines_of(page) -> list[list[dict]]:
    """Group chars into printed lines; keep content-stream order inside a line."""
    indexed = list(enumerate(page.chars))
    groups: list[list[tuple[int, dict]]] = []
    for i, c in sorted(indexed, key=lambda t: (t[1]["top"], t[0])):
        if groups and abs(groups[-1][0][1]["top"] - c["top"]) <= LINE_TOL:
            groups[-1].append((i, c))
        else:
            groups.append([(i, c)])
    return [[c for _, c in sorted(g, key=lambda t: t[0])] for g in groups]


def main() -> None:
    pdf_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    rows: list[dict] = []
    orphans: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        pending: list[dict] = []
        for page in pdf.pages:
            for line in lines_of(page):
                full = text_of(line)
                if not full or NOISE_RE.search(full):
                    continue
                parts = split_line(line)
                if CODE_RE.match(parts["campus_code"]):
                    for p in pending:  # wrapped text printed above the row
                        for k in ("school_name", "campus_name", "city"):
                            if p[k]:
                                parts[k] = (p[k] + " " + parts[k]).strip()
                    pending = []
                    rows.append(parts)
                else:
                    pending.append(parts)
        if pending:
            orphans = [" | ".join(v for v in p.values() if v) for p in pending]

    for r in rows:
        r["school_code"] = r["campus_code"][:12]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["school_name", "campus_name", "f_1", "m_1", "city", "state", "campus_code", "school_code"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    codes = [r["campus_code"] for r in rows]
    bad_flags = sum(1 for r in rows if r["f_1"] not in "YN" or r["m_1"] not in "YN" or not r["f_1"] or not r["m_1"])
    print(f"rows={len(rows)} unique_campus_codes={len(set(codes))} unique_school_codes={len({r['school_code'] for r in rows})}")
    print(f"rows_without_F/M_flags={bad_flags} empty_school_name={sum(1 for r in rows if not r['school_name'])} empty_state={sum(1 for r in rows if not r['state'])}")
    print(f"orphan_lines_after_last_row={orphans}")
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
