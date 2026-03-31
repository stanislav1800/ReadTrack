from sqlalchemy.orm import selectinload

from src.book_tracking.database.models import Books, UserBook
from src.book_tracking.database.repository.base import BaseRepository
from src.book_tracking.database.schemas.user_book import UserBookRead


class UserBookRepository(BaseRepository[UserBook, UserBookRead]):
    model = UserBook
    schema = UserBookRead

    def _options(self) -> list:
        return [
            selectinload(UserBook.user),
            selectinload(UserBook.book).selectinload(Books.tags),
        ]
