"""Ireland English courses: program kind, language course, program authorization (record 0008)

Record 0008/T5, T6, T13 and slice E2:

- ``programs.kind`` (``degree`` by default, ``language_course``). Every existing program is a
  degree. A language course carries ``programs.language_course`` (JSONB of VerifiedValues:
  ``cefr_entry``, ``cefr_exit``, ``exam``, ``weeks``, ``hours_per_week``, ``price``,
  ``start_dates``); a degree has none (check constraint).
- ``programs.intl_authorization``: the authorization held by the program itself (schemes
  ``ie_ilep``, ``ie_trusted``). The US keeps SEVP on ``campuses.intl_authorization``.
- ``program_identifiers`` (scheme, value), unique on (scheme, value): ``ie_ilep_ref`` and
  ``ie_trusted_ref``. The provider number goes to ``institution_identifiers`` with scheme
  ``ie_provider_no`` (digits only, no ``TE`` prefix).
- ``institutions.country_code`` (backfilled from the subdivision id) and a nullable
  ``institutions.subdivision_id``.

Places in Ireland: the subdivision of an Irish institution is its ISO 3166-2:IE county
(``IE-D`` Dublin, ``IE-CO`` Cork, ...) when every site listed for the provider lies in the same
county, derived from the city or the county named in the address; otherwise it is null. A
campus links to a ``localities`` row of scheme ``ie_county`` (code = the ISO 3166-2:IE code)
under the same rule, and its city is a known town matched in the address text, or null. Nothing
is guessed: an address naming two towns has no city.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-22 20:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("programs", sa.Column("kind", sa.Text(), server_default="degree",
                                        nullable=False))
    op.add_column("programs", sa.Column("language_course",
                                        postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("programs", sa.Column("intl_authorization",
                                        postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index(op.f("ix_programs_kind"), "programs", ["kind"])
    op.create_check_constraint("kind", "programs", "kind in ('degree', 'language_course')")
    op.create_check_constraint("language_course_kind", "programs",
                               "(kind = 'language_course') = (language_course is not null)")

    op.create_table(
        "program_identifiers",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("program_id", sa.Text(), nullable=False),
        sa.Column("scheme", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"],
                                name=op.f("fk_program_identifiers_program_id_programs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_program_identifiers")),
        sa.UniqueConstraint("scheme", "value", name="uq_program_identifiers_scheme_value"),
    )
    op.create_index(op.f("ix_program_identifiers_program_id"), "program_identifiers",
                    ["program_id"])

    op.add_column("institutions", sa.Column("country_code", sa.Text(), nullable=True))
    op.execute("update institutions set country_code = split_part(subdivision_id, '-', 1)")
    op.alter_column("institutions", "country_code", nullable=False)
    op.create_foreign_key(op.f("fk_institutions_country_code_countries"), "institutions",
                          "countries", ["country_code"], ["code"])
    op.create_index(op.f("ix_institutions_country_code"), "institutions", ["country_code"])
    op.alter_column("institutions", "subdivision_id", nullable=True)


def downgrade() -> None:
    op.execute("delete from institutions where subdivision_id is null")
    op.alter_column("institutions", "subdivision_id", nullable=False)
    op.drop_index(op.f("ix_institutions_country_code"), table_name="institutions")
    op.drop_constraint(op.f("fk_institutions_country_code_countries"), "institutions",
                       type_="foreignkey")
    op.drop_column("institutions", "country_code")
    op.drop_table("program_identifiers")
    op.drop_constraint("ck_programs_language_course_kind", "programs", type_="check")
    op.drop_constraint("ck_programs_kind", "programs", type_="check")
    op.drop_index(op.f("ix_programs_kind"), table_name="programs")
    for column in ("intl_authorization", "language_course", "kind"):
        op.drop_column("programs", column)
