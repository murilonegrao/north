"""Synthetic ILEP / TrustEd Ireland workbooks for the tests (record 0008, slice E2).

Every provider, title, address and contact is invented (example.com addresses, +353 1 000 ...
numbers); the tests prove the contacts land only in ``institution_contacts`` (record 0009).
The workbook is written with the stdlib (same 15 columns as the official files, title in
row 1, header in row 2).
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

CONTACT_NAME = "Alex Placeholder"
FAKE_EMAIL = "alex.placeholder@example.com"
FAKE_PHONE = "+353 1 000 0000"

HEADER = ["{ref}", "Programme Type", "Provider", "Addresss", "Contact Email",
          "Contact Telephone", "Contact Name", "Programme Title", "Awarding Body", "Award Title",
          "Duration (ECTS /Weeks per year)", "Hours per week", "NFQ Level", "Entry Level",
          "Exit Level"]


def row(ref: str, title: str, *, provider: str = "Example Language School",
        address: str = "1 Example Street, Dublin 2", ptype: str = "English Language",
        body: str = "Cambridge ESOL", award: str = "FCE", duration: str = "25 weeks",
        hours: str = "15 hours", nfq: str = "n/a", entry: str = "B1",
        exit_: str = "B2", contact: tuple[str, str, str] = (CONTACT_NAME, FAKE_EMAIL,
                                                             FAKE_PHONE)) -> list[str]:
    name, email, phone = contact
    return [ref, ptype, provider, address, email, phone, name, title, body,
            award, duration, hours, nfq, entry, exit_]


def write_list(path: Path, rows: list[list[str]], *, trusted: bool = False,
               title: str = "Synthetic list of eligible programmes August 2026") -> Path:
    header = [h.format(ref="Programme Ref:" if trusted else "Programme Reference No")
              for h in HEADER]

    def cell(v: str) -> str:
        return f'<c t="inlineStr"><is><t>{escape(v)}</t></is></c>'

    body = [[title], header, *rows, [""] * len(header)]
    sheet = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/'
             'spreadsheetml/2006/main"><sheetData>'
             + "".join("<row>" + "".join(cell(v) for v in r) + "</row>" for r in body)
             + "</sheetData></worksheet>")
    workbook = ('<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
                'officeDocument/2006/relationships"><sheets><sheet name="List" '
                'sheetId="1" r:id="rId1"/></sheets></workbook>')
    rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/'
            'package/2006/relationships"><Relationship Id="rId1" Type="worksheet" '
            'Target="worksheets/sheet1.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return path


def ilep_v1() -> list[list[str]]:
    """Five English rows (one duplicated reference), one HE row, one foundation row."""
    return [
        row("0901/0001", "General English", entry="Beginner A1.1", exit_="B1",
            body="IELTS", hours="15-20 hours"),
        row("0901/0002", "Intensive English", entry="IELTS 5.5", exit_="Y",
            body="Trinity College London", hours="20 hours", duration="25+ weeks"),
        row("0902/0001", "English for Work", provider="Coastal English College",
            address="9 Harbour Road, Cork City T12 AC34", body="TIE", entry="A2",
            exit_="B2+", hours="21 hours 20 mins"),
        row("0903/0001", "English Plus", provider="Two Towns Academy",
            address="1 Main Street, Bray, Co. Wicklow / 2 Quay Street, Dublin 1",
            body="Pearson", entry="A0/A1", exit_="C1"),
        row("0903/0001", "English Plus Evening", provider="Two Towns Academy",
            address="1 Main Street, Bray, Co. Wicklow / 2 Quay Street, Dublin 1"),
        row("0904/0001", "BA in Example Studies", provider="Example College",
            ptype="Higher education - Major award", duration="180 ECTS", hours="n/a",
            nfq="8", entry="n/a", exit_="n/a"),
        row("0905/0001", "Foundation Year", provider="Example College",
            ptype="Foundation", nfq="n/a"),
    ]


def trusted_v1() -> list[list[str]]:
    """The ILEP 'General English' moved to TrustEd (same provider number and title), plus a
    university language centre course."""
    return [
        row("TE0901/0050", "General  English", entry="CEFR A1 Minimum", exit_="CEFR B1",
            body="IELTS", hours="16+ hours", duration="25+ weeks"),
        row("TE0950/0001", "Academic English", provider="Example University Language Centre",
            address="Example Building, Example University, Galway", body="LanguageCert",
            entry="CEFR B1-B2", exit_="CEFR C1-C2", hours="20+ hours"),
        row("TE0950/0100", "MSc in Examples", provider="Example University",
            ptype="Higher education - Major award", duration="90 ECTS", nfq="9"),
    ]
