"""Shared fixtures.

Database tests run against PostgreSQL at ``NORTH_TEST_DATABASE_URL`` (the database is wiped
and migrated with Alembic) and are skipped when it is unset or unreachable.

Files under ``tests/fixtures/`` are synthetic, shaped like the official files: every
institution, code and value is invented, and contact columns hold ``PLACEHOLDER-CONTACT`` so
tests can prove they never reach the database. The IPEDS dictionary workbook is generated here.
"""

from __future__ import annotations

import os
import shutil
import zipfile
from collections.abc import Iterator
from pathlib import Path
from xml.sax.saxutils import escape

import pytest
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session, sessionmaker

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]
ISCED_CSV = REPO / "data" / "reference" / "cip-isced-f.csv"
PLACEHOLDER = "PLACEHOLDER-CONTACT"

DICT_ROWS = [
    ["varNumber", "VarName", "CodeValue", "ValueLabel", "Frequency", "Percent"],
    ["35000", "CIPCODE", "11.0101", "Computer and Information Sciences, General", "1", "0"],
    ["35000", "CIPCODE", "11.0701", "Computer Science", "1", "0"],
    ["35000", "CIPCODE", "11.1003",
     "Computer and Information Systems Security/Auditing/Information Assurance", "1", "0"],
    ["35000", "CIPCODE", "30.7001", "Data Science, General", "1", "0"],
    ["35000", "CIPCODE", "30.7101", "Data Analytics, General", "1", "0"],
    ["35000", "CIPCODE", "52.1201", "Management Information Systems, General", "1", "0"],
    ["35005", "AWLEVEL", "5", "Bachelor's degree", "1", "0"],
    ["35005", "AWLEVEL", "7", "Master's degree", "1", "0"],
]


def write_dictionary(path: Path, rows: list[list[str]]) -> None:
    """A minimal IPEDS dictionary: a zip holding an .xlsx with a Frequencies sheet."""
    def cell(v: str) -> str:
        return f'<c t="inlineStr"><is><t>{escape(v)}</t></is></c>'
    sheet = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/'
             'spreadsheetml/2006/main"><sheetData>'
             + "".join("<row>" + "".join(cell(v) for v in r) + "</row>" for r in rows)
             + "</sheetData></worksheet>")
    workbook = ('<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/'
                'spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/'
                'officeDocument/2006/relationships"><sheets><sheet name="Frequencies" '
                'sheetId="1" r:id="rId1"/></sheets></workbook>')
    rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/'
            'package/2006/relationships"><Relationship Id="rId1" Type="worksheet" '
            'Target="worksheets/sheet1.xml"/></Relationships>')
    xlsx = path.with_suffix(".xlsx.tmp")
    with zipfile.ZipFile(xlsx, "w") as z:
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    with zipfile.ZipFile(path, "w") as z:
        z.write(xlsx, "c2024_a_dict.xlsx")
    xlsx.unlink()


@pytest.fixture
def ipeds_dir(tmp_path: Path) -> Path:
    d = tmp_path / "ipeds"
    shutil.copytree(FIXTURES / "ipeds", d)
    write_dictionary(d / "C2024_A_Dict.zip", DICT_ROWS)
    return d


def check_test_database_url(url: str) -> None:
    """Refuse to wipe a database whose name does not say it is a test database."""
    name = make_url(url).database or ""
    if "test" not in name.lower():
        raise pytest.UsageError(
            f"NORTH_TEST_DATABASE_URL points at database {name!r}; the tests drop its schema, "
            f"so its name must contain 'test'")


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = os.environ.get("NORTH_TEST_DATABASE_URL")
    if not url:
        pytest.skip("NORTH_TEST_DATABASE_URL is not set; database tests skipped")
    check_test_database_url(url)
    eng = create_engine(url)
    try:
        with eng.connect() as conn:
            conn.execute(text("select 1"))
    except Exception as exc:  # pragma: no cover - depends on the environment
        pytest.skip(f"test database unreachable ({type(exc).__name__}); database tests skipped")
    from alembic import command
    from alembic.config import Config

    with eng.begin() as conn:
        conn.execute(text("drop schema public cascade"))
        conn.execute(text("create schema public"))
    cfg = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    with eng.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    from north.repository.models import Base

    names = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"truncate {names} restart identity cascade"))
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    with maker() as s:
        yield s


def load_fixtures(session: Session, ipeds_dir: Path) -> dict[str, object]:
    from north.ingest.us import dapip, dhs_stem, ipeds, reference, sevp

    out: dict[str, object] = {"reference": reference.load_cip_isced(session, ISCED_CSV)}
    for r in ipeds.ingest_ipeds_dir(session, ipeds_dir, "TX"):
        out[r.source] = r
    for r in (dhs_stem.ingest_dhs_stem(session, FIXTURES / "dhs" / "dhs-stem-list-test.csv"),
              sevp.ingest_sevp(session, FIXTURES / "sevp" / "sevp-test-2026-11-18.csv", "TX"),
              dapip.ingest_dapip(session, FIXTURES / "dapip", "TX")):
        out[r.source] = r
    return out


@pytest.fixture
def loaded(session: Session, ipeds_dir: Path) -> dict[str, object]:
    return load_fixtures(session, ipeds_dir)
