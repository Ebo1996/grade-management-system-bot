"""Generic base repository with common CRUD operations."""
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Provides common get/list/save/delete helpers.
    Concrete repositories extend this and add domain-specific queries.
    """

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, record_id: int) -> ModelT | None:
        """Fetch a record by primary key. Returns None if not found."""
        result = await self.session.get(self.model, record_id)
        return result

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        """Return a page of records."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def save(self, instance: ModelT) -> ModelT:
        """Persist a new or updated instance. Does NOT commit — caller handles that."""
        self.session.add(instance)
        await self.session.flush()  # Assign PK without committing
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Delete a record. Does NOT commit — caller handles that."""
        await self.session.delete(instance)
        await self.session.flush()

    async def count(self, **filters: Any) -> int:
        """Return the total count of records matching optional filters."""
        from sqlalchemy import func as sql_func

        stmt = select(sql_func.count()).select_from(self.model)
        for attr, value in filters.items():
            stmt = stmt.where(getattr(self.model, attr) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one()
