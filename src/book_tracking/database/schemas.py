import logging
from datetime import datetime
from typing import Any, Optional

import pytz
from pydantic import BaseModel, ConfigDict, field_serializer, model_validator
from sqlalchemy.orm import RelationshipProperty

from src.book_tracking.database.models import ReadingStatus
from src.users.database.schemas import UserSchema

logger = logging.getLogger()

class BookSchema(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    published_year: int
    minutes_read: int
    created_at: datetime

    model_config = ConfigDict(
        # Если где-то в коде попадаются ORM-объекты — разрешаем from_attributes
        from_attributes=True,
        # Не нужно для Redis, но полезно для читаемости
        arbitrary_types_allowed=False,
    )

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Гарантируем ISO-формат для datetime — Redis/JSON любит строки"""
        return dt.isoformat()

    def to_dict(self, exclude_none: bool = True, mode: str = 'json') -> dict[str, Any]:
        """
        Безопасно сериализует модель в dict, готовый для dialog_data / Redis.
        
        Используем mode='json' → все значения JSON-совместимы (datetime → str и т.д.).
        """
        return self.model_dump(
            mode=mode,              # 'json' — самый безопасный для Redis
            exclude_none=exclude_none,
            exclude_unset=False,    # если хотите скрыть unset поля — True
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'BookSchema':
        """
        Восстановление модели из dict (из dialog_data).
        Полезно, если в будущем решите кэшировать не только список, но и выбранную книгу.
        """
        return cls.model_validate(data)

class BookTagSchema(BaseModel):
    id: int
    book_id: int
    tag_id: int

class TagSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None


class UserBookSchema(BaseModel):
    id: int
    user: Optional[UserSchema] = None
    book: Optional[BookSchema] = None
    status: ReadingStatus
    minutes_read: Optional[int] = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,           # ← это ключевой флаг
        populate_by_name=True,          # полезно при смешанных именах
        arbitrary_types_allowed=True,   # если где-то Enum или datetime
    )
    