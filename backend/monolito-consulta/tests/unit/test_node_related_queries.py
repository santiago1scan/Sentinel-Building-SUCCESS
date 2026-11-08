"""Sub-recursos de nodo: cada endpoint consulta su propia tabla y devuelve su propio schema."""
import datetime
import decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.repositories.node_repository import NodeRepository
from app.schemas.connectivity_log import ConnectivityLogRead
from app.schemas.reading import ReadingRead
from app.schemas.sensor import SensorRead
from app.services.node_service import NodeService

NOW = datetime.datetime(2026, 11, 8, 12, 0, tzinfo=datetime.UTC)


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeSession:
    """Captura la sentencia SQL que ejecuta el repositorio y devuelve filas predefinidas."""

    def __init__(self, rows=()):
        self.rows = list(rows)
        self.statements = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        return FakeResult(self.rows)


def compiled_sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


@pytest.mark.asyncio
async def test_received_readings_query_targets_reading_table():
    session = FakeSession()
    await NodeRepository(session).get_received_readings(7)

    sql = compiled_sql(session.statements[0])
    assert "FROM reading" in sql
    assert "reading.receiving_node_id = 7" in sql


@pytest.mark.asyncio
async def test_sensors_query_targets_sensor_table_by_primary_node():
    session = FakeSession()
    await NodeRepository(session).get_sensors(7)

    sql = compiled_sql(session.statements[0])
    assert "FROM sensor" in sql
    assert "sensor.primary_node_id = 7" in sql


@pytest.mark.asyncio
async def test_connectivity_logs_query_targets_connectivity_log_table():
    session = FakeSession()
    await NodeRepository(session).get_connectivity_logs(7)

    sql = compiled_sql(session.statements[0])
    assert "FROM connectivity_log" in sql
    assert "connectivity_log.node_id = 7" in sql


class FakeNodeRepository:
    def __init__(self, rows, node_exists=True):
        self.rows = rows
        self.node_exists = node_exists

    async def get(self, node_id):
        return SimpleNamespace(node_id=node_id) if self.node_exists else None

    async def get_received_readings(self, node_id):
        return self.rows

    async def get_sensors(self, node_id):
        return self.rows

    async def get_connectivity_logs(self, node_id):
        return self.rows


@pytest.mark.asyncio
async def test_service_returns_reading_schema_for_received_readings():
    reading = SimpleNamespace(
        reading_id=1, sensor_id=3, receiving_node_id=7, measured_at=NOW,
        measured_value=decimal.Decimal("21.5"), sequence_number=1, received_at=NOW,
    )
    service = NodeService(FakeNodeRepository([reading]))

    result = await service.get_received_readings(7)

    assert len(result) == 1
    assert isinstance(result[0], ReadingRead)
    assert result[0].receiving_node_id == 7


@pytest.mark.asyncio
async def test_service_returns_sensor_schema_for_sensors():
    sensor = SimpleNamespace(
        sensor_id=3, code="ADXL355-NODE-FLOOR-1", primary_node_id=7,
        sensor_type_id=1, connection_type=None, connection_address=None,
    )
    result = await NodeService(FakeNodeRepository([sensor])).get_sensors(7)

    assert isinstance(result[0], SensorRead)
    assert result[0].primary_node_id == 7


@pytest.mark.asyncio
async def test_service_returns_connectivity_schema_for_logs():
    log = SimpleNamespace(connectivity_id=5, node_id=7, started_at=NOW, ended_at=None)
    result = await NodeService(FakeNodeRepository([log])).get_connectivity_logs(7)

    assert isinstance(result[0], ConnectivityLogRead)
    assert result[0].node_id == 7


@pytest.mark.asyncio
async def test_sub_resources_return_404_for_unknown_node():
    from app.core.exceptions import NotFoundError

    service = NodeService(FakeNodeRepository([], node_exists=False))

    with pytest.raises(NotFoundError):
        await service.get_received_readings(99)
    with pytest.raises(NotFoundError):
        await service.get_sensors(99)
    with pytest.raises(NotFoundError):
        await service.get_connectivity_logs(99)
