from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, delete, select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.book_tracking.database.models import BookTag
from src.book_tracking.database.repository.base import BaseRepository
from src.book_tracking.database.schemas.tag import BookTagRead


class BookTagRepository(BaseRepository[BookTag, BookTagRead]):
    model = BookTag
    schema = BookTagRead

    def _options(self) -> list:
        return [
            # selectinload(BookTag.book),
            # selectinload(BookTag.tag),
        ]
