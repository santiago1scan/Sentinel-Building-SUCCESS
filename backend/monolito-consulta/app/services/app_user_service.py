"""AppUser service."""
from collections.abc import Sequence

from app.repositories.app_user_repository import AppUserRepository
from app.schemas.app_user import AppUserCreate, AppUserRead, AppUserUpdate


class AppUserService:
    def __init__(self, repository: AppUserRepository):
        self.repository = repository

    async def create(self, user_in: AppUserCreate) -> AppUserRead:
        user = await self.repository.create(user_in)
        return AppUserRead.model_validate(user)

    async def get(self, user_id: int) -> AppUserRead | None:
        user = await self.repository.get(user_id)
        return AppUserRead.model_validate(user) if user else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[AppUserRead]:
        users = await self.repository.get_all(limit=limit, offset=offset)
        return [AppUserRead.model_validate(u) for u in users]

    async def update(self, user_id: int, user_in: AppUserUpdate) -> AppUserRead | None:
        user = await self.repository.get(user_id)
        if not user:
            return None
        updated = await self.repository.update(user, user_in)
        return AppUserRead.model_validate(updated)

    async def delete(self, user_id: int) -> bool:
        return await self.repository.delete(user_id)

    async def get_by_email(self, email: str) -> AppUserRead | None:
        user = await self.repository.get_by_email(email)
        return AppUserRead.model_validate(user) if user else None

    async def get_by_role(self, role_code: int) -> Sequence[AppUserRead]:
        users = await self.repository.get_by_role(role_code)
        return [AppUserRead.model_validate(u) for u in users]

    async def get_handled_alerts(self, user_id: int) -> Sequence[AppUserRead]:
        users = await self.repository.get_handled_alerts(user_id)
        return [AppUserRead.model_validate(u) for u in users]
