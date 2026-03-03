from aiogram import Router

from .dialogs import router as router_dialogs
from .handlers import router as router_handlers

router = Router(name=__name__)

router.include_router(router_handlers)
router.include_router(router_dialogs)
