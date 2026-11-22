"""Tables of UML section 8 needed by the official-data slice (API contract v0).

Names and columns follow UML §8 and decision record 0002. Deviations, all additive:
- ``institutions.website`` (HD ``WEBADDR``; the contract serves it, the ER has no column).
- ``ingestion_runs.scope`` (e.g. ``US-TX``): one file can be ingested once per scope, so the
  state filter stays a parameter; the partial unique index is on (source_file_id, scope).
- ``field_changes.program_id`` is nullable: institution and campus values are logged with a
  namespaced ``field_path`` such as ``institution[228778].accreditation``.
- ``source_files.uploaded_by`` has no foreign key yet (``accounts`` arrives with FR-25).
"""

from __future__ import annotations

import datetime as dt
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)
    type_annotation_map: ClassVar = {dict[str, Any]: JSONB, list[Any]: JSONB}


def _now() -> Mapped[dt.datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class Country(Base):
    __tablename__ = "countries"
    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(Text)
    rules_module: Mapped[str] = mapped_column(Text)


class Subdivision(Base):
    __tablename__ = "subdivisions"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    name: Mapped[str] = mapped_column(Text)
    coverage_status: Mapped[str] = mapped_column(Text, server_default="not_started")


class Locality(Base):
    __tablename__ = "localities"
    __table_args__ = (UniqueConstraint("country_code", "scheme", "code",
                                       name="uq_localities_country_scheme_code"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    scheme: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)


class Institution(Base):
    __tablename__ = "institutions"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    subdivision_id: Mapped[str] = mapped_column(ForeignKey("subdivisions.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    control: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    accreditation: Mapped[dict[str, Any] | None]
    carnegie_classification: Mapped[dict[str, Any] | None]

    identifiers: Mapped[list[InstitutionIdentifier]] = relationship(back_populates="institution")
    campuses: Mapped[list[Campus]] = relationship(back_populates="institution")
    subdivision: Mapped[Subdivision] = relationship()


class InstitutionIdentifier(Base):
    __tablename__ = "institution_identifiers"
    __table_args__ = (UniqueConstraint("scheme", "value",
                                       name="uq_institution_identifiers_scheme_value"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    scheme: Mapped[str] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text)

    institution: Mapped[Institution] = relationship(back_populates="identifiers")


class Campus(Base):
    __tablename__ = "campuses"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    locality_id: Mapped[int | None] = mapped_column(ForeignKey("localities.id"))
    sevp_campus_code: Mapped[str | None] = mapped_column(Text, unique=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    intl_authorization: Mapped[dict[str, Any] | None]

    institution: Mapped[Institution] = relationship(back_populates="campuses")
    locality: Mapped[Locality | None] = relationship()
    programs: Mapped[list[Program]] = relationship(back_populates="campus")


class Program(Base):
    __tablename__ = "programs"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    campus_id: Mapped[int] = mapped_column(ForeignKey("campuses.id"), index=True)
    name: Mapped[str] = mapped_column(Text)
    degree: Mapped[str] = mapped_column(Text)
    # Derived from modality and F-1 compatibility (0002/A11); null until those are known.
    in_strategy: Mapped[bool | None] = mapped_column(Boolean, index=True)
    flags: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    immigration: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    academic: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    cost: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    funding: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    admissions: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    career: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    family: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    schema_version: Mapped[int] = mapped_column(Integer, server_default="0")
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    campus: Mapped[Campus] = relationship(back_populates="programs")
    classifications: Mapped[list[ProgramClassification]] = relationship(
        back_populates="program")
    eligibilities: Mapped[list[ProgramEligibility]] = relationship(back_populates="program")


class Classification(Base):
    __tablename__ = "classifications"
    __table_args__ = (UniqueConstraint("scheme", "code", name="uq_classifications_scheme_code"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scheme: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)


class ProgramClassification(Base):
    __tablename__ = "program_classifications"
    program_id: Mapped[str] = mapped_column(ForeignKey("programs.id"), primary_key=True)
    classification_id: Mapped[int] = mapped_column(
        ForeignKey("classifications.id"), primary_key=True, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    verified: Mapped[dict[str, Any]]

    program: Mapped[Program] = relationship(back_populates="classifications")
    classification: Mapped[Classification] = relationship()


class ClassificationMap(Base):
    __tablename__ = "classification_maps"
    from_id: Mapped[int] = mapped_column(ForeignKey("classifications.id"), primary_key=True)
    to_id: Mapped[int] = mapped_column(ForeignKey("classifications.id"), primary_key=True)
    origin: Mapped[str] = mapped_column(Text)
    partial: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    notes: Mapped[str | None] = mapped_column(Text)

    target: Mapped[Classification] = relationship(foreign_keys=[to_id])


class SourceFile(Base):
    __tablename__ = "source_files"
    __table_args__ = (UniqueConstraint("source", "sha256", name="uq_source_files_source_sha256"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(Text)
    file_version: Mapped[str] = mapped_column(Text)
    original_name: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    source_url: Mapped[str | None] = mapped_column(Text)
    uploaded_by: Mapped[int | None] = mapped_column(Integer)
    uploaded_at: Mapped[dt.datetime] = _now()


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        Index("uq_ingestion_runs_succeeded", "source_file_id", "scope", unique=True,
              postgresql_where=text("status = 'succeeded'")),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_file_id: Mapped[int] = mapped_column(ForeignKey("source_files.id"), index=True)
    scope: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    started_at: Mapped[dt.datetime] = _now()
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    counts: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    errors: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))

    source_file: Mapped[SourceFile] = relationship()


class ReconciliationTask(Base):
    __tablename__ = "reconciliation_tasks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"), index=True)
    kind: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    candidates: Mapped[list[Any]] = mapped_column(server_default=text("'[]'::jsonb"))
    resolved: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class EligibilityRule(Base):
    __tablename__ = "eligibility_rules"
    __table_args__ = (UniqueConstraint("country_code", "key", "version",
                                       name="uq_eligibility_rules_country_key_version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    key: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(Text)
    published_on: Mapped[dt.date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(Text)
    params: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    source_file_id: Mapped[int | None] = mapped_column(ForeignKey("source_files.id"))


class EligibilityRuleCode(Base):
    __tablename__ = "eligibility_rule_codes"
    rule_id: Mapped[int] = mapped_column(ForeignKey("eligibility_rules.id"), primary_key=True)
    classification_id: Mapped[int] = mapped_column(
        ForeignKey("classifications.id"), primary_key=True)


class ProgramEligibility(Base):
    __tablename__ = "program_eligibilities"
    program_id: Mapped[str] = mapped_column(ForeignKey("programs.id"), primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("eligibility_rules.id"), primary_key=True,
                                         index=True)
    result: Mapped[dict[str, Any]]
    rule_version: Mapped[str] = mapped_column(Text)
    claim_mismatch: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    computed_at: Mapped[dt.datetime] = _now()

    program: Mapped[Program] = relationship(back_populates="eligibilities")
    rule: Mapped[EligibilityRule] = relationship()


class FieldChange(Base):
    __tablename__ = "field_changes"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    program_id: Mapped[str | None] = mapped_column(ForeignKey("programs.id"), index=True)
    field_path: Mapped[str] = mapped_column(Text)
    old_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    author: Mapped[str] = mapped_column(Text)
    at: Mapped[dt.datetime] = _now()


# --------------------------------------------------------------------------- admin area
# Record 0006 and docs/design/admin-and-sync.md: accounts with password and TOTP, server-side
# sessions, login throttling, an append-only audit log, and the job queue the worker claims.


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Stored lower-case; the unique index is on the stored value.
    username: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)  # admin, curator, viewer
    totp_secret: Mapped[str | None] = mapped_column(Text)
    totp_pending_secret: Mapped[str | None] = mapped_column(Text)
    # Last accepted TOTP time step: a code is never accepted twice.
    totp_last_step: Mapped[int | None] = mapped_column(BigInteger)
    must_change_password: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    disabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[dt.datetime] = _now()
    password_changed_at: Mapped[dt.datetime] = _now()
    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # Email (record 0007): stored lower-case, unique when set. Used for password reset and
    # notifications only once verified (a link sent to it was opened).
    email: Mapped[str | None] = mapped_column(Text)
    email_verified_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # Language of the emails: en or pt-BR (the admin languages).
    locale: Mapped[str] = mapped_column(Text, server_default="en")
    # Job failure emails; security notices cannot be turned off.
    notify_jobs: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class UserToken(Base):
    """Single-use links sent by email (password reset, email verification). Only the sha256
    of the token is stored."""

    __tablename__ = "user_tokens"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(Text)  # reset_password, verify_email
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    # verify_email: the address the link was sent to (it must still be the account's).
    email: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = _now()
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class EmailOutbox(Base):
    """Messages queued in the same transaction as the event they describe; the worker sends
    them. Bodies with a live link (sensitive) are blanked once sent."""

    __tablename__ = "email_outbox"
    __table_args__ = (Index("ix_email_outbox_status_next_attempt_at", "status", "next_attempt_at"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[dt.datetime] = _now()
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"),
                                                index=True)
    kind: Mapped[str] = mapped_column(Text)  # message name in north.mail.messages
    to_addr: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    sensitive: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    # queued, sent, failed (gave up), expired (queued too long, never sent)
    status: Mapped[str] = mapped_column(Text, server_default="queued")
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    next_attempt_at: Mapped[dt.datetime] = _now()
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class AdminSession(Base):
    __tablename__ = "admin_sessions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # sha256 of the cookie token: a database read does not give a usable session.
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    csrf_token: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # False between the password and the TOTP code.
    mfa_ok: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[dt.datetime] = _now()
    last_seen_at: Mapped[dt.datetime] = _now()
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship()


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_username_at", "username", "at"),
                      Index("ix_login_attempts_ip_at", "ip", "at"))
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    at: Mapped[dt.datetime] = _now()
    ip: Mapped[str | None] = mapped_column(Text)
    username: Mapped[str] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(Text)  # password, totp
    ok: Mapped[bool] = mapped_column(Boolean)


class AuditEntry(Base):
    """Append-only (a trigger refuses UPDATE and DELETE): who did what, when."""

    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    at: Mapped[dt.datetime] = _now()
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    actor: Mapped[str] = mapped_column(Text)  # username, "worker" or "scheduler"
    action: Mapped[str] = mapped_column(Text)
    target: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    ip: Mapped[str | None] = mapped_column(Text)


class Job(Base):
    """A unit of work for the worker, claimed with SELECT ... FOR UPDATE SKIP LOCKED."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_status_run_after", "status", "run_after"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, index=True)
    params: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    # queued, running, succeeded, attention, failed, cancelled
    status: Mapped[str] = mapped_column(Text, server_default="queued")
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    schedule_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = _now()
    run_after: Mapped[dt.datetime] = _now()
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    worker: Mapped[str | None] = mapped_column(Text)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    result: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    error: Mapped[str | None] = mapped_column(Text)
    log_lines: Mapped[int] = mapped_column(Integer, server_default="0")


class JobLog(Base):
    __tablename__ = "job_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    at: Mapped[dt.datetime] = _now()
    line: Mapped[str] = mapped_column(Text)


class Schedule(Base):
    """Recurring jobs. Declared in code (north.jobs.registry); the row keeps only state."""

    __tablename__ = "schedules"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    params: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'::jsonb"))
    every_hours: Mapped[int] = mapped_column(Integer)
    paused: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    next_run_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    last_job_id: Mapped[int | None] = mapped_column(BigInteger)
