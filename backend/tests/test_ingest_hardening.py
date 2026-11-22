"""Guards on untrusted input (FR-26 uploads) and on value rules; no database needed."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from north.domain.verified import SourceKind, Status, verified
from north.ingest.us import dhs_stem, sevp_pdf, xlsx, zipguard
from north.ingest.us.common import read_csv_rows
from north.ingest.us.ipeds import _int
from north.ingest.us.sevp_pdf import SevpCampus, check_rows
from tests.conftest import DICT_ROWS, REPO, check_test_database_url, write_dictionary

# --------------------------------------------------------------------------- IPEDS counts


@pytest.mark.parametrize("raw", [None, "", " ", ".", "abc", "nan", "inf"])
def test_ipeds_int_missing_is_none_not_zero(raw: str | None) -> None:
    assert _int(raw) is None


def test_ipeds_int_parses_counts() -> None:
    assert (_int("0"), _int("12"), _int(" 7 "), _int("3.0")) == (0, 12, 7, 3)


# --------------------------------------------------------------------------- verified()


@pytest.mark.parametrize("url", ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd",
                                 "ftp://example.gov/x", "//example.gov/x", "example.gov",
                                 "https://", " https://example.gov", "https://exa mple.gov"])
def test_verified_rejects_non_http_source_url(url: str) -> None:
    with pytest.raises(ValueError, match="http"):
        verified(1, Status.CONFIRMED_OFFICIAL, source_kind=SourceKind.PAGE, source_url=url,
                 verified_at="2026-11-21")
    with pytest.raises(ValueError, match="http"):
        verified(1, Status.EXTRACTED_UNVERIFIED, source_url=url, evidence="x")


def test_verified_keeps_source_rules() -> None:
    ok = verified(1, Status.CONFIRMED_OFFICIAL, source_kind=SourceKind.PAGE,
                  source_url="HTTPS://example.gov/a", verified_at="2026-11-21")
    assert ok["source_url"] == "HTTPS://example.gov/a"
    assert verified(1, Status.REPORTED_BY_PROGRAM, source_kind=SourceKind.CORRESPONDENCE,
                    verified_at="2026-11-21")["source_url"] is None  # K10
    with pytest.raises(ValueError):
        verified(1, Status.CONFIRMED_OFFICIAL, source_kind=SourceKind.PAGE,
                 verified_at="2026-11-21")  # A4: needs source_url
    with pytest.raises(ValueError):
        verified(1, Status.UNKNOWN)


# --------------------------------------------------------------------------- SEVP rows


def _campus(code: str, f_1: str = "Y", state: str = "TX") -> SevpCampus:
    return SevpCampus("S", "C", f_1, "N", "Austin", state, code)


def test_sevp_check_rows_tolerates_a_few_odd_flags_but_not_a_layout_change() -> None:
    rows = [_campus(f"DAL214F{90000000 + i}") for i in range(10)]
    check_rows([*rows[:9], _campus(rows[9].campus_code, f_1="")])  # one odd flag: data
    with pytest.raises(ValueError, match="F/M flags"):
        check_rows([_campus(r.campus_code, f_1="?") for r in rows])
    with pytest.raises(ValueError, match="duplicate"):
        check_rows([rows[0], rows[0]])
    with pytest.raises(ValueError, match="campus code"):
        check_rows([*rows, _campus("NOT-A-CODE")])
    with pytest.raises(ValueError, match="no campus"):
        check_rows([])


def test_sevp_pdf_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf = tmp_path / "certified-school-list-11-18-26.pdf"
    pdf.write_bytes(b"%PDF-1.4\n" + b"0" * 2048)
    monkeypatch.setattr(sevp_pdf, "MAX_PDF_BYTES", 1024)
    with pytest.raises(ValueError, match="byte limit"):
        sevp_pdf.parse_pdf(pdf)


def test_sevp_pdf_page_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdfplumber = pytest.importorskip("pdfplumber")

    class FakePdf:
        pages = [object()] * 3

        def __enter__(self) -> FakePdf:
            return self

        def __exit__(self, *a: object) -> None:
            return None

    pdf = tmp_path / "list.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(pdfplumber, "open", lambda _p: FakePdf())
    monkeypatch.setattr(sevp_pdf, "MAX_PDF_PAGES", 2)
    with pytest.raises(ValueError, match="page limit"):
        sevp_pdf.parse_pdf(pdf)


# --------------------------------------------------------------------------- DHS meta


GOOD_META = {"source_url": "https://www.ice.gov/doclib/sevis/pdf/stemList2024.pdf",
             "published_on": "2024-07-22", "version": "2024-07-22",
             "whole_series_included": ["14", "26"]}


def _meta(tmp_path: Path, **changes: object) -> Path:
    p = tmp_path / "m.meta.json"
    p.write_text(json.dumps({**GOOD_META, **changes}))
    return p


def test_dhs_meta_valid(tmp_path: Path) -> None:
    assert dhs_stem.load_meta(_meta(tmp_path))["whole_series_included"] == ["14", "26"]


@pytest.mark.parametrize(("changes", "match"), [
    ({"whole_series_included": ["1"]}, "two-digit"),
    ({"whole_series_included": ["14.01"]}, "two-digit"),
    ({"whole_series_included": [14]}, "two-digit"),
    ({"whole_series_included": "14"}, "two-digit"),
    ({"published_on": "2024-13-01"}, "not a date"),
    ({"published_on": "next week"}, "not a date"),
    ({"published_on": (dt.date.today() + dt.timedelta(days=1)).isoformat()}, "future"),
    ({"source_url": "http://www.ice.gov/x.pdf"}, "https"),
    ({"source_url": "javascript:alert(1)"}, "https"),
    ({"file_sha256": "abc"}, "sha256"),
])
def test_dhs_meta_rejected(tmp_path: Path, changes: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        dhs_stem.load_meta(_meta(tmp_path, **changes))


def test_dhs_pdf_must_match_meta_sha(tmp_path: Path) -> None:
    pdf = tmp_path / "stemList2024.pdf"
    pdf.write_bytes(b"%PDF-1.4 official")
    meta = {**GOOD_META, "file_sha256": _sha(pdf)}
    dhs_stem.verify_pdf(pdf, meta)  # same bytes: accepted
    pdf.write_bytes(b"%PDF-1.4 tampered")
    with pytest.raises(ValueError, match="refusing"):
        dhs_stem.verify_pdf(pdf, meta)
    with pytest.raises(ValueError, match="no file_sha256"):
        dhs_stem.verify_pdf(pdf, GOOD_META)


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- xlsx


def _xlsx(path: Path, sheet_xml: str) -> Path:
    workbook = ('<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
                'officeDocument/2006/relationships"><sheets><sheet name="Frequencies" '
                'sheetId="1" r:id="rId1"/></sheets></workbook>')
    rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/'
            'package/2006/relationships"><Relationship Id="rId1" Type="worksheet" '
            'Target="worksheets/sheet1.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return path


SHEET_HEAD = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<sheetData>')
SHEET_TAIL = "</sheetData></worksheet>"


def test_xlsx_reads_dictionary(tmp_path: Path) -> None:
    d = tmp_path / "C2024_A_Dict.zip"
    write_dictionary(d, DICT_ROWS)
    assert xlsx.value_labels(d)["AWLEVEL"]["7"] == "Master's degree"


@pytest.mark.parametrize("prolog", [
    # A DOCTYPE anywhere, not only in the first 4 KB, and in any case.
    "<?xml version=\"1.0\"?>" + "<!-- pad -->" * 500 + "<!DOCTYPE w>",
    "<?xml version=\"1.0\"?><!doctype w>",
    '<?xml version="1.0"?><!DOCTYPE w [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;">]>',
    '<?xml version="1.0"?><!DOCTYPE w SYSTEM "file:///etc/passwd">',
])
def test_xlsx_refuses_doctype(tmp_path: Path, prolog: str) -> None:
    path = _xlsx(tmp_path / "x.xlsx", prolog + SHEET_HEAD + SHEET_TAIL)
    with pytest.raises(ValueError, match=r"DOCTYPE|malformed"):
        xlsx.value_labels(path)


def test_xlsx_parse_xml_refuses_doctype_directly() -> None:
    with pytest.raises(ValueError, match="DOCTYPE"):
        xlsx.parse_xml(b'<!DOCTYPE a [<!ENTITY x "y">]><a>&x;</a>', "t.xml")
    assert xlsx.parse_xml(b'<a xmlns="urn:x" b="1"><c/></a>', "t.xml").tag == "{urn:x}a"


def test_xlsx_column_cap(tmp_path: Path) -> None:
    sheet = SHEET_HEAD + '<row><c r="XFE1" t="inlineStr"><is><t>x</t></is></c></row>' + SHEET_TAIL
    with pytest.raises(ValueError, match="column beyond"):
        xlsx.value_labels(_xlsx(tmp_path / "x.xlsx", sheet))
    sheet = SHEET_HEAD + '<row><c r="ZZZZZZZZ1"><v>1</v></c></row>' + SHEET_TAIL
    with pytest.raises(ValueError, match="column beyond"):
        xlsx.value_labels(_xlsx(tmp_path / "y.xlsx", sheet))


def test_xlsx_row_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xlsx, "MAX_ROWS", 3)
    sheet = SHEET_HEAD + "<row/>" * 4 + SHEET_TAIL
    with pytest.raises(ValueError, match="more than 3 rows"):
        xlsx.value_labels(_xlsx(tmp_path / "x.xlsx", sheet))


def test_xlsx_refuses_zip_bomb(tmp_path: Path) -> None:
    sheet = SHEET_HEAD + "<row/>" * 200_000 + SHEET_TAIL  # ~1.2 MB of repeats, > 100:1
    with pytest.raises(ValueError, match="compression ratio"):
        xlsx.value_labels(_xlsx(tmp_path / "x.xlsx", sheet))


def test_xlsx_refuses_oversized_member(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(xlsx, "MAX_PART", 100)
    with pytest.raises(ValueError, match="byte limit"):
        xlsx.value_labels(_xlsx(tmp_path / "x.xlsx", SHEET_HEAD + "<row/>" * 30 + SHEET_TAIL))


# --------------------------------------------------------------------------- zips (common)


def test_csv_zip_bomb_and_size_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bomb = tmp_path / "HD2024.zip"
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("hd2024.csv", "UNITID\n" + "1\n" * 500_000)
    with pytest.raises(ValueError, match="compression ratio"):
        list(read_csv_rows(bomb))
    ok = tmp_path / "IC2023_AY.zip"
    with zipfile.ZipFile(ok, "w", zipfile.ZIP_STORED) as z:
        z.writestr("ic2023_ay.csv", "UNITID,TUITION7\n900001,12000\n")
    assert list(read_csv_rows(ok)) == [{"UNITID": "900001", "TUITION7": "12000"}]
    monkeypatch.setattr(zipguard, "MAX_MEMBER_BYTES", 10)
    with pytest.raises(ValueError, match="byte limit"):
        list(read_csv_rows(ok))


# --------------------------------------------------------------------------- test database


@pytest.mark.parametrize("url", ["postgresql+psycopg://north:x@db:5432/north",
                                 "postgresql+psycopg://north_test:x@db:5432/production"])
def test_test_database_url_must_name_a_test_database(url: str) -> None:
    with pytest.raises(pytest.UsageError):
        check_test_database_url(url)


def test_test_database_url_accepted() -> None:
    check_test_database_url("postgresql+psycopg://u:p@localhost:5432/north_test")


# --------------------------------------------------------------------------- load script


def test_load_script_picks_newest_sevp_by_date_in_name(tmp_path: Path) -> None:
    sevp = tmp_path / "sevp"
    sevp.mkdir()
    for name in ("certified-school-list-12-01-25.pdf", "certified-school-list-01-15-26.pdf",
                 "certified-school-list-11-18-26.pdf", "certified-school-list-02-03-26.pdf"):
        (sevp / name).touch()
    script = REPO / "scripts" / "load_local_sample.sh"
    body = script.read_text()
    func = body[body.index("newest_sevp() {"):body.index("\n}\n", body.index("newest_sevp() {"))
                + 3]
    out = subprocess.run(["bash", "-c", func + "newest_sevp"], env={"RAW": str(tmp_path)},
                         capture_output=True, text=True, check=True).stdout
    assert out == str(sevp / "certified-school-list-11-18-26.pdf")


def test_sevp_candidates_skip_names_that_normalize_to_nothing() -> None:
    """A real SEVP row ("Campus ,Inc.", Sacramento, list of 2026-11-18) has only stop words;
    it broke the California load with max() of an empty sequence."""
    from north.ingest.us import sevp
    from north.ingest.us.sevp_pdf import SevpCampus

    blank = SevpCampus(school_name="Campus ,Inc.", campus_name="Campus, Inc.", f_1="Y",
                       m_1="N", city="SACRAMENTO", state="CA", campus_code="SFR214F61147000")
    other = SevpCampus(school_name="Sample State University", campus_name="Main", f_1="Y",
                       m_1="N", city="SACRAMENTO", state="CA", campus_code="SFR214F00000000")
    assert sevp.sevp_names(blank) == set()
    prepared = [(c, sevp.sevp_names(c), sevp.norm_city(c.city)) for c in (blank, other)]
    found = sevp.candidates_for(sevp.ipeds_names("Sample State University"), "sacramento",
                                prepared)
    assert [c["sevp_campus_code"] for c in found] == ["SFR214F00000000"]
    assert sevp.candidates_for(set(), "sacramento", prepared) == []
