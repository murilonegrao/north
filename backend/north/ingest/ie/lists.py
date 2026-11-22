"""Reader for the ILEP and TrustEd Ireland XLSX lists (same 15 columns; FR-26, FR-30, FR-31).

The workbook is untrusted data and is read with the hardened stdlib reader (no entities, zip
members size-checked). Rows are projected to a whitelist of columns as they are read. The
"Contact Email", "Contact Telephone" and "Contact Name" columns name staff: they never enter a
``ListRow`` (whose text feeds evidence, tasks and logs) but a separate ``Contact`` whose repr
hides the values; the loader stores them only in ``institution_contacts`` (record 0009). The
address is kept only long enough to derive the town and county.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from north.ingest.ie.parse import clean
from north.ingest.us.xlsx import MAX_PART, NS, parse_xml, read_sheet
from north.ingest.us.zipguard import read_member

# Field -> accepted header spellings (lower case, single spaces). Contact columns are absent
# on purpose: a header not listed here is dropped.
COLUMNS: dict[str, tuple[str, ...]] = {
    "ref": ("programme reference no", "programme ref:", "programme ref", "programme reference"),
    "programme_type": ("programme type",),
    "provider": ("provider",),
    "address": ("addresss", "address"),
    "title": ("programme title",),
    "awarding_body": ("awarding body",),
    "award_title": ("award title",),
    "duration": ("duration (ects /weeks per year)", "duration (ects / weeks per year)",
                 "duration"),
    "hours": ("hours per week",),
    "nfq": ("nfq level",),
    "entry": ("entry level",),
    "exit": ("exit level",),
}
REQUIRED = ("ref", "programme_type", "provider", "title")
# Private columns (record 0009): read into Contact, never into ListRow.
CONTACT_COLUMNS: dict[str, tuple[str, ...]] = {
    "name": ("contact name",), "email": ("contact email",), "phone": ("contact telephone",),
}


@dataclass(frozen=True)
class Contact:
    """A row's contact person. ``repr`` shows no value, so a log line or a traceback that
    prints it leaks nothing."""

    name: str = field(repr=False)
    email: str = field(repr=False)
    phone: str = field(repr=False)

    def __bool__(self) -> bool:
        return bool(self.name or self.email or self.phone)


@dataclass(frozen=True)
class ListRow:
    """One programme row, without the contact columns."""

    line: int  # spreadsheet row number, for error messages
    ref: str
    programme_type: str
    provider: str
    address: str
    title: str
    awarding_body: str
    award_title: str
    duration: str
    hours: str
    nfq: str
    entry: str
    exit: str

    @property
    def kind(self) -> str:
        """english, higher_education, foundation, professional or other."""
        t = self.programme_type.lower()
        if "english" in t:
            return "english"
        if "foundation" in t:
            return "foundation"
        if "professional" in t:
            return "professional"
        if "higher" in t or "major" in t:
            return "higher_education"
        return "other"


@dataclass(frozen=True)
class ListFile:
    title: str
    first_header: str
    rows: list[ListRow]
    # Spreadsheet row number -> contact (record 0009); private, see Contact.
    contacts: dict[int, Contact] = field(default_factory=dict, repr=False)


def _first_sheet(z: zipfile.ZipFile) -> str:
    workbook = parse_xml(read_member(z, "xl/workbook.xml", MAX_PART), "xl/workbook.xml")
    sheet = next(workbook.iter(f"{NS}sheet"), None)
    if sheet is None or not sheet.get("name"):
        raise ValueError("the workbook has no sheet")
    return str(sheet.get("name"))


def _norm_header(h: str) -> str:
    return clean(h).lower()


def read_list(path: Path) -> ListFile:
    try:
        with zipfile.ZipFile(path) as z:
            cells = read_sheet(z, _first_sheet(z))
    except zipfile.BadZipFile:
        raise ValueError(f"{path.name}: not an xlsx file") from None
    header_at = next((n for n, row in enumerate(cells[:10])
                      if "programme title" in {_norm_header(c) for c in row}), None)
    if header_at is None:
        raise ValueError(f"{path.name}: no header row with 'Programme Title'")
    header = [_norm_header(c) for c in cells[header_at]]
    index: dict[str, int] = {}
    for name, names in COLUMNS.items():
        for n, h in enumerate(header):
            if h in names:
                index[name] = n
                break
    contact_index = {f: n for f, names in CONTACT_COLUMNS.items()
                     for n, h in enumerate(header) if h in names}
    missing = [f for f in REQUIRED if f not in index]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")
    title = clean(cells[0][0]) if header_at > 0 and cells[0] else ""
    rows: list[ListRow] = []
    contacts: dict[int, Contact] = {}
    for n, raw in enumerate(cells[header_at + 1:], start=header_at + 2):
        values = {f: clean(raw[i]) if i < len(raw) else "" for f, i in index.items()}
        if not any(values.values()):
            continue
        rows.append(ListRow(line=n, **{f: values.get(f, "") for f in COLUMNS}))
        person = Contact(**{f: clean(raw[contact_index[f]])
                            if f in contact_index and contact_index[f] < len(raw) else ""
                            for f in CONTACT_COLUMNS})
        if person:
            contacts[n] = person
    del cells
    return ListFile(title=title, first_header=header[index["ref"]], rows=rows,
                    contacts=contacts)


_DATE_IN_NAME = re.compile(r"(\d{1,2})[-_ ]([A-Za-z]+)[-_ ](\d{4})")
_DATE_IN_TITLE = re.compile(r"(\d{1,2}) ([A-Za-z]+) (\d{4})")
_MONTH_IN_TITLE = re.compile(r"\b([A-Za-z]+) (\d{4})\s*$")
MONTHS = {m: n for n, m in enumerate(
    ("january", "february", "march", "april", "may", "june", "july", "august", "september",
     "october", "november", "december"), start=1)}


def file_version(name: str, title: str) -> str:
    """Version of a list file: the date in its name ('...updated-22-September-2026.xlsx'),
    else the date or month in the sheet title ('... August 2026'), else the file stem."""
    for rx, text in ((_DATE_IN_NAME, name), (_DATE_IN_TITLE, title)):
        m = rx.search(text)
        if m and m.group(2).lower() in MONTHS:
            return f"{m.group(3)}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    m = _MONTH_IN_TITLE.search(title)
    if m and m.group(1).lower() in MONTHS:
        return f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}"
    return Path(name).stem
