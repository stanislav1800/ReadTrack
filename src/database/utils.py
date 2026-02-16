import logging

from src.database.base import Base
from src.database.engine import engine

logger = logging.getLogger(__name__)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
