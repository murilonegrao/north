"""Ireland job kinds for the worker (registered in north.jobs.registry).

The ILEP and TrustEd lists are uploaded by an admin (FR-26): ``ie.accept_upload`` recognises
the file, keeps a copy under ``<raw>/ie/<source>/`` and loads it at once. ``ie.load`` reloads
the newest stored file of each list (a file already loaded is skipped, NFR-03). No automatic
download in this slice.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from north.jobs.registry import JobKind

COUNTRY = "IE"
UPLOAD_KIND = "ie.accept_upload"
UPLOAD_NAME = re.compile(r"^[0-9a-f]{32}__(?P<name>[\w.\-]{1,120})$")
SOURCES = ("ie_ilep", "ie_trusted")


def recognise(name: str, path: Path) -> str:
    """``ie_ilep`` or ``ie_trusted`` from the file's first header cell (the two lists have the
    same columns except that one); ValueError with a message for the admin otherwise."""
    from north.ingest.ie.lists import read_list

    if not name.lower().endswith(".xlsx"):
        raise ValueError(f"{name}: expected the ILEP or TrustEd Ireland .xlsx list")
    with path.open("rb") as fh:
        if not fh.read(2).startswith(b"PK"):
            raise ValueError(f"{name}: not an xlsx file")
    header = read_list(path).first_header
    if header.startswith("programme reference"):
        return "ie_ilep"
    if header.startswith("programme ref"):
        return "ie_trusted"
    raise ValueError(f"{name}: not recognised (first column {header!r})")


def _validate_upload(p: dict[str, Any]) -> dict[str, Any]:
    file = str(p.get("file", ""))
    if not UPLOAD_NAME.match(file):
        raise ValueError("invalid upload reference")
    sha = str(p.get("sha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("invalid sha256")
    return {"file": file, "sha256": sha, "by": str(p.get("by", ""))[:64]}


def _load(ctx: Any, source: str, path: Path) -> dict[str, Any]:
    from north.ingest.ie.load import ingest_list

    with ctx.sessions() as s:
        result = ingest_list(s, path, source)
    ctx.log(f"{source} {result.file_version}: {result.status} {result.counts}")
    if result.status == "failed":
        raise RuntimeError("; ".join(result.errors) or f"{source} failed")
    return result.as_dict()


def run_accept_upload(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    from north.ingest.common import sha256_file

    src = ctx.incoming() / params["file"]
    if not src.is_file():
        raise FileNotFoundError(f"upload {params['file']} is no longer in incoming/")
    try:
        name = UPLOAD_NAME.match(params["file"]).group("name")  # type: ignore[union-attr]
        if sha256_file(src) != params["sha256"]:
            raise ValueError("the stored upload does not match its sha256")
        source = recognise(name, src)
        ctx.log(f"{name}: recognised as {source}")
        dest = ctx.raw() / "ie" / source / f"{params['sha256'][:12]}__{name}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        return {"file": name, "kind": source, "path": str(dest.relative_to(ctx.raw())),
                "load": _load(ctx, source, dest)}
    finally:
        if src.exists():
            src.unlink()


def run_load(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for source in SOURCES:
        files = sorted((ctx.raw() / "ie" / source).glob("*.xlsx"),
                       key=lambda p: p.stat().st_mtime)
        if not files:
            ctx.log(f"{source}: no file uploaded yet")
            continue
        out[source] = _load(ctx, source, files[-1])
    return out


KINDS = [
    JobKind("ie.load", "Load the Irish lists",
            "Loads the newest uploaded ILEP and TrustEd Ireland files (English courses). Files "
            "already loaded are skipped.", run_load),
    JobKind(UPLOAD_KIND, "Accept an uploaded Irish list",
            "Recognises an uploaded ILEP or TrustEd Ireland file, stores it and loads it.",
            run_accept_upload, _validate_upload, manual=False),
]

SCHEDULES: list[Any] = []


def overview(session: Any) -> dict[str, Any]:
    from north.ingest.report import report

    return report(session, COUNTRY)
