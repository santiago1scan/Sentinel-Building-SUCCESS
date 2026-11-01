"""Alert service - Create, Read, Update operations."""
from collections.abc import Sequence

from app.repositories.alert_repository import AlertRepository
from app.schemas.alert import AlertCreate, AlertRead, AlertUpdate


class AlertService:
    def __init__(self, repository: AlertRepository):
        self.repository = repository

    async def create(self, alert_in: AlertCreate) -> AlertRead:
        alert = await self.repository.create(alert_in)
        return AlertRead.model_validate(alert)

    async def get(self, alert_id: int) -> AlertRead | None:
        alert = await self.repository.get(alert_id)
        return AlertRead.model_validate(alert) if alert else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[AlertRead]:
        alerts = await self.repository.get_all(limit=limit, offset=offset)
        return [AlertRead.model_validate(a) for a in alerts]

    async def update(self, alert_id: int, alert_in: AlertUpdate) -> AlertRead | None:
        alert = await self.repository.get(alert_id)
        if not alert:
            return None
        updated = await self.repository.update(alert, alert_in)
        return AlertRead.model_validate(updated)

    async def get_by_event_uuid(self, event_uuid: str) -> AlertRead | None:
        alert = await self.repository.get_by_event_uuid(event_uuid)
        return AlertRead.model_validate(alert) if alert else None

    async def get_by_reading(self, reading_id: int) -> Sequence[AlertRead]:
        alerts = await self.repository.get_by_reading(reading_id)
        return [AlertRead.model_validate(a) for a in alerts]

    async def get_by_handled_user(self, user_id: int) -> Sequence[AlertRead]:
        alerts = await self.repository.get_by_handled_user(user_id)
        return [AlertRead.model_validate(a) for a in alerts]

    async def get_unhandled(self) -> Sequence[AlertRead]:
        alerts = await self.repository.get_unhandled()
        return [AlertRead.model_validate(a) for a in alerts]
