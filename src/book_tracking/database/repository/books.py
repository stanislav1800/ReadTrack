from typing import Optional, TypeVar

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from src.book_tracking.database.models import BookStatus, Books
from src.book_tracking.database.repository.base import T, BaseRepository
from src.book_tracking.database.schemas import BookDetailRead, BookRead


class BookRepository(BaseRepository[Books, BookDetailRead]):
    model = Books
    schema = BookDetailRead

    def _options(self) -> list:
        return [
            selectinload(Books.tags),
            selectinload(Books.user_associations),
            selectinload(Books.add_books),
        ]

    async def get_by_filter(self, query: Optional[str] = None, user_id: Optional[int] = None, **filters) -> list[Optional[T]]:
        where_clauses = [getattr(self.model, "status") != BookStatus.DELETED]

        # Специальная обработка поиска
        if query:
            where_clauses.append(
                or_(
                    self.model.title.ilike(f"%{query}%"),
                    self.model.author.ilike(f"%{query}%"),
                    self.model.description.ilike(f"%{query}%"),
                )
            )

        # Обычные точные фильтры (равенство)
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                where_clauses.append(getattr(self.model, key) == value)

        stmt = select(self.model).where(*where_clauses).options(*self._options())  # or and_(*where_clauses)
        # можно добавить .order_by(...), limit и т.д.
        if user_id:
            stmt = stmt.filter(self.model.user_associations.any(user_id=user_id))

        result = await self.session.execute(stmt)
        books = result.scalars().all()
        return [BookRead.model_validate(book) for book in books]
