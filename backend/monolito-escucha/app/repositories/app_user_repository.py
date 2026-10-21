"""AppUser repository."""
from collections.abc import Sequence

from sqlalchemy import select

from app.models.app_user import AppUser
from app.repositories.base import BaseRepository


class AppUserRepository(BaseRepository[AppUser, AppUser, AppUser]):
    model = AppUser

    async def get_by_email(self, email: str) -> AppUser | None:
        """Get user by email."""
        stmt = select(AppUser).where(AppUser.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_role(self, role_code: int) -> Sequence[AppUser]:
        """Get users by role code."""
        stmt = select(AppUser).where(AppUser.role_code == role_code)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_handled_alerts(self, user_id: int) -> Sequence[AppUser]:
        """Get handled alerts for a user."""
        stmt = select(AppUser).where(AppUser.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
