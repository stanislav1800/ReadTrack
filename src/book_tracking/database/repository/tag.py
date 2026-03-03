from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.book_tracking.database.models import Tag
from src.book_tracking.database.schemas import TagSchema
from src.database.repository import AbstractRepository


class TagRepository(AbstractRepository[Tag, int]):
    model = Tag

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add(self, data: dict[str, Any]) -> TagSchema:
        obj = self.model(**data)
        self.session.add(obj)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ValueError("User with this user_id already exists") from exc
        return self._to_domain(obj)

    async def get(self, telegram_id: int) -> TagSchema | None:
        stmt = select(self.model).where(self.model.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        obj: Tag | None = result.scalar_one_or_none()

        if obj is None:
            return None

        return self._to_domain(obj)

    async def update(self, telegram_id: int, data: dict[str, Any]) -> TagSchema | None:
        stmt = select(self.model).where(self.model.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        obj: Tag | None = result.scalar_one_or_none()

        if not obj:
            return None

        for key, value in data.items():
            if hasattr(obj, key) and key not in ["id", "telegram_id"]:
                setattr(obj, key, value)

        await self.session.flush()

        return self._to_domain(obj)

    async def delete(self, telegram_id: int) -> None:
        obj = await self.get_by_telegram_id(telegram_id)
        await self.session.delete(obj)

    async def get_by_filters(self, **filters: Any) -> TagSchema | None:
        stmt = select(self.model).filter_by(**filters)
        obj = await self.session.execute(stmt)
        obj = obj.scalar_one_or_none()
        if obj is None:
            return None
        return self._to_domain(obj)

    async def update_by_filters(
        self,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> Sequence[Tag]:
        stmt = (
            update(self.model)
            .filter_by(**filters)
            .values(**{k: v for k, v in data.items() if k not in ["id", "telegram_id"]})
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_filters(self, **filters: Any) -> None:
        stmt = delete(self.model).filter_by(**filters)
        await self.session.execute(stmt)

    async def list_by_filters(self, **filters: Any) -> Sequence[Tag]:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def execute(self, stmt: Select) -> Sequence[Tag]:
        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return users

    @staticmethod
    def _to_domain(obj: Tag) -> TagSchema:
        return TagSchema(
            id=obj.id,
            name=obj.name,
            description=obj.description,
        )
