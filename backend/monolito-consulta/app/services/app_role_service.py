"""AppRole service."""
from collections.abc import Sequence

from app.repositories.app_role_repository import AppRoleRepository
from app.schemas.app_role import AppRoleCreate, AppRoleRead, AppRoleUpdate


class AppRoleService:
    def __init__(self, repository: AppRoleRepository):
        self.repository = repository

    async def create(self, role_in: AppRoleCreate) -> AppRoleRead:
        role = await self.repository.create(role_in)
        return AppRoleRead.model_validate(role)

    async def get(self, role_code: int) -> AppRoleRead | None:
        role = await self.repository.get(role_code)
        return AppRoleRead.model_validate(role) if role else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[AppRoleRead]:
        roles = await self.repository.get_all(limit=limit, offset=offset)
        return [AppRoleRead.model_validate(r) for r in roles]

    async def update(self, role_code: int, role_in: AppRoleUpdate) -> AppRoleRead | None:
        role = await self.repository.get(role_code)
        if not role:
            return None
        updated = await self.repository.update(role, role_in)
        return AppRoleRead.model_validate(updated)

    async def delete(self, role_code: int) -> bool:
        return await self.repository.delete(role_code)

    async def get_by_code(self, role_code: int) -> AppRoleRead | None:
        role = await self.repository.get_by_code(role_code)
        return AppRoleRead.model_validate(role) if role else None

    async def get_users(self, role_code: int) -> Sequence[AppRoleRead]:
        roles = await self.repository.get_users(role_code)
        return [AppRoleRead.model_validate(r) for r in roles]
