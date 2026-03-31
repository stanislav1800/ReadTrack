from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.book_tracking.database import repository
from src.database.unit_of_work import AbstractUnitOfWork


class BookUnitOfWork(AbstractUnitOfWork):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.book = repository.BookRepository(self._session)
        self.tag = repository.TagRepository(self._session)
        self.user_add_book = repository.UserAddBookRepository(self._session)
        self.user_book = repository.UserBookRepository(self._session)
        return self

    async def __aexit__(self, *args):
        await super().__aexit__(*args)
        await self._session.close()

    async def _commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()
