import logging
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.common.scroll import ManagedScroll
from aiogram_dialog.widgets.kbd import Button, Select, SwitchTo, Toggle
from sqlalchemy.exc import IntegrityError

from src.book_tracking import states
from src.book_tracking.database.models import Books, ReadingStatus, Tag, UserAddBook, UserBook
from src.book_tracking.database.uow import BookUnitOfWork
from src.core.commands import set_user_commands
from src.database.engine import async_session_maker
from src.users.database.models import Users
from src.users.database.uow import UserUnitOfWork

logger = logging.getLogger()


async def switch_to_by_state(manager: DialogManager, target_state_name: str):
    current_state = manager.current_context().state
    group_class = current_state.group
    target_state = getattr(group_class, target_state_name)
    await manager.switch_to(target_state)


async def on_book_update_status(
    c: CallbackQuery,
    widget: Select[Any],
    manager: DialogManager,
    selected_id: str,
) -> None:
    current_user: Users | None = manager.middleware_data.get("current_user")
    book_id = manager.dialog_data.get("book_id")

    async with BookUnitOfWork(async_session_maker) as uow:
        user_book = await uow.user_book.get_by_filter(user_id=current_user.id, book_id=book_id, as_schema=False)   
        await uow.user_book.update(user_book, {"status": selected_id})
        await uow.commit()
        await c.answer("Статус обновлён ✅")


async def on_book_selected(
    c: CallbackQuery,
    widget: Select[Any],
    manager: DialogManager,
    selected_id: str,
) -> None:
    manager.dialog_data["book_id"] = int(selected_id)
    current_state = manager.current_context().state
    group_class = current_state.group
    target_state = getattr(group_class, "book_detail")
    await manager.switch_to(target_state)



async def on_new_search_click(
    callback: CallbackQuery,
    widget: SwitchTo,
    manager: DialogManager,
) -> None:
    """Очистка кэша поиска при выборе 'Найти другое'"""
    manager.dialog_data.pop("search_results", None)
    manager.dialog_data.pop("last_search_term", None)
    # manager.show_mode = ShowMode.EDIT  # если нужно перерисовать без перехода
    # await manager.next()              # если нужно вручную перейти — но SwitchTo сам перейдёт


async def on_find_more_click(
    callback: CallbackQuery,
    widget: SwitchTo,
    manager: DialogManager,
) -> None:
    """«Найти еще» — добавляем текущие книги в исключения и сбрасываем кэш"""
    logger.info("Нажата кнопка 'Найти еще' — добавляем текущие книги в excluded")

    current_results: list[dict] | None = manager.dialog_data.get("search_results")
    if current_results:
        # Храним только строки "Название|Автор" — 100% сериализуемо в Redis
        excluded = manager.dialog_data.setdefault("excluded_books", [])
        for book in current_results:
            title = book.get("title", "").strip()
            author = book.get("author") or "Неизвестен"
            key = f"{title}|{author}".lower()
            if key not in excluded:
                excluded.append(key)

        # Ограничиваем размер (чтобы не переполнить промпт)
        if len(excluded) > 12:
            excluded[:] = excluded[-12:]  # оставляем только последние 12

    # Сбрасываем кэш результатов — заставляем getter сделать новый поиск
    manager.dialog_data.pop("search_results", None)
    # last_search_term оставляем — запрос тот же

async def on_add_to_my_list(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
) -> None:
    current_user: Users | None =manager.middleware_data.get("current_user")
    book_id = manager.dialog_data.get("book_id")
    user_id = current_user.id
    async with BookUnitOfWork(async_session_maker) as uow:
        await uow.user_book.add({
            "user_id": user_id,
            "book_id": book_id,
        })
        await uow.commit()
        await callback.answer("Книга добавлена в ваш список", show_alert=True)
    


async def on_start_book_detail(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
) -> None:
    await manager.start(states.MyBooks.book_detail, data={"book_id": manager.dialog_data["book_id"]})


async def on_add_to_list(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
) -> None:
    current_user: Users | None =manager.middleware_data.get("current_user")
    user_id = current_user.id
    book_id = manager.dialog_data.get("book_id")

    async with BookUnitOfWork(async_session_maker) as uow:
        await uow.user_book.add(
            UserBook(
                user_id=user_id,
                book_id=book_id,
                status=ReadingStatus.planned,
                minutes_read=None
            )
        )
        await uow.commit()

        await callback.answer("Книга добавлена в «Планирую прочитать»", show_alert=True)


async def on_status_toggle(
    callback: CallbackQuery,
    widget: Toggle,
    dialog_manager: DialogManager,
    item_id: str,
):
    current_user: Users | None = dialog_manager.middleware_data.get("current_user")
    book_id_str = dialog_manager.dialog_data.get("book_id")
    book_id = int(book_id_str)
    async with BookUnitOfWork(async_session_maker) as uow:
        logger.info(current_user.id)
        logger.info(book_id)
        logger.info(item_id)
        book = await uow.user_book.update(current_user.id, book_id, {"status": item_id})
        logger.info(book)
        await uow.commit()

    await callback.answer("Статус обновлён ✅")

async def on_search_success(
    message: Message,
    widget,  # ManagedTextInput
    manager: DialogManager,
    text: str
):
    m_select = manager.find("scrolling_list_books")
    await m_select.set_page(0)
    manager.dialog_data["search_query"] = text

    await switch_to_by_state(manager, "list_books")


async def on_cancel_filter(
    message: Message,
    widget,
    manager: DialogManager,
):
    m_select: ManagedScroll = manager.find("scrolling_list_books")
    await m_select.set_page(0)
    manager.dialog_data.pop("search_query", None)

    await switch_to_by_state(manager, "list_books")


async def on_create_book(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
):
    current_user: Users | None = manager.middleware_data.get("current_user")

    title = manager.find("title").get_value()
    author = manager.find("author").get_value()
    description = manager.find("description").get_value()
    published_year = manager.find("published_year").get_value()
    minutes_read = manager.find("minutes_read").get_value()
    if minutes_read is not None:
        minutes_read = int(minutes_read)
    tags = manager.find("tags").get_checked()

    async with BookUnitOfWork(async_session_maker) as uow:
        tags_objs = await uow.tag.get_by_filter_dynamic({"id": [int(tag_id) for tag_id in tags]}, as_schema=False)

        book = await uow.book.add(
            Books(
                title=title,
                author=author,
                description=description,
                published_year=int(published_year),
                minutes_read=minutes_read,
                tags=list(tags_objs),
            )
        )
        
        await uow.user_add_book.add(
            UserAddBook(
                user_id=current_user.id,
                book_id=book.id,
            )
        )

        await uow.commit()
        manager.dialog_data["book_id"] = book.id
        await callback.answer("Книга создана", show_alert=True)
    
    # await manager.done()


async def on_next_or_update_book(
    callback: CallbackQuery,
    widget: TextInput,
    manager: DialogManager,
    *args,
    **kwargs,
):
    if manager.start_data:
        book_id = manager.start_data.get("book_id")
        field = manager.start_data.get("field")

        async with BookUnitOfWork(async_session_maker) as uow:
            if field == "tags":
                tags = manager.find("tags").get_checked()
                tags_objs = await uow.tag.get_by_filter_dynamic({"id": [int(tag_id) for tag_id in tags]}, as_schema=False)
                book = await uow.book.get_by_id(book_id)
                book.tags = list(tags_objs)

            else:
                # data = kwargs.get("data")
                data = args[0]
                if book_id:
                    if field in ["published_year", "minutes_read"]:
                        data = int(data)
                    await uow.book.update_by_id(book_id, **{field: data})

            await uow.commit()

            await manager.done()
            return
        
    await manager.next()

async def on_check_update_book(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
):
    manager.dialog_data.update(update_book=True)

async def on_start_update_book(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
):
    state_to_start = {
        "update_title": states.CreateBook.title,
        "update_author": states.CreateBook.author,
        "update_description": states.CreateBook.description,
        "update_published_year": states.CreateBook.published_year,
        "update_minutes_read": states.CreateBook.minutes_read,
        "update_tags": states.CreateBook.tags,
    }
    widget_id = button.widget_id
    await manager.start(state_to_start[widget_id], data={"book_id": manager.dialog_data["book_id"], "field": widget_id.replace("update_", "")})

async def on_error_data_not_int(
        message: Message,
        dialog_: Any,
        manager: DialogManager,
        error_: ValueError
):
    await message.answer("Введите число!")


async def on_change_reading_status(
    callback: CallbackQuery,
    select: Any,
    manager: DialogManager,
    data: ValueError
):
    current_user: Users | None = manager.middleware_data.get("current_user")
    book_id = manager.dialog_data.get("book_id")

    async with BookUnitOfWork(async_session_maker) as uow:
        user_book = await uow.user_book.get_one_or_none(user_id=current_user.id, book_id=book_id, as_schema=False)
        await uow.user_book.update(user_book, status=data)
        await uow.commit()
        await callback.answer("Статус обновлён ✅")

async def on_update_minutes_read(
    callback: CallbackQuery,
    widget: TextInput,
    manager: DialogManager,
    data,
):
    current_user: Users | None = manager.middleware_data.get("current_user")
    book_id = manager.dialog_data.get("book_id")

    async with BookUnitOfWork(async_session_maker) as uow:
        user_book = await uow.user_book.get_one_or_none(user_id=current_user.id, book_id=book_id, as_schema=False)
        await uow.user_book.update(user_book, minutes_read=int(data))
        await uow.commit()

    await manager.switch_to(states.MyBooks.book_detail)

async def on_delete_my_book(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
):
    current_user: Users | None = manager.middleware_data.get("current_user")
    book_id = manager.dialog_data.get("book_id")

    async with BookUnitOfWork(async_session_maker) as uow:
        user_book = await uow.user_book.get_one_or_none(user_id=current_user.id, book_id=book_id, as_schema=False)
        await uow.user_book.delete(user_book)
        await uow.commit()
        await callback.answer("Книга удалена")

    await manager.reset_stack()
    await manager.start(states.MyBooks.list_books)


async def on_ai_book_selected(
    callback: CallbackQuery,
    widget: Select[Any],
    manager: DialogManager,
    selected_id: str,
) -> None:
    """Обработчик выбора книги из результатов ИИ поиска"""
    cached_results = manager.dialog_data.get("ii_search_results", [])
    
    # Ищем индекс книги по ID (это хеш от названия и автора)
    try:
        for idx, book in enumerate(cached_results):
            # Книги хранятся как словари
            title = book.get("title", "") if isinstance(book, dict) else book.title
            author = book.get("author", "") if isinstance(book, dict) else book.author
            book_hash = str(hash(title + author) % 1000000)
            if book_hash == selected_id:
                manager.dialog_data["ai_book_index"] = idx
                await manager.switch_to(states.AISearchBooks.book_detail)
                return
            
        await callback.answer("❌ Книга не найдена")
    except Exception as e:
        logger.error(f"Ошибка при выборе книги: {e}")
        await callback.answer("❌ Ошибка при выборе книги")


async def on_ai_save_book(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
) -> None:
    """Сохраняет найденную книгу из ИИ в БД и добавляет пользователю"""
    current_user: Users | None = manager.middleware_data.get("current_user")
    book_index = manager.dialog_data.get("ai_book_index")
    cached_results = manager.dialog_data.get("ii_search_results", [])
    
    if book_index is None or not (0 <= book_index < len(cached_results)):
        await callback.answer("❌ Ошибка: книга не найдена")
        return
    
    book_data = cached_results[book_index]
    
    try:
        async with BookUnitOfWork(async_session_maker) as uow:
            # Извлекаем данные из словаря или объекта
            title = book_data.get("title") if isinstance(book_data, dict) else book_data.title
            author = book_data.get("author") if isinstance(book_data, dict) else book_data.author
            description = book_data.get("description") if isinstance(book_data, dict) else book_data.description
            published_year = book_data.get("published_year") if isinstance(book_data, dict) else book_data.published_year
            estimated_minutes = book_data.get("estimated_minutes_read") if isinstance(book_data, dict) else book_data.estimated_minutes_read
            
            # Проверяем, существует ли уже такая книга
            db_book = await uow.book.get_one_or_none(title=title, author=author)
            
            if db_book:
                logger.info(f"Книга уже существует в БД: {db_book.id}")
            else:
                # Создаём новую книгу
                new_book = Books(
                    title=title,
                    author=author,
                    description=description,
                    published_year=published_year,
                    minutes_read=estimated_minutes,
                )
                
                if book_data["tags"]:
                    for tag_name in book_data["tags"]:
                        db_tag = await uow.tag.get_one_or_none(name=tag_name, as_schema=False)
                        if not db_tag:
                            db_tag = await uow.tag.add(Tag(name=tag_name))
                        
                        new_book.tags.append(db_tag)
                
                db_book = await uow.book.add(new_book)

                await uow.user_add_book.add(
                    UserAddBook(
                        user_id=current_user.id,
                        book_id=db_book.id,
                    )
                )
                logger.info(f"Создана новая книга в БД: {db_book.id}")
                
            
            # Проверяем, есть ли у пользователя эта книга
            user_book = await uow.user_book.get_by_filter(
                user_id=current_user.id,
                book_id=db_book.id
            )
            
            if user_book:
                await callback.answer("✅ Эта книга уже в вашем списке")
            else:
                await uow.user_book.add(
                    UserBook(
                        user_id=current_user.id, 
                        book_id=db_book.id, 
                        status=ReadingStatus.planned
                    )
                )
                await callback.answer("✅ Книга добавлена в ваш список!", show_alert=True)
            
            await uow.commit()
    
    except Exception as e:
        logger.error(f"Ошибка при сохранении книги: {type(e).__name__}: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка при добавлении книги в ваш список.")
        return


async def on_ai_search_new_query(
    callback: CallbackQuery,
    widget: SwitchTo,
    manager: DialogManager,
) -> None:
    """Очистка кэша при выборе 'Найти другое'"""
    manager.dialog_data.pop("ii_search_query", None)
    manager.dialog_data.pop("ii_search_results", None)
    manager.dialog_data.pop("ii_search_error", None)
    manager.dialog_data.pop("ai_book_index", None)
    logger.info("Кэш поиска очищен для нового запроса")


async def on_ai_search_more(
    callback: CallbackQuery,
    widget: SwitchTo,
    manager: DialogManager,
) -> None:
    """Добавляем текущие книги в excluded для поиска ещё"""
    logger.info("Нажата кнопка 'Найти ещё' в ИИ поиске")
    
    current_results = manager.dialog_data.get("ii_search_results", [])
    if current_results:
        excluded = manager.dialog_data.setdefault("excluded_books", [])
        for book in current_results:
            title = book.get("title", "").strip() if isinstance(book, dict) else book.title
            if title not in excluded:
                excluded.append(title)
        
        # Ограничиваем размер
        if len(excluded) > 15:
            excluded[:] = excluded[-15:]
        
        logger.info(f"Исключили {len(current_results)} книг, всего исключено: {len(excluded)}")
    
    # Сбрасываем кэш результатов
    manager.dialog_data.pop("ii_search_results", None)
    manager.dialog_data.pop("ii_search_error", None)
    manager.dialog_data.pop("ai_book_index", None)

    await callback.message.delete()


async def on_ai_search(
    message: Message,
    widget: ManagedTextInput,
    manager: DialogManager,
    text: str
) -> None:
    """Обработчик ввода поиска для ИИ"""
    # Очищаем старые результаты поиска при новом запросе
    manager.dialog_data.pop("ii_search_query", None)
    manager.dialog_data.pop("ii_search_results", None)
    manager.dialog_data.pop("ii_search_error", None)
    manager.dialog_data.pop("ai_book_index", None)
    
    # Переходим к окну со списком результатов
    current_state = manager.current_context().state
    group_class = current_state.group
    target_state = getattr(group_class, "list_books")
    await manager.switch_to(target_state)
    