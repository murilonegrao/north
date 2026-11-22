"""email: user addresses, single-use links, outbox sent by the worker (record 0007)

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-22 16:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _ts(name: str, *, nullable: bool = True, now: bool = False) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable,
                     server_default=sa.text("now()") if now else None)


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.Text(), nullable=True))
    op.add_column("users", _ts("email_verified_at"))
    op.add_column("users", sa.Column("locale", sa.Text(), server_default="en", nullable=False))
    op.add_column("users", sa.Column("notify_jobs", sa.Boolean(), server_default=sa.text("true"),
                                     nullable=False))
    # One account per address; the application stores it lower-case.
    op.create_index("uq_users_email", "users", ["email"], unique=True,
                    postgresql_where=sa.text("email is not null"))
    op.create_check_constraint("email_lower", "users", "email = lower(email)")
    op.create_check_constraint("locale", "users", "locale in ('en', 'pt-BR')")

    op.create_table(
        "user_tokens",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        _ts("created_at", nullable=False, now=True),
        _ts("expires_at", nullable=False),
        _ts("used_at"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE",
                                name=op.f("fk_user_tokens_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_tokens_token_hash")),
    )
    op.create_index(op.f("ix_user_tokens_user_id"), "user_tokens", ["user_id"])
    op.create_check_constraint("purpose", "user_tokens",
                               "purpose in ('reset_password', 'verify_email')")

    op.create_table(
        "email_outbox",
        sa.Column("id", sa.BigInteger(), nullable=False),
        _ts("created_at", nullable=False, now=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("to_addr", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sensitive", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        _ts("next_attempt_at", nullable=False, now=True),
        _ts("sent_at"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL",
                                name=op.f("fk_email_outbox_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_outbox")),
    )
    op.create_index(op.f("ix_email_outbox_user_id"), "email_outbox", ["user_id"])
    op.create_index("ix_email_outbox_status_next_attempt_at", "email_outbox",
                    ["status", "next_attempt_at"])
    op.create_check_constraint("status", "email_outbox",
                               "status in ('queued', 'sent', 'failed', 'expired')")


def downgrade() -> None:
    op.drop_table("email_outbox")
    op.drop_table("user_tokens")
    op.drop_constraint("ck_users_locale", "users", type_="check")
    op.drop_constraint("ck_users_email_lower", "users", type_="check")
    op.drop_index("uq_users_email", table_name="users")
    for column in ("notify_jobs", "locale", "email_verified_at", "email"):
        op.drop_column("users", column)
