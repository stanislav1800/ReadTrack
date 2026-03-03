from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.book_tracking.database.models import Books, UserBook
from src.book_tracking.database.schemas import UserBookSchema
from src.database.repository import AbstractRepository


class UserBookRepository(AbstractRepository[UserBook, int]):
    model = UserBook

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def add(self, data: dict[str, Any]) -> UserBookSchema:
        obj = self.model(**data)
        self.session.add(obj)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ValueError("User with this user_id already exists") from exc
        return self._to_domain(obj)

    async def get(self, telegram_id: int) -> UserBookSchema | None:
        stmt = select(self.model).where(self.model.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        obj: UserBook | None = result.scalar_one_or_none()

        if obj is None:
            return None

        return self._to_domain(obj)

    async def update(self, user_id: int, book_id: int, data: dict[str, Any]) -> UserBookSchema | None:
        stmt = select(self.model).where(self.model.user_id == user_id, self.model.book_id == book_id)
        result = await self.session.execute(stmt)
        obj: UserBook | None = result.scalar_one_or_none()

        if not obj:
            return None

        for key, value in data.items():
            if hasattr(obj, key) and key not in ["id", "user_id", "book_id"]:
                setattr(obj, key, value)

        await self.session.flush()
        await self.session.refresh(obj)

        return self._to_domain(obj)

    async def delete(self, telegram_id: int) -> None:
        obj = await self.get_by_telegram_id(telegram_id)
        await self.session.delete(obj)

    async def get_user_books(
        self,
        user_id: int,
        limit: int = 50,                    # разумный лимит на всякий случай
        offset: int = 0,
        order_by: str = "created_at desc"   # можно потом параметризовать
    ) -> list[UserBookSchema]:
        """
        Возвращает все связи UserBook + связанные Books для пользователя
        """
        stmt = (
            select(UserBook, Books)
            .join(Books, UserBook.book_id == Books.id)
            .where(UserBook.user_id == user_id)
            .order_by(UserBook.created_at.desc())
            .options(
                selectinload(UserBook.user),
                selectinload(UserBook.book),
            )
            # .limit(limit)
            # .offset(offset)
        )

        result = await self.session.execute(stmt)
        result = result.scalars().all()
        return [UserBookSchema.model_validate(obj, from_attributes=True) for obj in result]

    async def get_by_filters(self, **filters: Any) -> UserBookSchema | None:
        stmt = select(self.model).filter_by(**filters)
        obj = await self.session.scalar(stmt)
        if obj is None:
            return None
        # return UserBookSchema.model_validate(obj, from_attributes=True)
        return UserBookSchema(
            id=obj.id,
            user=None,
            book=None,
            status=obj.status,
            minutes_read=obj.minutes_read,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )

    async def update_by_filters(
        self,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> Sequence[UserBook]:
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

    async def list_by_filters(self, **filters: Any) -> Sequence[UserBook]:
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def execute(self, stmt: Select) -> Sequence[UserBook]:
        result = await self.session.execute(stmt)
        users = result.scalars().all()

        return users

    @staticmethod
    def _to_domain(obj: UserBook) -> UserBookSchema:
        return UserBookSchema(
            id=obj.id,
            user_id=obj.user_id,
            book_id=obj.book_id,
            status=obj.status,
            minutes_read=obj.minutes_read,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )
