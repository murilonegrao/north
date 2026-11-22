"""Parsers and reader of the Irish lists (FR-30), no database."""

from __future__ import annotations

import csv
from dataclasses import fields
from pathlib import Path

import pytest

from north.ingest.ie.jobs import recognise
from north.ingest.ie.lists import ListRow, file_version, read_list
from north.ingest.ie.parse import (
    EXAM_CODES,
    ExamMap,
    Place,
    norm_title,
    parse_cefr,
    parse_hours,
    parse_ref,
    parse_weeks,
    place_of,
    scrub,
)
from tests.conftest import REPO
from tests.ie_lists import CONTACT_NAME, FAKE_EMAIL, FAKE_PHONE, ilep_v1, trusted_v1, write_list

EXAM_CSV = REPO / "data" / "reference" / "ie_exam_names.csv"


@pytest.mark.parametrize(("raw", "weeks"), [
    ("25 weeks", 25), ("25+ weeks ", 25), ("25-28 weeks", 25), ("25 week minimum", 25),
    ("25 weeks (+holidays)", 25), ("25", 25), ("26 Weeks", 26),
    ("", None), ("60 ECTS", None), ("n/a", None), ("Research", None), ("2.5 weeks", None),
])
def test_parse_weeks(raw: str, weeks: int | None) -> None:
    assert parse_weeks(raw) == weeks


@pytest.mark.parametrize(("raw", "hours"), [
    ("15 hours", 15), ("15", 15), ("15hrs", 15), ("18.33 hours", 18.33), ("15-20 hours", 15),
    ("15 - 22.5 hours", 15), ("16+ hours", 16), ("21 hours 20 mins ", 21.33),
    ("15 mornings only. 25 including afternoons ", 15), ("18hrs, 20 hrs", 18),
    ("15 hours & 20 hours", 15), ("", None), ("n/a", None), ("0.5", None), ("200 hours", None),
])
def test_parse_hours(raw: str, hours: float | None) -> None:
    assert parse_hours(raw) == hours


@pytest.mark.parametrize(("raw", "bands"), [
    ("B1", ("B1", "B1")), ("A2+", ("A2", "A2")), ("Beginner A1.1", ("A1", "A1")),
    ("A1 / A2 / B1 / B2 / C1", ("A1", "C1")), ("A2-C1", ("A2", "C1")),
    ("CEFRL B2", ("B2", "B2")), ("CEFR: B1", ("B1", "B1")), ("A0/A1", ("A0", "A1")),
    ("4.5 / B1", ("B1", "B1")), ("B1-C2 depending on length of course", ("B1", "C2")),
    ("ISE Pass B2", ("B2", "B2")), ("From A2 Pre-Intermediate to C1 Advanced", ("A2", "C1")),
    ("IELTS 5.5", (None, None)), ("Beginner", (None, None)), ("B+", (None, None)),
    ("Y", (None, None)), ("6.5", (None, None)), ("n/a", (None, None)), ("", (None, None)),
])
def test_parse_cefr(raw: str, bands: tuple[str | None, str | None]) -> None:
    assert parse_cefr(raw) == bands


@pytest.mark.parametrize(("address", "place"), [
    ("1 Example Street, Dublin 2", Place("Dublin", "D")),
    ("33 / 34 Example Street, Dublin 2", Place("Dublin", "D")),
    ("Block B, Example Street, Dublin 1 D01X997", Place("Dublin", "D")),
    ("29/30 Dublin Road, Bray, Co. Wicklow", Place("Bray", "WW")),
    ("1 Example Park, Dun Laoghaire, Co. Dublin", Place("Dun Laoghaire", "D")),
    ("2 Example Street Cork City T12 KP40", Place("Cork", "CO")),
    ("Example Road, Limerick City, Limerick", Place("Limerick", "LK")),
    ("1A Main Street, Naas. Co. Kildare", Place("Naas", "KE")),
    ("Upper Example Street, Y35TH2A, Wexford Town", Place("Wexford", "WX")),
    ("Example Lane, Example Abbey Dublin 7 (Main centre) / 39 Example Square, Dublin 1",
     Place("Dublin", "D")),
    # Several towns: no city; one county only when every site is in it.
    ("1 Main Street, Bray, Co. Wicklow / 2 Quay Street, Dublin 1", Place(None, None)),
    ("Example Campus, Ballinode, Co. Sligo", Place(None, "SO")),
    ("West End, Budoran, Co. Donegal", Place(None, "DL")),  # a typo is not guessed
    ("", Place(None, None)),
])
def test_place_of(address: str, place: Place) -> None:
    assert place_of(address) == place


def test_refs_titles_and_scrub() -> None:
    assert parse_ref("0018/0001").provider_no == "0018"  # type: ignore[union-attr]
    te = parse_ref("TE0058/0012")
    assert te is not None and te.trusted and te.provider_no == "0058" and te.value == "TE0058/0012"
    assert parse_ref("0123/012") is not None
    assert parse_ref("TE58/1") is None and parse_ref("") is None
    assert norm_title("General  English & IELTS!") == norm_title("general english and ielts")
    assert "@" not in scrub(f"note {FAKE_EMAIL}") and "000 0000" not in scrub(f"call {FAKE_PHONE}")
    assert scrub('ILEP 2026-09-22, 0018/0001: Hours per week "15-20 hours"').endswith('hours"')


def test_exam_map_covers_every_code_and_spelling() -> None:
    with EXAM_CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows and {r["exam"] for r in rows} <= set(EXAM_CODES)
    exams = ExamMap.load(EXAM_CSV)
    assert exams.code("Cambridge ESOL") == "cambridge"
    assert exams.code(" cambridge  esol ") == "cambridge"  # case and spaces do not matter
    assert exams.code("IELT") == "tie" and exams.code("IELTS") == "ielts"
    assert exams.code("Trinity College London") == "trinity"
    assert exams.code("Language Cert") == "languagecert" and exams.code("Pearson") == "pte"
    assert exams.code("Oxford University Press") == "other"
    assert exams.code("Some New Board") is None  # unknown spelling: never guessed


def test_exam_map_rejects_unknown_codes(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("raw,exam,note\nX,ielts_academic,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown exam code"):
        ExamMap.load(bad)


def test_reader_keeps_contacts_out_of_rows(tmp_path: Path) -> None:
    """Contacts are read apart from the row (record 0009) and never printed."""
    listed = read_list(write_list(tmp_path / "ilep.xlsx", ilep_v1()))
    assert len(listed.rows) == 7 and listed.first_header == "programme reference no"
    names = {f.name for f in fields(ListRow)}
    assert not names & {"contact_email", "contact_telephone", "contact_name", "email", "phone"}
    for r in listed.rows:
        text = repr(r)
        assert CONTACT_NAME not in text and FAKE_EMAIL not in text and FAKE_PHONE not in text
    person = listed.contacts[listed.rows[0].line]
    assert (person.name, person.email, person.phone) == (CONTACT_NAME, FAKE_EMAIL, FAKE_PHONE)
    for text in (repr(person), repr(listed), str(listed.contacts)):
        assert CONTACT_NAME not in text and FAKE_EMAIL not in text and FAKE_PHONE not in text
    assert [r.kind for r in listed.rows].count("english") == 5
    assert listed.rows[5].kind == "higher_education" and listed.rows[6].kind == "foundation"


def test_file_version_and_recognise(tmp_path: Path) -> None:
    assert file_version("Interim-List-of-Eligible-Programmes-updated-22-September-2026.xlsx",
                        "ILEP ... with effect from 11 February 2026") == "2026-09-22"
    assert file_version("ilep.xlsx", "ILEP ... with effect from 11 February 2026") == "2026-02-11"
    assert file_version("trusted.xlsx", "TrustEd ... Programmes) August 2026") == "2026-08"
    assert file_version("list.xlsx", "no date") == "list"
    ilep = write_list(tmp_path / "a.xlsx", ilep_v1())
    trusted = write_list(tmp_path / "b.xlsx", trusted_v1(), trusted=True)
    assert recognise("a.xlsx", ilep) == "ie_ilep"
    assert recognise("b.xlsx", trusted) == "ie_trusted"
    with pytest.raises(ValueError):
        recognise("a.pdf", ilep)
    other = tmp_path / "c.xlsx"
    other.write_bytes(b"not a zip")
    with pytest.raises(ValueError):
        recognise("c.xlsx", other)
