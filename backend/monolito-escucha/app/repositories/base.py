"""Base repository with generic CRUD operations."""
from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic repository for CRUD operations."""

    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> ModelType | None:
        """Get a single record by ID."""
        return await self.session.get(self.model, id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> Sequence[ModelType]:
        """Get all records with optional pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else obj_in
        db_obj = self.model(**obj_data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """Update an existing record."""
        obj_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, "model_dump") else obj_in
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        db_obj = await self.get(id)
        if db_obj:
            await self.session.delete(db_obj)
            await self.session.flush()
            return True
        return False

    async def exists(self, id: int) -> bool:
        """Check if a record exists by ID."""
        return await self.get(id) is not None
