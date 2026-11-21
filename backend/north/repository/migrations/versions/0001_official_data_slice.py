"""official data slice

Revision ID: 0001
Revises:
Create Date: 2026-11-21 01:20:29.776062
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scheme", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_classifications")),
        sa.UniqueConstraint("scheme", "code", name="uq_classifications_scheme_code"),
    )
    op.create_table(
        "countries",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("rules_module", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_countries")),
    )
    op.create_table(
        "source_files",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("file_version", sa.Text(), nullable=False),
        sa.Column("original_name", sa.Text(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_files")),
        sa.UniqueConstraint("source", "sha256", name="uq_source_files_source_sha256"),
    )
    op.create_table(
        "classification_maps",
        sa.Column("from_id", sa.Integer(), nullable=False),
        sa.Column("to_id", sa.Integer(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("partial", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["from_id"],
            ["classifications.id"],
            name=op.f("fk_classification_maps_from_id_classifications"),
        ),
        sa.ForeignKeyConstraint(
            ["to_id"],
            ["classifications.id"],
            name=op.f("fk_classification_maps_to_id_classifications"),
        ),
        sa.PrimaryKeyConstraint("from_id", "to_id", name=op.f("pk_classification_maps")),
    )
    op.create_table(
        "eligibility_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("published_on", sa.Date(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column(
            "params",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("source_file_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["countries.code"],
            name=op.f("fk_eligibility_rules_country_code_countries"),
        ),
        sa.ForeignKeyConstraint(
            ["source_file_id"],
            ["source_files.id"],
            name=op.f("fk_eligibility_rules_source_file_id_source_files"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eligibility_rules")),
        sa.UniqueConstraint(
            "country_code", "key", "version", name="uq_eligibility_rules_country_key_version"
        ),
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "counts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "errors",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_file_id"],
            ["source_files.id"],
            name=op.f("fk_ingestion_runs_source_file_id_source_files"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_runs")),
    )
    op.create_index(
        op.f("ix_ingestion_runs_source_file_id"), "ingestion_runs", ["source_file_id"], unique=False
    )
    op.create_index(
        "uq_ingestion_runs_succeeded",
        "ingestion_runs",
        ["source_file_id", "scope"],
        unique=True,
        postgresql_where=sa.text("status = 'succeeded'"),
    )
    op.create_table(
        "localities",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("scheme", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["country_code"], ["countries.code"], name=op.f("fk_localities_country_code_countries")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_localities")),
        sa.UniqueConstraint(
            "country_code", "scheme", "code", name="uq_localities_country_scheme_code"
        ),
    )
    op.create_table(
        "subdivisions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("country_code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("coverage_status", sa.Text(), server_default="not_started", nullable=False),
        sa.ForeignKeyConstraint(
            ["country_code"],
            ["countries.code"],
            name=op.f("fk_subdivisions_country_code_countries"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subdivisions")),
    )
    op.create_table(
        "eligibility_rule_codes",
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("classification_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["classification_id"],
            ["classifications.id"],
            name=op.f("fk_eligibility_rule_codes_classification_id_classifications"),
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["eligibility_rules.id"],
            name=op.f("fk_eligibility_rule_codes_rule_id_eligibility_rules"),
        ),
        sa.PrimaryKeyConstraint(
            "rule_id", "classification_id", name=op.f("pk_eligibility_rule_codes")
        ),
    )
    op.create_table(
        "institutions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("subdivision_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("control", sa.Text(), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("accreditation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "carnegie_classification", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["subdivision_id"],
            ["subdivisions.id"],
            name=op.f("fk_institutions_subdivision_id_subdivisions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_institutions")),
    )
    op.create_index(
        op.f("ix_institutions_subdivision_id"), "institutions", ["subdivision_id"], unique=False
    )
    op.create_table(
        "reconciliation_tasks",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "candidates",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("resolved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_reconciliation_tasks_run_id_ingestion_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reconciliation_tasks")),
    )
    op.create_index(
        op.f("ix_reconciliation_tasks_run_id"), "reconciliation_tasks", ["run_id"], unique=False
    )
    op.create_table(
        "campuses",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("institution_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("locality_id", sa.BigInteger(), nullable=True),
        sa.Column("sevp_campus_code", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("intl_authorization", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_campuses_institution_id_institutions"),
        ),
        sa.ForeignKeyConstraint(
            ["locality_id"], ["localities.id"], name=op.f("fk_campuses_locality_id_localities")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campuses")),
        sa.UniqueConstraint("sevp_campus_code", name=op.f("uq_campuses_sevp_campus_code")),
    )
    op.create_index(
        op.f("ix_campuses_institution_id"), "campuses", ["institution_id"], unique=False
    )
    op.create_table(
        "institution_identifiers",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("institution_id", sa.Text(), nullable=False),
        sa.Column("scheme", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name=op.f("fk_institution_identifiers_institution_id_institutions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_institution_identifiers")),
        sa.UniqueConstraint("scheme", "value", name="uq_institution_identifiers_scheme_value"),
    )
    op.create_index(
        op.f("ix_institution_identifiers_institution_id"),
        "institution_identifiers",
        ["institution_id"],
        unique=False,
    )
    op.create_table(
        "programs",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("campus_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("degree", sa.Text(), nullable=False),
        sa.Column("in_strategy", sa.Boolean(), nullable=True),
        sa.Column(
            "flags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "immigration",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "academic",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "cost",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "funding",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "admissions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "career",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "family",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("schema_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campus_id"], ["campuses.id"], name=op.f("fk_programs_campus_id_campuses")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_programs")),
    )
    op.create_index(op.f("ix_programs_campus_id"), "programs", ["campus_id"], unique=False)
    op.create_index(op.f("ix_programs_in_strategy"), "programs", ["in_strategy"], unique=False)
    op.create_table(
        "field_changes",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=True),
        sa.Column("field_path", sa.Text(), nullable=False),
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column(
            "at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["program_id"], ["programs.id"], name=op.f("fk_field_changes_program_id_programs")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_field_changes")),
    )
    op.create_index(
        op.f("ix_field_changes_program_id"), "field_changes", ["program_id"], unique=False
    )
    op.create_table(
        "program_classifications",
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("classification_id", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("verified", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["classification_id"],
            ["classifications.id"],
            name=op.f("fk_program_classifications_classification_id_classifications"),
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name=op.f("fk_program_classifications_program_id_programs"),
        ),
        sa.PrimaryKeyConstraint(
            "program_id", "classification_id", name=op.f("pk_program_classifications")
        ),
    )
    op.create_index(
        op.f("ix_program_classifications_classification_id"),
        "program_classifications",
        ["classification_id"],
        unique=False,
    )
    op.create_table(
        "program_eligibilities",
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_version", sa.Text(), nullable=False),
        sa.Column("claim_mismatch", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name=op.f("fk_program_eligibilities_program_id_programs"),
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["eligibility_rules.id"],
            name=op.f("fk_program_eligibilities_rule_id_eligibility_rules"),
        ),
        sa.PrimaryKeyConstraint("program_id", "rule_id", name=op.f("pk_program_eligibilities")),
    )
    op.create_index(
        op.f("ix_program_eligibilities_rule_id"), "program_eligibilities", ["rule_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_program_eligibilities_rule_id"), table_name="program_eligibilities")
    op.drop_table("program_eligibilities")
    op.drop_index(
        op.f("ix_program_classifications_classification_id"), table_name="program_classifications"
    )
    op.drop_table("program_classifications")
    op.drop_index(op.f("ix_field_changes_program_id"), table_name="field_changes")
    op.drop_table("field_changes")
    op.drop_index(op.f("ix_programs_in_strategy"), table_name="programs")
    op.drop_index(op.f("ix_programs_campus_id"), table_name="programs")
    op.drop_table("programs")
    op.drop_index(
        op.f("ix_institution_identifiers_institution_id"), table_name="institution_identifiers"
    )
    op.drop_table("institution_identifiers")
    op.drop_index(op.f("ix_campuses_institution_id"), table_name="campuses")
    op.drop_table("campuses")
    op.drop_index(op.f("ix_reconciliation_tasks_run_id"), table_name="reconciliation_tasks")
    op.drop_table("reconciliation_tasks")
    op.drop_index(op.f("ix_institutions_subdivision_id"), table_name="institutions")
    op.drop_table("institutions")
    op.drop_table("eligibility_rule_codes")
    op.drop_table("subdivisions")
    op.drop_table("localities")
    op.drop_index(
        "uq_ingestion_runs_succeeded",
        table_name="ingestion_runs",
        postgresql_where=sa.text("status = 'succeeded'"),
    )
    op.drop_index(op.f("ix_ingestion_runs_source_file_id"), table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
    op.drop_table("eligibility_rules")
    op.drop_table("classification_maps")
    op.drop_table("source_files")
    op.drop_table("countries")
    op.drop_table("classifications")
