import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram_dialog import setup_dialogs
from aiohttp import BasicAuth

from src.core.config import settings
from src.core.infrastructure.redis_client import get_redis
from src.core.middleware import (
    AccessByFlagsMiddleware,
    AuthenticationMiddleware,
    ErrorReportingMiddleware,
    UserBlockMiddleware,
    VerificationMiddleware,
)
from src.users.router import router as users_router

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    return Bot(
        token=settings.telegram_token,
        session=AiohttpSession(settings.get_proxy()),
        # session=create_session(),
        default=DefaultBotProperties(
            parse_mode=settings.parse_mode,
            protect_content=settings.protect_content,
        ),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=get_storage())

    setup_middlewares(dp)
    setup_routers(dp)
    setup_dialogs(dp)

    return dp


def setup_routers(dp: Dispatcher) -> Dispatcher:
    dp.include_routers(
        users_router,
    )


def setup_middlewares(dp: Dispatcher) -> Dispatcher:
    # dp.errors.middleware(ErrorReportingMiddleware(settings.admin_ids))
    dp.message.outer_middleware(AuthenticationMiddleware(settings.show_auth_users))
    dp.callback_query.outer_middleware(AuthenticationMiddleware(settings.show_auth_users))
    # dp.message.middleware(VerificationMiddleware())
    # dp.callback_query.middleware(VerificationMiddleware())
    dp.message.middleware(AccessByFlagsMiddleware(settings.show_alert))
    dp.callback_query.middleware(AccessByFlagsMiddleware(settings.show_alert))
    dp.update.middleware(UserBlockMiddleware())
    return dp


def create_session() -> AiohttpSession:
    proxy = None
    if settings.proxy_url:
        logger.info(f"Задаем прокси {settings.proxy_url}")
        logger.info(settings.proxy_user)
        logger.info(settings.proxy_password)
        proxy_auth = BasicAuth(settings.proxy_user, settings.proxy_password)
        proxy = (settings.proxy_url, proxy_auth)
    return AiohttpSession(proxy)


def get_storage() -> RedisStorage | MemoryStorage:
    if settings.redis_url:
        return RedisStorage(
            redis=get_redis(),
            key_builder=DefaultKeyBuilder(
                with_bot_id=True,
                with_destiny=True,
            ),
        )
    return MemoryStorage()
