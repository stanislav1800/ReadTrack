import logging

from aiogram_dialog import DialogManager
from sqlalchemy import or_, select

from src.core.config import settings
from src.database.engine import async_session_maker
from src.users.database.models import Users
from src.users.database.uow import UserUnitOfWork

logger = logging.getLogger()


async def update_dialog_data(dialog_manager: DialogManager):
    if dialog_manager.start_data:
        logger.info(f"Получаем данные из start_data={dialog_manager.start_data}")
        dialog_manager.dialog_data.update(**dialog_manager.start_data)
        dialog_manager.start_data.clear()


async def get_list_users(dialog_manager: DialogManager, **kwargs):
    await update_dialog_data(dialog_manager)

    query = dialog_manager.dialog_data.get("query")
    stmt = select(Users)

    if query:
        if query.isdigit():
            stmt = stmt.where(Users.telegram_id == int(query))
        else:
            query = query.replace("@", "").strip()
            stmt = stmt.where(
                or_(
                    Users.username.ilike(f"%{query}%"),
                    Users.first_name.ilike(f"%{query}%"),
                    Users.last_name.ilike(f"%{query}%"),
                )
            )

        stmt = stmt.order_by(Users.created_at.desc())

    async with UserUnitOfWork(async_session_maker) as uow:
        users = await uow.users.execute(stmt)
        await uow.commit()

    return {"users": users}


async def get_user(dialog_manager: DialogManager, **kwargs):
    await update_dialog_data(dialog_manager)

    filters = {}
    if "user_id" in dialog_manager.dialog_data:
        user_id = dialog_manager.dialog_data.get("user_id")
        filters["telegram_id"] = int(user_id)

    elif "username" in dialog_manager.dialog_data:
        username = dialog_manager.dialog_data.get("username")
        filters["username"] = username

    async with UserUnitOfWork(async_session_maker) as uow:
        user = await uow.users.get_by_filters(**filters)
        await uow.commit()

    return {"user": user}
