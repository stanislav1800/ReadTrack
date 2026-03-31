import enum
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.config import settings
from src.database.base import Base

if TYPE_CHECKING:
    from src.users.database.models import Users


logger = logging.getLogger(__name__)

book_tag = Table(
    "book_tag",
    Base.metadata,
    Column("book_id", ForeignKey("books.id"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id"), primary_key=True),
)

class ReadingStatus(enum.Enum):
    planned = "planned"
    reading = "reading"
    read = "read"

    def label(self) -> str:
        return {
            ReadingStatus.planned: "Запланировано",
            ReadingStatus.reading: "Читаю",
            ReadingStatus.read: "Прочитано",
        }[self]

class BookStatus(enum.Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DELETED = "deleted"


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
    status: Mapped[str] = mapped_column(
        Enum(BookStatus), 
        default=BookStatus.UNVERIFIED, 
        nullable=True,
        comment="Статус книги",
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
    tags = relationship("Tag", secondary=book_tag)
    add_books: Mapped[list["UserAddBook"]] = relationship(
        "UserAddBook", 
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


class UserAddBook(Base):
    __tablename__ = "user_add_book"

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
    created_at: Mapped[int] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
        comment="Дата добавления книги в список книг",
    )

    user: Mapped["Users"] = relationship("Users", back_populates="add_books")
    book: Mapped["Books"] = relationship("Books", back_populates="add_books")

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

    books = relationship("Books", secondary=book_tag)

# class BookTag(Base):
#     __tablename__ = "book_tag"

#     id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
#     book_id: Mapped[int] = mapped_column(
#         Integer, 
#         ForeignKey("books.id"), 
#         nullable=False,
#         comment="tag",
#     )
#     tag_id: Mapped[int] = mapped_column(
#         Integer, 
#         ForeignKey("tag.id"), 
#         nullable=False,
#         comment="Ссылка на тег",
#     )

#     book: Mapped["Books"] = relationship("Books", back_populates="tags")
#     tag: Mapped["Tag"] = relationship("Tag", back_populates="book_associations")
