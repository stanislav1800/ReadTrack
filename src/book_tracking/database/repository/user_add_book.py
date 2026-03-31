from sqlalchemy.orm import selectinload

from src.book_tracking.database.models import UserAddBook
from src.book_tracking.database.repository.base import BaseRepository
from src.book_tracking.database.schemas.user_book import UserAddBookRead


class UserAddBookRepository(BaseRepository[UserAddBook, UserAddBookRead]):
    model = UserAddBook
    schema = UserAddBookRead

    def _options(self) -> list:
        return [
            selectinload(UserAddBook.user),
            selectinload(UserAddBook.book),
        ]
