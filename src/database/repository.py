import abc
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")
ModelSchemasType = TypeVar("ModelSchemasType")
KeyType = TypeVar("KeyType")


class AbstractRepository(abc.ABC, Generic[ModelType, KeyType]):
    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    @abc.abstractmethod
    async def add(self, data: dict[str, Any]) -> ModelSchemasType:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, key: KeyType) -> ModelSchemasType | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, key: KeyType, data: dict[str, Any]) -> ModelSchemasType | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, **filters: Any) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_filters(self, **filters: Any) -> ModelSchemasType | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def update_by_filters(
        self,
        filters: dict[str, Any],
        data: dict[str, Any],
    ) -> Sequence[ModelType]:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_by_filters(self, **filters: Any) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def list_by_filters(self, **filters: Any) -> Sequence[ModelType]:
        raise NotImplementedError
