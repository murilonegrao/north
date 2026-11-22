"""The official-file fetcher with a fake network: storage rules, conditional requests, blocks."""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from north.ingest.us import fetch
from north.ingest.us.fetch import Fetcher, HostNotAllowed, check_url

URL = "https://nces.ed.gov/ipeds/datacenter/data/HD2024.zip"


class FakeResponse(io.BytesIO):
    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None) -> None:
        super().__init__(body)
        self.status = status
        self.headers = headers or {}


class FakeNet:
    """Answers queued per URL; records the requests."""

    def __init__(self) -> None:
        self.answers: dict[str, list[Any]] = {}
        self.requests: list[Any] = []

    def add(self, url: str, *answers: Any) -> None:
        self.answers.setdefault(url, []).extend(answers)

    def __call__(self, req: Any, timeout: float) -> FakeResponse:
        self.requests.append(req)
        answer = self.answers[req.full_url].pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(URL, code, "x", {}, None)  # type: ignore[arg-type]


@pytest.fixture
def net() -> FakeNet:
    return FakeNet()


def fetcher(tmp_path: Path, net: FakeNet) -> Fetcher:
    return Fetcher(tmp_path / "raw", opener=net, sleep=lambda s: None, log=lambda s: None)


def test_new_unchanged_changed_and_not_modified(tmp_path: Path, net: FakeNet) -> None:
    f = fetcher(tmp_path, net)
    dest = f.raw / "ipeds" / "HD2024.zip"
    net.add(URL, FakeResponse(200, b"PK v1", {"ETag": '"a"'}))
    assert f.download("hd", URL, dest, expect=b"PK").status == "new"
    net.add(URL, FakeResponse(200, b"PK v1", {"ETag": '"a"'}))
    assert f.download("hd", URL, dest, expect=b"PK").status == "unchanged"
    assert net.requests[-1].headers["If-none-match"] == '"a"'
    net.add(URL, http_error(304))
    assert f.download("hd", URL, dest, expect=b"PK").status == "not_modified"
    net.add(URL, FakeResponse(200, b"PK v2"))
    assert f.download("hd", URL, dest, expect=b"PK").status == "new"
    assert dest.read_bytes() == b"PK v2"
    kept = [p.name for p in dest.parent.iterdir() if p.name != "HD2024.zip"]
    assert len(kept) == 1 and kept[0].startswith("HD2024.") and kept[0].endswith(".zip")
    lines = (f.raw / "manifest.jsonl").read_text().splitlines()
    assert [json.loads(x)["status"] for x in lines] == ["new", "unchanged", "not_modified", "new"]
    assert "User-agent" in net.requests[0].headers


def test_blocked_and_failed(tmp_path: Path, net: FakeNet) -> None:
    f = fetcher(tmp_path, net)
    dest = f.raw / "x.zip"
    net.add(URL, FakeResponse(202, b""))
    assert f.download("hd", URL, dest, expect=b"PK").status == "blocked"
    net.add(URL, FakeResponse(200, b"<html>challenge</html>"))
    assert f.download("hd", URL, dest, expect=b"PK").status == "blocked"
    net.add(URL, http_error(404))
    got = f.download("hd", URL, dest, expect=b"PK")
    assert got.status == "failed" and "404" in got.note
    assert not dest.exists()


def test_retries_5xx_but_not_4xx(tmp_path: Path, net: FakeNet) -> None:
    f = fetcher(tmp_path, net)
    net.add(URL, http_error(503), urllib.error.URLError("reset"), FakeResponse(200, b"PK ok"))
    assert f.download("hd", URL, f.raw / "a.zip", expect=b"PK").status == "new"
    assert len(net.requests) == 3
    net.add(URL, http_error(403))
    assert f.download("hd", URL, f.raw / "b.zip", expect=b"PK").status == "failed"
    assert len(net.requests) == 4


def test_only_allowed_hosts() -> None:
    check_url(URL)
    for bad in ("http://nces.ed.gov/x.zip", "https://evil.example/x.zip",
                "https://nces.ed.gov.evil.example/x", "file:///etc/passwd"):
        with pytest.raises(HostNotAllowed):
            check_url(bad)


def test_redirect_to_another_host_is_refused() -> None:
    import urllib.request

    handler = fetch._CheckedRedirect()
    req = urllib.request.Request(URL)
    with pytest.raises(HostNotAllowed):
        handler.redirect_request(req, None, 302, "Found", {}, "https://evil.example/x.zip")


def test_sevp_links_and_newest() -> None:
    page = (b'<a href="/assets/certified-school-list-9-1-26.pdf">old</a>'
            b'<a href="/assets/certified-school-list-11-18-26.pdf">new</a>'
            b'<a href="https://elsewhere/certified-school-list-12-1-26.pdf">x</a>')
    links = fetch.sevp_links(page)
    assert links[0] == "https://studyinthestates.dhs.gov/assets/certified-school-list-9-1-26.pdf"
    assert fetch.newest_by_date(links[:2]).endswith("11-18-26.pdf")


def test_inputs_from_raw_names_what_is_missing(tmp_path: Path) -> None:
    meta = tmp_path / "m.json"
    meta.write_text(json.dumps({"source_url": "https://www.ice.gov/x/stemList2024.pdf"}))
    with pytest.raises(FileNotFoundError) as e:
        fetch.inputs_from_raw(tmp_path / "raw", meta)
    for part in ("ipeds/", "sevp/", "dapip/"):
        assert part in str(e.value)
