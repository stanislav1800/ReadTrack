import logging
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Select, SwitchTo, Toggle
from sqlalchemy.exc import IntegrityError

from src.book_tracking.database.models import ReadingStatus
from src.book_tracking.database.uow import BookUnitOfWork
from src.core.commands import set_user_commands
from src.database.engine import async_session_maker
from src.users.database.models import Users
from src.users.database.uow import UserUnitOfWork

logger = logging.getLogger()


async def on_book_selected(
    c: CallbackQuery,
    widget: Select[Any],
    manager: DialogManager,
    selected_id: str,
) -> None:
    manager.dialog_data["book_id"] = selected_id
    await manager.next()


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

async def on_add_to_list(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
) -> None:
    current_user: Users | None =manager.middleware_data.get("current_user")
    book_id_str = manager.dialog_data.get("book_id")
    if not book_id_str:
        await callback.answer("Книга не выбрана", show_alert=True)
        return

    try:
        book_id = int(book_id_str)
    except ValueError:
        logger.error(f"Некорректный book_id: {book_id_str}")
        await callback.answer("Ошибка: неверный ID книги", show_alert=True)
        return

    user_id = current_user.id
    if not user_id:
        await callback.answer("Не удалось определить пользователя", show_alert=True)
        return

    async with BookUnitOfWork(async_session_maker) as uow:
        try:
            # Проверка на существование — защита от race condition
            exists = await uow.user_book.get_by_filters(user_id=user_id, book_id=book_id)
            if exists:
                await callback.answer("Книга уже в вашем списке", show_alert=True)
                # Сразу скрываем кнопку при повторном рендере
                manager.dialog_data["book_added"] = True
                await manager.update(data={"book_added": True})
                return

            await uow.user_book.add({
                "user_id": user_id,
                "book_id": book_id,
                "status": ReadingStatus.planned,
                "minutes_read": None,
            })
            await uow.commit()

            # Успех → ставим флаг и обновляем интерфейс
            manager.dialog_data["book_added"] = True
            await callback.answer("Книга добавлена в «Планирую прочитать»", show_alert=True)

            # Перерисовываем текущее окно без кнопки
            manager.show_mode = ShowMode.EDIT

        except IntegrityError:
            await uow.rollback()
            await callback.answer("Книга уже добавлена", show_alert=True)
            manager.dialog_data["book_added"] = True
            manager.show_mode = ShowMode.EDIT

        except Exception:
            await uow.rollback()
            logger.exception("Ошибка при добавлении книги в список")
            await callback.answer("Произошла ошибка. Попробуйте позже", show_alert=True)


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
