import logging
from dataclasses import dataclass
from typing import Any

from aiogram import Bot
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
    query = dialog_manager.dialog_data.get("search_query")

    async with BookUnitOfWork(async_session_maker) as uow:
        user_books = await uow.book.get_by_filter(query=query, user_id=current_user.id)

    return {"books": user_books}


async def get_list_books(dialog_manager: DialogManager, **kwargs):
    logger.info(dialog_manager.__dict__)
    context = dialog_manager.current_context()
    logger.info(context)
    logger.info(context.__dict__)
    state = context.state

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
    user_book = None

    book_id = dialog_manager.dialog_data.get("book_id")
    if book_id is None:
        book_id = dialog_manager.start_data.get("book_id")

    async with BookUnitOfWork(async_session_maker) as uow:
        book = await uow.book.get_by_id(book_id)
        if any([True for user in book.user_associations if current_user.id == user.user_id]):
            is_my_book = True
            user_book = await uow.user_book.get_one_or_none(user_id=current_user.id, book_id=book_id)
            logger.info(user_book)
            radio = dialog_manager.find("r_reading_status")
            if radio:
                await radio.set_checked(user_book.status)
        else:
            is_my_book = False

    return {
        "book": book,
        "user_books": user_book,
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


async def find_books_for_ii(dialog_manager: DialogManager,event_from_user, **kwargs):
    search_query = dialog_manager.find("search_book").get_value()
    
    excluded_books = dialog_manager.dialog_data.get("excluded_books", [])
    cached_query = dialog_manager.dialog_data.get("ii_search_query")
    cached_results = dialog_manager.dialog_data.get("ii_search_results")
    cached_error = dialog_manager.dialog_data.get("ii_search_error")

    bot: Bot = dialog_manager.middleware_data.get("bot")
    user_id = event_from_user.id
    
    if cached_query == search_query:
        if cached_results is not None:
            logger.info(f"Используем кэшированные результаты для запроса '{search_query}': {len(cached_results)} книг")
            books = [BookSearchResult(**book) for book in cached_results]
            return {"books": books, "error": None}
    
        if cached_error is not None:
            logger.info(f"Возвращаем кэшированную ошибку для запроса '{search_query}'")        
            return {"books": [], "error": cached_error}
    
    status_msg = await bot.send_message(user_id, "🔍 Ищу книги... Это может занять некоторое время...")

    search_results = None
    user_error = None

    try:
        logger.info(f"Делаем новый поиск для запроса: '{search_query}'")
        
        book_search_results: BookSearchResponse = await find_books(
            search_query,
            excluded_books=excluded_books
        )
        search_results = book_search_results.books
        logger.info(f"Найдено {len(search_results)} книг, сохранили в кэш")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"API search failed: {type(e).__name__}: {error_msg}", exc_info=True)
        
        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            user_error = "⚠️ Лимит запросов превышен. Попробуйте позже."
        elif "api" in error_msg.lower() or "key" in error_msg.lower():
            user_error = "⚠️ Ошибка при подключении к сервису поиска книг. Попробуйте позже."
        elif "timeout" in error_msg.lower():
            user_error = "⚠️ Превышено время ожидания ответа. Попробуйте ещё раз."
        elif "неполный ответ" in error_msg.lower() or "обрезан" in error_msg.lower():
            user_error = "⚠️ Ответ был слишком длинный. Попробуйте переформулировать запрос короче или конкретнее."
        elif "json" in error_msg.lower():
            user_error = "⚠️ Ошибка при обработке ответа. Попробуйте ещё раз."
        else:
            user_error = f"⚠️ Ошибка при поиске. Попробуйте позже."

    finally:
        try:
            await bot.delete_message(user_id, status_msg.message_id)
        except Exception as delete_error:
            logger.debug(f"Не удалось удалить сообщение о поиске: {delete_error}")

        books_as_dicts = None
        if search_results:
            books_as_dicts = [book.model_dump() for book in search_results]

        dialog_manager.dialog_data["ii_search_query"] = search_query
        dialog_manager.dialog_data["ii_search_results"] = books_as_dicts
        dialog_manager.dialog_data["ii_search_error"] = user_error
        
        return {"books": search_results or [], "error": user_error}


async def get_ai_search_book_detail(dialog_manager: DialogManager, **kwargs):
    """Получить детали найденной книги из кэша"""
    book_index = dialog_manager.dialog_data.get("ai_book_index")
    cached_results = dialog_manager.dialog_data.get("ii_search_results", [])
    
    if book_index is not None and 0 <= book_index < len(cached_results):
        # Преобразуем словарь в BookSearchResult объект
        book_dict = cached_results[book_index]
        book = BookSearchResult(**book_dict) if isinstance(book_dict, dict) else book_dict
        logger.info(f"Получаем детали книги с индексом {book_index}")
        return {"book": book}
    
    logger.warning(f"Не удалось получить книгу с индексом {book_index}")
    return {"book": None}