"""Irish lists -> English courses, and the API over them (needs NORTH_TEST_DATABASE_URL).

Synthetic files (tests/ie_lists.py): ILEP v1 has five English rows (one reference used twice),
one higher-education row and one foundation row; the TrustEd file moves 'General English' of
provider 0901 to TrustEd and adds a university language centre course in Galway.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from north.api.app import app
from north.ingest.ie.load import ingest_list
from north.repository.db import session_scope
from north.repository.models import (
    Base,
    FieldChange,
    Institution,
    InstitutionContact,
    InstitutionIdentifier,
    Program,
    ProgramIdentifier,
    ReconciliationTask,
)
from tests.ie_lists import (
    CONTACT_NAME,
    FAKE_EMAIL,
    FAKE_PHONE,
    ilep_v1,
    row,
    trusted_v1,
    write_list,
)

SECRETS = (CONTACT_NAME, FAKE_EMAIL, FAKE_PHONE)

GENERAL = "ie-ilep-0901-0001"
INTENSIVE = "ie-ilep-0901-0002"
CORK = "ie-ilep-0902-0001"
TWO_TOWNS = "ie-ilep-0903-0001"
GALWAY = "ie-trusted-0950-0001"


@pytest.fixture
def files(tmp_path: Path) -> dict[str, Path]:
    v2 = [r for r in ilep_v1() if r[0] not in ("0901/0001", "0901/0002")]
    return {
        "ilep": write_list(tmp_path / "ilep-updated-22-September-2026.xlsx", ilep_v1()),
        "trusted": write_list(tmp_path / "trusted.xlsx", trusted_v1(), trusted=True),
        "ilep_v2": write_list(tmp_path / "ilep-updated-1-December-2026.xlsx", v2),
    }


def lc(session: Session, pid: str) -> dict:
    p = session.get(Program, pid)
    assert p is not None
    session.refresh(p)
    return p.language_course or {}


def test_ilep_rows_become_language_courses(session: Session, files: dict[str, Path]) -> None:
    r = ingest_list(session, files["ilep"], "ie_ilep")
    assert r.status == "succeeded" and r.file_version == "2026-09-22"
    c = r.counts
    assert (c["rows"], c["english_rows"], c["skipped_higher_education"],
            c["skipped_foundation"]) == (7, 5, 1, 1)
    assert c["programs_created"] == 4 and c["institutions_created"] == 3
    assert c["duplicate_ref_rows"] == 1 and c["tasks_ie_duplicate_ref"] == 1
    assert c["cefr_entry_unknown"] == 1 and c["cefr_exit_unknown"] == 1
    assert c["city_unknown"] == 1

    p = session.get(Program, GENERAL)
    assert p is not None and p.kind == "language_course" and p.degree == "language_course"
    assert p.name == "General English" and p.campus.city == "Dublin"
    assert p.campus.institution.subdivision_id == "IE-D"
    assert p.campus.locality is not None and p.campus.locality.code == "IE-D"
    v = p.language_course
    assert v["cefr_entry"]["value"] == "A1" and "Beginner A1.1" in v["cefr_entry"]["evidence"]
    assert v["cefr_exit"]["value"] == "B1"
    assert v["exam"]["value"] == "ielts" and "IELTS" in v["exam"]["evidence"]
    assert v["weeks"]["value"] == 25 and v["hours_per_week"]["value"] == 15
    assert "15-20 hours" in v["hours_per_week"]["evidence"]
    for key in ("cefr_entry", "cefr_exit", "exam", "weeks", "hours_per_week"):
        assert v[key]["status"] == "confirmed_official"
        assert v[key]["source_kind"] == "uploaded_file"
        assert v[key]["source_url"].startswith("https://www.irishimmigration.ie/")
        assert v[key]["verified_at"]
    assert v["price"] == {"value": None, "status": "unknown", "source_kind": None,
                          "source_url": None, "evidence": None, "verified_at": None}
    assert v["start_dates"] == []
    auth = p.intl_authorization
    assert auth["value"] == {"scheme": "ie_ilep", "authorized": True}
    assert auth["status"] == "confirmed_official" and "0901/0001" in auth["evidence"]
    assert p.campus.intl_authorization is None  # the US campus field stays untouched

    intensive = lc(session, INTENSIVE)
    # Unknown, never negative, and the raw text is kept for a curator (BR-02).
    assert intensive["cefr_entry"]["status"] == "unknown"
    assert intensive["cefr_entry"]["value"] is None
    assert "IELTS 5.5" in intensive["cefr_entry"]["evidence"]
    assert intensive["exam"]["value"] == "trinity"

    cork = session.get(Program, CORK)
    assert cork is not None and cork.campus.city == "Cork"
    assert lc(session, CORK)["exam"]["value"] == "tie"
    assert lc(session, CORK)["hours_per_week"]["value"] == 21.33
    two = session.get(Program, TWO_TOWNS)
    assert two is not None and two.campus.city is None and two.campus.locality is None
    assert two.campus.institution.subdivision_id is None
    assert two.campus.institution.country_code == "IE"
    assert lc(session, TWO_TOWNS)["cefr_entry"]["value"] == "A0"

    ids = dict(session.execute(select(InstitutionIdentifier.institution_id,
                                      InstitutionIdentifier.value)
                               .where(InstitutionIdentifier.scheme == "ie_provider_no")).all())
    assert ids == {"ie-0901": "0901", "ie-0902": "0902", "ie-0903": "0903"}
    refs = dict(session.execute(select(ProgramIdentifier.value, ProgramIdentifier.program_id)
                                .where(ProgramIdentifier.scheme == "ie_ilep_ref")).all())
    assert refs == {"0901/0001": GENERAL, "0901/0002": INTENSIVE, "0902/0001": CORK,
                    "0903/0001": TWO_TOWNS}
    dup = session.scalars(select(ReconciliationTask).where(
        ReconciliationTask.kind == "ie_duplicate_ref")).one()
    assert "English Plus Evening" in dup.reason


def test_reupload_changes_nothing(session: Session, files: dict[str, Path]) -> None:
    ingest_list(session, files["ilep"], "ie_ilep")
    changes = session.scalar(select(text("count(*)")).select_from(FieldChange))
    again = ingest_list(session, files["ilep"], "ie_ilep")
    assert again.status == "skipped"
    assert session.scalar(select(text("count(*)")).select_from(FieldChange)) == changes


def _dump(session: Session, table: str) -> str:
    return " ".join(session.scalars(text(f"select row_to_json(t)::text from {table} t")).all())


def test_contacts_land_only_in_the_private_table(session: Session,
                                                 files: dict[str, Path]) -> None:
    """Record 0009: contacts are kept, privately, and nowhere else."""
    ingest_list(session, files["ilep"], "ie_ilep")
    ingest_list(session, files["trusted"], "ie_trusted")
    for table in Base.metadata.sorted_tables:
        if table.name == "institution_contacts":
            continue
        dump = _dump(session, table.name)
        for secret in SECRETS:
            assert secret not in dump, table.name
    rows = session.scalars(select(InstitutionContact).order_by(InstitutionContact.id)).all()
    assert {(c.source, c.institution_id) for c in rows} == {
        ("ie_ilep", "ie-0901"), ("ie_ilep", "ie-0902"), ("ie_ilep", "ie-0903"),
        ("ie_trusted", "ie-0901"), ("ie_trusted", "ie-0950")}
    c = rows[0]
    assert (c.name, c.email, c.phone, c.title) == (CONTACT_NAME, FAKE_EMAIL, FAKE_PHONE, None)
    assert CONTACT_NAME not in repr(c) and FAKE_EMAIL not in repr(c)


def test_a_new_file_replaces_the_contacts_of_its_source(session: Session,
                                                        files: dict[str, Path]) -> None:
    ingest_list(session, files["ilep"], "ie_ilep")
    ingest_list(session, files["trusted"], "ie_trusted")
    ingest_list(session, files["ilep"], "ie_ilep")  # the same file: skipped, nothing changes
    assert session.scalar(select(text("count(*)")).select_from(InstitutionContact)) == 5
    newer = ("Sam Example", "sam.example@example.com", "+353 1 000 0001")
    v2 = write_list(files["ilep"].with_name("ilep-updated-3-December-2026.xlsx"),
                    [row("0902/0001", "English for Work", provider="Coastal English College",
                         address="9 Harbour Road, Cork City T12 AC34", contact=newer)])
    ingest_list(session, v2, "ie_ilep")
    got = {(c.source, c.institution_id, c.name) for c in
           session.scalars(select(InstitutionContact))}
    assert got == {("ie_ilep", "ie-0902", "Sam Example"),
                   ("ie_trusted", "ie-0901", CONTACT_NAME),
                   ("ie_trusted", "ie-0950", CONTACT_NAME)}


def test_move_from_ilep_to_trusted(session: Session, files: dict[str, Path]) -> None:
    ingest_list(session, files["ilep"], "ie_ilep")
    t = ingest_list(session, files["trusted"], "ie_trusted")
    assert t.counts["linked_to_ie_ilep"] == 1 and t.counts["programs_created"] == 1
    assert t.counts["skipped_higher_education"] == 1
    general = session.get(Program, GENERAL)
    assert general is not None
    session.refresh(general)
    assert general.intl_authorization["value"] == {"scheme": "ie_trusted", "authorized": True}
    assert lc(session, GENERAL)["hours_per_week"]["value"] == 16
    assert set(session.scalars(select(ProgramIdentifier.scheme).where(
        ProgramIdentifier.program_id == GENERAL))) == {"ie_ilep_ref", "ie_trusted_ref"}
    galway = session.get(Program, GALWAY)
    assert galway is not None and galway.campus.city == "Galway"
    assert galway.campus.institution_id == "ie-0950"

    # ILEP drops both 0901 rows: the moved one is fine, the other needs a person.
    v2 = ingest_list(session, files["ilep_v2"], "ie_ilep")
    assert v2.counts["moved_to_trusted"] == 1 and v2.counts["left_list"] == 1
    task = session.scalars(select(ReconciliationTask).where(
        ReconciliationTask.kind == "ie_list_move")).one()
    assert task.candidates[0] == {"program_id": INTENSIVE, "ref": "0901/0002"}
    intensive = session.get(Program, INTENSIVE)
    assert intensive is not None
    session.refresh(intensive)
    # Never confirmed_negative automatically (BR-18): the value is kept.
    assert intensive.intl_authorization["status"] == "confirmed_official"
    assert intensive.intl_authorization["value"]["scheme"] == "ie_ilep"

    # A later file still without it does not open a second task.
    v3 = write_list(files["ilep_v2"].with_name("ilep-updated-2-December-2026.xlsx"),
                    [*[r for r in ilep_v1() if r[0] not in ("0901/0001", "0901/0002")],
                     row("0902/0002", "Evening English", provider="Coastal English College",
                         address="9 Harbour Road, Cork City T12 AC34")])
    again = ingest_list(session, v3, "ie_ilep")
    assert again.counts["left_list"] == 1 and "tasks_ie_list_move" not in again.counts
    assert again.counts["programs_created"] == 1


def test_trusted_first_then_ilep_links_the_other_way(session: Session,
                                                    files: dict[str, Path]) -> None:
    ingest_list(session, files["trusted"], "ie_trusted")
    r = ingest_list(session, files["ilep"], "ie_ilep")
    assert r.counts["linked_to_ie_trusted"] == 1
    assert r.counts["kept_trusted_authorization"] == 1
    pid = session.scalar(select(ProgramIdentifier.program_id).where(
        ProgramIdentifier.scheme == "ie_ilep_ref", ProgramIdentifier.value == "0901/0001"))
    assert pid == "ie-trusted-0901-0050"
    p = session.get(Program, pid)
    assert p is not None and p.intl_authorization["value"]["scheme"] == "ie_trusted"


def test_us_reports_ignore_ireland(session: Session, files: dict[str, Path]) -> None:
    from north.ingest.report import report

    ingest_list(session, files["ilep"], "ie_ilep")
    assert report(session, "US")["states"] == []
    ie = report(session, "IE")
    assert {s["scope"] for s in ie["states"]} == {"IE", "IE-CO", "IE-D"}
    assert ie["total"]["programs"] == 4 and set(ie["source_files"]) == {"ie_ilep"}
    assert session.get(Institution, "ie-0903").subdivision_id is None  # type: ignore[union-attr]


# --------------------------------------------------------------------------- API


@pytest.fixture
def client(session: Session, loaded: dict, files: dict[str, Path]) -> Iterator[TestClient]:
    ingest_list(session, files["ilep"], "ie_ilep")
    ingest_list(session, files["trusted"], "ie_trusted")

    def override() -> Iterator[Session]:
        yield session

    app.dependency_overrides[session_scope] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def ids(client: TestClient, qs: str) -> set[str]:
    r = client.get(f"/api/programs?{qs}")
    assert r.status_code == 200, r.text
    return {i["id"] for i in r.json()["items"]}


COURSES = {"ie-trusted-0901-0050", GENERAL, INTENSIVE, CORK, TWO_TOWNS, GALWAY} - {
    "ie-trusted-0901-0050"}


def test_us_listing_is_unaffected(client: TestClient) -> None:
    us = client.get("/api/programs").json()
    assert us["total"] == 6 and all(i["kind"] == "degree" and i["country"] == "US"
                                    for i in us["items"])
    item = us["items"][0]
    assert item["language_course"] is None and item["intl_authorization"] is None
    assert item["cip"]["code"]
    assert ids(client, "country=US&kind=language_course") == set()


def test_course_list_and_filters(client: TestClient) -> None:
    assert ids(client, "country=IE") == COURSES
    assert ids(client, "country=IE&kind=language_course") == COURSES
    assert ids(client, "country=IE&kind=degree") == set()
    assert ids(client, "country=IE&city=Dublin") == {GENERAL, INTENSIVE}
    assert ids(client, "country=IE&city=Galway&city=Cork") == {GALWAY, CORK}
    assert ids(client, "country=IE&exam=tie") == {CORK}
    assert ids(client, "country=IE&exam=pte&exam=languagecert") == {TWO_TOWNS, GALWAY}
    # Entry at or below a band; a course with an unknown entry level (INTENSIVE) stays in (BR-02).
    assert ids(client, "country=IE&cefr_entry_max=A1") == {GENERAL, TWO_TOWNS, INTENSIVE}
    assert ids(client, "country=IE&cefr_entry_max=B1") == {
        GENERAL, TWO_TOWNS, CORK, GALWAY, INTENSIVE}
    assert ids(client, "country=IE&hours_min=20") == {INTENSIVE, CORK, GALWAY}
    assert ids(client, "country=IE&hours_min=16&cefr_entry_max=A2") == {GENERAL, CORK, INTENSIVE}
    assert ids(client, "country=IE&state=D") == {GENERAL, INTENSIVE}
    assert ids(client, "country=IE&q=academic") == {GALWAY}


def test_course_item_shape(client: TestClient) -> None:
    items = {i["id"]: i for i in client.get("/api/programs?country=IE").json()["items"]}
    g = items[GENERAL]
    assert g["kind"] == "language_course" and g["country"] == "IE" and g["cip"] is None
    assert g["campus"] == {"city": "Dublin", "state": "D"}
    assert g["language_course"]["exam"]["value"] == "ielts"
    assert "evidence" not in g["language_course"]["exam"]  # lists omit evidence
    assert g["language_course"]["price"]["status"] == "unknown"
    assert g["language_course"]["start_dates"] == []
    assert g["graduate_tuition_nonresident"] == {"value": None, "status": "unknown",
                                                 "source_kind": None, "source_url": None,
                                                 "verified_at": None, "note_code": None}
    assert g["intl_authorization"]["value"]["scheme"] == "ie_trusted"
    assert g["intl_authorization"]["notes"] == []
    i = items[INTENSIVE]["intl_authorization"]
    assert i["value"] == {"scheme": "ie_ilep", "authorized": True}
    assert [n["code"] for n in i["notes"]] == ["ie.ilep_end"]
    assert i["notes"][0]["source_url"].startswith("https://www.irishimmigration.ie/")
    assert items[TWO_TOWNS]["campus"] == {"city": None, "state": None}


def test_course_detail(client: TestClient) -> None:
    r = client.get(f"/api/programs/{INTENSIVE}")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["kind"] == "language_course" and d["cip"] is None
    assert d["identifiers"] == [{"scheme": "ie_ilep_ref", "value": "0901/0002"}]
    assert d["institution"]["identifiers"] == {"ie_provider_no": "0901"}
    assert d["language_course"]["cefr_entry"]["status"] == "unknown"
    assert "IELTS 5.5" in d["language_course"]["cefr_entry"]["evidence"]
    assert d["intl_authorization"]["evidence"]
    assert d["not_yet_collected"] == ["language_course.price", "language_course.start_dates"]
    assert d["campus"]["locality"] == {"country": "IE", "scheme": "ie_county", "code": "IE-D",
                                       "name": "Dublin"}
    assert [s["source"] for s in d["sources"]] == ["ie_ilep", "ie_trusted"]
    us = client.get("/api/programs/900001-110701").json()
    assert us["kind"] == "degree" and us["language_course"] is None
    assert us["not_yet_collected"][0] == "admissions.english"


def test_public_api_never_serves_contacts(client: TestClient) -> None:
    pages = ["/api/programs?country=IE", "/api/programs", "/api/facets?country=IE",
             "/api/sources", *[f"/api/programs/{pid}" for pid in COURSES]]
    for url in pages:
        body = client.get(url).text
        for secret in (*SECRETS, "Dapip Admin", "Chief Example", "@example.com"):
            assert secret not in body, url


def test_course_facets(client: TestClient) -> None:
    f = client.get("/api/facets?country=IE&kind=language_course").json()
    assert f["country"] == "IE" and f["kind_scope"] == "language_course" and f["total"] == 5
    assert f["kind"] == {"degree": 0, "language_course": 5}
    assert {k: v for k, v in f["exam"].items() if v} == {
        "ielts": 1, "trinity": 1, "tie": 1, "pte": 1, "languagecert": 1}
    assert {k: v for k, v in f["cefr_entry"].items() if v} == {
        "A0": 1, "A1": 1, "A2": 1, "B1": 1, "unknown": 1}
    assert f["hours_per_week"] == {"min": 15, "max": 21.33, "known": 5, "unknown": 0}
    # Irish city names are one place each: cities without a state.
    assert f["cities"] == [{"city": "Dublin", "count": 2}, {"city": "Cork", "count": 1},
                           {"city": "Galway", "count": 1}]
    assert f["tuition"]["currency"] == "EUR" and f["tuition"]["known"] == 0
    assert {s["state"] for s in f["states"]} == {"CO", "D", "G"}
    for exam, n in f["exam"].items():
        if exam != "unknown":
            assert client.get(f"/api/programs?country=IE&exam={exam}").json()["total"] == n
    for c in f["cities"]:
        assert client.get("/api/programs", params={"country": "IE", "city": c["city"]}
                          ).json()["total"] == c["count"]
    us = client.get("/api/facets").json()
    assert us["country"] == "US" and us["total"] == 6 and us["kind"]["language_course"] == 0


@pytest.mark.parametrize("qs", ["country=FR", "country=IRL", "kind=course", "exam=toeic",
                                "cefr_entry_max=B3", "hours_min=-1", "hours_min=81"])
def test_course_filters_reject_bad_values(client: TestClient, qs: str) -> None:
    assert client.get(f"/api/programs?{qs}").status_code == 422


# --------------------------------------------------------------------------- jobs


class _Ctx:
    """The parts of JobContext the Irish job kinds use."""

    def __init__(self, session: Session, tmp: Path) -> None:
        from sqlalchemy.orm import sessionmaker

        self.sessions = sessionmaker(bind=session.get_bind(), expire_on_commit=False)
        self._raw, self._incoming = tmp / "raw", tmp / "incoming"
        self._incoming.mkdir()
        self.lines: list[str] = []

    def log(self, line: str) -> None:
        self.lines.append(line)

    def raw(self) -> Path:
        self._raw.mkdir(exist_ok=True)
        return self._raw

    def incoming(self) -> Path:
        return self._incoming


def test_upload_job_recognises_stores_and_loads(session: Session, tmp_path: Path,
                                                files: dict[str, Path]) -> None:
    import shutil

    from north.ingest.common import sha256_file
    from north.ingest.ie import jobs
    from north.jobs import registry

    assert registry.upload_kind()["IE"] == jobs.UPLOAD_KIND
    assert {"ie.load", "ie.accept_upload"} <= set(registry.kinds())
    ctx = _Ctx(session, tmp_path)
    stored = "0" * 32 + "__trusted.xlsx"
    shutil.copyfile(files["trusted"], ctx.incoming() / stored)
    params = jobs._validate_upload({"file": stored, "sha256": sha256_file(files["trusted"])})
    out = jobs.run_accept_upload(ctx, params)
    assert out["kind"] == "ie_trusted" and out["load"]["status"] == "succeeded"
    assert out["load"]["counts"]["programs_created"] == 2
    assert not (ctx.incoming() / stored).exists()
    assert (ctx.raw() / out["path"]).is_file()
    again = jobs.run_load(ctx, {})
    assert again["ie_trusted"]["status"] == "skipped" and "ie_ilep" not in again
