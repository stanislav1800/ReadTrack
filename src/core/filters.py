import logging

from aiogram.filters import Filter
from aiogram.types import Message

from src.core.config import settings
from src.users.database.schemas import UserSchema

logger = logging.getLogger()


class IsSuperuser(Filter):
    async def __call__(self, message: Message, **data) -> bool:
        current_user: UserSchema = data.get("current_user")
        logger.info(f"IsSuperuser {current_user}")
        if not current_user:
            return False
        return current_user.is_superuser


class IsVerified(Filter):
    async def __call__(self, message: Message, **data) -> bool:
        current_user: UserSchema = data.get("current_user")
        if not current_user:
            return False
        return current_user.is_verified
