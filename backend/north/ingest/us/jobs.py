"""US job kinds and schedules for the worker (registered in north.jobs.registry)."""

from __future__ import annotations

import dataclasses
import re
import zipfile
from pathlib import Path
from typing import Any

from north.ingest.us.states import STATE_NAMES
from north.jobs.registry import JobKind, Param, ScheduleSpec, next_weekday_at

COUNTRY = "US"
UPLOAD_KIND = "us.accept_upload"


def _states(raw: Any) -> list[str]:
    text = str(raw or "ALL").strip().upper()
    if text == "ALL":
        return sorted(STATE_NAMES)
    codes = sorted({c.strip() for c in text.split(",") if c.strip()})
    unknown = [c for c in codes if c not in STATE_NAMES]
    if unknown or not codes:
        raise ValueError(f"unknown state code(s): {', '.join(unknown) or text}")
    return codes


def _validate_sync(p: dict[str, Any]) -> dict[str, Any]:
    states = str(p.get("states") or "ALL").strip().upper()
    _states(states)
    return {"states": states, "fetch": bool(p.get("fetch", True))}


def _paths(ctx: Any) -> tuple[Path, Path]:
    from north.ingest.us import dhs_stem
    from north.ingest.us.cli import default_dhs_csv

    csv = default_dhs_csv()
    return csv, dhs_stem.default_meta_path(csv)


def _fetch(ctx: Any) -> list[dict[str, Any]]:
    from north.ingest.us.fetch import Fetcher, fetch_all

    _, meta = _paths(ctx)
    fetcher = Fetcher(ctx.raw(), log=ctx.log)
    return [dataclasses.asdict(r) | {"ok": r.ok} for r in fetch_all(ctx.raw(), meta,
                                                                    fetcher=fetcher)]


def run_fetch(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    fetched = _fetch(ctx)
    bad = [r for r in fetched if not r["ok"]]
    return {"fetched": fetched, "needs_attention": len(bad)}


def run_sync(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    from north.ingest.us.cli import default_isced, load_all
    from north.ingest.us.fetch import inputs_from_raw

    out: dict[str, Any] = {"states": params["states"]}
    bad = 0
    if params.get("fetch", True):
        fetched = _fetch(ctx)
        out["fetched"] = fetched
        bad = sum(not r["ok"] for r in fetched)
    dhs_csv, meta = _paths(ctx)
    inp = inputs_from_raw(ctx.raw(), meta)
    ctx.checkpoint()
    with ctx.sessions() as s:
        ok = load_all(s, _states(params["states"]), ipeds_dir=inp.ipeds_dir, dhs_csv=dhs_csv,
                      dhs_meta=meta, dhs_pdf=inp.dhs_pdf, sevp_file=inp.sevp_pdf,
                      dapip_path=inp.dapip_dir, isced_csv=default_isced(), emit=ctx.log)
    if not ok:
        raise RuntimeError("a load step failed; see the log")
    out["needs_attention"] = bad
    return out


def run_recompute(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    from north.ingest.us.eligibility import recompute_stem_eligibilities

    with ctx.sessions() as s:
        n = recompute_stem_eligibilities(s, author="admin:recompute")
        s.commit()
    ctx.log(f"recomputed us.stem_opt for {n} programs")
    return {"programs": n}


# ------------------------------------------------------------------------------ uploads

IPEDS_NAME = re.compile(r"^(HD\d{4}|C\d{4}_A|IC\d{4}_AY)(_Dict)?\.zip$", re.I)
SEVP_NAME = re.compile(r"^certified-school-list-\d{1,2}-\d{1,2}-\d{2,4}\.pdf$", re.I)
HUD_NAME = re.compile(r"^FY\d{2}_(FMRs|safmrs)[\w-]*\.xlsx$", re.I)
UPLOAD_NAME = re.compile(r"^[0-9a-f]{32}__(?P<name>[\w.\-]{1,120})$")


def destination(name: str, head: bytes, path: Path, dhs_pdf_name: str) -> tuple[str, str]:
    """(kind, relative destination) for an uploaded file, from its name and first bytes.

    Raises ValueError with a message for the admin when the file is not recognised."""
    is_zip, is_pdf = head.startswith(b"PK"), head.startswith(b"%PDF")
    if IPEDS_NAME.match(name):
        if not is_zip:
            raise ValueError(f"{name}: an IPEDS file must be a zip")
        return "ipeds", f"ipeds/{name}"
    if SEVP_NAME.match(name):
        if not is_pdf:
            raise ValueError(f"{name}: the SEVP list must be a PDF")
        return "sevp", f"sevp/{name.lower()}"
    if name == dhs_pdf_name:
        if not is_pdf:
            raise ValueError(f"{name}: the DHS STEM list must be a PDF")
        return "dhs", f"dhs/{name}"
    if HUD_NAME.match(name):
        if not is_zip:  # xlsx is a zip container
            raise ValueError(f"{name}: not an xlsx file")
        return "hud", f"hud/{name}"
    if is_zip:
        try:
            with zipfile.ZipFile(path) as z:
                members = {n.rsplit("/", 1)[-1].lower() for n in z.namelist()}
        except zipfile.BadZipFile:
            raise ValueError(f"{name}: damaged zip") from None
        if {"institutioncampus.csv", "accreditationrecords.csv"} <= members:
            return "dapip", "dapip/extracted"
    raise ValueError(
        f"{name}: not recognised. Expected an IPEDS zip (HD2024.zip, C2024_A.zip, IC2024_AY.zip"
        f" or their _Dict), certified-school-list-MM-DD-YY.pdf, {dhs_pdf_name}, the DAPIP zip,"
        " or a HUD FY??_FMRs xlsx")


def _validate_upload(p: dict[str, Any]) -> dict[str, Any]:
    file = str(p.get("file", ""))
    if not UPLOAD_NAME.match(file):
        raise ValueError("invalid upload reference")
    sha = str(p.get("sha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ValueError("invalid sha256")
    return {"file": file, "sha256": sha, "by": str(p.get("by", ""))[:64]}


def run_accept_upload(ctx: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Move an uploaded file from incoming/ into the raw layout, with the download's rules."""
    import json

    from north.ingest.us.common import sha256_file
    from north.ingest.us.fetch import Fetched, Fetcher, install_dapip_zip, place_file

    src = ctx.incoming() / params["file"]
    if not src.is_file():
        raise FileNotFoundError(f"upload {params['file']} is no longer in incoming/")
    try:
        name = UPLOAD_NAME.match(params["file"]).group("name")  # type: ignore[union-attr]
        if sha256_file(src) != params["sha256"]:
            raise ValueError("the stored upload does not match its sha256")
        _, meta = _paths(ctx)
        dhs_name = str(json.loads(meta.read_text(encoding="utf-8"))["source_url"]).rsplit("/", 1)[1]
        with src.open("rb") as fh:
            head = fh.read(8)
        kind, rel = destination(name, head, src, dhs_name)
        ctx.log(f"{name}: recognised as {kind}")
        raw = ctx.raw()
        url = f"upload:{params.get('by') or 'admin'}"
        source = f"upload {kind}"
        if kind == "dapip":
            got = install_dapip_zip(raw, src, source=source, url=url)
        else:
            got = place_file(raw, src, rel, source=source, url=url)
        Fetcher(raw, log=ctx.log).done(got)
        if isinstance(got, Fetched) and got.status == "failed":
            raise ValueError(got.note)
        return {"file": name, "kind": kind, "status": got.status, "path": got.path,
                "sha256": got.sha256, "note": got.note,
                "next": "run a sync without download to load it" if kind != "hud"
                        else "kept for the HUD loader (not built yet)"}
    finally:
        if src.exists():
            src.unlink()


KINDS = [
    JobKind("us.fetch", "Download official files",
            "Downloads IPEDS, SEVP, the DHS STEM list and DAPIP into the raw store. "
            "Nothing changes in the database.", run_fetch),
    JobKind("us.sync", "Download and load",
            "Downloads (optional) and loads every source for the chosen states. Files already "
            "loaded for a state are skipped.", run_sync, _validate_sync,
            params=(Param("states", "text", "ALL", "USPS codes, comma-separated, or ALL"),
                    Param("fetch", "bool", True, "download first"))),
    JobKind("us.recompute", "Recompute STEM OPT eligibility",
            "Recomputes us.stem_opt for every program under the current rule.",
            run_recompute, min_role="admin"),
    JobKind(UPLOAD_KIND, "Accept an uploaded file",
            "Moves an uploaded official file into the raw store.", run_accept_upload,
            _validate_upload, manual=False),
]

SCHEDULES = [
    ScheduleSpec("us-sync-weekly", "us.sync", every_hours=24 * 7,
                 params={"states": "ALL", "fetch": True}, first_run=next_weekday_at(0, 6)),
]


def overview(session: Any) -> dict[str, Any]:
    from north.ingest.us.report import report

    return report(session)

