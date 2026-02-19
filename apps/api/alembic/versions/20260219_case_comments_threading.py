"""add threaded comment metadata to case_notes

Revision ID: 20260219_case_comments_threading
Revises: 20260218_alert_rule_attribution
Create Date: 2026-02-19 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260219_case_comments_threading"
down_revision = "20260218_alert_rule_attribution"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "case_notes" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("case_notes")}

    with op.batch_alter_table("case_notes") as batch_op:
        if "parent_note_id" not in columns:
            batch_op.add_column(sa.Column("parent_note_id", sa.Integer(), nullable=True))
        if "mentions" not in columns:
            batch_op.add_column(sa.Column("mentions", sa.JSON(), nullable=True))

    inspector = sa.inspect(bind)
    foreign_keys = {fk.get("name") for fk in inspector.get_foreign_keys("case_notes")}
    if "fk_case_notes_parent_note_id" not in foreign_keys:
        op.create_foreign_key(
            "fk_case_notes_parent_note_id",
            source_table="case_notes",
            referent_table="case_notes",
            local_cols=["parent_note_id"],
            remote_cols=["id"],
            ondelete="SET NULL",
        )

    indexes = {index["name"] for index in inspector.get_indexes("case_notes")}
    parent_idx = op.f("ix_case_notes_parent_note_id")
    if parent_idx not in indexes:
        op.create_index(parent_idx, "case_notes", ["parent_note_id"], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "case_notes" not in inspector.get_table_names():
        return

    indexes = {index["name"] for index in inspector.get_indexes("case_notes")}
    parent_idx = op.f("ix_case_notes_parent_note_id")
    if parent_idx in indexes:
        op.drop_index(parent_idx, table_name="case_notes")

    foreign_keys = {fk.get("name") for fk in inspector.get_foreign_keys("case_notes")}
    if "fk_case_notes_parent_note_id" in foreign_keys:
        op.drop_constraint("fk_case_notes_parent_note_id", "case_notes", type_="foreignkey")

    columns = {column["name"] for column in inspector.get_columns("case_notes")}
    with op.batch_alter_table("case_notes") as batch_op:
        if "mentions" in columns:
            batch_op.drop_column("mentions")
        if "parent_note_id" in columns:
            batch_op.drop_column("parent_note_id")
