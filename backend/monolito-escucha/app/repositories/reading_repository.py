"""Reading repository - Create and Read operations only."""
from collections.abc import Sequence

from sqlalchemy import select

from app.models.reading import Reading
from app.repositories.base import BaseRepository


class ReadingRepository(BaseRepository[Reading, Reading, Reading]):
    model = Reading

    async def get_by_sensor(self, sensor_id: int) -> Sequence[Reading]:
        """Get readings by sensor ID."""
        stmt = select(Reading).where(Reading.sensor_id == sensor_id).order_by(Reading.measured_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_receiving_node(self, receiving_node_id: int) -> Sequence[Reading]:
        """Get readings by receiving node ID."""
        stmt = select(Reading).where(Reading.receiving_node_id == receiving_node_id).order_by(Reading.measured_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_sequence_number(self, sequence_number: int) -> Sequence[Reading]:
        """Get readings by sequence number."""
        stmt = select(Reading).where(Reading.sequence_number == sequence_number)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_alerts(self, reading_id: int) -> Sequence[Reading]:
        """Get alerts for a reading."""
        stmt = select(Reading).where(Reading.reading_id == reading_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
