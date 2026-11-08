"""add node token hash

Revision ID: a1d3f0c7b2e4
Revises: 5c5ab91f7ea8
Create Date: 2026-11-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1d3f0c7b2e4'
down_revision: Union[str, Sequence[str], None] = '5c5ab91f7ea8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('node', sa.Column('token_hash', sa.String(length=64), nullable=True))
    op.create_unique_constraint('node_token_hash_key', 'node', ['token_hash'])
    op.add_column('node', sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('node', 'revoked_at')
    op.drop_constraint('node_token_hash_key', 'node', type_='unique')
    op.drop_column('node', 'token_hash')
