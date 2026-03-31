from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class TagRead(BaseModel):    
    id: int
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TagDetailRead(TagRead):
    book_associations: List["BookTagRead"] = []

    model_config = ConfigDict(from_attributes=True)


class BookTagRead(BaseModel):    
    id: int
    book_id: int
    tag_id: int

    # Можно добавить вложенные объекты
    # tag: Optional[TagRead] = None
    # book: Optional["BookRead"] = None

    model_config = ConfigDict(from_attributes=True)


# Для избежания циклических импортов
from .book import BookRead
TagDetailRead.model_rebuild()