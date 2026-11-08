"""Alert repository - Create, Read, Update operations."""
from collections.abc import Sequence

from sqlalchemy import select

from app.models.alert import Alert
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository[Alert, Alert, Alert]):
    model = Alert

    async def get_by_event_uuid(self, event_uuid: str) -> Alert | None:
        """Get alert by event UUID."""
        stmt = select(Alert).where(Alert.event_uuid == event_uuid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_reading(self, reading_id: int) -> Sequence[Alert]:
        """Get alerts by reading ID."""
        stmt = select(Alert).where(Alert.reading_id == reading_id).order_by(Alert.generated_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_handled_user(self, user_id: int) -> Sequence[Alert]:
        """Get alerts handled by a user."""
        stmt = select(Alert).where(Alert.handled_by_user_id == user_id).order_by(Alert.generated_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_unhandled(self) -> Sequence[Alert]:
        """Get unhandled alerts."""
        stmt = select(Alert).where(Alert.handled_by_user_id.is_(None)).order_by(Alert.generated_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
