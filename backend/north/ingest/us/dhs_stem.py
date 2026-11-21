"""DHS STEM Designated Degree Program List -> rule ``us.stem_opt`` (record 0002/A14).

Input: the CSV parsed from the official PDF (``data/reference/dhs-stem-list-<date>.csv``, built by
``spikes/s3_dhs_stem/parse_stem_list.py``) and its ``.meta.json`` (URL, date, whole series).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from north.domain.countries.us.cip import is_cip6
from north.domain.countries.us.stem import RULE_KEY
from north.ingest.us.common import (
    COUNTRY,
    RunContext,
    StepResult,
    ensure_country,
    read_csv_rows,
    run_step,
    sha256_file,
)
from north.ingest.us.eligibility import recompute_stem_eligibilities
from north.ingest.us.ipeds import ensure_cip
from north.repository.models import Classification, EligibilityRule, EligibilityRuleCode


def default_meta_path(csv_path: Path) -> Path:
    return csv_path.with_name(csv_path.stem + ".meta.json")


SERIES_RE = re.compile(r"^\d{2}$")
URL_RE = re.compile(r"^https://")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def load_meta(meta_path: Path, today: dt.date | None = None) -> dict[str, Any]:
    """Read and validate the ``.meta.json`` written next to the CSV (refuse anything odd)."""
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if not isinstance(meta, dict):
        raise ValueError(f"{meta_path.name}: not a JSON object")
    today = today or dt.date.today()
    source_url = meta.get("source_url")
    if not isinstance(source_url, str) or not URL_RE.match(source_url):
        raise ValueError(f"{meta_path.name}: source_url must start with https://")
    version = meta.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(f"{meta_path.name}: version is required")
    raw_date = meta.get("published_on") or version
    try:
        published = dt.date.fromisoformat(str(raw_date))
    except ValueError:
        raise ValueError(f"{meta_path.name}: published_on {raw_date!r} is not a date") from None
    if published > today:
        raise ValueError(f"{meta_path.name}: published_on {published} is in the future")
    series = meta.get("whole_series_included", [])
    if not isinstance(series, list) or not all(
            isinstance(x, str) and SERIES_RE.match(x) for x in series):
        raise ValueError(f"{meta_path.name}: whole_series_included must be two-digit strings")
    sha = meta.get("file_sha256")
    if sha is not None and (not isinstance(sha, str) or not SHA256_RE.match(sha)):
        raise ValueError(f"{meta_path.name}: file_sha256 is not a sha256 hex digest")
    return {**meta, "published_on": published.isoformat()}


def verify_pdf(pdf_path: Path, meta: dict[str, Any]) -> None:
    """The official PDF must be the one the CSV was parsed from (meta ``file_sha256``)."""
    expected = meta.get("file_sha256")
    if not expected:
        raise ValueError("the meta has no file_sha256; cannot verify the PDF")
    got = sha256_file(pdf_path)
    if got != expected:
        raise ValueError(f"{pdf_path.name}: sha256 {got} differs from the meta file_sha256 "
                         f"{expected}; refusing")


def ingest_dhs_stem(session: Session, csv_path: Path, meta_path: Path | None = None,
                    pdf_path: Path | None = None) -> StepResult:
    meta_path = meta_path or default_meta_path(csv_path)
    meta = load_meta(meta_path)
    if pdf_path is not None:
        verify_pdf(pdf_path, meta)
    version = str(meta["version"])
    source_url = str(meta["source_url"])
    whole_series = [str(s) for s in meta.get("whole_series_included", [])]

    def work(ctx: RunContext) -> None:
        ensure_country(session)
        if meta.get("file_sha256"):
            ctx.counts["pdf_bytes"] = int(meta.get("file_bytes") or 0)
        codes: list[str] = []
        for r in read_csv_rows(csv_path, columns=("cip_code", "title", "version", "level")):
            ctx.counts["rows"] += 1
            if r["level"] != "6":
                continue  # 2- and 4-digit headings
            if not is_cip6(r["cip_code"]):
                ctx.errors.append(f"bad code {r['cip_code']!r}")
                continue
            if r["version"] and r["version"] != version:
                raise ValueError(f"row version {r['version']} differs from meta {version}")
            ensure_cip(session, r["cip_code"], r["title"])
            codes.append(r["cip_code"])
        ctx.counts["codes_listed"] = len(codes)

        rule = session.scalar(select(EligibilityRule).where(
            EligibilityRule.country_code == COUNTRY, EligibilityRule.key == RULE_KEY,
            EligibilityRule.version == version))
        params = {"whole_series": whole_series}
        if rule is None:
            rule = EligibilityRule(country_code=COUNTRY, key=RULE_KEY, version=version)
            session.add(rule)
        rule.published_on = dt.date.fromisoformat(meta["published_on"])
        rule.source_url = source_url
        rule.params = params
        rule.source_file_id = ctx.source_file.id
        session.flush()

        # Listed codes plus every known code of a whole series (expanded at import, 0002/A14).
        ids = set(session.scalars(select(Classification.id).where(
            Classification.scheme == "cip2020", Classification.code.in_(codes))))
        for s in whole_series:
            ids |= set(session.scalars(select(Classification.id).where(
                Classification.scheme == "cip2020", Classification.code.like(f"{s}.%"))))
        have = set(session.scalars(select(EligibilityRuleCode.classification_id).where(
            EligibilityRuleCode.rule_id == rule.id)))
        for cid in ids - have:
            session.add(EligibilityRuleCode(rule_id=rule.id, classification_id=cid))
        ctx.counts["rule_codes"] = len(ids)
        session.flush()
        ctx.counts["eligibilities_computed"] = recompute_stem_eligibilities(
            session, author=ctx.author, counts=ctx.counts)

    # The digest covers the CSV and its meta: a corrected meta (series, date) is a new run.
    return run_step(session, source="dhs_stem_list", files=[csv_path, meta_path],
                    file_version=version,
                    source_url=source_url, scope=COUNTRY, work=work)
