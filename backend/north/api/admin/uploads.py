"""Upload of an official file (FR-26): streamed to incoming/, then a worker job places it.

The body is the raw file (not multipart): it is written as it arrives, capped in size, hashed
on the way, and never parsed by the web process (P3).
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from north.api.admin.deps import Curator
from north.api.admin.jobs import job_view
from north.auth import audit
from north.jobs import queue, registry
from north.repository.models import Job
from north.settings import get_settings

router = APIRouter()

SAFE_NAME = re.compile(r"^[\w.\-]{1,120}$")


@router.put("/uploads")
async def upload(request: Request, auth: Curator,
                 filename: str = Query(max_length=120), country: str = "US") -> object:
    settings = get_settings()
    incoming = settings.incoming_dir
    if incoming is None:
        raise HTTPException(503, "uploads are not configured on this server")
    kind = registry.upload_kind().get(country.upper())
    if kind is None:
        raise HTTPException(400, "unknown country")
    name = os.path.basename(filename)
    if not SAFE_NAME.match(name) or name.startswith("."):
        raise HTTPException(400, "file name: letters, digits, dot, dash and underscore only")
    cap = settings.upload_max_mib << 20
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > cap:
        raise HTTPException(413, f"larger than {settings.upload_max_mib} MiB")
    incoming.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}__{name}"
    part = incoming / f".{stored}.part"
    digest, size = hashlib.sha256(), 0
    try:
        with part.open("xb") as out:
            async for chunk in request.stream():
                size += len(chunk)
                if size > cap:
                    raise HTTPException(413, f"larger than {settings.upload_max_mib} MiB")
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise HTTPException(400, "empty file")
        os.replace(part, incoming / stored)
    finally:
        part.unlink(missing_ok=True)
    sha = digest.hexdigest()

    def record() -> Job:
        audit.record(auth.db, "file_uploaded", actor=auth.user, target=name, ip=auth.ip,
                     sha256=sha, bytes=size)
        return queue.enqueue(auth.db, kind, {"file": stored, "sha256": sha,
                                             "by": auth.user.username},
                             actor=auth.user, ip=auth.ip, allow_parallel=True)

    job = await run_in_threadpool(record)
    return JSONResponse(jsonable_encoder(job_view(job, {auth.user.id: auth.user.username}) |
                                         {"sha256": sha, "bytes": size}), status_code=201)
