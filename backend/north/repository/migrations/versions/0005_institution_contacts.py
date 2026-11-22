"""institution_contacts: private institution contacts from the official files (record 0009)

Record 0009 keeps the contacts the official files print, privately, so the admin can contact
schools: ILEP and TrustEd (contact name, email, telephone), DAPIP (AdminName, AdminEmail,
AdminPhone) and IPEDS HD (CHFNM, CHFTITLE, GENTELE). One row per distinct contact of an
institution, with its ``source``; a new run of a source replaces that source's rows for the
institutions it covers (data minimization). A row may hold only a general phone. Never served
by the public API; read only through an admin endpoint that writes the audit log.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-22 21:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "institution_contacts",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("institution_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                  nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"],
                                name=op.f("fk_institution_contacts_institution_id_institutions")),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"],
                                name=op.f("fk_institution_contacts_source_file_id_source_files")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_institution_contacts")),
    )
    op.create_index(op.f("ix_institution_contacts_institution_id"), "institution_contacts",
                    ["institution_id"])
    op.create_index(op.f("ix_institution_contacts_source"), "institution_contacts", ["source"])
    op.create_index(op.f("ix_institution_contacts_source_file_id"), "institution_contacts",
                    ["source_file_id"])


def downgrade() -> None:
    op.drop_table("institution_contacts")
