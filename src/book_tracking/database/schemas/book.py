from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, computed_field


class TagRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BookRead(BaseModel):
    """Схема для списка книг (используется в aiogram-dialog)"""
    
    id: int
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    published_year: int
    minutes_read: Optional[int] = None
    status: Optional[str] = None
    created_at: datetime

    # Отношения
    tags: List[TagRead] = []

    # Удобное поле только с названиями тегов
    @computed_field
    @property
    def tag_names(self) -> List[str]:
        return [tag.name for tag in self.tags] if self.tags else []

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,      # BookStatus.UNVERIFIED → "unverified"
    )


class BookDetailRead(BookRead):
    """Полная схема книги (если понадобится детальный просмотр)"""
    user_associations: List["UserBookRead"] = []
    add_books: List["UserAddBookRead"] = []


# Для избежания циклических импортов
from .user_book import UserBookRead, UserAddBookRead
BookDetailRead.model_rebuild()