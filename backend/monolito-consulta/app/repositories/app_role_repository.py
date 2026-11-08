"""AppRole repository."""
from collections.abc import Sequence

from sqlalchemy import select

from app.models.app_role import AppRole
from app.repositories.base import BaseRepository


class AppRoleRepository(BaseRepository[AppRole, AppRole, AppRole]):
    model = AppRole

    async def get_by_code(self, role_code: int) -> AppRole | None:
        """Get role by code."""
        stmt = select(AppRole).where(AppRole.role_code == role_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_users(self, role_code: int) -> Sequence[AppRole]:
        """Get users for a role."""
        stmt = select(AppRole).where(AppRole.role_code == role_code)
        result = await self.session.execute(stmt)
        return result.scalars().all()
