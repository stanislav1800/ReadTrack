import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from src.core.filters import IsSuperuser
from src.users import states
from src.users.database.schemas import UserSchema

logger = logging.getLogger()
router = Router(name=__name__)


@router.message(CommandStart(), IsSuperuser())
async def admin_cmd_start(
    message: Message,
    dialog_manager: DialogManager,
    command: CommandObject,
    current_user: UserSchema,
):
    logger.info("admin")
    logger.info(current_user.__dict__)
    if command.args:
        if command.args.startswith("cmd_users"):
            user_id = command.args.split("-")[1]
            await dialog_manager.start(states.ListUsers.user_info, data={"user_id": int(user_id)})


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    dialog_manager: DialogManager,
    command: CommandObject,
    current_user: UserSchema,
):
    logger.info("user")
    logger.info(current_user.__dict__)


@router.message(Command("test_error"))
async def test_error_handler(message: Message):
    raise RuntimeError("Тестовая ошибка для проверки middleware")


@router.message(Command("users"), flags={"access": ["superuser"]})
async def cmd_users(message: Message, dialog_manager: DialogManager, command: CommandObject, current_user: UserSchema):
    logger.info(command)
    if command.args:
        if command.args.isdigit():
            logger.info(f"Передаем user_id={command.args}")
            await dialog_manager.start(states.ListUsers.user_info, data={"user_id": int(command.args)})

        elif command.args.startswith("@"):
            username = command.args.replace("@", "")
            logger.info(f"Передаем username={username}")
            await dialog_manager.start(states.ListUsers.user_info, data={"username": username})

        else:
            logger.info(f"Передаем query={command.args}")
            await dialog_manager.start(states.ListUsers.list_users, data={"query": command.args})

    else:
        await dialog_manager.start(states.ListUsers.list_users, mode=StartMode.RESET_STACK)
