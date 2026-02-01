"""Merge policy template + rename metadata heads

Revision ID: af3b7e9d1cb5
Revises: 4788ca423751, cbee3d7ad225
Create Date: 2026-02-01
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "af3b7e9d1cb5"
down_revision: Union[str, Sequence[str], None] = ("4788ca423751", "cbee3d7ad225")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge heads."""
    pass


def downgrade() -> None:
    """Downgrade merge."""
    pass
