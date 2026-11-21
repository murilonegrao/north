"""Minimal reader for the sheets of an IPEDS dictionary workbook (.xlsx), stdlib only.

The workbook is untrusted data (FR-26 uploads): any DOCTYPE or entity declaration aborts the
parse (no entity expansion, no external entities), zip members are size- and ratio-checked,
column and row counts are capped, and only cell values are read.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.parsers import expat

from north.ingest.us.zipguard import read_member

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MAX_PART = 64 << 20
MAX_XLSX = 64 << 20  # the inner .xlsx of a *_Dict.zip
MAX_COLUMNS = 16384  # Excel's limit (XFD)
MAX_ROWS = 2_000_000


def _refuse(name: str):
    def handler(*_args: object) -> None:
        raise ValueError(f"{name} has a DOCTYPE or entity declaration; refusing to parse")
    return handler


def parse_xml(data: bytes, name: str) -> ET.Element:
    """Parse with expat into an ElementTree, aborting on any DOCTYPE or entity declaration."""
    builder = ET.TreeBuilder()
    parser = expat.ParserCreate(namespace_separator="}")

    def qname(n: str) -> str:
        return "{" + n if "}" in n else n

    parser.StartDoctypeDeclHandler = _refuse(name)
    parser.EntityDeclHandler = _refuse(name)
    parser.UnparsedEntityDeclHandler = _refuse(name)
    parser.ExternalEntityRefHandler = _refuse(name)
    parser.StartElementHandler = lambda tag, attrs: builder.start(
        qname(tag), {qname(k): v for k, v in attrs.items()})
    parser.EndElementHandler = lambda tag: builder.end(qname(tag))
    parser.CharacterDataHandler = builder.data
    parser.buffer_text = True
    try:
        parser.Parse(data, True)
    except expat.ExpatError as exc:
        raise ValueError(f"{name}: malformed XML ({exc})") from None
    return builder.close()


def _xml(z: zipfile.ZipFile, name: str) -> ET.Element:
    return parse_xml(read_member(z, name, MAX_PART), name)


def read_sheet(z: zipfile.ZipFile, sheet_name: str) -> list[list[str]]:
    workbook = _xml(z, "xl/workbook.xml")
    rels = _xml(z, "xl/_rels/workbook.xml.rels")
    targets = {r.get("Id"): r.get("Target", "") for r in rels}
    target = None
    for s in workbook.iter(f"{NS}sheet"):
        if (s.get("name") or "").lower() == sheet_name.lower():
            target = targets.get(s.get(f"{REL_NS}id"))
    if not target:
        raise KeyError(f"sheet {sheet_name!r} not found")
    target = target.lstrip("/")
    path = target if target.startswith("xl/") else f"xl/{target}"
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        shared = ["".join(t.text or "" for t in si.iter(f"{NS}t"))
                  for si in _xml(z, "xl/sharedStrings.xml").findall(f"{NS}si")]
    rows: list[list[str]] = []
    for row in _xml(z, path).iter(f"{NS}row"):
        if len(rows) >= MAX_ROWS:
            raise ValueError(f"{path}: more than {MAX_ROWS} rows")
        cells: list[str] = []
        for c in row.findall(f"{NS}c"):
            col = _col_index(c.get("r", ""))
            if (col if col is not None else len(cells)) >= MAX_COLUMNS:
                raise ValueError(f"{path}: column beyond {MAX_COLUMNS}")
            while col is not None and len(cells) < col:
                cells.append("")
            t = c.get("t")
            if t == "inlineStr":
                el = c.find(f"{NS}is")
                val = "".join(x.text or "" for x in el.iter(f"{NS}t")) if el is not None else ""
            else:
                v = c.find(f"{NS}v")
                val = "" if v is None or v.text is None else v.text
                if t == "s" and val:
                    val = shared[int(val)]
            cells.append(val)
        rows.append(cells)
    return rows


def _col_index(ref: str) -> int | None:
    m = re.match(r"([A-Z]+)", ref)
    if not m:
        return None
    if len(m.group(1)) > 3:  # XFD (16384) is the last Excel column
        return MAX_COLUMNS
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def value_labels(path: Path, sheet: str = "Frequencies") -> dict[str, dict[str, str]]:
    """``{VarName: {CodeValue: ValueLabel}}`` from the Frequencies sheet of an IPEDS dictionary.

    ``path`` is the ``*_Dict.zip`` as downloaded (it holds one .xlsx) or the .xlsx itself.
    """
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as outer:
            inner = next(n for n in outer.namelist() if n.lower().endswith(".xlsx"))
            with zipfile.ZipFile(io.BytesIO(read_member(outer, inner, MAX_XLSX))) as z:
                rows = read_sheet(z, sheet)
    else:
        with zipfile.ZipFile(path) as z:
            rows = read_sheet(z, sheet)
    header = [h.strip().lower() for h in rows[0]]
    iv, ic, il = header.index("varname"), header.index("codevalue"), header.index("valuelabel")
    out: dict[str, dict[str, str]] = {}
    for r in rows[1:]:
        if len(r) > max(iv, ic, il):
            out.setdefault(r[iv].strip().upper(), {})[r[ic].strip()] = r[il].strip()
    return out
