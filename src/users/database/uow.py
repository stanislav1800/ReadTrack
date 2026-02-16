from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.unit_of_work import AbstractUnitOfWork
from src.users.database.repository import UserRepository


class UserUnitOfWork(AbstractUnitOfWork):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.users = UserRepository(self._session)
        return self

    async def __aexit__(self, *args):
        await super().__aexit__(*args)
        await self._session.close()

    async def _commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()
