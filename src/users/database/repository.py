from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repository import AbstractRepository
from src.users.database.models import Users
from src.users.database.schemas import UserSchema


class UserRepository(AbstractRepository[Users, int]):
    model = Users

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add(self, data: dict[str, Any]) -> UserSchema:
        obj = self.model(**data)
        self.session.add(obj)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ValueError("User with this user_id already exists") from exc
        return self._to_domain(obj)

    async def get(self, telegram_id: int) -> UserSchema | None:
        stmt = select(self.model).where(self.model.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        obj: Users | None = result.scalar_one_or_none()

        if obj is None:
            return None

        return self._to_domain(obj)

    async def update(self, telegram_id: int, data: dict[str, Any]) -> UserSchema | None:
        stmt = select(self.model).where(self.model.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        obj: Users | None = result.scalar_one_or_none()

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

    async def get_by_filters(self, **filters: Any) -> UserSchema | None:
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
    ) -> Sequence[Users]:
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

    async def list_by_filters(self, **filters: Any) -> Sequence[Users]:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def execute(self, stmt: Select) -> Sequence[Users]:
        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return users

    @staticmethod
    def _to_domain(obj: Users) -> UserSchema:
        return UserSchema(
            id=obj.id,
            telegram_id=obj.telegram_id,
            username=obj.username,
            first_name=obj.first_name,
            last_name=obj.last_name,
            is_active=obj.is_active,
            is_superuser=obj.is_superuser,
            is_verified=obj.is_verified,
            created_at=obj.created_at,
        )
