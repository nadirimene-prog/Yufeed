"""add official journal act table

Revision ID: aa1b2c3d4e5f
Revises: 9a4c2d1e7f8b
Create Date: 2026-01-25 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "aa1b2c3d4e5f"
down_revision = "9a4c2d1e7f8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "official_journal_acts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("act_identifier", sa.String(length=255), nullable=False),
        sa.Column("act_uri", sa.String(length=1000), nullable=True),
        sa.Column("signature_identifier", sa.String(length=255), nullable=True),
        sa.Column("signature_uri", sa.String(length=1000), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("series", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_official_journal_acts_act_identifier",
        "official_journal_acts",
        ["act_identifier"],
        unique=True,
    )
    op.create_index(
        "ix_official_journal_acts_publication_date",
        "official_journal_acts",
        ["publication_date"],
        unique=False,
    )
    op.create_index(
        "ix_official_journal_acts_series",
        "official_journal_acts",
        ["series"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_official_journal_acts_series", table_name="official_journal_acts")
    op.drop_index("ix_official_journal_acts_publication_date", table_name="official_journal_acts")
    op.drop_index("ix_official_journal_acts_act_identifier", table_name="official_journal_acts")
    op.drop_table("official_journal_acts")
