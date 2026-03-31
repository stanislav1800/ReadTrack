from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.book_tracking.database.models import ReadingStatus
from src.book_tracking.database.schemas.book import BookRead


class UserBookRead(BaseModel):
    """Связь пользователь — книга (UserBook)"""
    
    id: int
    user_id: int
    book_id: int
    status: ReadingStatus
    minutes_read: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Можно добавить вложенную книгу (но осторожно с циклами)
    book: Optional[BookRead] = None

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
    )


class UserAddBookRead(BaseModel):
    """Связь "пользователь добавил книгу" (UserAddBook)"""
    
    id: int
    user_id: int
    book_id: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )