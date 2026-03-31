import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd.select import Select, Toggle
from aiogram_dialog.widgets.common.scroll import ManagedScroll
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from src.book_tracking.database.models import BookStatus, Books
from src.book_tracking.database.uow import BookUnitOfWork
from src.core.config import settings
from src.database.engine import async_session_maker
from src.integration.infrastructure.book_search.book_finder_openai import (
    BookSearchResponse,
    BookSearchResult,
    find_books,
    find_books_async,
)
from src.users.database.models import Users


logger = logging.getLogger()

@dataclass
class BookStatusItem:
    id: str
    name: str
    emoji: str

async def get_my_list_books(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    current_user: Users | None = dialog_manager.middleware_data.get("current_user")

    async with BookUnitOfWork(async_session_maker) as uow:
        user_books = await uow.user_book.get_by_filter(user_id=current_user.id)

    return {"books": user_books}


async def get_list_books(dialog_manager: DialogManager, **kwargs):
    # m_select: ManagedScroll = dialog_manager.find("scrolling_list_books")
    # logger.info(m_select)
    # logger.info(m_select.__dict__)
    # m_select.set_page()
    query = dialog_manager.dialog_data.get("search_query")

    async with BookUnitOfWork(async_session_maker) as uow:
        books = await uow.book.get_by_filter(query=query)

    return {"books": books}


# async def get_list_books_(dialog_manager: DialogManager, **kwargs):
#     search_book = dialog_manager.find("search_book").get_value()

#     cached_term: str | None = dialog_manager.dialog_data.get("last_search_term")
#     cached_books: list | None = dialog_manager.dialog_data.get("search_results")
#     excluded: list[str] = dialog_manager.dialog_data.get("excluded_books", [])

#     # Автоматический сброс excluded при смене поискового запроса
#     if cached_term and cached_term != search_book:
#         dialog_manager.dialog_data.pop("excluded_books", None)
#         excluded = []
    
#     if cached_books and cached_term == search_book:
#         logger.info(f"Кэш хит для запроса '{search_book}' — возвращаем {len(cached_books)} книг")
#         return {"books": [BookSchema.model_validate(serialized) for serialized in cached_books]}
    
#     logger.info(f"Новый поиск '{search_book}' (исключено {len(excluded)} книг)")

#     async with BookUnitOfWork(async_session_maker) as uow:
#         stmt = select(Books).where(
#             or_(
#                 Books.title.ilike(f"%{search_book}%"),
#                 Books.author.ilike(f"%{search_book}%"),
#                 Books.description.ilike(f"%{search_book}%"),
#             )
#         ).order_by(Books.title)
#         result = await uow.books.execute(stmt)
#         db_books = [uow.books._to_domain(book) for book in result]

#         if db_books:
#             books_list = db_books
#         else:
#             try:
#                 # book_search_results: BookSearchResponse = await find_books_async(search_book, count=8)
#                 book_search_results: BookSearchResponse = await asyncio.to_thread(find_books, search_book, count=8, excluded_books=excluded)
#             except Exception as e:
#                 logger.error(f"API search failed: {e}", exc_info=True)
#                 book_search_results = BookSearchResponse(books=[])

#             added_books = []
#             for book in book_search_results.books:
#                 existing = await uow.books.get_by_filters(title=book.title, author=book.author)
#                 if existing:
#                     added_books.append(existing)
#                     continue

#                 try:
#                     db_book = await uow.books.add({
#                         "title": book.title,
#                         "author": book.author,
#                         "description": book.description,
#                         "published_year": book.published_year,
#                         "minutes_read": book.estimated_minutes_read,
#                     })

#                     seen_tags = set()
#                     for tag in book.tags:
#                         seen_tags.add(tag)
#                         db_tag = await uow.tag.get_by_filters(name=tag)
#                         if db_tag is None:
#                             db_tag = await uow.tag.add({"name": tag})

#                         await uow.book_tag.add({
#                             "book_id": db_book.id,
#                             "tag_id": db_tag.id,
#                         })

#                     added_books.append(db_book)

#                 except IntegrityError:
#                     existing = await uow.books.get_by_filters(title=book.title, author=book.author)
#                     if existing:
#                         added_books.append(existing)

#             await uow.commit()
#             books_list = added_books

#     serialized_books = [book.model_dump(mode="json", exclude_none=True) for book in books_list]
#     dialog_manager.dialog_data["search_results"] = serialized_books
#     dialog_manager.dialog_data["last_search_term"] = search_book
    
#     logger.info(f"Сохранён кэш: {len(books_list)} книг для запроса '{search_book}'")

#     return {"books": books_list}


async def get_book(dialog_manager: DialogManager, **kwargs):
    current_user: Users | None = dialog_manager.middleware_data.get("current_user")

    book_id = dialog_manager.dialog_data.get("book_id")
    if book_id is None:
        book_id = dialog_manager.start_data.get("book_id")

    async with BookUnitOfWork(async_session_maker) as uow:
        book = await uow.book.get_by_id(book_id)
        if any([True for user in book.user_associations if current_user.id == user.user_id]):
            is_my_book = True
        else:
            is_my_book = False

    return {
        "book": book,
        "is_my_book": is_my_book
    }


async def get_book_(dialog_manager: DialogManager, **kwargs):
    current_user: Users | None = dialog_manager.middleware_data.get("current_user")
    book_id = dialog_manager.dialog_data.get("book_id")
    async with BookUnitOfWork(async_session_maker) as uow:
        book = await uow.books.get(book_id)
        exists = await uow.user_book.get_by_filters(user_id=current_user.id, book_id=book_id)
        if exists:
            dialog_manager.dialog_data["book_added"] = True
            toggle: Toggle = dialog_manager.find("toggle_change_status")
            if toggle:
                toggle.set_checked
                await toggle.set_checked(
                    item_id=exists.status.value,
                )

        else:
            dialog_manager.dialog_data.pop("book_added", None)
    
    statuses = [
        BookStatusItem("planned", "В планах", "📌"),
        BookStatusItem("reading", "Читаю", "📖"),
        BookStatusItem("read", "Прочитано", "✅"),
    ]


    return {"book": book, "book_status": statuses}


async def get_tags_for_m_select(dialog_manager: DialogManager, **kwargs):
    async with BookUnitOfWork(async_session_maker) as uow:
        if dialog_manager.start_data and not dialog_manager.dialog_data.get("is_update_m_select"):
            book = await uow.book.get_by_id(dialog_manager.start_data.get("book_id"))
            widget = dialog_manager.find("tags")
            for tag in book.tags:
                await widget.set_checked(tag.id, True)
            dialog_manager.dialog_data.update(is_update_m_select=True)

        tags = await uow.tag.get_all()
        
    return {"tags": tags}

async def get_book_pre_create(dialog_manager: DialogManager, **kwargs):
    book_id = dialog_manager.dialog_data.get("book_id")

    if book_id is None:
        title = dialog_manager.find("title").get_value()
        author = dialog_manager.find("author").get_value()
        description = dialog_manager.find("description").get_value()
        published_year = dialog_manager.find("published_year").get_value()
        minutes_read = dialog_manager.find("minutes_read").get_value()
        tags = dialog_manager.find("tags").get_checked()

        async with BookUnitOfWork(async_session_maker) as uow:
            tags_data = []
            for tag_id in tags:
                tags_obj = await uow.tag.get_by_filter(id=int(tag_id))
                tags_data.extend([tag.name for tag in tags_obj])
    
    else:
        async with BookUnitOfWork(async_session_maker) as uow:
            book = await uow.book.get_by_id(book_id)
            title = book.title
            author = book.author
            description = book.description
            published_year = book.published_year
            minutes_read = book.minutes_read
            tags_data = [tag.name for tag in book.tags]
            
    logger.info(f"{tags_data=}")
    
    return {"book": 
            {
                "title": title, 
                "author": author, 
                "description": description, 
                "published_year": published_year, 
                "minutes_read": minutes_read, 
                "tags": tags_data
                }
            }