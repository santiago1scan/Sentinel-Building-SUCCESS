"""node.code stops being unique: the node is identified by node_id, the code is only a label

A revoked node keeps its row (and its readings); a new node can reuse the same code and gets its own node_id.

downgrade restores the constraint and fails if two nodes already share a code.

Revision ID: e4b7d2a9c3f1
Revises: c3f8a2d6b9e1
Create Date: 2026-11-17 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "e4b7d2a9c3f1"
down_revision: Union[str, Sequence[str], None] = "c3f8a2d6b9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("node_code_key", "node", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("node_code_key", "node", ["code"])
