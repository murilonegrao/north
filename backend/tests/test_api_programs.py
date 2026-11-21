"""Programs API against the synthetic load (needs NORTH_TEST_DATABASE_URL)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from north.api.app import app
from north.repository.db import session_scope


@pytest.fixture
def client(session: Session, loaded: dict) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        yield session

    app.dependency_overrides[session_scope] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_defaults(client: TestClient) -> None:
    body = client.get("/api/programs").json()
    assert (body["total"], body["limit"], body["offset"]) == (6, 50, 0)
    item = next(i for i in body["items"] if i["id"] == "900001-110701")
    assert item["title"] == "Computer Science" and item["title_source"] == "cip_title"
    assert item["cip"] == {"code": "11.0701", "title": "Computer Science.", "family": "11"}
    assert item["institution"] == {"id": "900001", "name": "Lone Star Test University",
                                   "control": "public"}
    assert item["campus"] == {"city": "Austin", "state": "TX"}
    assert item["stem_opt"]["value"] == {"eligible": True, "rule_version": "2024-07-22",
                                         "claim_mismatch": False}
    assert item["stem_opt"]["status"] == "confirmed_official"
    assert item["stem_opt"]["source_kind"] == "official_list"
    assert item["completions"]["value"] == {"total": 12, "nonresident": 8, "year": "2023-24"}
    assert item["sevp_status"] == "confirmed_official"
    assert item["accreditation_status"] == "confirmed_official"
    assert item["flags"] == []


def test_filters(client: TestClient) -> None:
    def ids(qs: str) -> set[str]:
        return {i["id"] for i in client.get(f"/api/programs?{qs}").json()["items"]}

    assert ids("cip_family=11") == {"900001-110701", "900002-110101", "900003-111003"}
    assert ids("cip_family=30.70&cip_family=52.12") == {"900002-307001", "900001-521201"}
    assert ids("stem=not_eligible") == {"900001-521201"}
    assert len(ids("stem=eligible")) == 5
    assert ids("stem=unknown") == set()
    assert ids("q=houston") == {"900002-110101", "900002-307001"}
    assert ids("q=analytics") == {"900001-307101"}
    assert ids("state=CA") == set()
    page = client.get("/api/programs?limit=2&offset=4").json()
    assert page["total"] == 6 and len(page["items"]) == 2


def test_flag_and_negative_status(client: TestClient) -> None:
    item = client.get("/api/programs/900001-521201").json()
    assert item["flags"] == ["no_stem_opt_extension"]
    assert item["stem_opt"]["status"] == "confirmed_negative"
    assert item["stem_opt"]["value"]["eligible"] is False


def test_invalid_parameters(client: TestClient) -> None:
    assert client.get("/api/programs?limit=201").status_code == 422
    assert client.get("/api/programs?stem=maybe").status_code == 422
    assert client.get("/api/programs?cip_family=14").status_code == 422


def test_detail(client: TestClient) -> None:
    d = client.get("/api/programs/900001-110701").json()
    assert d["cip"]["isced_f"] == "0613"
    inst = d["institution"]
    assert inst["website"] == "https://www.lonestar-test.example/"
    assert inst["identifiers"]["unitid"] == "900001" and inst["identifiers"]["opeid"] == "09000100"
    assert inst["accreditation"]["value"]["accreditor"] == "SACSCOC"
    assert inst["carnegie_classification"] == {"value": None, "status": "unknown",
                                               "source_kind": None, "source_url": None,
                                               "evidence": None, "verified_at": None}
    camp = d["campus"]
    assert camp["locality"] == {"country": "US", "scheme": "us_county_fips", "code": "48453",
                                "name": "Travis County"}
    assert camp["sevp_campus_code"] == "DAL214F90000000"
    assert camp["intl_authorization"]["value"] == {"scheme": "sevp", "authorized": True}
    t = d["graduate_tuition_nonresident"]
    assert t["value"] == {"amount": 12000, "currency": "USD"}
    assert t["note_code"] == "institution_wide_average"
    assert "funding" in d["not_yet_collected"]
    assert [s["source"] for s in d["sources"]] == [
        "ipeds_hd", "ipeds_c_a", "ipeds_ic_ay", "dhs_stem_list", "sevp_csl", "dapip"]
    assert set(d["sources"][0]) == {"source", "file_version", "sha256", "uploaded_at", "rows"}
    assert d["sources"][0]["file_version"] == "HD2024" and d["sources"][0]["rows"] == 6


def test_detail_unknowns_stay_unknown(client: TestClient) -> None:
    d = client.get("/api/programs/900002-110101").json()
    assert d["graduate_tuition_nonresident"]["status"] == "unknown"
    assert d["graduate_tuition_nonresident"]["value"] is None
    assert d["institution"]["accreditation"]["status"] == "unknown"


def test_not_found(client: TestClient) -> None:
    r = client.get("/api/programs/000000-110701")
    assert r.status_code == 404 and r.json() == {"detail": "program not found"}


def test_sources(client: TestClient) -> None:
    rows = client.get("/api/sources").json()
    assert {r["source"] for r in rows} == {"ipeds_hd", "ipeds_c_a", "ipeds_ic_ay",
                                           "dhs_stem_list", "sevp_csl", "dapip"}
    assert all(set(r) == {"source", "file_version", "sha256", "uploaded_at", "rows"}
               for r in rows)
