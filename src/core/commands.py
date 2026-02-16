import logging
from typing import Literal

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)

from src.core.config import settings

logger = logging.getLogger(__name__)

user_commands = [
    BotCommand(command="start", description="Старт"),
]

admin_commands = user_commands + [
    BotCommand(command="users", description="Admin command"),
]


def _is_missing_private_chat_error(err: Exception) -> bool:
    text = str(err).lower()
    needles = [
        "chat not found",
        "forbidden",
        "bot was blocked by the user",
        "user is deactivated",
        "peer_id_invalid",
    ]
    return any(needle in text for needle in needles)


async def _safe_delete_commands(bot: Bot, scope, note: str) -> None:
    try:
        await bot.delete_my_commands(scope=scope)
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        if _is_missing_private_chat_error(e):
            logger.warning("Skip delete commands for %s: %s", note, e)
        else:
            raise


async def _safe_set_commands(bot: Bot, scope, commands, note: str) -> None:
    try:
        await bot.set_my_commands(commands, scope=scope)
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        if _is_missing_private_chat_error(e):
            logger.warning("Skip set commands for %s: %s", note, e)
        else:
            raise


async def set_default_commands(bot: Bot):
    admins = settings.admin_ids

    await _safe_delete_commands(bot, BotCommandScopeDefault(), "default")
    await _safe_delete_commands(bot, BotCommandScopeAllPrivateChats(), "all_private")
    await _safe_delete_commands(bot, BotCommandScopeAllGroupChats(), "all_groups")

    for admin_id in admins:
        scope = BotCommandScopeChat(chat_id=admin_id)
        await _safe_delete_commands(bot, scope, f"admin_chat:{admin_id}")

    await _safe_set_commands(bot, BotCommandScopeDefault(), user_commands, "default")
    await _safe_set_commands(bot, BotCommandScopeAllPrivateChats(), user_commands, "all_private")
    await _safe_set_commands(bot, BotCommandScopeAllGroupChats(), user_commands, "all_groups")

    for admin_id in admins:
        scope = BotCommandScopeChat(chat_id=admin_id)
        await _safe_set_commands(bot, scope, admin_commands, f"admin_chat:{admin_id}")

    logger.info("Commands loaded. Admin-specific commands applied where chats exist.")


async def set_user_commands(bot: Bot, user_id: int, mode: Literal["admin", "default"]):
    logger.info(f"Обновляем команды для пользователя {user_id} {mode}")
    if mode == "admin":
        scope = BotCommandScopeChat(chat_id=user_id)
        await _safe_set_commands(bot, scope, admin_commands, f"admin_chat:{user_id}")

    elif mode == "default":
        scope = BotCommandScopeChat(chat_id=user_id)
        await _safe_delete_commands(bot, scope, f"admin_chat:{user_id}")
        await _safe_set_commands(bot, scope, user_commands, "default")
