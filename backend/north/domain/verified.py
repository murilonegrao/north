"""VerifiedValue: the envelope every verifiable value carries (BR-02, record 0002/A1, R12, R13).

Pure helpers that build the JSON form stored in JSONB columns and served by the API.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class Status(StrEnum):
    CONFIRMED_OFFICIAL = "confirmed_official"
    REPORTED_BY_PROGRAM = "reported_by_program"
    EXTRACTED_UNVERIFIED = "extracted_unverified"
    UNKNOWN = "unknown"
    CONFIRMED_NEGATIVE = "confirmed_negative"


class SourceKind(StrEnum):
    PAGE = "page"
    OFFICIAL_LIST = "official_list"
    CORRESPONDENCE = "correspondence"
    UPLOADED_FILE = "uploaded_file"


# Values written by ingestion of official files. A value with any other source kind was set
# by a curator and is never overwritten by ingestion (UML 5.1: reconciliation task instead).
MACHINE_SOURCE_KINDS = frozenset({SourceKind.UPLOADED_FILE, SourceKind.OFFICIAL_LIST})


def verified(
    value: Any,
    status: Status,
    *,
    source_kind: SourceKind | None = None,
    source_url: str | None = None,
    evidence: str | None = None,
    verified_at: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a VerifiedValue dict and enforce the source rules of 0002/A4 and K10.

    A ``source_url`` is always an absolute http(s) URL: it is rendered as a link, so any other
    scheme (``javascript:``, ``data:``, ``file:``) is refused here, whatever the status.
    """
    if source_url is not None and not _is_http_url(source_url):
        raise ValueError(f"source_url must be an http(s) URL, got {source_url!r}")
    if status == Status.UNKNOWN:
        if value is not None:
            raise ValueError("unknown has no value")
    else:
        if value is None:
            raise ValueError(f"{status} needs a value")
        if status in (Status.CONFIRMED_OFFICIAL, Status.REPORTED_BY_PROGRAM,
                      Status.CONFIRMED_NEGATIVE):
            if source_kind is None or verified_at is None:
                raise ValueError(f"{status} needs source_kind and verified_at")
            if source_url is None and source_kind != SourceKind.CORRESPONDENCE:
                raise ValueError(f"{status} needs source_url")
        if status == Status.EXTRACTED_UNVERIFIED and (source_url is None or evidence is None):
            raise ValueError("extracted_unverified needs source_url and evidence")
    out: dict[str, Any] = {
        "value": value,
        "status": str(status),
        "source_kind": str(source_kind) if source_kind else None,
        "source_url": source_url,
        "evidence": evidence,
        "verified_at": verified_at,
    }
    out.update(extra)
    return out


def _is_http_url(url: object) -> bool:
    if not isinstance(url, str) or url != url.strip() or any(c.isspace() for c in url):
        return False
    scheme, sep, rest = url.partition("://")
    return bool(sep) and scheme.lower() in ("http", "https") and bool(rest.split("/")[0])


def unknown(**extra: Any) -> dict[str, Any]:
    return verified(None, Status.UNKNOWN, **extra)


def is_curated(value: dict[str, Any] | None) -> bool:
    """True when a stored value was set by a person (not by ingestion of an official file)."""
    if not value or value.get("status") == Status.UNKNOWN:
        return False
    return value.get("source_kind") not in MACHINE_SOURCE_KINDS
