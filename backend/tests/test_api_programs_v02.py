"""Contract v0.2: list price, new filters, sorting, facets (needs NORTH_TEST_DATABASE_URL).

The synthetic load has six TX programs:

    900001 Lone Star (Austin, public, tuition 12000, SEVP confirmed, accredited)
        110701 12/8 graduates, 521201 3/0, 307101 0/0
    900002 Gulf Coast (Houston, private nonprofit, tuition unknown, SEVP negative, accr. unknown)
        110101 20/15, 307001 5/2
    900003 Prairie (Dallas, private for-profit, tuition 30000, SEVP unknown, accredited)
        111003 4/1
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from north.api.app import app
from north.repository.db import session_scope
from north.repository.models import Program

ALL = {"900001-110701", "900001-521201", "900001-307101",
       "900002-110101", "900002-307001", "900003-111003"}
LONE_STAR = {"900001-110701", "900001-521201", "900001-307101"}
GULF = {"900002-110101", "900002-307001"}


@pytest.fixture
def client(session: Session, loaded: dict) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        yield session

    app.dependency_overrides[session_scope] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def ids(client: TestClient, qs: str) -> set[str]:
    r = client.get(f"/api/programs?{qs}")
    assert r.status_code == 200, r.text
    return {i["id"] for i in r.json()["items"]}


def order(client: TestClient, qs: str) -> list[str]:
    r = client.get(f"/api/programs?{qs}")
    assert r.status_code == 200, r.text
    return [i["id"] for i in r.json()["items"]]


def test_list_items_carry_tuition(client: TestClient) -> None:
    items = {i["id"]: i for i in client.get("/api/programs").json()["items"]}
    t = items["900001-110701"]["graduate_tuition_nonresident"]
    assert t["value"] == {"amount": 12000, "currency": "USD"}
    assert t["status"] == "confirmed_official"
    assert t["note_code"] == "institution_wide_average"
    assert t["source_url"] and t["verified_at"]
    assert "evidence" not in t
    unknown = items["900002-110101"]["graduate_tuition_nonresident"]
    assert unknown["value"] is None and unknown["status"] == "unknown"
    assert unknown["note_code"] == "institution_wide_average"


def test_filter_control(client: TestClient) -> None:
    assert ids(client, "control=public") == LONE_STAR
    assert ids(client, "control=private_nonprofit&control=private_for_profit") == (
        GULF | {"900003-111003"})


def test_filter_city(client: TestClient) -> None:
    assert ids(client, "city=Houston") == GULF
    assert ids(client, "city=Houston&city=Dallas") == GULF | {"900003-111003"}
    assert ids(client, "city=houston") == set()  # exact name as served
    assert ids(client, "city=Austin%27%20OR%201%3D1--") == set()  # bound, not SQL


def test_filter_tuition_range_excludes_unknown(client: TestClient) -> None:
    assert ids(client, "min_tuition=0") == LONE_STAR | {"900003-111003"}
    assert ids(client, "min_tuition=12000&max_tuition=12000") == LONE_STAR
    assert ids(client, "min_tuition=12000.5") == {"900003-111003"}
    assert ids(client, "max_tuition=29999") == LONE_STAR
    assert ids(client, "max_tuition=100") == set()


def test_filter_sevp(client: TestClient) -> None:
    assert ids(client, "sevp=confirmed") == LONE_STAR
    # confirmed_negative (Gulf Coast) is neither confirmed nor unknown.
    assert ids(client, "sevp=unknown") == {"900003-111003"}


def test_filter_accredited(client: TestClient) -> None:
    assert ids(client, "accredited=true") == LONE_STAR | {"900003-111003"}
    assert ids(client, "accredited=unknown") == GULF


def test_filter_has_graduates(client: TestClient) -> None:
    assert ids(client, "has_graduates=false") == {"900001-307101"}
    assert ids(client, "has_graduates=true") == ALL - {"900001-307101"}


def test_filters_combine(client: TestClient) -> None:
    assert ids(client, "control=public&has_graduates=true&cip_family=11") == {"900001-110701"}
    body = client.get("/api/programs?control=public&limit=1").json()
    assert body["total"] == 3 and len(body["items"]) == 1


def test_default_sort_is_title_with_stable_ties(client: TestClient) -> None:
    titles = [i["title"] for i in client.get("/api/programs").json()["items"]]
    assert titles == sorted(titles, key=str.casefold)  # database collation, not byte order
    assert order(client, "") == order(client, "sort=title&order=asc")


def test_sort_tuition_unknown_last_both_orders(client: TestClient) -> None:
    asc = order(client, "sort=tuition")
    desc = order(client, "sort=tuition&order=desc")
    # Ties (Lone Star, 12000) break by institution name, then program id.
    assert asc == ["900001-110701", "900001-307101", "900001-521201", "900003-111003",
                   "900002-110101", "900002-307001"]
    assert desc == ["900003-111003", "900001-110701", "900001-307101", "900001-521201",
                    "900002-110101", "900002-307001"]


def test_sort_city_and_institution(client: TestClient) -> None:
    cities = [i["campus"]["city"] for i in client.get("/api/programs?sort=city").json()["items"]]
    assert cities == ["Austin"] * 3 + ["Dallas", "Houston", "Houston"]
    names = [i["institution"]["name"]
             for i in client.get("/api/programs?sort=institution&order=desc").json()["items"]]
    assert names == sorted(names, reverse=True)


def test_sort_graduates(client: TestClient) -> None:
    assert order(client, "sort=graduates&order=desc")[:2] == ["900002-110101", "900001-110701"]
    assert order(client, "sort=graduates")[0] == "900001-307101"
    assert order(client, "sort=nonresident_graduates&order=desc")[0] == "900002-110101"


def test_sort_nonresident_share(client: TestClient) -> None:
    # 15/20, 8/12, 2/5, 1/4, 0/3; 0/0 is undefined and goes last in both orders.
    desc = order(client, "sort=nonresident_share&order=desc")
    assert desc == ["900002-110101", "900001-110701", "900002-307001", "900003-111003",
                    "900001-521201", "900001-307101"]
    asc = order(client, "sort=nonresident_share&order=asc")
    assert asc == ["900001-521201", "900003-111003", "900002-307001", "900001-110701",
                   "900002-110101", "900001-307101"]


def test_unknown_completions_sort_last(client: TestClient, session: Session) -> None:
    prog = session.get(Program, "900002-110101")
    assert prog is not None
    prog.academic = {**prog.academic, "completions": {"value": None, "status": "unknown"}}
    session.flush()
    for key in ("graduates", "nonresident_graduates", "nonresident_share"):
        for direction in ("asc", "desc"):
            got = order(client, f"sort={key}&order={direction}")
            # The share of 0/0 is undefined too; both unknowns tie, Gulf Coast first by name.
            tail = got[-2:] if key == "nonresident_share" else got[-1:]
            assert "900002-110101" in tail, (key, direction, got)
    # Unknown completions are neither "has graduates" nor "has none" (BR-02).
    assert "900002-110101" not in ids(client, "has_graduates=true")
    assert "900002-110101" not in ids(client, "has_graduates=false")


def test_pages_are_stable(client: TestClient) -> None:
    full = order(client, "sort=tuition&limit=200")
    paged = [pid for off in range(0, 6, 2)
             for pid in order(client, f"sort=tuition&limit=2&offset={off}")]
    assert paged == full


def test_facets(client: TestClient) -> None:
    f = client.get("/api/facets").json()
    assert f == {
        "state": "TX",
        "total": 6,
        "cip_family": {"11": 3, "30.70": 1, "30.71": 1, "52.12": 1},
        "control": {"public": 3, "private_nonprofit": 2, "private_for_profit": 1},
        "cities": [{"city": "Austin", "count": 3}, {"city": "Houston", "count": 2},
                   {"city": "Dallas", "count": 1}],
        "stem": {"eligible": 5, "not_eligible": 1, "unknown": 0},
        "sevp": {"confirmed": 3, "unknown": 1},
        "accredited": {"true": 4, "unknown": 2},
        "has_graduates": {"true": 5, "false": 1},
        "tuition": {"min": 12000, "max": 30000, "known": 4, "unknown": 2, "currency": "USD"},
    }


def test_facets_match_filters(client: TestClient) -> None:
    f = client.get("/api/facets").json()
    for group, param in (("control", "control"), ("sevp", "sevp"), ("accredited", "accredited"),
                         ("has_graduates", "has_graduates"), ("stem", "stem"),
                         ("cip_family", "cip_family")):
        for value, n in f[group].items():
            assert client.get(f"/api/programs?{param}={value}").json()["total"] == n
    for c in f["cities"]:
        assert client.get("/api/programs", params={"city": c["city"]}).json()["total"] == c["count"]


def test_facets_other_state_and_filters_ignored(client: TestClient) -> None:
    ca = client.get("/api/facets?state=ca").json()
    assert ca["state"] == "CA" and ca["total"] == 0 and ca["cities"] == []
    assert ca["tuition"] == {"min": None, "max": None, "known": 0, "unknown": 0,
                             "currency": "USD"}
    assert client.get("/api/facets?control=public").json()["total"] == 6
    assert client.get("/api/facets?state=Texas").status_code == 422


@pytest.mark.parametrize("qs", [
    "sort=price", "sort=title;drop table programs", "order=up", "control=state",
    "sevp=yes", "accredited=false", "has_graduates=maybe", "min_tuition=-1",
    "max_tuition=-0.01", "min_tuition=abc", "min_tuition=5000&max_tuition=4000",
    "min_tuition=1e12", "limit=201", "limit=0", "offset=-1", f"city={'x' * 121}",
])
def test_invalid_parameters_v02(client: TestClient, qs: str) -> None:
    r = client.get(f"/api/programs?{qs}")
    assert r.status_code == 422, (qs, r.text)
    assert isinstance(r.json()["detail"], list)


def test_too_many_cities(client: TestClient) -> None:
    r = client.get("/api/programs", params=[("city", f"C{n}") for n in range(51)])
    assert r.status_code == 422


def test_null_nonresident_is_unknown(client: TestClient, session: Session) -> None:
    prog = session.get(Program, "900002-110101")
    assert prog is not None
    c = prog.academic["completions"]
    prog.academic = {**prog.academic,
                     "completions": {**c, "value": {**c["value"], "nonresident": None}}}
    session.flush()
    item = next(i for i in client.get("/api/programs").json()["items"]
                if i["id"] == "900002-110101")
    assert item["completions"]["value"] == {"total": 20, "nonresident": None, "year": "2023-24"}
    for direction in ("asc", "desc"):
        assert order(client, f"sort=nonresident_graduates&order={direction}")[-1] == (
            "900002-110101")
        # Share: unknown, ties with the undefined 0/0 share at the end.
        assert "900002-110101" in order(client, f"sort=nonresident_share&order={direction}")[-2:]
    # The total is still known, so the program still has graduates.
    assert "900002-110101" in ids(client, "has_graduates=true")
