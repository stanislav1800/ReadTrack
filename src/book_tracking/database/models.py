import enum
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.config import settings
from src.database.base import Base

if TYPE_CHECKING:
    from src.users.database.models import Users


logger = logging.getLogger(__name__)

class ReadingStatus(enum.Enum):
    planned = "planned"
    reading = "reading"
    read = "read"


class Books(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Название книги",
    )
    author: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="Автор книги",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Краткое описание книги",
    )
    published_year: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
        comment="Год публикации",
    )
    minutes_read: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Сколько минут/времени предварительно займет прочтение",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        comment="Дата добавления в базу",
    )

    user_associations: Mapped[list["UserBook"]] = relationship(
        "UserBook", 
        back_populates="book"
    )
    tags: Mapped[list["BookTag"]] = relationship(
        "BookTag", 
        back_populates="book"
    )


class UserBook(Base):
    __tablename__ = "user_books"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("users.id"), 
        nullable=False,
        comment="Пользователь",
    )
    book_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("books.id"), 
        nullable=False,
        comment="Книга",
    )
    status: Mapped[int] = mapped_column(
        Enum(ReadingStatus), 
        default=ReadingStatus.planned, 
        nullable=False,
        comment="Статус: planned, reading, read",
    )
    minutes_read: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Сколько минут/времени потрачено",
    )
    created_at: Mapped[int] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
        comment="Дата добавления книги в трекер",
    )
    updated_at: Mapped[int] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Последнее обновление статуса",
    )

    user: Mapped["Users"] = relationship("Users", back_populates="books")
    book: Mapped["Books"] = relationship("Books", back_populates="user_associations")

class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(
        String(100),
        comment="Название тега",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(560),
        comment="Описание тега",
    )

    book_associations: Mapped[list["BookTag"]] = relationship(
        "BookTag", back_populates="tag"
    )

class BookTag(Base):
    __tablename__ = "book_tag"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("books.id"), 
        nullable=False,
        comment="tag",
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("tag.id"), 
        nullable=False,
        comment="Ссылка на тег",
    )

    book: Mapped["Books"] = relationship("Books", back_populates="tags")
    tag: Mapped["Tag"] = relationship("Tag", back_populates="book_associations")
