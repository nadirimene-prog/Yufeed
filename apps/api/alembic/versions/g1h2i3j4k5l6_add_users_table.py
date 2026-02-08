"""Add users table for authentication

Revision ID: g1h2i3j4k5l6
Revises: ab2c3d4e5f6g
Create Date: 2025-01-28 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

# revision identifiers, used by Alembic.
revision = "g1h2i3j4k5l6"
down_revision = "ab2c3d4e5f6g"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table with timezone-aware timestamps
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("default_role", sa.String(50), nullable=True, server_default="user"),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("locked_until", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_login_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(45), nullable=True),
        sa.Column("password_changed_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("preferences", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_users_email_lower", table_name="users")
    op.drop_index("ix_users_email", table_name="users")

    # Drop table
    op.drop_table("users")
