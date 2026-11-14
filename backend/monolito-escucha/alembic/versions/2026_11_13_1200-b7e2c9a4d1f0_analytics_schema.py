"""analytics schema: database structure of 26-Oct (sensor_metric, ingest_message, reading per metric)

Brings the backend to the database design of backend/sumothings_db/success_db.sql (26-Oct):
- sensor_metric: one row per variable of a sensor type, with its normal range (and physical range).
- ingest_message: envelope of every message received from the bridge (deduplicated by message_uid).
- reading: one row per variable and aggregation (raw, avg, max, min), linked to its message and metric.
- alert: becomes the episode the guard sees (start, last reading, end, peak, who handled it and when).

Existing column names (node.code, sensor.code, reading.measured_value...) are kept.

DATA: upgrade deletes the current rows of `alert` and `reading`. They were written by the simulator, carry a
single value per sensor without saying which variable it is, and cannot be converted.

Revision ID: b7e2c9a4d1f0
Revises: a1d3f0c7b2e4
Create Date: 2026-11-13 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2c9a4d1f0"
down_revision: Union[str, Sequence[str], None] = "a1d3f0c7b2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("DELETE FROM alert")
    op.execute("DELETE FROM reading")

    op.create_table(
        "sensor_metric",
        sa.Column("metric_id", sa.BigInteger(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("sensor_type_id", sa.BigInteger(), nullable=False),
        sa.Column("metric_code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(150)),
        sa.Column("unit", sa.String(40)),
        sa.Column("normal_minimum", sa.Numeric(14, 4)),
        sa.Column("normal_maximum", sa.Numeric(14, 4)),
        sa.Column("physical_minimum", sa.Numeric(14, 4)),
        sa.Column("physical_maximum", sa.Numeric(14, 4)),
        sa.Column("alarm_below", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("alarm_above", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["sensor_type_id"], ["sensor_type.sensor_type_id"], name="fk_sensor_metric_sensor_type",
                                onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("sensor_type_id", "metric_code", name="uq_sensor_metric_type_code"),
        sa.CheckConstraint("normal_minimum IS NULL OR normal_maximum IS NULL OR normal_minimum <= normal_maximum",
                           name="chk_sensor_metric_normal_range"),
        sa.CheckConstraint("physical_minimum IS NULL OR physical_maximum IS NULL OR physical_minimum <= physical_maximum",
                           name="chk_sensor_metric_physical_range"),
    )

    op.create_table(
        "ingest_message",
        sa.Column("message_id", sa.BigInteger(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("message_uid", sa.String(100), nullable=False),
        sa.Column("building_code", sa.String(50)),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("schema_version", sa.String(20), nullable=False),
        sa.Column("sequence_number", sa.BigInteger()),
        sa.Column("priority", sa.String(20)),
        sa.Column("quality", sa.String(20)),
        sa.Column("transport", sa.String(20)),
        sa.Column("generated_at", TZ, nullable=False),
        sa.Column("sent_at", TZ),
        sa.Column("received_at", TZ, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("window_start", TZ),
        sa.Column("window_end", TZ),
        sa.Column("sample_count_bridge", sa.Integer()),
        sa.UniqueConstraint("message_uid", name="uq_ingest_message_uid"),
        sa.CheckConstraint("window_start IS NULL OR window_end IS NULL OR window_end >= window_start",
                           name="chk_ingest_message_window"),
    )
    op.create_index("idx_ingest_message_generated_at", "ingest_message", ["generated_at"])

    op.add_column("reading", sa.Column("message_id", sa.BigInteger(), nullable=False))
    op.add_column("reading", sa.Column("metric_id", sa.BigInteger(), nullable=False))
    op.add_column("reading", sa.Column("aggregation", sa.String(10), nullable=False))
    op.add_column("reading", sa.Column("sample_count_sensor", sa.Integer()))
    op.add_column("reading", sa.Column("alert_id", sa.BigInteger()))
    op.create_foreign_key("fk_reading_message", "reading", "ingest_message", ["message_id"], ["message_id"],
                          onupdate="CASCADE", ondelete="RESTRICT")
    op.create_foreign_key("fk_reading_metric", "reading", "sensor_metric", ["metric_id"], ["metric_id"],
                          onupdate="CASCADE", ondelete="RESTRICT")
    op.create_check_constraint("chk_reading_aggregation", "reading", "aggregation IN ('raw', 'avg', 'max', 'min')")
    op.create_unique_constraint("uq_reading_message_sensor_metric_aggregation", "reading",
                                ["message_id", "sensor_id", "metric_id", "aggregation"])
    op.create_index("idx_reading_sensor_metric_measured_at", "reading", ["sensor_id", "metric_id", "measured_at"])
    op.create_index("idx_reading_alert", "reading", ["alert_id"])

    op.alter_column("alert", "reading_id", nullable=True)
    op.add_column("alert", sa.Column("alert_type", sa.String(20), nullable=False))
    op.add_column("alert", sa.Column("direction", sa.String(10)))
    op.add_column("alert", sa.Column("node_id", sa.BigInteger()))
    op.add_column("alert", sa.Column("sensor_id", sa.BigInteger()))
    op.add_column("alert", sa.Column("metric_id", sa.BigInteger()))
    op.add_column("alert", sa.Column("started_at", TZ, nullable=False))
    op.add_column("alert", sa.Column("last_seen_at", TZ, nullable=False))
    op.add_column("alert", sa.Column("ended_at", TZ))
    op.add_column("alert", sa.Column("peak_value", sa.Numeric(14, 4)))
    op.add_column("alert", sa.Column("deviation", sa.Numeric(14, 4), nullable=False, server_default="0"))
    op.add_column("alert", sa.Column("reading_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("alert", sa.Column("handled_at", TZ))
    op.create_foreign_key("fk_alert_node", "alert", "node", ["node_id"], ["node_id"],
                          onupdate="CASCADE", ondelete="RESTRICT")
    op.create_foreign_key("fk_alert_sensor", "alert", "sensor", ["sensor_id"], ["sensor_id"],
                          onupdate="CASCADE", ondelete="RESTRICT")
    op.create_foreign_key("fk_alert_metric", "alert", "sensor_metric", ["metric_id"], ["metric_id"],
                          onupdate="CASCADE", ondelete="RESTRICT")
    op.create_check_constraint("chk_alert_type", "alert", "alert_type IN ('out_of_range', 'technical')")
    op.create_check_constraint("chk_alert_direction", "alert", "direction IS NULL OR direction IN ('above', 'below')")
    op.create_index("idx_alert_open", "alert", ["ended_at", "alert_type"])

    # Created last: alert and reading point at each other.
    op.create_foreign_key("fk_reading_alert", "reading", "alert", ["alert_id"], ["alert_id"],
                          onupdate="CASCADE", ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_reading_alert", "reading", type_="foreignkey")

    op.drop_index("idx_alert_open", table_name="alert")
    op.drop_constraint("chk_alert_direction", "alert", type_="check")
    op.drop_constraint("chk_alert_type", "alert", type_="check")
    for fk in ("fk_alert_metric", "fk_alert_sensor", "fk_alert_node"):
        op.drop_constraint(fk, "alert", type_="foreignkey")
    for col in ("handled_at", "reading_count", "deviation", "peak_value", "ended_at", "last_seen_at", "started_at",
                "metric_id", "sensor_id", "node_id", "direction", "alert_type"):
        op.drop_column("alert", col)
    # Technical alerts have no reading; they cannot survive the old NOT NULL.
    op.execute("DELETE FROM alert WHERE reading_id IS NULL")
    op.alter_column("alert", "reading_id", nullable=False)

    op.drop_index("idx_reading_alert", table_name="reading")
    op.drop_index("idx_reading_sensor_metric_measured_at", table_name="reading")
    op.drop_constraint("uq_reading_message_sensor_metric_aggregation", "reading", type_="unique")
    op.drop_constraint("chk_reading_aggregation", "reading", type_="check")
    op.drop_constraint("fk_reading_metric", "reading", type_="foreignkey")
    op.drop_constraint("fk_reading_message", "reading", type_="foreignkey")
    for col in ("alert_id", "sample_count_sensor", "aggregation", "metric_id", "message_id"):
        op.drop_column("reading", col)

    op.drop_index("idx_ingest_message_generated_at", table_name="ingest_message")
    op.drop_table("ingest_message")
    op.drop_table("sensor_metric")
