"""Download the official US source files into a raw directory (design admin-and-sync, P1/P2/P7).

Fetching only produces files: ingestion reads them from disk exactly as it reads an upload
(FR-26), so a source that blocks automated download falls back to a manual copy into the same
layout without changing anything else.

Layout of the raw directory (the loaders find the newest file of each kind)::

    ipeds/HD<year>.zip, C<year>_A.zip, IC<year>_AY.zip and their *_Dict.zip
    sevp/certified-school-list-MM-DD-YY.pdf
    dhs/<name of the official PDF>
    dapip/extracted/InstitutionCampus.csv, AccreditationRecords.csv  (current version)
    dapip/DAPIPData-<date>.zip                                        (every version kept)
    manifest.jsonl     one line per download attempt (url, status, sha256, bytes, time)
    fetch-state.json   ETag / Last-Modified per URL, for conditional requests

Raw files are never overwritten: a file that changes under the same name (an IPEDS revision)
keeps its old bytes as "<stem>.<sha12><suffix>", which the loaders ignore.

Polite and honest client: a user-agent that names the project, conditional requests, retries
with backoff on network errors and 5xx only, no browser impersonation. A challenge page (HTTP
202, an empty body, HTML where a file was expected) is reported as "blocked".
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from north.ingest.us.common import sha256_file, sha256_files
from north.ingest.us.sevp_pdf import date_from_filename
from north.ingest.us.zipguard import check_member

USER_AGENT = "north-data-fetch/0.2 (+https://github.com/murilonegrao/north)"
MAX_BYTES = 512 << 20
TIMEOUT = 180

IPEDS_FILE = "https://nces.ed.gov/ipeds/datacenter/data/{name}.zip"
# Families the loaders read, and whether the loader also reads the family's dictionary (only
# C_A: CIP titles and the AWLEVEL check). The year is discovered by probing (no index exists).
IPEDS_FAMILIES = (("HD{y}", False), ("C{y}_A", True), ("IC{y}_AY", False))
IPEDS_LOOKBACK = 4
SEVP_PAGE = "https://studyinthestates.dhs.gov/school-search"
SEVP_HOST = "https://studyinthestates.dhs.gov"
SEVP_LINK = re.compile(rb"[\w/:.\-]*certified-school-list-\d{1,2}-\d{1,2}-\d{2,4}\.pdf")
DAPIP_URL = "https://ope.ed.gov/dapip/api/downloadFiles/accreditationDataFiles"
DAPIP_BODY = b'{"CSVChecked":true,"ExcelChecked":false}'
DAPIP_FILES = ("InstitutionCampus.csv", "AccreditationRecords.csv")


# The only hosts the fetcher talks to, redirects included (NetworkPolicy cannot filter by name,
# so this list is the allowlist). A new source adds its host here, in review.
ALLOWED_HOSTS = frozenset({
    "nces.ed.gov",
    "studyinthestates.dhs.gov",
    "www.ice.gov",
    "ope.ed.gov",
})


class HostNotAllowed(Exception):
    pass


def check_url(url: str) -> None:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise HostNotAllowed(f"refusing {parts.scheme}://{parts.hostname}: not an allowed source")


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_CheckedRedirect)


class Blocked(Exception):
    """The source answered with something that is not the file (a bot challenge)."""


class HttpStatus(Exception):
    def __init__(self, code: int, reason: str = "") -> None:
        super().__init__(f"HTTP {code} {reason}".strip())
        self.code = code


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


@dataclass
class Fetched:
    """Outcome of one file: new, unchanged, not_modified, changed, blocked, failed or missing."""

    source: str
    status: str
    url: str
    path: str | None = None
    sha256: str | None = None
    bytes: int | None = None
    note: str = ""
    at: str = field(default_factory=lambda: dt.datetime.now(dt.UTC).isoformat(timespec="seconds"))

    @property
    def ok(self) -> bool:
        return self.status in ("new", "unchanged", "not_modified")


Opener = Callable[[urllib.request.Request, float], Any]


def _urlopen(req: urllib.request.Request, timeout: float) -> Any:
    return _OPENER.open(req, timeout=timeout)  # allowed https hosts only, redirects checked


class Fetcher:
    """Downloads into a raw directory with conditional requests, retries and a manifest."""

    def __init__(self, raw: Path, *, opener: Opener = _urlopen,
                 sleep: Callable[[float], None] = time.sleep, tries: int = 3,
                 log: Callable[[str], None] = print) -> None:
        self.raw = raw
        self.opener = opener
        self.sleep = sleep
        self.tries = tries
        self.log = log
        self.results: list[Fetched] = []
        raw.mkdir(parents=True, exist_ok=True)
        self._state_path = raw / "fetch-state.json"
        try:
            self.state: dict[str, dict[str, str]] = json.loads(self._state_path.read_text())
        except (FileNotFoundError, ValueError):
            self.state = {}

    # ------------------------------------------------------------------ HTTP

    def request(self, url: str, *, method: str = "GET", data: bytes | None = None,
                headers: dict[str, str] | None = None) -> Response:
        """One request with retries on network errors and 5xx. 304 is returned, not raised."""
        check_url(url)
        h = {"User-Agent": USER_AGENT, **(headers or {})}
        last: Exception | None = None
        for attempt in range(1, self.tries + 1):
            req = urllib.request.Request(url, data=data, method=method, headers=h)
            try:
                with self.opener(req, TIMEOUT) as r:
                    body = r.read(MAX_BYTES + 1)
                    if len(body) > MAX_BYTES:
                        raise ValueError(f"over {MAX_BYTES} bytes; refusing")
                    return Response(r.status, {k.lower(): v for k, v in r.headers.items()}, body)
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    return Response(304, {}, b"")
                last = HttpStatus(e.code, str(e.reason))
                if e.code < 500:
                    break
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last = e
            if attempt < self.tries:
                self.sleep(5 * attempt)
        assert last is not None
        raise last

    def exists(self, url: str) -> bool:
        """Cheap check that a file is published: GET of its first byte. 404 means no."""
        try:
            r = self.request(url, headers={"Range": "bytes=0-0"})
        except HttpStatus as e:
            if e.code in (403, 404, 410):
                return False
            raise
        return r.status in (200, 206) and bool(r.body)

    # ------------------------------------------------------------------ files

    def download(self, source: str, url: str, dest: Path, *, method: str = "GET",
                 data: bytes | None = None, headers: dict[str, str] | None = None,
                 expect: bytes | None = None) -> Fetched:
        """Fetch url into dest; expect is the file's magic number (b"PK" for a zip)."""
        rel = str(dest.relative_to(self.raw))
        h = dict(headers or {})
        known = self.state.get(url, {})
        if dest.exists() and method == "GET":
            if known.get("etag"):
                h["If-None-Match"] = known["etag"]
            if known.get("last_modified"):
                h["If-Modified-Since"] = known["last_modified"]
        try:
            r = self.request(url, method=method, data=data, headers=h)
            if r.status == 304:
                return self.done(Fetched(source, "not_modified", url, rel,
                                         known.get("sha256"), dest.stat().st_size))
            check_body(r, expect)
        except Blocked as e:
            return self.done(Fetched(source, "blocked", url, note=str(e)))
        except Exception as e:  # network, HTTP status, size: reported, never raised
            return self.done(Fetched(source, "failed", url, note=f"{type(e).__name__}: {e}"[:200]))
        sha = hashlib.sha256(r.body).hexdigest()
        status = "new"
        if dest.exists():
            old = sha256_file(dest)
            if old == sha:
                status = "unchanged"
            else:
                dest.rename(dest.with_name(f"{dest.stem}.{old[:12]}{dest.suffix}"))
        if status == "new":
            write_atomic(dest, r.body)
        self.state[url] = {k: v for k, v in (("etag", r.headers.get("etag")),
                                             ("last_modified", r.headers.get("last-modified")),
                                             ("sha256", sha)) if v}
        return self.done(Fetched(source, status, url, rel, sha, len(r.body)))

    def done(self, f: Fetched) -> Fetched:
        """Record an outcome: results, manifest line, saved state and one log line."""
        self.results.append(f)
        with (self.raw / "manifest.jsonl").open("a", encoding="utf-8") as m:
            m.write(json.dumps(asdict(f), sort_keys=True) + "\n")
        write_atomic(self._state_path, json.dumps(self.state, indent=1, sort_keys=True).encode())
        self.log(f"{'OK  ' if f.ok else 'FAIL'} {f.source:<22} {f.status:<12} "
                 f"{(f.sha256 or '-')[:12]:<12} {f.bytes or '-':>10} {f.path or f.url} {f.note}")
        return f


def check_body(r: Response, expect: bytes | None) -> None:
    if r.status not in (200, 206) or not r.body:
        raise Blocked(f"HTTP {r.status} with {len(r.body)} bytes: challenge or empty body")
    if expect is not None and not r.body.startswith(expect):
        raise Blocked(f"body does not start with {expect!r} (an HTML page instead of the file?)")


def write_atomic(dest: Path, body: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(body)
        os.replace(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------- sources


def fetch_ipeds(f: Fetcher, today: dt.date | None = None) -> None:
    """Newest published year of each family (probing back from this year) and its dictionary."""
    year = (today or dt.date.today()).year
    for family, with_dict in IPEDS_FAMILIES:
        found = None
        for y in range(year, year - IPEDS_LOOKBACK, -1):
            name = family.format(y=y)
            try:
                if f.exists(IPEDS_FILE.format(name=name)):
                    found = name
                    break
            except Exception as e:
                f.done(Fetched(f"ipeds {name}", "failed", IPEDS_FILE.format(name=name),
                               note=f"probe: {type(e).__name__}: {e}"[:200]))
                break
        if found is None:
            f.done(Fetched(f"ipeds {family.format(y='')}", "missing", IPEDS_FILE.format(
                name=family.format(y=year)), note=f"no year in the last {IPEDS_LOOKBACK} found"))
            continue
        for name in (found, f"{found}_Dict") if with_dict else (found,):
            f.download(f"ipeds {name}", IPEDS_FILE.format(name=name),
                       f.raw / "ipeds" / f"{name}.zip", expect=b"PK")


def sevp_links(page: bytes) -> list[str]:
    """Absolute URLs of the certified school list PDFs linked from the search page."""
    out = []
    for m in SEVP_LINK.finditer(page):
        url = m.group(0).decode()
        if url.startswith("/"):
            url = SEVP_HOST + url
        if url.startswith("https://") and url not in out:
            out.append(url)
    return out


def newest_by_date(urls_or_paths: Iterable[Any]) -> Any | None:
    """The item whose file name carries the newest list date (MM-DD-YY does not sort as text)."""
    dated = [(d, x) for x in urls_or_paths
             if (d := date_from_filename(Path(str(x).rsplit("/", 1)[-1])))]
    return max(dated, key=lambda t: t[0])[1] if dated else None


def fetch_sevp(f: Fetcher) -> None:
    try:
        page = f.request(SEVP_PAGE)
        check_body(page, None)
    except Exception as e:
        f.done(Fetched("sevp search page", "failed", SEVP_PAGE, note=f"{type(e).__name__}: {e}"))
        return
    url = newest_by_date(sevp_links(page.body))
    if url is None:
        f.done(Fetched("sevp certified list", "missing", SEVP_PAGE,
                       note="no certified-school-list-*.pdf link on the page; layout changed?"))
        return
    f.download("sevp certified list", url, f.raw / "sevp" / url.rsplit("/", 1)[1], expect=b"%PDF")


def fetch_dhs_stem(f: Fetcher, meta_path: Path) -> Fetched:
    """The official STEM list PDF named in the reference meta; flags a changed file."""
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    url = str(meta["source_url"])
    got = f.download("dhs stem list", url, f.raw / "dhs" / url.rsplit("/", 1)[1], expect=b"%PDF")
    if got.ok and meta.get("file_sha256") and got.sha256 != meta["file_sha256"]:
        got.status = "changed"
        got.note = ("the official PDF changed: rebuild data/reference/dhs-stem-list-*.csv "
                    "(docs/sources/dhs-stem.md); the current reference CSV stays in use")
        f.log(f"NEW  dhs stem list: {got.note}")
    return got


def fetch_dapip(f: Fetcher, today: dt.date | None = None) -> None:
    """DAPIP regenerates its zip on every download (new sha256 each time), so the version's
    identity is the extracted CSVs: a new zip is kept only when they changed."""
    source = "dapip accreditation"
    try:
        r = f.request(DAPIP_URL, method="POST", data=DAPIP_BODY,
                      headers={"Content-Type": "application/json"})
        check_body(r, b"PK")
    except Blocked as e:
        f.done(Fetched(source, "blocked", DAPIP_URL, note=str(e)))
        return
    except Exception as e:
        f.done(Fetched(source, "failed", DAPIP_URL, note=f"{type(e).__name__}: {e}"[:200]))
        return
    base = f.raw / "dapip"
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base) as tmp:
        zpath = Path(tmp) / "dapip.zip"
        zpath.write_bytes(r.body)
        f.done(install_dapip_zip(f.raw, zpath, source=source, url=DAPIP_URL, today=today))


def install_dapip_zip(raw: Path, zpath: Path, *, source: str, url: str,
                      today: dt.date | None = None) -> Fetched:
    """Extract the two CSVs into dapip/extracted and keep the zip, unless they are unchanged.

    Shared by the download and the upload paths. The zip at zpath is moved (or left alone when
    the content is unchanged); the caller owns its directory.
    """
    base = raw / "dapip"
    current = base / "extracted"
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base) as tmp:
        tmpdir = Path(tmp)
        try:
            with zipfile.ZipFile(zpath) as z:
                names = {n.rsplit("/", 1)[-1].lower(): n for n in z.namelist()}
                for want in DAPIP_FILES:
                    member = names.get(want.lower())
                    if member is None:
                        raise ValueError(f"{want} missing from the zip")
                    check_member(z, member)
                    with z.open(member) as src, (tmpdir / want).open("wb") as dst:
                        shutil.copyfileobj(src, dst)
        except (zipfile.BadZipFile, ValueError) as e:
            return Fetched(source, "failed", url, note=str(e))
        new_files = [tmpdir / n for n in DAPIP_FILES]
        identity = sha256_files(new_files)
        size = sum(p.stat().st_size for p in new_files)
        old_files = [current / n for n in DAPIP_FILES]
        if all(p.exists() for p in old_files) and sha256_files(old_files) == identity:
            return Fetched(source, "unchanged", url, "dapip/extracted", identity, size,
                           note="identity = sha256 of the extracted CSVs")
        keep = base / f"DAPIPData-{(today or dt.date.today()).isoformat()}.zip"
        if not keep.exists():
            shutil.move(zpath, keep)
        current.mkdir(parents=True, exist_ok=True)
        for p in new_files:
            os.replace(p, current / p.name)
    return Fetched(source, "new", url, "dapip/extracted", identity, size,
                   note=f"zip kept as dapip/{keep.name}")


def place_file(raw: Path, src: Path, rel: str, *, source: str, url: str) -> Fetched:
    """Move a local file (an accepted upload) to raw/rel with the download's rules: the same
    bytes are "unchanged", different bytes keep the old file as <stem>.<sha12><suffix>."""
    dest = raw / rel
    sha = sha256_file(src)
    size = src.stat().st_size
    if dest.exists():
        old = sha256_file(dest)
        if old == sha:
            return Fetched(source, "unchanged", url, rel, sha, size)
        dest.rename(dest.with_name(f"{dest.stem}.{old[:12]}{dest.suffix}"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(src, dest)
    return Fetched(source, "new", url, rel, sha, size)


def fetch_all(raw: Path, dhs_meta: Path, *, fetcher: Fetcher | None = None,
              today: dt.date | None = None) -> list[Fetched]:
    """Every source the US loaders read. Failures are reported in the result, never raised."""
    f = fetcher or Fetcher(raw)
    fetch_ipeds(f, today)
    fetch_sevp(f)
    fetch_dhs_stem(f, dhs_meta)
    fetch_dapip(f, today)
    return f.results


# ---------------------------------------------------------------------- inputs


@dataclass
class Inputs:
    """The files a load uses, found in a raw directory (fetched or copied by hand)."""

    ipeds_dir: Path
    sevp_pdf: Path
    dapip_dir: Path
    dhs_pdf: Path | None


def inputs_from_raw(raw: Path, dhs_meta: Path) -> Inputs:
    """Newest file of each kind; raises FileNotFoundError naming what is missing."""
    missing = []
    ipeds_dir = raw / "ipeds"
    for pattern in (r"HD\d{4}\.zip", r"C\d{4}_A\.zip", r"IC\d{4}_AY\.zip"):
        if not ipeds_dir.is_dir() or not any(re.fullmatch(pattern, p.name, re.I)
                                             for p in ipeds_dir.iterdir()):
            missing.append(f"ipeds/{pattern}")
    sevp_pdf = newest_by_date((raw / "sevp").glob("certified-school-list-*.pdf"))
    if sevp_pdf is None:
        missing.append("sevp/certified-school-list-MM-DD-YY.pdf")
    dapip_dir = raw / "dapip" / "extracted"
    if not all((dapip_dir / n).is_file() for n in DAPIP_FILES):
        missing.append("dapip/extracted/{" + ",".join(DAPIP_FILES) + "}")
    if missing:
        raise FileNotFoundError("missing in " + str(raw) + ": " + ", ".join(missing))
    # The PDF goes to the loader only when it is the one the reference CSV was parsed from; a
    # changed PDF is reported by fetch_dhs_stem and the reference CSV stays in use.
    meta = json.loads(dhs_meta.read_text(encoding="utf-8"))
    pdf = raw / "dhs" / str(meta.get("source_url", "")).rsplit("/", 1)[-1]
    dhs_pdf = pdf if pdf.is_file() and sha256_file(pdf) == meta.get("file_sha256") else None
    return Inputs(ipeds_dir, sevp_pdf, dapip_dir, dhs_pdf)
