import abc


class AbstractUnitOfWork(abc.ABC):
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.rollback()

    async def commit(self):
        await self._commit()

    @abc.abstractmethod
    async def rollback(self):
        pass

    @abc.abstractmethod
    async def _commit(self):
        pass
