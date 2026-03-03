from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")
SchemaType = TypeVar("SchemaType")


class AbstractRepository(ABC, Generic[ModelType, SchemaType]):
    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    @abstractmethod
    async def add(self, data: dict[str, Any]) -> SchemaType:
        """Создать запись и вернуть схему"""
        ...

    @abstractmethod
    async def get(self, id: Any) -> SchemaType | None:
        """Получить по первичному ключу"""
        ...

    # @abstractmethod
    # async def get_one_or_none(self, **filters: Any) -> SchemaType | None:
    #     """Получить одну запись или None по фильтрам"""
    #     ...

    # @abstractmethod
    # async def list(self, **filters: Any) -> Sequence[SchemaType]:
    #     """Список записей по фильтрам"""
    #     ...

    # @abstractmethod
    # async def exists(self, **filters: Any) -> bool:
    #     """Существует ли хотя бы одна запись"""
    #     ...

    async def get_or_create(
        self,
        defaults: dict[str, Any] | None = None,
        **filters: Any
    ) -> tuple[SchemaType, bool]:
        """Аналог get_or_create из Django ORM"""
        existing = await self.get_one_or_none(**filters)
        if existing:
            return existing, False

        data = {**filters, **(defaults or {})}
        created = await self.add(data)
        return created, True
