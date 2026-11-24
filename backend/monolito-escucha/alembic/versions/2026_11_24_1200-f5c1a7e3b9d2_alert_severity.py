"""alert.severity: emergencia | leve, set by the analytics (app/analytics/severity.py)

Only out-of-range alerts get a severity; technical notices and alerts from before this migration stay NULL.
The rule lives in code, the column only keeps the result so it stays in the history (24-Nov-2026).

Revision ID: f5c1a7e3b9d2
Revises: e4b7d2a9c3f1
Create Date: 2026-11-24 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f5c1a7e3b9d2"
down_revision: Union[str, Sequence[str], None] = "e4b7d2a9c3f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("alert", sa.Column("severity", sa.String(20), nullable=True))
    op.create_check_constraint(
        "chk_alert_severity", "alert", "severity IS NULL OR severity IN ('emergencia', 'leve')")


def downgrade() -> None:
    op.drop_constraint("chk_alert_severity", "alert", type_="check")
    op.drop_column("alert", "severity")
