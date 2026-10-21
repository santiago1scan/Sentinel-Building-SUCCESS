"""baseline_existing_schema

Revision ID: f1cdba68c97b
Revises:
Create Date: 2026-10-14 20:04:17.886695

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'f1cdba68c97b'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
