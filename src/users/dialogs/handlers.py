import logging

from aiogram.types import Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, Select

from src.core.commands import set_user_commands
from src.database.engine import async_session_maker
from src.users.database.uow import UserUnitOfWork

logger = logging.getLogger()


async def selected_user_id(message: Message, widget: Select, manager: DialogManager, items_id: str):
    manager.dialog_data.update(user_id=int(items_id))
    await manager.next()


async def input_search_data(message: Message, widget: ManagedTextInput, manager: DialogManager, data: str):
    await manager.done(result={"query": data})


async def reset_search(message: Message, widget: Button, manager: DialogManager):
    await manager.done(result={"query": None})


async def update_superuser_or_verified(message: Message, widget: Button, manager: DialogManager):
    field = widget.widget_id.replace("update_", "")
    user_id = manager.dialog_data.get("user_id")
    async with UserUnitOfWork(async_session_maker) as uow:
        user = await uow.users.get(user_id)
        field_data = getattr(user, field)
        await uow.users.update(user_id, {field: not field_data})
        await uow.commit()


async def update_superuser(message: Message, widget: Button, manager: DialogManager):
    user_id = manager.dialog_data.get("user_id")
    async with UserUnitOfWork(async_session_maker) as uow:
        user = await uow.users.get(user_id)
        user = await uow.users.update(user_id, {"is_superuser": not user.is_superuser})

        mode = "default"
        if user.is_superuser:
            mode = "admin"

        await set_user_commands(message.bot, user.telegram_id, mode)
        await uow.commit()


async def on_start(start_data: dict, result: dict | None, manager: DialogManager):
    logger.info(f"Предобработка {manager}")
    if result and type(result) is dict:
        logger.info(f"{result=}")
        manager.dialog_data.update(**result)

    if start_data and type(start_data) is dict:
        logger.info(f"{start_data=}")
        manager.dialog_data.update(**start_data)
