"""S-3: reproducible parser for the DHS STEM Designated Degree Program List (PDF).

Usage:
    uv run --with pdfplumber python -I spikes/s3_dhs_stem/parse_stem_list.py \
        spikes/_raw/dhs_stem/stemList2024.pdf \
        --source-url https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf \
        --out-dir data/reference

Outputs:
    <out-dir>/dhs-stem-list-<YYYY-MM-DD>.csv        (cip_code, title, version, level)
    <out-dir>/dhs-stem-list-<YYYY-MM-DD>.meta.json  (url, date, sha256, totals, checks)

Method: the PDF is a 3-column table (2-digit series, 2020 CIP code, title).
Long titles wrap onto lines above and below the code, with the code vertically
centred. Each title line is assigned to the code whose baseline is nearest
(measured gap: own code <= 7.2 pt, neighbour >= 12.5 pt in the 2024 file; the
script fails if any line is ambiguous). The table borders are not used: in this
PDF they do not line up with the text. An independent check (regex over
`pdftotext -layout` output, when available) must yield the same code set.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pdfplumber

CODE_RE = re.compile(r"^\d{2}\.\d{4}$")
DATE_RE = re.compile(r"Last Updated:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", re.I)
# Column limits in PDF points (letter page), measured on the 2024 file.
CODE_MIN_X, TITLE_MIN_X = 140, 210
LINE_TOL = 1.5      # words within this vertical gap are on the same line
MARGIN = 15         # title lines must lie within this distance of the code block
AMBIGUITY_GAP = 1.0  # nearest vs. second-nearest code must differ by at least this
WHOLE_SERIES_RE = re.compile(
    r"designates the following four primary CIP series.*?:(.*?)Any new additions", re.S
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def group_lines(words: list[dict]) -> list[list[dict]]:
    lines: list[list[dict]] = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(lines[-1][0]["top"] - w["top"]) <= LINE_TOL:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [sorted(l, key=lambda w: w["x0"]) for l in lines]


def parse(pdf_path: Path) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    ambiguous: list[str] = []
    info: dict = {}
    with pdfplumber.open(pdf_path) as pdf:
        first_text = pdf.pages[0].extract_text() or ""
        m = DATE_RE.search(first_text)
        if not m:
            sys.exit("'Last Updated' date not found on page 1")
        info["last_updated"] = dt.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
        info["pdf_title"] = (pdf.metadata or {}).get("Title")
        info["pages"] = len(pdf.pages)
        ws = WHOLE_SERIES_RE.search(first_text.replace("\n", " "))
        info["whole_series"] = re.findall(r"\((\d{2})\)", ws.group(1)) if ws else []

        for pno, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
            codes = [w for w in words if CODE_MIN_X <= w["x0"] < TITLE_MIN_X and CODE_RE.match(w["text"])]
            if not codes:
                continue
            lo, hi = min(c["top"] for c in codes) - MARGIN, max(c["top"] for c in codes) + MARGIN
            title_words = [w for w in words if w["x0"] >= TITLE_MIN_X and lo < w["top"] < hi]
            parts: dict[int, list[tuple[float, str]]] = {i: [] for i in range(len(codes))}
            for line in group_lines(title_words):
                top = line[0]["top"]
                dists = sorted((abs(c["top"] - top), i) for i, c in enumerate(codes))
                if len(dists) > 1 and dists[1][0] - dists[0][0] < AMBIGUITY_GAP:
                    ambiguous.append(f"p{pno}: '{' '.join(w['text'] for w in line)}'")
                parts[dists[0][1]].append((top, " ".join(w["text"] for w in line)))
            for i, c in enumerate(codes):
                title = " ".join(t for _, t in sorted(parts[i]))
                rows.append({"cip_code": c["text"], "title": title, "page": pno})
    info["ambiguous_lines"] = ambiguous
    return rows, info


def crosscheck_pdftotext(pdf_path: Path) -> set[str] | None:
    if not shutil.which("pdftotext"):
        return None
    txt = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True, check=True
    ).stdout
    return set(re.findall(r"^\s*\d{2}\s+(\d{2}\.\d{4})", txt, re.M))


def level(code: str, whole_series: list[str]) -> int:
    """2 = heading of a whole series (NN.0000), 4 = 4-digit group heading (NN.NN00),
    6 = 6-digit code. Headings only appear inside the whole series (14, 26, 27, 40);
    elsewhere NN.0000 is a real 6-digit code (e.g. 15.0000, 41.0000)."""
    if code[:2] in whole_series:
        if code.endswith(".0000"):
            return 2
        if code.endswith("00"):
            return 4
    return 6


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    rows, info = parse(args.pdf)
    if info["ambiguous_lines"]:
        sys.exit(f"ambiguous title lines, review the PDF layout: {info['ambiguous_lines']}")
    version = info["last_updated"]

    seen: dict[str, dict] = {}
    dups = []
    for r in rows:
        if r["cip_code"] in seen:
            dups.append(r["cip_code"])
            continue
        seen[r["cip_code"]] = r
    empty = [c for c, r in seen.items() if not r["title"]]

    check = crosscheck_pdftotext(args.pdf)
    cross = None
    if check is not None:
        cross = {
            "pdftotext_codes": len(check),
            "only_in_pdfplumber": sorted(set(seen) - check),
            "only_in_pdftotext": sorted(check - set(seen)),
        }
        if cross["only_in_pdfplumber"] or cross["only_in_pdftotext"]:
            sys.exit(f"code sets differ between extractors: {cross}")

    ws = info["whole_series"]
    if ws != ["14", "26", "27", "40"]:
        print(f"WARNING: whole series changed: {ws}", file=sys.stderr)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_dir / f"dhs-stem-list-{version}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["cip_code", "title", "version", "level"])
        for code in sorted(seen):
            w.writerow([code, seen[code]["title"], version, level(code, ws)])

    by_level = {lv: sum(1 for c in seen if level(c, ws) == lv) for lv in (2, 4, 6)}
    meta = {
        "source": "DHS STEM Designated Degree Program List",
        "source_url": args.source_url,
        "pdf_title": info["pdf_title"],
        "published_on": version,
        "version": version,
        "cip_edition": "CIP 2020",
        "file_sha256": sha256(args.pdf),
        "file_bytes": args.pdf.stat().st_size,
        "pages": info["pages"],
        "total_rows": len(seen),
        "rows_by_level": {"series_2_digit": by_level[2], "group_4_digit": by_level[4], "code_6_digit": by_level[6]},
        "whole_series_included": info["whole_series"],
        "whole_series_note": (
            "These 2-digit series are designated in full; per the PDF text, any new CIP "
            "added to them is automatically on the list. Match them by prefix, not only by listed code."
        ),
        "duplicates_skipped": dups,
        "empty_titles": empty,
        "crosscheck": cross,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "generator": "spikes/s3_dhs_stem/parse_stem_list.py",
    }
    meta_path = args.out_dir / f"dhs-stem-list-{version}.meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("version", "total_rows", "rows_by_level", "file_sha256", "crosscheck", "empty_titles", "duplicates_skipped")}, indent=2))
    print(f"-> {csv_path}\n-> {meta_path}")


if __name__ == "__main__":
    main()
