from typing import Generic, TypeVar, Optional, Any

from pydantic import BaseModel
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import Base


T = TypeVar("T", bound=Base)
S = TypeVar("S", bound=BaseModel)


class BaseRepository(Generic[T, S]):
    model: type[T]
    schema: type[S]

    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _options(self) -> list:
        return []
    
    def _build_filters(self, filters: dict):
        conditions = []
        for key, value in filters.items():
            column = getattr(self.model, key)
            if isinstance(value, list):
                conditions.append(column.in_(value))
            else:
                conditions.append(column == value)
        return conditions

    async def add(self, instance: T) -> T:
        """Добавить одну сущность"""
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def add_all(self, instances: list[T]) -> list[T]:
        """Добавить несколько сущностей"""
        self.session.add_all(instances)
        await self.session.flush()
        return instances

    async def get_by_id(self, id: Any, as_schema: bool = True) -> Optional[T | S]:
        """Получить по первичному ключу"""
        instance = await self.session.get(self.model, id, options=self._options())
        if as_schema:
            return self.to_schema(instance) if instance else None
        return instance

    async def get_by_filter(self, as_schema: bool = True, **filters) -> list[T, S]:
        """Получить по фильтру"""
        stmt = (
            select(self.model)
            .filter_by(**filters)
            .options(*self._options())
        )
        result = await self.session.execute(stmt)
        instances = result.scalars().all()
        if as_schema:
            return [self.to_schema(obj) for obj in instances]
        return instances
    
    async def get_by_filter_dynamic(self, filters: dict, as_schema: bool = True) -> list[T, S]:
        """Получить по динамическому фильтру"""
        stmt = select(self.model).filter(*self._build_filters(filters))
        result = await self.session.execute(stmt)
        instances = result.scalars().all()
        if as_schema:
            return [self.to_schema(obj) for obj in instances]
        return instances
    
    async def get_one_or_none(self, as_schema: bool = True, **filters) -> Optional[T | S]:
        """Получить одну запись или None"""
        stmt = select(self.model).filter_by(**filters).options(*self._options())
        result = await self.session.execute(stmt)
        instance = result.scalars().one_or_none()
        if as_schema:
            return self.to_schema(instance) if instance else None
        return instance
        

    async def get_all(self, *order_by, limit: Optional[int] = None, offset: Optional[int] = None, as_schema: bool = True) -> list[T, S]:
        """Получить все записи с сортировкой и пагинацией"""
        stmt = select(self.model)
        if order_by:
            stmt = stmt.order_by(*order_by)
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        stmt = stmt.options(*self._options())
        result = await self.session.execute(stmt)
        instances = result.scalars().all()
        if as_schema:
            return [self.to_schema(obj) for obj in instances]
        return instances

    async def update(self, instance: T, **values) -> T:
        """Обновить сущность"""
        for key, value in values.items():
            setattr(instance, key, value)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update_by_id(self, id_: Any, **values) -> Optional[T]:
        """Обновить по id"""
        stmt = (
            update(self.model)
            .where(self.model.id == id_)
            .values(**values)
            .returning(self.model)
        )
        result = await self.session.execute(stmt)
        instance = result.scalars().one_or_none()
        return instance

    async def delete(self, instance: T) -> None:
        """Удалить сущность"""
        await self.session.delete(instance)
        await self.session.flush()

    async def delete_by_id(self, id_: Any) -> bool:
        """Удалить по id, возвращает True если удалено"""
        stmt = delete(self.model).where(self.model.id == id_)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    def to_schema(self, instance: T) -> S:
        """Преобразовать сущность в схему"""
        return self.schema.model_validate(instance)
