import logging
import traceback
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.dispatcher.flags import get_flag
from aiogram.types import CallbackQuery, ErrorEvent, Message, TelegramObject, Update, User

from src.core.config import settings
from src.database.engine import async_session_maker
from src.users.database.models import Users
from src.users.database.uow import UserUnitOfWork

logger = logging.getLogger()


class AuthenticationMiddleware(BaseMiddleware):
    """
    Middleware, который:
    1. Получает информацию о пользователе из события
    2. Ищет пользователя в базе по telegram_id
    3. Если пользователя нет → создаёт новую запись
    4. Сохраняет объект пользователя в data['current_user']

    Используется практически для всех входящих сообщений/колбэков.
    """

    def __init__(self, show_auth_users: bool = True, admin_ids: list = []):
        self.show_auth_users = show_auth_users
        self.admin_ids = admin_ids

    async def __call__(
        self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]], event: Message, data: dict[str, Any]
    ) -> Any:
        logger.info("AuthenticationMiddleware")
        logger.info(event)
        logger.info(handler)
        logger.info(data)
        inner_event = get_event(event)
        user = None
        if isinstance(inner_event, (Message, CallbackQuery)) and inner_event.from_user:
            user: User = inner_event.from_user

        if user is None:
            return await handler(event, data)

        async with UserUnitOfWork(async_session_maker) as uow:
            current_user = await uow.users.get(user.id)
            if current_user is None:
                current_user = await uow.users.add(
                    {
                        "telegram_id": user.id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                    }
                )
                await uow.commit()
                logger.info(f"Новый пользователь {current_user} зашел в бота")

                if self.show_auth_users:
                    bot: Bot = data["bot"]
                    user_bot: User = await bot.me()

                    link = (
                        f'<a href="https://t.me/{user_bot.username}?start=cmd_users-{user.id}">'
                        f"{user.username or user.id}</a>"
                    )
                    message = f"{link} зашел в бота."
                    for admin_id in settings.admin_ids:
                        await bot.send_message(admin_id, message, parse_mode="html")

        data["current_user"] = current_user
        result = await handler(event, data)
        return result


class VerificationMiddleware(BaseMiddleware):
    """
    Middleware, который блокирует доступ неверифицированным пользователям.

    Проверяет поле `is_verified` у пользователя из data['current_user'].
    Если `is_verified == False` → обработка прерывается (ничего не возвращается → хендлер не вызывается).
    """

    async def __call__(
        self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]], event: Message, data: dict[str, Any]
    ) -> Any:
        logger.info("VerificationMiddleware")
        current_user: Users = data.get("current_user")
        if current_user is None:
            return await handler(event, data)

        if current_user.is_verified:
            result = await handler(event, data)
            return result

        logger.warning(f"Неверефицированный пользователь {current_user} пытается получить доступ к боту")


class ErrorReportingMiddleware(BaseMiddleware):
    """
    Middleware для перехвата и отправки ошибок администраторам.

    Ловит исключения, произошедшие в хендлерах или других middleware.
    Формирует сообщение с кратким traceback и отправляет его всем указанным admin_ids.
    """

    def __init__(self, admin_ids: list[int]) -> None:
        self.admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[ErrorEvent, dict[str, Any]], Awaitable[Any]],
        event: ErrorEvent,
        data: dict[str, Any],
    ) -> Any:
        try:
            error_message = f"An error occurred:: {event.exception}"

            traceback_info = traceback.format_exc()
            shortened_traceback = "\n".join(traceback_info.splitlines()[-5:])

            details = f"Details:\n\n{shortened_traceback}"
            full_message = f"{error_message}\n\n{details}"

            bot: Bot = data["bot"]
            for admin_id in self.admin_ids:
                await bot.send_message(admin_id, full_message)

        except Exception as e:
            logger.error(e)

        return await handler(event, data)


class UserBlockMiddleware(BaseMiddleware):
    """
    Middleware для отслеживания блокировки/разблокировки бота пользователем.

    Реагирует на событие my_chat_member (изменение статуса бота в чате с пользователем).
    При статусе "kicked" → помечает пользователя как неактивного (is_active=False)
    При возвращении в "member" → возвращает is_active=True
    """

    async def __call__(self, handler, event: TelegramObject, data: dict):
        if hasattr(event, "my_chat_member") and event.my_chat_member:
            logger.info("UserBlockMiddleware")
            user: User = event.my_chat_member.from_user
            new_status = event.my_chat_member.new_chat_member.status

            async with UserUnitOfWork(async_session_maker) as uow:
                if new_status == "kicked":
                    await uow.users.update(user.id, {"is_active": False})
                    logger.info(f"[BLOCK] User {user.id} blocked bot")
                elif new_status == "member":
                    await uow.users.update(user.id, {"is_active": True})
                    logger.info(f"[UNBLOCK] User {user.id} unblocked bot")
                await uow.commit()

        return await handler(event, data)


class AccessByFlagsMiddleware(BaseMiddleware):
    """
    Middleware контроля доступа на основе флагов хендлера.

    Читает флаг `access` из data (обычно задаётся через @flags(access=...)).
    Поддерживаемые форматы:
        flags(access="superuser")           → требуется is_superuser
        flags(access="verified")            → требуется is_verified
        flags(access=["superuser", "verified"])  → требуется хотя бы один из списка (OR)

    Если нужных прав нет → отправляет сообщение "Доступ запрещён" и прерывает обработку.
    """

    def __init__(self, show_alert: bool = True):
        self.show_alert = show_alert

    async def __call__(self, handler, event: TelegramObject, data: dict):
        logger.info("AccessByFlagsMiddleware")
        required_flags = get_flag(data, "access", default=[])
        logger.info(required_flags)

        if not required_flags:
            return await handler(event, data)

        current_user: Users = data.get("current_user")

        user_has = {
            "superuser": current_user.is_superuser,
            "verified": current_user.is_verified,
            # в будущем: "moderator": db_user.is_moderator, ...
        }

        has_access = any(user_has.get(flag_name, False) for flag_name in required_flags)

        if has_access:
            return await handler(event, data)

        return await self._deny(event)

    async def _deny(self, event: TelegramObject):
        text = "🚫 Доступ запрещён.\nУ вас недостаточно прав для выполнения этой команды."

        if self.show_alert:
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)


def get_event(event: TelegramObject):
    inner_event = event
    if isinstance(event, Update):
        inner_event = (
            event.message
            or event.callback_query
            or event.my_chat_member
            or event.chat_member
            or event.chat_join_request
        ) or event
    return inner_event
