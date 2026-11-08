import datetime
import decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AppRole(Base):
    __tablename__ = 'app_role'
    __table_args__ = (
        PrimaryKeyConstraint('role_code', name='app_role_pkey'),
        UniqueConstraint('name', name='app_role_name_key')
    )

    role_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    app_user: Mapped[list['AppUser']] = relationship('AppUser', back_populates='app_role')


class Building(Base):
    __tablename__ = 'building'
    __table_args__ = (
        PrimaryKeyConstraint('building_id', name='building_pkey'),
    )

    building_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str | None] = mapped_column(String(250))

    zone: Mapped[list['Zone']] = relationship('Zone', back_populates='building')


class SensorType(Base):
    __tablename__ = 'sensor_type'
    __table_args__ = (
        CheckConstraint('normal_minimum IS NULL OR normal_maximum IS NULL OR normal_minimum <= normal_maximum', name='chk_sensor_type_normal_range'),
        CheckConstraint('sampling_interval > 0', name='chk_sensor_type_sampling_interval'),
        PrimaryKeyConstraint('sensor_type_id', name='sensor_type_pkey'),
        UniqueConstraint('name', name='sensor_type_name_key')
    )

    sensor_type_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sampling_interval: Mapped[int] = mapped_column(Integer, nullable=False)
    default_unit: Mapped[str | None] = mapped_column(String(40))
    normal_minimum: Mapped[decimal.Decimal | None] = mapped_column(Numeric(12, 4))
    normal_maximum: Mapped[decimal.Decimal | None] = mapped_column(Numeric(12, 4))

    sensor: Mapped[list['Sensor']] = relationship('Sensor', back_populates='sensor_type')


class AppUser(Base):
    __tablename__ = 'app_user'
    __table_args__ = (
        ForeignKeyConstraint(['role_code'], ['app_role.role_code'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_app_user_role'),
        PrimaryKeyConstraint('user_id', name='app_user_pkey'),
        UniqueConstraint('email', name='app_user_email_key')
    )

    user_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('true'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    role_code: Mapped[str] = mapped_column(String(50), nullable=False)
    last_login_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))

    app_role: Mapped['AppRole'] = relationship('AppRole', back_populates='app_user')
    alert: Mapped[list['Alert']] = relationship('Alert', back_populates='handled_by_user')


class Zone(Base):
    __tablename__ = 'zone'
    __table_args__ = (
        ForeignKeyConstraint(['building_id'], ['building.building_id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_zone_building'),
        PrimaryKeyConstraint('zone_id', name='zone_pkey'),
        Index('idx_zone_building', 'building_id')
    )

    zone_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    building_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    floor: Mapped[int | None] = mapped_column(Integer)

    building: Mapped['Building'] = relationship('Building', back_populates='zone')
    node: Mapped[list['Node']] = relationship('Node', back_populates='zone')


class Node(Base):
    __tablename__ = 'node'
    __table_args__ = (
        CheckConstraint('local_storage_mb IS NULL OR local_storage_mb >= 0::numeric', name='chk_node_local_storage'),
        ForeignKeyConstraint(['zone_id'], ['zone.zone_id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_node_zone'),
        PrimaryKeyConstraint('node_id', name='node_pkey'),
        UniqueConstraint('code', name='node_code_key'),
        Index('idx_node_zone', 'zone_id')
    )

    node_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    zone_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    registered_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    ip_address: Mapped[object | None] = mapped_column(INET)
    local_storage_mb: Mapped[decimal.Decimal | None] = mapped_column(Numeric(12, 2))
    last_signal_received_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))

    zone: Mapped['Zone'] = relationship('Zone', back_populates='node')
    connectivity_log: Mapped[list['ConnectivityLog']] = relationship('ConnectivityLog', back_populates='node')
    sensor: Mapped[list['Sensor']] = relationship('Sensor', back_populates='primary_node')
    reading: Mapped[list['Reading']] = relationship('Reading', back_populates='receiving_node')


class ConnectivityLog(Base):
    __tablename__ = 'connectivity_log'
    __table_args__ = (
        CheckConstraint('ended_at IS NULL OR ended_at >= started_at', name='chk_connectivity_log_dates'),
        ForeignKeyConstraint(['node_id'], ['node.node_id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_connectivity_log_node'),
        PrimaryKeyConstraint('connectivity_id', name='connectivity_log_pkey'),
        Index('idx_connectivity_log_node_started_at', 'node_id', 'started_at')
    )

    connectivity_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    node_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(True))

    node: Mapped['Node'] = relationship('Node', back_populates='connectivity_log')


class Sensor(Base):
    __tablename__ = 'sensor'
    __table_args__ = (
        ForeignKeyConstraint(['primary_node_id'], ['node.node_id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_sensor_primary_node'),
        ForeignKeyConstraint(['sensor_type_id'], ['sensor_type.sensor_type_id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_sensor_sensor_type'),
        PrimaryKeyConstraint('sensor_id', name='sensor_pkey'),
        UniqueConstraint('code', name='sensor_code_key'),
        Index('idx_sensor_primary_node', 'primary_node_id'),
        Index('idx_sensor_sensor_type', 'sensor_type_id')
    )

    sensor_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    primary_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sensor_type_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    connection_type: Mapped[str | None] = mapped_column(String(50))
    connection_address: Mapped[str | None] = mapped_column(String(250))

    primary_node: Mapped['Node'] = relationship('Node', back_populates='sensor')
    sensor_type: Mapped['SensorType'] = relationship('SensorType', back_populates='sensor')
    reading: Mapped[list['Reading']] = relationship('Reading', back_populates='sensor')


class Reading(Base):
    __tablename__ = 'reading'
    __table_args__ = (
        CheckConstraint('sequence_number IS NULL OR sequence_number >= 0', name='chk_reading_sequence_number'),
        ForeignKeyConstraint(['receiving_node_id'], ['node.node_id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_reading_receiving_node'),
        ForeignKeyConstraint(['sensor_id'], ['sensor.sensor_id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_reading_sensor'),
        PrimaryKeyConstraint('reading_id', name='reading_pkey'),
        Index('idx_reading_receiving_node_received_at', 'receiving_node_id', 'received_at'),
        Index('idx_reading_sensor_measured_at', 'sensor_id', 'measured_at')
    )

    reading_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    sensor_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    receiving_node_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    measured_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    received_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    measured_value: Mapped[decimal.Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    sequence_number: Mapped[int | None] = mapped_column(BigInteger)

    receiving_node: Mapped['Node'] = relationship('Node', back_populates='reading')
    sensor: Mapped['Sensor'] = relationship('Sensor', back_populates='reading')
    alert: Mapped[list['Alert']] = relationship('Alert', back_populates='reading')


class Alert(Base):
    __tablename__ = 'alert'
    __table_args__ = (
        ForeignKeyConstraint(['handled_by_user_id'], ['app_user.user_id'], ondelete='SET NULL', onupdate='CASCADE', name='fk_alert_handled_by_user'),
        ForeignKeyConstraint(['reading_id'], ['reading.reading_id'], ondelete='RESTRICT', onupdate='CASCADE', name='fk_alert_reading'),
        PrimaryKeyConstraint('alert_id', name='alert_pkey'),
        UniqueConstraint('event_uuid', name='alert_event_uuid_key'),
        Index('idx_alert_generated_at', 'generated_at'),
        Index('idx_alert_handled_by_user', 'handled_by_user_id')
    )

    alert_id: Mapped[int] = mapped_column(BigInteger, Identity(start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), primary_key=True, autoincrement=True)
    event_uuid: Mapped[str] = mapped_column(String(100), nullable=False)
    reading_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    alert_code: Mapped[str] = mapped_column(String(100), nullable=False)
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    handled_by_user_id: Mapped[int | None] = mapped_column(BigInteger)

    handled_by_user: Mapped[Optional['AppUser']] = relationship('AppUser', back_populates='alert')
    reading: Mapped['Reading'] = relationship('Reading', back_populates='alert')
